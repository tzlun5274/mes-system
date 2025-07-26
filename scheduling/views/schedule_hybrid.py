from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from ..models import OrderMain, ProductionSafetySettings, Event
from ..hybrid_algorithms import (
    hybrid_scheduling_algorithm,
    validate_hybrid_schedule,
    get_scheduling_statistics,
    group_orders_by_priority,
)
from ..utils import log_user_operation
import logging
import requests
import traceback
from scheduling.scheduling_models import ScheduleWarning

logger = logging.getLogger("scheduling.views")
TAIWAN_TZ = ZoneInfo("Asia/Taipei")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def schedule_hybrid(request):
    """混合式排程主視圖"""

    if request.method == "POST":
        with open("/tmp/schedule_hybrid_view.log", "a") as f:
            f.write(
                f"進入 schedule_hybrid view, user: {request.user.username}, time: {datetime.now()}\n"
            )
        try:
            # 獲取排程參數
            include_urgent = request.POST.get("include_urgent", "true") == "true"
            include_normal = request.POST.get("include_normal", "true") == "true"
            include_flexible = request.POST.get("include_flexible", "true") == "true"
            clear_old_schedule = (
                request.POST.get("clear_old_schedule", "false") == "true"
            )

            # 處理最大訂單數量（可選）
            max_orders_str = request.POST.get("max_orders", "").strip()
            max_orders = None
            if max_orders_str:
                try:
                    max_orders = int(max_orders_str)
                    if max_orders <= 0:
                        max_orders = None
                except ValueError:
                    max_orders = None

            # 清理舊的混合排程事件
            deleted_events_count = 0
            if clear_old_schedule:
                try:
                    # 刪除舊的混合排程事件
                    old_events = Event.objects.filter(
                        classNames__contains="hybrid", created_by=request.user.username
                    )
                    deleted_events_count = old_events.count()
                    old_events.delete()

                    logger.info(f"清理了 {deleted_events_count} 個舊的混合排程事件")

                    log_user_operation(
                        username=request.user.username,
                        module="scheduling",
                        action=f"清理舊混合排程事件：{deleted_events_count} 個",
                        ip_address=request.META.get("REMOTE_ADDR"),
                    )

                except Exception as e:
                    logger.error(f"清理舊排程事件失敗: {str(e)}")
                    # 不中斷排程，繼續執行

            # 獲取有效訂單
            orders = OrderMain.objects.filter(
                qty_remain__gt=0, product_id__startswith="PFP-"
            )
            if not orders.exists():
                return JsonResponse(
                    {"status": "error", "message": "沒有可用的訂單進行排程"}, status=400
                )

            # 按組過濾訂單
            groups = group_orders_by_priority(orders)
            selected_orders = []

            if include_urgent and "urgent" in groups:
                if max_orders:
                    selected_orders.extend(groups["urgent"].orders[: max_orders // 3])
                else:
                    selected_orders.extend(groups["urgent"].orders)
            if include_normal and "normal" in groups:
                if max_orders:
                    selected_orders.extend(groups["normal"].orders[: max_orders // 3])
                else:
                    selected_orders.extend(groups["normal"].orders)
            if include_flexible and "flexible" in groups:
                if max_orders:
                    selected_orders.extend(groups["flexible"].orders[: max_orders // 3])
                else:
                    selected_orders.extend(groups["flexible"].orders)

            if not selected_orders:
                return JsonResponse(
                    {"status": "error", "message": "沒有符合條件的訂單"}, status=400
                )

            # 獲取必要數據
            processes, operators, equipments, smt_equipments = get_scheduling_data(
                request
            )

            # 執行混合排程
            tasks, error, suggestion = hybrid_scheduling_algorithm(
                selected_orders, processes, operators, equipments, smt_equipments
            )

            if error:
                return JsonResponse(
                    {"status": "error", "message": error, "suggestion": suggestion},
                    status=500,
                )

            # 驗證排程結果
            validation_errors = validate_hybrid_schedule(tasks)
            if validation_errors:
                logger.warning(f"排程驗證發現 {len(validation_errors)} 個問題")

            # 每次排程前先清空舊的警告
            ScheduleWarning.objects.all().delete()
            # 將每個警告寫入資料表
            for warn in validation_errors:
                # 嘗試自動解析訂單編號與工序名稱
                order_id = ""
                process_name = ""
                # 常見格式："作業員 XXX 時間衝突: 任務 1 (2025-06-25 08:00-10:00) 與任務 2 (2025-06-25 09:00-11:00)"
                # 或 "訂單 12345 工序 SMT ..."
                import re

                m = re.search(r"訂單\s*(\d+)", warn)
                if m:
                    order_id = m.group(1)
                m2 = re.search(r"工序\s*([\w\u4e00-\u9fa5]+)", warn)
                if m2:
                    process_name = m2.group(1)
                ScheduleWarning.objects.create(
                    order_id=order_id, process_name=process_name, warning_message=warn
                )

            # 創建排程事件
            created_events = []
            for task in tasks:
                try:
                    event = Event.objects.create(
                        title=f"混合排程: {task['process']['name']} - 訂單 {task['order_id']}",
                        unit=None,
                        start=datetime.strptime(
                            task["start_time"], "%Y-%m-%dT%H:%M"
                        ).replace(tzinfo=TAIWAN_TZ),
                        end=datetime.strptime(
                            task["end_time"], "%Y-%m-%dT%H:%M"
                        ).replace(tzinfo=TAIWAN_TZ),
                        type="production",
                        description=task["description"],
                        classNames="production hybrid",
                        all_day=False,
                        category="general",
                        created_by=request.user.username,
                        employee_id=(
                            task["selected_operator"]["id"]
                            if task["selected_operator"]
                            else None
                        ),
                        equipment_id=(
                            task["selected_equipment"]["id"]
                            if task["selected_equipment"]
                            else None
                        ),
                        smt_equipment_id=(
                            task["selected_smt_equipment"]["id"]
                            if task["selected_smt_equipment"]
                            else None
                        ),
                        order_id=str(task["order_id"]),
                    )
                    created_events.append(event)

                    log_user_operation(
                        username=request.user.username,
                        module="scheduling",
                        action=f"創建混合排程事件：{event.title} (ID: {event.id})",
                        ip_address=request.META.get("REMOTE_ADDR"),
                        event_related=event,
                    )

                except Exception as e:
                    logger.error(f"創建事件失敗: {str(e)}")
                    continue

            # 獲取統計信息
            stats = get_scheduling_statistics(tasks)

            # 若有部分訂單失敗，回傳詳細清單
            if (
                suggestion
                and isinstance(suggestion, dict)
                and suggestion.get("failed_orders")
            ):
                failed_orders = suggestion["failed_orders"]
                # 只保留每個產品編號一筆
                product_failed = {}
                for oid, (reason, sug) in failed_orders.items():
                    order_obj = OrderMain.objects.filter(id=oid).first()
                    product_id = order_obj.product_id if order_obj else str(oid)
                    if product_id not in product_failed:
                        product_failed[product_id] = {
                            "order_id": oid,
                            "product_id": product_id,
                            "reason": reason,
                            "suggestion": sug,
                        }
                failed_list = list(product_failed.values())
                return JsonResponse(
                    {
                        "status": "partial_success",
                        "message": f"部分訂單無法生成，成功創建 {len(created_events)} 個排程事件",
                        "failed_orders": failed_list,
                        "created_events_count": len(created_events),
                        "statistics": stats,
                        "validation_errors": validation_errors,
                        "deleted_events_count": deleted_events_count,
                        "clear_old_schedule": clear_old_schedule,
                    }
                )

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"混合排程完成！成功創建 {len(created_events)} 個排程事件",
                    "statistics": stats,
                    "validation_errors": validation_errors,
                    "created_events_count": len(created_events),
                    "deleted_events_count": deleted_events_count,
                    "clear_old_schedule": clear_old_schedule,
                }
            )

        except Exception as e:
            logger.error(f"混合排程失敗: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse(
                {"status": "error", "message": f"混合排程失敗: {str(e)}"}, status=500
            )

    # GET 請求：顯示排程頁面
    try:
        # 獲取訂單統計
        orders = OrderMain.objects.filter(
            qty_remain__gt=0, product_id__startswith="PFP-"
        )
        groups = group_orders_by_priority(orders)

        group_stats = {}
        for group_name, group in groups.items():
            group_stats[group_name] = {
                "count": len(group.orders),
                "total_qty": sum(order.qty_remain for order in group.orders),
                "avg_qty": (
                    sum(order.qty_remain for order in group.orders) / len(group.orders)
                    if group.orders
                    else 0
                ),
            }

        # 獲取系統數據
        processes, operators, equipments, smt_equipments = get_scheduling_data(request)

        log_user_operation(
            username=request.user.username,
            module="scheduling",
            action="訪問混合排程頁面",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        return render(
            request,
            "scheduling/schedule_hybrid.html",
            {
                "group_stats": group_stats,
                "total_orders": orders.count(),
                "processes_count": len(processes),
                "operators_count": len(operators),
                "equipments_count": len(equipments),
                "smt_equipments_count": len(smt_equipments),
                "group_orders": {k: v.orders for k, v in groups.items()},
            },
        )

    except Exception as e:
        logger.error(f"混合排程頁面渲染失敗: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, f"頁面載入失敗: {str(e)}")
        return render(
            request,
            "scheduling/schedule_hybrid.html",
            {
                "group_stats": {},
                "total_orders": 0,
                "processes_count": 0,
                "operators_count": 0,
                "equipments_count": 0,
                "smt_equipments_count": 0,
            },
        )


def get_scheduling_data(request):
    """獲取排程所需的數據"""
    processes = []
    operators = []
    equipments = []
    smt_equipments = []

    try:
        # 獲取工序數據
        process_response = requests.get(
            "http://localhost:8000/process/api/process_names/",
            cookies={"sessionid": request.COOKIES.get("sessionid", "")},
            timeout=10,
        )
        if process_response.status_code == 200:
            processes = process_response.json().get("process_names", [])
        else:
            logger.error(f"無法獲取工序數據，狀態碼: {process_response.status_code}")

        # 獲取作業員數據
        operator_response = requests.get(
            "http://localhost:8000/process/api/operators/",
            cookies={"sessionid": request.COOKIES.get("sessionid", "")},
            timeout=10,
        )
        if operator_response.status_code == 200:
            operators = operator_response.json().get("operators", [])
        else:
            logger.error(f"無法獲取作業員數據，狀態碼: {operator_response.status_code}")

        # 獲取設備數據
        equipment_response = requests.get(
            "http://localhost:8000/equip/api/equipments/",
            cookies={"sessionid": request.COOKIES.get("sessionid", "")},
            timeout=10,
        )
        if equipment_response.status_code == 200:
            equipments = equipment_response.json().get("equipments", [])
        else:
            logger.error(f"無法獲取設備數據，狀態碼: {equipment_response.status_code}")

        # 獲取SMT設備數據
        smt_equipment_response = requests.get(
            "http://localhost:8000/smt_equipment/api/smt_equipments/",
            cookies={"sessionid": request.COOKIES.get("sessionid", "")},
            timeout=10,
        )
        if smt_equipment_response.status_code == 200:
            smt_equipments = smt_equipment_response.json().get("smt_equipments", [])
        else:
            logger.error(
                f"無法獲取SMT設備數據，狀態碼: {smt_equipment_response.status_code}"
            )

    except Exception as e:
        logger.error(f"獲取排程數據失敗: {str(e)}")

    return processes, operators, equipments, smt_equipments


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def hybrid_scheduling_preview(request):
    """混合排程預覽"""
    try:
        # 獲取預覽參數
        max_orders_str = request.GET.get("max_orders", "").strip()
        max_orders = None
        if max_orders_str:
            try:
                max_orders = int(max_orders_str)
                if max_orders <= 0:
                    max_orders = None
            except ValueError:
                max_orders = None

        include_urgent = request.GET.get("include_urgent", "true") == "true"
        include_normal = request.GET.get("include_normal", "true") == "true"
        include_flexible = request.GET.get("include_flexible", "true") == "true"

        # 獲取訂單
        orders = OrderMain.objects.filter(
            qty_remain__gt=0, product_id__startswith="PFP-"
        )
        groups = group_orders_by_priority(orders)

        selected_orders = []
        if include_urgent and "urgent" in groups:
            if max_orders:
                selected_orders.extend(groups["urgent"].orders[: max_orders // 3])
            else:
                selected_orders.extend(groups["urgent"].orders)
        if include_normal and "normal" in groups:
            if max_orders:
                selected_orders.extend(groups["normal"].orders[: max_orders // 3])
            else:
                selected_orders.extend(groups["normal"].orders)
        if include_flexible and "flexible" in groups:
            if max_orders:
                selected_orders.extend(groups["flexible"].orders[: max_orders // 3])
            else:
                selected_orders.extend(groups["flexible"].orders)

        # 獲取數據
        processes, operators, equipments, smt_equipments = get_scheduling_data(request)

        # 執行預覽排程
        tasks, error, suggestion = hybrid_scheduling_algorithm(
            selected_orders, processes, operators, equipments, smt_equipments
        )

        if error:
            return JsonResponse({"status": "error", "message": error}, status=500)

        # 獲取統計信息
        stats = get_scheduling_statistics(tasks)

        return JsonResponse(
            {
                "status": "success",
                "preview_data": {
                    "tasks_count": len(tasks),
                    "orders_count": len(selected_orders),
                    "statistics": stats,
                    "sample_tasks": (
                        tasks[:5] if tasks else []
                    ),  # 只返回前5個任務作為預覽
                },
            }
        )

    except Exception as e:
        logger.error(f"混合排程預覽失敗: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": f"預覽失敗: {str(e)}"}, status=500
        )


def schedule_warning_board(request):
    """
    排程警告看板：顯示所有排程驗證警告
    """
    warnings = ScheduleWarning.objects.all()
    return render(
        request, "scheduling/schedule_warning_board.html", {"warnings": warnings}
    )
