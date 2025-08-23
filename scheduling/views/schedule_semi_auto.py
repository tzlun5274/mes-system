from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from ..models import OrderMain, ProductionSafetySettings, Event
from ..semi_auto_algorithms import generate_semi_auto_tasks, set_global_schedule_time
from ..utils import check_holiday_conflicts, log_user_operation
import logging
import requests
import traceback
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger("scheduling.views")
TAIWAN_TZ = ZoneInfo("Asia/Taipei")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def schedule_semi_auto(request):
    def handle_error_response(
        request,
        orders,
        processes,
        operators,
        equipments,
        smt_equipments,
        selected_order_id,
        mode,
        error_message,
        log_level="error",
    ):
        if log_level == "error":
            logger.error(error_message)
        elif log_level == "warning":
            logger.warning(error_message)
        messages.error(request, error_message)
        return render(
            request,
            "scheduling/schedule_semi_auto.html",
            {
                "orders": orders,
                "processes": processes,
                "operators": operators,
                "equipments": equipments,
                "smt_equipments": smt_equipments,
                "selected_order_id": selected_order_id,
                "mode": mode,
                "tasks": [],
                "show_semi_auto_form": False,
                "order_qty": 0,
            },
        )

    if request.method == "POST":
        try:
            # 支援多訂單
            order_ids = request.POST.getlist("order_id")
            confirm_holiday = request.POST.get("confirm_holiday", "false") == "true"
            tasks = []
            for key in request.POST:
                if key.startswith("tasks["):
                    index = int(key.split("[")[1].split("]")[0])
                    if len(tasks) <= index:
                        tasks.append({})
                    task_field = key.split("[")[2].split("]")[0]
                    tasks[index][task_field] = request.POST[key]
            # 讓每個 task 都有 order_id
            for t in tasks:
                if "order_id" not in t:
                    t["order_id"] = (
                        request.POST.get("order_id")
                        if isinstance(request.POST.get("order_id"), str)
                        else (
                            request.POST.getlist("order_id")[0]
                            if request.POST.getlist("order_id")
                            else None
                        )
                    )
                # 解析 overtime 為布林值
                t["overtime"] = str(t.get("overtime", "")).lower() in [
                    "on",
                    "true",
                    "1",
                ]
                # 保存分批資訊
                t["splits"] = []
                split_prefix = f"tasks[{tasks.index(t)}][splits]"
                for key in request.POST:
                    if key.startswith(split_prefix):
                        split_index = int(key.split("[")[3].split("]")[0])
                        split_field = key.split("[")[4].split("]")[0]
                        if len(t["splits"]) <= split_index:
                            t["splits"].append({})
                        t["splits"][split_index][split_field] = request.POST[key]

            # 依 order_id 分組
            tasks_by_order = {}
            for t in tasks:
                oid = t.get("order_id")
                if not oid:
                    continue
                if oid not in tasks_by_order:
                    tasks_by_order[oid] = []
                tasks_by_order[oid].append(t)
            # 驗證每個訂單分攤數量
            for oid, tlist in tasks_by_order.items():
                order = OrderMain.objects.filter(id=oid).first()
                if not order:
                    messages.error(request, _(f"訂單 {oid} 不存在"))
                    return JsonResponse(
                        {"status": "error", "message": f"訂單 {oid} 不存在"}, status=404
                    )
                order_qty = order.qty_remain
                for idx, task in enumerate(tlist):
                    # 檢查分批數量總和是否等於訂單數量
                    total_split_qty = sum(
                        int(split.get("split_qty", 0))
                        for split in task.get("splits", [])
                    )
                    if total_split_qty != order_qty:
                        pname = task.get("process_name", f"步驟{idx+1}")
                        messages.error(
                            request,
                            _(
                                f"訂單 {order.product_id} 第{idx+1}道工序（{pname}）分批數量總和必須等於訂單未出數量"
                            ),
                        )
                        return JsonResponse(
                            {
                                "status": "error",
                                "message": f"訂單 {order.product_id} 第{idx+1}道工序（{pname}）分批數量總和必須等於訂單未出數量",
                            },
                            status=400,
                        )

            # 建立事件
            for t in tasks:
                oid = t.get("order_id")
                order = OrderMain.objects.filter(id=oid).first()
                process_id = t.get("process_id")
                description = t.get("description", "")
                splits = t.get("splits", [])

                if not process_id:
                    messages.error(request, _(f"訂單 {oid} 任務缺少工序 ID"))
                    return JsonResponse(
                        {"status": "error", "message": f"訂單 {oid} 任務缺少工序 ID"},
                        status=400,
                    )

                process_response = requests.get(
                    "http://localhost:8000/process/api/process_names/",
                    cookies={"sessionid": request.COOKIES.get("sessionid", "")},
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
                process = next(
                    (p for p in processes if p["id"] == int(process_id)), None
                )
                if not process:
                    messages.error(request, _(f"訂單 {oid} 無效的工序 ID"))
                    return JsonResponse(
                        {"status": "error", "message": f"訂單 {oid} 無效的工序 ID"},
                        status=400,
                    )

                # 為每個分批創建事件
                for split in splits:
                    try:
                        start_time = split.get("start_time")
                        end_time = split.get("end_time")
                        split_qty = split.get("split_qty")
                        operator_id = split.get("operator_id")
                        equipment_id = split.get("equipment_id")
                        smt_equipment_id = split.get("smt_equipment_id")

                        if not all([start_time, end_time, split_qty]):
                            messages.error(request, _(f"訂單 {oid} 分批缺少必要欄位"))
                            return JsonResponse(
                                {
                                    "status": "error",
                                    "message": f"訂單 {oid} 分批缺少必要欄位",
                                },
                                status=400,
                            )

                        start_datetime = datetime.strptime(
                            start_time, "%Y-%m-%dT%H:%M"
                        ).replace(tzinfo=TAIWAN_TZ)
                        end_datetime = datetime.strptime(
                            end_time, "%Y-%m-%dT%H:%M"
                        ).replace(tzinfo=TAIWAN_TZ)
                        split_qty = int(split_qty)

                        event = Event.objects.create(
                            title=f"生產任務: {order.product_name} - {process['name']} (分批)",
                            unit=None,
                            start=start_datetime,
                            end=end_datetime,
                            type="production",
                            description=f"{description} (分批數量: {split_qty})",
                            classNames="production",
                            all_day=False,
                            category="general",
                            created_by=request.user.username,
                            employee_id=operator_id or None,
                            equipment_id=equipment_id or None,
                            smt_equipment_id=smt_equipment_id or None,
                            order_id=str(oid),
                        )
                        log_user_operation(
                            username=request.user.username,
                            module="scheduling",
                            action=f"創建半自動排程分批事件：{event.title} (ID: {event.id}, 分批數量: {split_qty})",
                            ip_address=request.META.get("REMOTE_ADDR"),
                            event_related=event,
                        )
                    except ValueError as e:
                        messages.error(request, _(f"訂單 {oid} 時間格式或數量無效"))
                        return JsonResponse(
                            {"status": "error", "message": str(e)}, status=400
                        )

            messages.success(request, _("生產任務創建成功"))
            return JsonResponse({"status": "success", "message": "生產任務創建成功"})
        except Exception as e:
            logger.error(f"創建半自動排程失敗: {str(e)}\n{traceback.format_exc()}")
            messages.error(request, _("創建生產任務失敗"))
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    try:
        orders = OrderMain.objects.filter(
            qty_remain__gt=0, product_id__startswith="PFP-"
        )
        if not orders.exists():
            logger.warning("無符合條件的訂單")
            messages.warning(request, _("無可用訂單，請檢查訂單數據"))
            return handle_error_response(
                request,
                [],
                [],
                [],
                [],
                [],
                None,
                "semi_auto",
                error_message="無可用訂單，請檢查訂單數據",
                log_level="warning",
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
                except ValueError as e:
                    logger.warning(
                        f"訂單 {order.id} 的 pre_in_date 格式無效: {order.pre_in_date}, 錯誤: {str(e)}"
                    )
                    continue
            else:
                valid_orders.append(order)

        process_response = requests.get(
            "http://localhost:8000/process/api/process_names/",
            cookies={"sessionid": request.COOKIES.get("sessionid", "")},
            timeout=10,
        )
        if process_response.status_code != 200:
            logger.error(f"無法獲取工序數據，狀態碼: {process_response.status_code}")
            return handle_error_response(
                request,
                valid_orders,
                [],
                [],
                [],
                [],
                None,
                "semi_auto",
                error_message="無法獲取工序數據，請聯繫管理員",
            )
        processes = process_response.json().get("process_names", [])

        operator_response = requests.get(
            "http://localhost:8000/process/api/operators/",
            cookies={"sessionid": request.COOKIES.get("sessionid", "")},
            timeout=10,
        )
        if operator_response.status_code != 200:
            logger.error(f"無法獲取作業員數據，狀態碼: {operator_response.status_code}")
            messages.warning(request, _("無法獲取作業員數據，請聯繫管理員"))
        operators = operator_response.json().get("operators", [])

        equipment_response = requests.get(
            "http://localhost:8000/equip/api/equipments/",
            cookies={"sessionid": request.COOKIES.get("sessionid", "")},
            timeout=10,
        )
        if equipment_response.status_code != 200:
            logger.error(f"無法獲取設備數據，狀態碼: {equipment_response.status_code}")
            messages.warning(request, _("無法獲取設備數據，請聯繫管理員"))
        equipments = equipment_response.json().get("equipments", [])

        smt_equipment_response = requests.get(
            "http://localhost:8000/smt_equipment/api/smt_equipments/",
            cookies={"sessionid": request.COOKIES.get("sessionid", "")},
            timeout=10,
        )
        if smt_equipment_response.status_code != 200:
            logger.error(
                f"無法獲取 SMT 設備數據，狀態碼: {smt_equipment_response.status_code}"
            )
            messages.warning(request, _("無法獲取 SMT 設備數據，請聯繫管理員"))
        smt_equipments = smt_equipment_response.json().get("smt_equipments", [])

        order_id = request.GET.get("order_id")
        selected_order_id = int(order_id) if order_id and order_id.isdigit() else None
        tasks = []
        order = None

        # 取得 overtime 狀態（從 GET 參數）
        overtime_list = []
        idx = 0
        while True:
            key = f"tasks_overtime_{idx}"
            if key in request.GET:
                overtime_list.append(request.GET.get(key) in ["on", "true", "1"])
                idx += 1
            else:
                break

        # 取得分批資訊（從 GET 參數）
        saved_splits = []
        idx = 0
        while True:
            splits = []
            split_idx = 0
            while True:
                split_prefix = f"tasks[{idx}][splits][{split_idx}]"
                split_data = {}
                for key in request.GET:
                    if key.startswith(split_prefix):
                        field = key.split("]")[-1][1:]  # 提取欄位名稱
                        split_data[field] = request.GET[key]
                if not split_data:
                    break
                splits.append(split_data)
                split_idx += 1
            if not splits:
                break
            saved_splits.append(splits)
            idx += 1

        if selected_order_id:
            logger.info(
                f"[重新計算] 觸發半自動排程，order_id={selected_order_id}，user={request.user.username}"
            )
            order = next((o for o in valid_orders if o.id == selected_order_id), None)
            if order:
                try:
                    routes_response = requests.get(
                        "http://localhost:8000/process/api/product_routes/",
                        params={"product_id": order.product_id},
                        cookies={"sessionid": request.COOKIES.get("sessionid", "")},
                        timeout=10,
                    )
                    logger.debug(
                        f"產品路線 API 響應狀態碼: {routes_response.status_code}"
                    )
                    if routes_response.status_code != 200:
                        logger.error(
                            f"無法獲取產品路線，狀態碼: {routes_response.status_code}"
                        )
                        return handle_error_response(
                            request,
                            valid_orders,
                            processes,
                            operators,
                            equipments,
                            smt_equipments,
                            selected_order_id,
                            "semi_auto",
                            error_message="無法獲取產品路線",
                        )
                    all_routes = routes_response.json().get("product_routes", [])
                    matched_routes = [
                        route
                        for route in all_routes
                        if route["product_id"] == order.product_id
                    ]
                    logger.debug(f"匹配的產品路線數量: {len(matched_routes)}")
                    matched_routes.sort(key=lambda x: x["step_order"])

                    if not matched_routes:
                        logger.warning(f"訂單 {order.id} 未找到匹配的產品路線")
                        return handle_error_response(
                            request,
                            valid_orders,
                            processes,
                            operators,
                            equipments,
                            smt_equipments,
                            selected_order_id,
                            "semi_auto",
                            error_message=f"訂單 {order.id} 無產品路線，請設定產品路線",
                            log_level="warning",
                        )

                    global_schedule_time = current_time.replace(
                        hour=8, minute=30, second=0, microsecond=0
                    )
                    if global_schedule_time < current_time:
                        global_schedule_time += timedelta(days=1)
                    set_global_schedule_time(global_schedule_time)

                    # 若 overtime_list 長度不足，補 False
                    while len(overtime_list) < len(matched_routes):
                        overtime_list.append(False)

                    # 呼叫 generate_semi_auto_tasks 時傳遞 overtime_list
                    tasks, reason, suggestion = generate_semi_auto_tasks(
                        order=order,
                        processes=processes,
                        operators=operators,
                        equipments=equipments,
                        smt_equipments=smt_equipments,
                        matched_routes=matched_routes,
                        overtime_list=overtime_list,
                    )
                    logger.debug(
                        f"生成任務數量: {len(tasks)}, 原因: {reason}, 建議: {suggestion}"
                    )

                    # 如果有保存的分批資訊，將其添加到對應的任務中
                    if saved_splits:
                        for task, splits in zip(tasks, saved_splits):
                            task["splits"] = splits

                    if reason:
                        logger.error(f"生成任務失敗: {reason}")
                        return handle_error_response(
                            request,
                            valid_orders,
                            processes,
                            operators,
                            equipments,
                            smt_equipments,
                            selected_order_id,
                            "semi_auto",
                            error_message=reason,
                        )
                except requests.RequestException as e:
                    logger.error(
                        f"獲取產品路線失敗: {str(e)}\n{traceback.format_exc()}"
                    )
                    return handle_error_response(
                        request,
                        valid_orders,
                        processes,
                        operators,
                        equipments,
                        smt_equipments,
                        selected_order_id,
                        "semi_auto",
                        error_message="獲取產品路線失敗，請檢查網路連接",
                    )

        return render(
            request,
            "scheduling/schedule_semi_auto.html",
            {
                "orders": valid_orders,
                "processes": processes,
                "operators": operators,
                "equipments": equipments,
                "smt_equipments": smt_equipments,
                "selected_order_id": selected_order_id,
                "mode": "semi_auto",
                "tasks": tasks,
                "show_semi_auto_form": bool(tasks),
                "order_qty": order.qty_remain if order else 0,
                "all_operators_json": json.dumps(operators),
                "all_equipments_json": json.dumps(equipments),
                "all_smt_equipments_json": json.dumps(smt_equipments),
            },
        )

    except Exception as e:
        logger.error(f"半自動排程頁面載入失敗: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, _("頁面載入失敗"))
        return handle_error_response(
            request,
            [],
            [],
            [],
            [],
            [],
            None,
            "semi_auto",
            error_message="頁面載入失敗，請聯繫管理員",
        )


@csrf_exempt
@require_POST
def recalc_log_api(request):
    order_id = request.POST.get("order_id")
    user = (
        request.user.username
        if hasattr(request, "user") and request.user.is_authenticated
        else "anonymous"
    )
    logger.info(f"[recalcBtn] 重新計算觸發，order_id={order_id}，user={user}")
    return JsonResponse({"status": "success", "message": "recalc log ok"})
