print("schedule_auto.py 被載入")
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from ..models import OrderMain, ProductionSafetySettings, Event
from ..algorithms import (
    check_holiday_conflicts,
    generate_auto_tasks,
    generate_optimized_auto_tasks,
)
import logging
import requests
import traceback

logger = logging.getLogger("scheduling.views")
TAIWAN_TZ = ZoneInfo("Asia/Taipei")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def schedule_auto(request):
    if request.method == "POST":
        try:
            # 獲取排程參數
            confirm_holiday = request.POST.get("confirm_holiday", "false") == "true"
            use_optimized = request.POST.get("use_optimized", "true") == "true"
            max_orders = request.POST.get("max_orders", "")
            clear_old_schedule = (
                request.POST.get("clear_old_schedule", "false") == "true"
            )

            # 清理舊的排程事件
            deleted_events_count = 0
            if clear_old_schedule:
                deleted_events = Event.objects.filter(
                    type="production", created_by=request.user.username
                ).delete()
                deleted_events_count = deleted_events[0] if deleted_events[0] else 0

            # 獲取訂單
            orders = OrderMain.objects.filter(
                qty_remain__gt=0, product_id__startswith="PFP-"
            )
            if not orders.exists():
                messages.error(request, _("無可用訂單"))
                return JsonResponse(
                    {"status": "error", "message": "無可用訂單"}, status=400
                )

            # 限制訂單數量
            if max_orders and max_orders.isdigit():
                orders = orders[: int(max_orders)]

            safety_settings = ProductionSafetySettings.objects.first()
            safety_days = (
                safety_settings.delivery_to_completion_safety_days
                if safety_settings
                else 3
            )
            current_time = datetime.now(TAIWAN_TZ)

            # 過濾有效訂單
            valid_orders = []
            for order in orders:
                if order.pre_in_date and order.pre_in_date != "N/A":
                    try:
                        pre_in_date_dt = datetime.strptime(
                            order.pre_in_date, "%Y-%m-%d"
                        ).replace(tzinfo=TAIWAN_TZ)
                        if current_time <= pre_in_date_dt - timedelta(days=safety_days):
                            valid_orders.append((order, pre_in_date_dt))
                    except ValueError as e:
                        logger.warning(
                            f"訂單 {order.id} 的 pre_in_date 格式無效: {order.pre_in_date}, 錯誤: {str(e)}"
                        )
                        continue
                else:
                    valid_orders.append((order, None))

            if not valid_orders:
                messages.error(request, _("無符合交期條件的訂單"))
                return JsonResponse(
                    {"status": "error", "message": "無符合交期條件的訂單"}, status=400
                )

            # 按交期排序
            valid_orders.sort(
                key=lambda x: x[1] if x[1] else datetime.max.replace(tzinfo=TAIWAN_TZ)
            )
            orders = [order for order, _ in valid_orders]

            cookies = {"sessionid": request.COOKIES.get("sessionid", "")}

            # 獲取資源數據
            process_response = requests.get(
                "http://localhost:8000/process/api/process_names/",
                cookies=cookies,
                timeout=10,
            )
            if process_response.status_code != 200:
                logger.error(
                    f"無法獲取工序數據，狀態碼: {process_response.status_code}"
                )
                return JsonResponse(
                    {"status": "error", "message": "無法獲取工序數據"}, status=500
                )
            processes = process_response.json().get("process_names", [])

            operator_response = requests.get(
                "http://localhost:8000/process/api/operators/",
                cookies=cookies,
                timeout=10,
            )
            if operator_response.status_code != 200:
                logger.error(
                    f"無法獲取作業員數據，狀態碼: {operator_response.status_code}"
                )
                return JsonResponse(
                    {"status": "error", "message": "無法獲取作業員數據"}, status=500
                )
            operators = operator_response.json().get("operators", [])

            equipment_response = requests.get(
                "http://localhost:8000/equip/api/equipments/",
                cookies=cookies,
                timeout=10,
            )
            if equipment_response.status_code != 200:
                logger.error(
                    f"無法獲取設備數據，狀態碼: {equipment_response.status_code}"
                )
                return JsonResponse(
                    {"status": "error", "message": "無法獲取設備數據"}, status=500
                )
            equipments = equipment_response.json().get("equipments", [])

            smt_equipment_response = requests.get(
                "http://localhost:8000/smt_equipment/api/smt_equipments/",
                cookies=cookies,
                timeout=10,
            )
            if smt_equipment_response.status_code != 200:
                logger.error(
                    f"無法獲取 SMT 設備數據，狀態碼: {smt_equipment_response.status_code}"
                )
                return JsonResponse(
                    {"status": "error", "message": "無法獲取 SMT 設備數據"}, status=500
                )
            smt_equipments = smt_equipment_response.json().get("smt_equipments", [])

            all_tasks = []
            failed_orders = {}

            if use_optimized:
                # 使用優化算法
                routes_by_order = {}
                for order in orders:
                    routes_response = requests.get(
                        "http://localhost:8000/process/api/product_routes/",
                        params={"product_id": order.product_id},
                        cookies=cookies,
                        timeout=10,
                    )
                    if routes_response.status_code != 200:
                        failed_orders[order.id] = (
                            f"無法獲取產品工序路線數據: 狀態碼={routes_response.status_code}",
                            "請檢查工序管理中的產品工序路線設定",
                        )
                        continue

                    all_routes = routes_response.json().get("product_routes", [])
                    matched_routes = [
                        route
                        for route in all_routes
                        if route["product_id"] == order.product_id
                    ]
                    if not matched_routes:
                        failed_orders[order.id] = (
                            f"產品 {order.product_id} 未設定工藝路線",
                            "請在工序管理中設定產品工藝路線",
                        )
                        continue

                    routes_by_order[order.id] = matched_routes

                # 生成優化排程
                all_tasks, additional_failed_orders = generate_optimized_auto_tasks(
                    orders=[order for order in orders if order.id not in failed_orders],
                    processes=processes,
                    operators=operators,
                    equipments=equipments,
                    smt_equipments=smt_equipments,
                    routes_by_order=routes_by_order,
                    current_time=current_time,
                )
                failed_orders.update(additional_failed_orders)

            else:
                # 使用原始算法
                for order in orders:
                    routes_response = requests.get(
                        "http://localhost:8000/process/api/product_routes/",
                        params={"product_id": order.product_id},
                        cookies=cookies,
                        timeout=10,
                    )
                    if routes_response.status_code != 200:
                        failed_orders[order.id] = (
                            f"無法獲取產品工序路線數據: 狀態碼={routes_response.status_code}",
                            "請檢查工序管理中的產品工序路線設定",
                        )
                        continue

                    all_routes = routes_response.json().get("product_routes", [])
                    matched_routes = [
                        route
                        for route in all_routes
                        if route["product_id"] == order.product_id
                    ]
                    if not matched_routes:
                        failed_orders[order.id] = (
                            f"產品 {order.product_id} 未設定工藝路線",
                            "請在工序管理中設定產品工藝路線",
                        )
                        continue

                    matched_routes.sort(key=lambda x: x["step_order"])
                    tasks, reason, suggestion = generate_auto_tasks(
                        order=order,
                        processes=processes,
                        operators=operators,
                        equipments=equipments,
                        smt_equipments=smt_equipments,
                        matched_routes=matched_routes,
                    )

                    # 防呆：確保 tasks 一定是 list
                    if not tasks:
                        tasks = []
                    if reason:
                        failed_orders[order.id] = (reason, suggestion)
                        continue

                    if not confirm_holiday:
                        holiday_conflicts = check_holiday_conflicts(tasks)
                        if holiday_conflicts:
                            return JsonResponse(
                                {
                                    "status": "holiday_conflict",
                                    "message": "以下任務與放假日衝突，是否確認？",
                                    "conflicts": holiday_conflicts,
                                    "tasks": tasks,
                                    "order_id": order.id,
                                },
                                status=400,
                            )

                    all_tasks.extend(tasks)

            # 創建事件
            created_events_count = 0
            if not all_tasks:
                all_tasks = []
            for task in all_tasks:
                start_datetime = datetime.strptime(
                    task["start_time"], "%Y-%m-%dT%H:%M"
                ).replace(tzinfo=TAIWAN_TZ)
                end_datetime = datetime.strptime(
                    task["end_time"], "%Y-%m-%dT%H:%M"
                ).replace(tzinfo=TAIWAN_TZ)
                order = OrderMain.objects.filter(id=task.get("order_id")).first()
                process_name = task["process"]["name"]

                Event.objects.create(
                    title=f"產品 {order.product_name} - {process_name}",
                    unit=None,
                    start=start_datetime,
                    end=end_datetime,
                    type="production",
                    description=task.get("description"),
                    classNames="production",
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
                    order_id=str(task.get("order_id")),
                )
                created_events_count += 1

            # 回傳失敗訂單詳細資訊
            if failed_orders:
                # 只保留每個產品編號一筆
                product_failed = {}
                for oid, (reason, suggestion) in failed_orders.items():
                    order_obj = OrderMain.objects.filter(id=oid).first()
                    product_id = order_obj.product_id if order_obj else str(oid)
                    if product_id not in product_failed:
                        product_failed[product_id] = {
                            "order_id": oid,
                            "product_id": product_id,
                            "reason": reason,
                            "suggestion": suggestion,
                        }
                failed_list = list(product_failed.values())
                return JsonResponse(
                    {
                        "status": "partial_success",
                        "message": f"部分訂單無法生成，成功創建 {created_events_count} 個事件 (使用優化算法)",
                        "failed_orders": failed_list,
                        "created_events_count": created_events_count,
                    }
                )

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"成功創建 {created_events_count} 個事件 (使用優化算法)",
                    "created_events_count": created_events_count,
                }
            )

        except Exception as e:
            logger.error(f"全自動排程失敗: {str(e)}")
            messages.error(request, _("全自動排程失敗"))
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    try:
        orders = OrderMain.objects.filter(
            qty_remain__gt=0, product_id__startswith="PFP-"
        )
        safety_settings = ProductionSafetySettings.objects.first()
        safety_days = (
            safety_settings.delivery_to_completion_safety_days if safety_settings else 3
        )
        current_time = datetime.now(TAIWAN_TZ)
        valid_orders = []
        for order in orders:
            if order.pre_in_date and order.pre_in_date != "N/A":
                try:
                    pre_in_date_dt = datetime.strptime(
                        order.pre_in_date, "%Y-%m-%d"
                    ).replace(tzinfo=TAIWAN_TZ)
                    if current_time <= pre_in_date_dt - timedelta(days=safety_days):
                        valid_orders.append(order)
                except ValueError:
                    continue
            else:
                valid_orders.append(order)

        context = {
            "orders": valid_orders,
            "total_orders": len(valid_orders),
            "safety_days": safety_days,
        }
        return render(request, "scheduling/schedule_auto.html", context)
    except Exception as e:
        logger.error(f"處理 /scheduling/schedule_auto/ 請求時發生錯誤: {str(e)}")
        messages.error(request, _("無法加載全自動排程頁面"))
        return render(request, "scheduling/schedule_auto.html", {"error": str(e)})
