import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.paginator import Paginator
from .models import (
    WorkOrder,
    PrdMKOrdMain,
    SystemConfig,
    CompanyOrder,
    WorkOrderProcess,
    WorkOrderProcessLog,
    WorkOrderAssignment,
    DispatchLog,
)
from .tasks import get_standard_processes
from .forms import WorkOrderForm
from django.contrib import messages
from reporting.models import ProductionDailyReport
from datetime import datetime, timedelta, timezone as dt_timezone, date
from django.db import models
import psycopg2
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.utils import timezone

from process.models import (
    ProductProcessRoute,
    ProcessEquipment,
    Operator,
    OperatorSkill,
    ProcessName,
    ProductProcessStandardCapacity,
)
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from equip.models import Equipment
from django.contrib.auth.decorators import login_required, user_passes_test
from collections import defaultdict
from django.views.decorators.http import require_POST
from django import forms
from django.conf import settings
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views import View
import json
from django.views.decorators.csrf import ensure_csrf_cookie

# 設定工單管理模組的日誌記錄器
workorder_logger = logging.getLogger("workorder")
workorder_handler = logging.FileHandler("/var/log/mes/workorder.log")
workorder_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
workorder_logger.addHandler(workorder_handler)
workorder_logger.setLevel(logging.INFO)

# Create your views here.


# 工單列表
def index(request):
    workorders = WorkOrder.objects.all().order_by("-created_at")
    context = {
        "workorders": workorders,
        "is_debug": settings.DEBUG,  # 傳遞是否為測試環境
    }
    return render(request, "workorder/workorder/workorder_list.html", context)


# 新增工單
def create(request):
    error = None
    if request.method == "POST":
        form = WorkOrderForm(request.POST)
        if form.is_valid():
            company_code = form.cleaned_data["company_code"]
            order_number = form.cleaned_data["order_number"]
            # 檢查公司代號+工單編號是否重複
            if WorkOrder.objects.filter(
                company_code=company_code, order_number=order_number
            ).exists():
                error = "公司代號＋工單編號已存在，不能重複新增！"
            else:
                workorder = form.save()
                # 新增成功後自動導向工序明細頁面
                return redirect(
                    reverse("workorder:workorder_process_detail", args=[workorder.id])
                )
    else:
        form = WorkOrderForm()
    return render(
        request, "workorder/workorder/workorder_form.html", {"form": form, "error": error}
    )


@csrf_exempt
@require_GET
def get_company_order_info(request):
    """
    AJAX 視圖：根據產品編號取得公司製令單資訊
    回傳工單號與數量
    """
    product_id = request.GET.get("product_id")
    company_code = request.GET.get("company_code")

    if not product_id:
        return JsonResponse({"status": "error", "message": "請提供產品編號"})

    try:
        # 查詢公司製令單
        query = CompanyOrder.objects.filter(product_id=product_id, is_converted=False)
        if company_code:
            query = query.filter(company_code=company_code)

        company_order = query.first()

        if company_order:
            return JsonResponse(
                {
                    "status": "success",
                    "data": {
                        "mkordno": company_order.mkordno,
                        "prodt_qty": company_order.prodt_qty,
                        "company_code": company_order.company_code,
                    },
                }
            )
        else:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"找不到產品編號 {product_id} 的未轉換製令單",
                }
            )

    except Exception as e:
        return JsonResponse({"status": "error", "message": f"查詢失敗：{str(e)}"})


# 編輯工單
def edit(request, pk):
    workorder = get_object_or_404(WorkOrder, pk=pk)
    if request.method == "POST":
        form = WorkOrderForm(request.POST, instance=workorder)
        if form.is_valid():
            form.save()
            return redirect(reverse("workorder:index"))
    else:
        form = WorkOrderForm(instance=workorder)
    return render(
        request, "workorder/workorder/workorder_form.html", {"form": form, "edit_mode": True}
    )


# 刪除工單
def delete(request, pk):
    workorder = get_object_or_404(WorkOrder, pk=pk)
    if request.method == "POST":
        try:
            # 直接刪除工單（會自動刪除相關的工序）
            workorder.delete()
            messages.success(request, "工單刪除成功！")
            return redirect(reverse("workorder:index"))
            
        except Exception as e:
            messages.error(request, f"刪除工單時發生錯誤：{str(e)}")
            return redirect(reverse("workorder:index"))
            
    return render(
        request, "workorder/workorder_confirm_delete.html", {"workorder": workorder}
    )


# 刪除所有未派工工單（支援 all=1 參數時同時刪除已派工工單）
def delete_pending_workorders(request):
    """
    刪除所有未派工工單（狀態為 pending）
    若帶有 ?all=1 參數，則同時刪除已派工工單（狀態為 in_progress）
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:index")

    delete_all = request.GET.get("all") == "1"

    if request.method == "POST":
        try:
            if delete_all:
                # 同時刪除 pending 和 in_progress
                pending_count = WorkOrder.objects.filter(status="pending").count()
                in_progress_count = WorkOrder.objects.filter(status="in_progress").count()
                
                # 刪除工單
                WorkOrder.objects.filter(status__in=["pending", "in_progress"]).delete()
                
                messages.success(
                    request,
                    f"成功刪除所有工單！共刪除 {pending_count + in_progress_count} 個工單（待生產：{pending_count}，生產中：{in_progress_count}）"
                )
            else:
                # 只刪除 pending
                pending_count = WorkOrder.objects.filter(status="pending").count()
                
                # 刪除工單
                WorkOrder.objects.filter(status="pending").delete()
                
                messages.success(
                    request, 
                    f"成功刪除所有未派工工單！共刪除 {pending_count} 個工單"
                )
            return redirect("workorder:dispatch_list")
        except Exception as e:
            messages.error(request, f"刪除工單時發生錯誤：{str(e)}")
            return redirect("workorder:dispatch_list")

    # GET 請求顯示確認頁面
    pending_count = WorkOrder.objects.filter(status="pending").count()
    in_progress_count = (
        WorkOrder.objects.filter(status="in_progress").count() if delete_all else 0
    )
    return render(
        request,
        "workorder/delete_pending_confirm.html",
        {
            "pending_count": pending_count,
            "in_progress_count": in_progress_count,
            "delete_all": delete_all,
        },
    )


# 刪除所有已派工工單
def delete_in_progress_workorders(request):
    """
    刪除所有已派工工單（狀態為 in_progress），支援 AJAX 回傳 JSON
    """
    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.content_type == "application/json"
        or request.headers.get("Accept") == "application/json"
    )
    if not (request.user.is_staff or request.user.is_superuser):
        msg = "只有管理員可以執行此操作"
        if is_ajax:
            return JsonResponse({"status": "danger", "message": msg})
        messages.error(request, msg)
        return redirect("workorder:index")

    if request.method == "POST":
        try:
            in_progress_count = WorkOrder.objects.filter(status="in_progress").count()
            WorkOrder.objects.filter(status="in_progress").update(status="pending")
            msg = f"成功停止所有生產中工單！共處理 {in_progress_count} 個工單"
            if is_ajax:
                return JsonResponse({"status": "success", "message": msg})
            messages.success(request, msg)
            return redirect("workorder:dispatch_list")
        except Exception as e:
            msg = f"停止所有生產中工單時發生錯誤：{str(e)}"
            if is_ajax:
                return JsonResponse({"status": "danger", "message": msg})
            messages.error(request, msg)
            return redirect("workorder:dispatch_list")

    # GET 請求顯示確認頁面
    in_progress_count = WorkOrder.objects.filter(status="in_progress").count()
    return render(
        request,
        "workorder/delete_in_progress_confirm.html",
        {"in_progress_count": in_progress_count},
    )





# 派工單管理頁（可重用原本工單列表）
def dispatch_list(request):
    """
    派工單管理頁：分成待生產（pending）和已派工（in_progress）兩個區塊
    並提供每個工單的補登記錄數量與待核准數量
    包含所有類型的工單：正式生產、PP試產(330-)、重工(339-)等
    """
    from process.models import ProductProcessRoute

    # 顯示所有狀態的工單，包括 pending、in_progress、completed 等
    all_orders = WorkOrder.objects.all().order_by("-created_at")
    
    # 按狀態分組
    pending_orders = [order for order in all_orders if order.status == "pending"]
    in_progress_orders = [order for order in all_orders if order.status == "in_progress"]
    completed_orders = [order for order in all_orders if order.status == "completed"]
    other_orders = [order for order in all_orders if order.status not in ["pending", "in_progress", "completed"]]

    # 計算統計數據
    total_workorders = WorkOrder.objects.count()
    pending_count = len(pending_orders)
    in_progress_count = len(in_progress_orders)
    completed_count = len(completed_orders)
    other_count = len(other_orders)
    
    # 計算工藝路線已設定總數
    process_route_set_count = 0
    # 計算分配資訊已分配總數
    assignment_set_count = 0
    
    # 檢查所有工單的工藝路線和分配狀態
    all_workorders = WorkOrder.objects.all()
    for workorder in all_workorders:
        # 檢查工藝路線設定
        has_process_route = ProductProcessRoute.objects.filter(
            product_id=workorder.product_code
        ).exists()
        if has_process_route:
            process_route_set_count += 1
            
        # 檢查分配資訊
        has_assignment = (
            WorkOrderProcess.objects.filter(workorder=workorder)
            .filter(
                models.Q(assigned_operator__isnull=False, assigned_operator__gt="")
                | models.Q(assigned_equipment__isnull=False, assigned_equipment__gt="")
            )
            .exists()
        )
        if has_assignment:
            assignment_set_count += 1

    # 檢查每個工單的工序設定狀態和分配資訊
    for order in list(pending_orders) + list(in_progress_orders):
        order.has_process_route = ProductProcessRoute.objects.filter(
            product_id=order.product_code
        ).exists()
        # 新增：檢查工序明細裡有沒有分配作業員或設備
        order.has_assignment = (
            WorkOrderProcess.objects.filter(workorder=order)
            .filter(
                models.Q(assigned_operator__isnull=False, assigned_operator__gt="")
                | models.Q(assigned_equipment__isnull=False, assigned_equipment__gt="")
            )
            .exists()
        )
        # 移除 has_process_detail 與 process_configured 判斷，回復只看 has_process_route
        # 只有同時有工藝路線且有工序明細才算「已設定」
        # order.process_configured = order.has_process_route and order.has_process_detail
        # 預載入分配資訊
        order.workorderassignment_set.all()

        # 計算作業員工作負載
        for assignment in order.workorderassignment_set.all():
            if assignment.operator_id:
                assignment.operator_current_load = WorkOrderAssignment.objects.filter(
                    operator_id=assignment.operator_id, workorder__status="in_progress"
                ).count()

            # 添加設備名稱屬性
            if assignment.equipment_id:
                try:
                    equipment = Equipment.objects.get(id=assignment.equipment_id)
                    assignment.equipment_name = equipment.name
                except (Equipment.DoesNotExist, ValueError):
                    assignment.equipment_name = f"未知設備({assignment.equipment_id})"
            else:
                assignment.equipment_name = "未分配"

    return render(
        request,
        "workorder/dispatch/dispatch_list.html",
        {
            "pending_orders": pending_orders,
            "in_progress_orders": in_progress_orders,
            "completed_orders": completed_orders,
            "other_orders": other_orders,
            "total_workorders": total_workorders,
            "pending_count": pending_count,
            "in_progress_count": in_progress_count,
            "completed_count": completed_count,
            "other_count": other_count,
            "process_route_set_count": process_route_set_count,
            "assignment_set_count": assignment_set_count,
        },
    )


# 公司製令單列表（依公司分群）
def company_orders(request):
    """
    公司製令單列表：顯示所有公司 MES 資料庫的 ERP 製令單，工單號前加公司代號，不分公司顯示
    只顯示未結案的製令單（BillStatus=1）
    """
    from erp_integration.models import CompanyConfig

    companies = CompanyConfig.objects.all()
    search = request.GET.get("search", "").strip()
    sort = request.GET.get("sort", "")
    status = request.GET.get("status", "")

    # 讀取目前自動轉換工單間隔設定（預設 30 分鐘）
    auto_convert_interval = 30
    try:
        config = SystemConfig.objects.get(key="auto_convert_interval")
        auto_convert_interval = int(config.value)
    except SystemConfig.DoesNotExist:
        pass
    # 讀取自動同步製令間隔（預設 30 分鐘）
    auto_sync_companyorder_interval = 30
    try:
        config = SystemConfig.objects.get(key="auto_sync_companyorder_interval")
        auto_sync_companyorder_interval = int(config.value)
    except SystemConfig.DoesNotExist:
        pass

    # 讀取不分攤關鍵字設定（預設：只計算最後一天,不分攤,不分配）
    no_distribute_keywords = "只計算最後一天,不分攤,不分配"
    try:
        config = SystemConfig.objects.get(key="no_distribute_keywords")
        no_distribute_keywords = config.value
    except SystemConfig.DoesNotExist:
        pass

    # 管理員可設定自動轉換工單間隔與自動同步製令間隔
    if request.method == "POST" and (
        request.user.is_staff or request.user.is_superuser
    ):
        if "no_distribute_keywords" in request.POST:
            new_no_distribute_keywords = request.POST.get("no_distribute_keywords")
            if new_no_distribute_keywords:
                old_value = no_distribute_keywords
                SystemConfig.objects.update_or_create(
                    key="no_distribute_keywords",
                    defaults={"value": new_no_distribute_keywords},
                )
                workorder_logger.info(
                    f"管理員 {request.user} 變更不分攤關鍵字設定，原值：{old_value}，新值：{new_no_distribute_keywords}。IP: {request.META.get('REMOTE_ADDR')}"
                )
            return redirect(request.path)
        else:
            # 原本的自動轉換/同步間隔設定
            new_convert_interval = request.POST.get("auto_convert_interval")
            if (
                new_convert_interval
                and new_convert_interval.isdigit()
                and int(new_convert_interval) > 0
            ):
                old_value = auto_convert_interval
                SystemConfig.objects.update_or_create(
                    key="auto_convert_interval",
                    defaults={"value": new_convert_interval},
                )
                workorder_logger.info(
                    f"管理員 {request.user} 變更自動轉換工單間隔，原值：{old_value} 分鐘，新值：{new_convert_interval} 分鐘。IP: {request.META.get('REMOTE_ADDR')}"
                )
                auto_convert_interval = int(new_convert_interval)
            new_sync_interval = request.POST.get("auto_sync_companyorder_interval")
            if (
                new_sync_interval
                and new_sync_interval.isdigit()
                and int(new_sync_interval) > 0
            ):
                old_value = auto_sync_companyorder_interval
                SystemConfig.objects.update_or_create(
                    key="auto_sync_companyorder_interval",
                    defaults={"value": new_sync_interval},
                )
                workorder_logger.info(
                    f"管理員 {request.user} 變更自動同步製令間隔，原值：{old_value} 分鐘，新值：{new_sync_interval} 分鐘。IP: {request.META.get('REMOTE_ADDR')}"
                )
                auto_sync_companyorder_interval = int(new_sync_interval)
    # POST 處理完後，重新查詢最新關鍵字設定
    try:
        config = SystemConfig.objects.get(key="no_distribute_keywords")
        no_distribute_keywords = config.value
    except SystemConfig.DoesNotExist:
        no_distribute_keywords = "只計算最後一天,不分攤,不分配"

    # 查詢本地 CompanyOrder 表
    workorders = CompanyOrder.objects.all()

    # 搜尋條件
    if search:
        workorders = workorders.filter(
            models.Q(company_code__icontains=search)
            | models.Q(mkordno__icontains=search)
            | models.Q(product_id__icontains=search)
        )

    # 排序條件
    if sort == "est_stock_out_date_asc":
        workorders = workorders.order_by("est_stock_out_date")
    elif sort == "est_stock_out_date_desc":
        workorders = workorders.order_by("-est_stock_out_date")
    else:
        workorders = workorders.order_by("-sync_time")

    # 計算統計數據
    total_orders = workorders.count()
    converted_orders = workorders.filter(is_converted=True).count()
    unconverted_orders = workorders.filter(is_converted=False).count()

    # 轉換成字典格式，保持與原本模板的相容性
    workorders_list = []
    for order in workorders:
        workorder_dict = {
            "MKOrdNO": f"{order.company_code}_{order.mkordno}",
            "ProductID": order.product_id,
            "ProdtQty": order.prodt_qty,
            "EstTakeMatDate": order.est_take_mat_date,
            "EstStockOutDate": order.est_stock_out_date,
            "is_converted": order.is_converted,
            "conversion_status": "已轉換" if order.is_converted else "未轉換",
        }
        workorders_list.append(workorder_dict)

    workorder_logger.info(
        f"使用者 {request.user} 檢視公司製令單列表。IP: {request.META.get('REMOTE_ADDR')}"
    )
    return render(
        request,
        "workorder/dispatch/company_orders.html",
        {
            "workorders": workorders_list,
            "companies": companies,
            "auto_convert_interval": auto_convert_interval,
            "auto_sync_companyorder_interval": auto_sync_companyorder_interval,
            "no_distribute_keywords": no_distribute_keywords,
            "total_orders": total_orders,
            "converted_orders": converted_orders,
            "unconverted_orders": unconverted_orders,
        },
    )


# 手動同步製令單
def manual_sync_orders(request):
    """
    手動同步各公司製令單到 CompanyOrder 表
    """
    if not (request.user.is_staff or request.user.is_superuser):
        workorder_logger.warning(
            f"非管理員 {request.user} 嘗試手動同步製令單，已拒絕。IP: {request.META.get('REMOTE_ADDR')}"
        )
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:company_orders")

    if request.method != "POST":
        return redirect("workorder:company_orders")

    try:
        # 執行同步命令
        call_command("sync_pending_workorders")
        workorder_logger.info(
            f"管理員 {request.user} 手動同步公司製令單成功。IP: {request.META.get('REMOTE_ADDR')}"
        )
        messages.success(request, "手動同步製令單完成！")
    except Exception as e:
        workorder_logger.error(
            f"管理員 {request.user} 手動同步公司製令單失敗：{e}。IP: {request.META.get('REMOTE_ADDR')}"
        )
        messages.error(request, f"同步失敗：{e}")

    return redirect("workorder:company_orders")


# 手動轉換工單
def manual_convert_orders(request):
    """
    手動轉換製令單為 MES 工單
    支援 AJAX 請求，回傳 JSON。
    新增：在轉換時自動分配作業員和設備
    """
    from process.models import ProductProcessRoute, ProductProcessStandardCapacity, Operator, OperatorSkill, ProcessEquipment
    from equip.models import Equipment

    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.content_type == "application/json"
        or request.headers.get("Accept") == "application/json"
    )
    if request.method != "POST":
        msg = "請用 POST 方式呼叫手動轉換"
        if is_ajax:
            return JsonResponse({"status": "danger", "message": msg})
        messages.error(request, msg)
        return redirect("workorder:company_orders")

    try:
        # 取得未轉換的製令單
        pending_orders = CompanyOrder.objects.filter(is_converted=False)
        if not pending_orders.exists():
            msg = "沒有需要轉換的製令單！"
            if is_ajax:
                return JsonResponse({"status": "warning", "message": msg})
            messages.warning(request, msg)
            return redirect("workorder:company_orders")

        count_converted = 0
        count_processes_created = 0
        count_auto_assigned = 0

        for company_order in pending_orders:
            # 檢查工單是否已存在
            existing_workorder = WorkOrder.objects.filter(
                company_code=company_order.company_code,
                order_number=company_order.mkordno
            ).first()
            
            if existing_workorder:
                # 如果工單已存在，跳過並標記為已轉換
                company_order.is_converted = True
                company_order.save()
                print(f"⚠️ 工單已存在，跳過轉換：{company_order.mkordno}")
                continue
            
            # 建立工單
            workorder = WorkOrder.objects.create(
                order_number=WorkOrder.generate_order_number(company_order.company_code),  # 自動生成工單號碼
                product_code=company_order.product_id,  # 使用 product_id
                quantity=company_order.prodt_qty,  # 使用 prodt_qty
                status="pending",
                company_code=company_order.company_code,
            )
            count_converted += 1

            # 建立工序明細
            try:
                # 從產品工藝路線取得工序資料
                routes = ProductProcessRoute.objects.filter(
                    product_id=workorder.product_code
                ).order_by("step_order")

                if routes.exists():
                    # 使用產品工藝路線建立工序明細
                    for route in routes:
                        # 查詢標準產能資料
                        capacity_data = ProductProcessStandardCapacity.objects.filter(
                            product_code=workorder.product_code,
                            process_name=route.process_name.name,
                            is_active=True
                        ).order_by('-version').first()
                        
                        # 使用標準產能或預設值
                        target_hourly_output = (
                            capacity_data.standard_capacity_per_hour 
                            if capacity_data else 1000
                        )
                        
                        # 建立工序明細
                        process = WorkOrderProcess.objects.create(
                            workorder=workorder,
                            process_name=route.process_name.name,
                            step_order=route.step_order,
                            planned_quantity=workorder.quantity,
                            target_hourly_output=target_hourly_output,
                        )
                        count_processes_created += 1

                        # ====== 自動分配作業員和設備 ======
                        assigned_operator = None
                        assigned_equipment = None

                        # 1. 自動分配作業員：根據工序名稱找到有對應技能的作業員
                        try:
                            # 找到有該工序技能的作業員
                            skilled_operators = Operator.objects.filter(
                                skills__process_name__name=route.process_name.name
                            ).distinct()
                            
                            if skilled_operators.exists():
                                # 選擇工作負載最輕的作業員
                                operator_loads = {}
                                for op in skilled_operators:
                                    # 計算該作業員目前的工作負載（進行中的工序數量）
                                    current_load = WorkOrderProcess.objects.filter(
                                        assigned_operator=op.name,
                                        status='in_progress'
                                    ).count()
                                    operator_loads[op] = current_load
                                
                                # 選擇負載最輕的作業員
                                assigned_operator = min(operator_loads.items(), key=lambda x: x[1])[0]
                                process.assigned_operator = assigned_operator.name
                                print(f"✅ 自動分配作業員：{assigned_operator.name} (工序：{route.process_name.name})")
                            else:
                                print(f"⚠️ 找不到有 {route.process_name.name} 技能的作業員")
                        except Exception as e:
                            print(f"⚠️ 分配作業員失敗：{str(e)}")

                        # 2. 自動分配設備：根據工序名稱找到可用的設備
                        try:
                            # 檢查工序是否有指定可用設備
                            if route.usable_equipment_ids:
                                # 解析可用設備ID列表
                                equipment_ids = [
                                    int(eid.strip()) 
                                    for eid in route.usable_equipment_ids.split(',') 
                                    if eid.strip().isdigit()
                                ]
                                
                                if equipment_ids:
                                    # 找到可用且狀態為閒置的設備
                                    available_equipments = Equipment.objects.filter(
                                        id__in=equipment_ids,
                                        status='idle'
                                    )
                                    
                                    if available_equipments.exists():
                                        # 選擇第一個可用設備
                                        assigned_equipment = available_equipments.first()
                                        process.assigned_equipment = assigned_equipment.name
                                        print(f"✅ 自動分配設備：{assigned_equipment.name} (工序：{route.process_name.name})")
                                    else:
                                        print(f"⚠️ 工序 {route.process_name.name} 的指定設備都不可用")
                                else:
                                    print(f"⚠️ 工序 {route.process_name.name} 的可用設備ID格式錯誤")
                            else:
                                # 如果沒有指定設備，嘗試從工序設備對應表找
                                process_equipments = ProcessEquipment.objects.filter(
                                    process_name__name=route.process_name.name
                                )
                                
                                if process_equipments.exists():
                                    equipment_ids = [pe.equipment_id for pe in process_equipments]
                                    available_equipments = Equipment.objects.filter(
                                        id__in=equipment_ids,
                                        status='idle'
                                    )
                                    
                                    if available_equipments.exists():
                                        assigned_equipment = available_equipments.first()
                                        process.assigned_equipment = assigned_equipment.name
                                        print(f"✅ 自動分配設備：{assigned_equipment.name} (工序：{route.process_name.name})")
                                    else:
                                        print(f"⚠️ 工序 {route.process_name.name} 的對應設備都不可用")
                                else:
                                    print(f"⚠️ 工序 {route.process_name.name} 沒有對應的設備設定")
                        except Exception as e:
                            print(f"⚠️ 分配設備失敗：{str(e)}")

                        # 3. 如果有分配到作業員或設備，更新狀態並記錄
                        if assigned_operator or assigned_equipment:
                            process.save()
                            count_auto_assigned += 1
                            
                            # 記錄分配日誌
                            try:
                                WorkOrderProcessLog.objects.create(
                                    workorder_process=process,
                                    action='auto_assignment',
                                    operator=assigned_operator.name if assigned_operator else None,
                                    equipment=assigned_equipment.name if assigned_equipment else None,
                                    notes=f"製令轉工單時自動分配 - 工序：{route.process_name.name}",
                                    quantity_before=0,
                                    quantity_after=0,
                                )
                            except Exception as e:
                                print(f"⚠️ 記錄分配日誌失敗：{str(e)}")

                else:
                    # 使用標準工序建立工序明細
                    standard_processes = [
                        {"name": "SMT 貼片", "target_hourly_output": 1000},
                        {"name": "測試", "target_hourly_output": 500},
                        {"name": "包裝", "target_hourly_output": 200},
                    ]

                    for step_order, process_info in enumerate(
                        standard_processes, 1
                    ):
                        WorkOrderProcess.objects.create(
                            workorder=workorder,
                            process_name=process_info["name"],
                            step_order=step_order,
                            planned_quantity=workorder.quantity,
                            target_hourly_output=process_info[
                                "target_hourly_output"
                            ],
                        )
                        count_processes_created += 1
            except Exception as e:
                # 如果建立工序明細失敗，記錄錯誤但不影響工單轉換
                print(f"建立工序明細失敗 (工單: {workorder.order_number}): {e}")

        # 更新 CompanyOrder 的轉換狀態
        if count_converted > 0:
            CompanyOrder.objects.filter(is_converted=False).update(is_converted=True)
            
            # 更新成功訊息，包含自動分配資訊
            auto_assignment_msg = f"，並自動分配 {count_auto_assigned} 個工序的作業員和設備" if count_auto_assigned > 0 else ""
            
            messages.success(
                request,
                f"手動轉換完成！共轉換 {count_converted} 筆製令單為 MES 工單，並自動建立 {count_processes_created} 個工序明細{auto_assignment_msg}",
            )
        else:
            messages.info(request, "沒有需要轉換的製令單")

        workorder_logger.info(
            f"管理員 {request.user} 手動轉換工單成功，轉換 {count_converted} 筆，建立工序 {count_processes_created} 筆，自動分配 {count_auto_assigned} 筆。IP: {request.META.get('REMOTE_ADDR')}"
        )
    except Exception as e:
        workorder_logger.error(
            f"管理員 {request.user} 手動轉換工單失敗：{e}。IP: {request.META.get('REMOTE_ADDR')}"
        )
        messages.error(request, f"轉換失敗：{e}")

    return redirect("workorder:company_orders")


# 派工單工序明細管理
def workorder_process_detail(request, workorder_id):
    """
    派工單工序明細頁面：顯示工單的所有工序及執行狀況
    """
    workorder = get_object_or_404(WorkOrder, pk=workorder_id)
    processes = WorkOrderProcess.objects.filter(workorder=workorder).order_by(
        "step_order"
    )

    # 計算整體進度
    total_planned = sum(p.planned_quantity for p in processes)
    total_completed = sum(p.completed_quantity for p in processes)
    overall_progress = round(
        (total_completed / total_planned * 100) if total_planned > 0 else 0, 2
    )

    # 檢查產品是否有工藝路線設定
    from process.models import ProductProcessRoute

    has_process_route = ProductProcessRoute.objects.filter(
        product_id=workorder.product_code
    ).exists()

    # 取得所有工序名稱供下拉選單使用
    from process.models import ProcessName
    process_names = ProcessName.objects.all().order_by('name')

    return render(
        request,
        "workorder/process/workorder_process_detail.html",
        {
            "workorder": workorder,
            "processes": processes,
            "total_planned": total_planned,
            "total_completed": total_completed,
            "overall_progress": overall_progress,
            "has_process_route": has_process_route,
            "process_names": process_names,
        },
    )


def create_workorder_processes(request, workorder_id):
    """
    為指定工單建立工序明細
    支援 AJAX 請求，回傳 JSON。
    新增：在建立工序時自動分配作業員和設備
    """
    from process.models import ProductProcessRoute, ProductProcessStandardCapacity, Operator, OperatorSkill, ProcessEquipment
    from equip.models import Equipment

    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.content_type == "application/json"
        or request.headers.get("Accept") == "application/json"
    )

    try:
        workorder = WorkOrder.objects.get(id=workorder_id)
    except WorkOrder.DoesNotExist:
        msg = "工單不存在！"
        if is_ajax:
            return JsonResponse({"status": "danger", "message": msg})
        messages.error(request, msg)
        return redirect("workorder:workorder_list")

    try:
        # 檢查是否已有工序明細
        existing_processes = WorkOrderProcess.objects.filter(workorder=workorder)
        if existing_processes.exists():
            msg = "此工單已有工序明細，無法重複建立！"
            if is_ajax:
                return JsonResponse({"status": "warning", "message": msg})
            messages.warning(request, msg)
            return redirect("workorder:workorder_process_detail", workorder_id=workorder_id)

        created_count = 0
        auto_assigned_count = 0

        # 從產品工藝路線取得工序資料
        routes = ProductProcessRoute.objects.filter(
            product_id=workorder.product_code
        ).order_by("step_order")

        if routes.exists():
            # 使用產品工藝路線建立工序明細
            for route in routes:
                # 查詢標準產能資料
                capacity_data = ProductProcessStandardCapacity.objects.filter(
                    product_code=workorder.product_code,
                    process_name=route.process_name.name,
                    is_active=True
                ).order_by('-version').first()
                
                # 使用標準產能或預設值
                target_hourly_output = (
                    capacity_data.standard_capacity_per_hour 
                    if capacity_data else 1000
                )
                
                # 建立工序明細
                process = WorkOrderProcess.objects.create(
                    workorder=workorder,
                    process_name=route.process_name.name,
                    step_order=route.step_order,
                    planned_quantity=workorder.quantity,
                    target_hourly_output=target_hourly_output,
                )
                created_count += 1

                # ====== 自動分配作業員和設備 ======
                assigned_operator = None
                assigned_equipment = None

                # 1. 自動分配作業員：根據工序名稱找到有對應技能的作業員
                try:
                    # 找到有該工序技能的作業員
                    skilled_operators = Operator.objects.filter(
                        skills__process_name__name=route.process_name.name
                    ).distinct()
                    
                    if skilled_operators.exists():
                        # 選擇工作負載最輕的作業員
                        operator_loads = {}
                        for op in skilled_operators:
                            # 計算該作業員目前的工作負載（進行中的工序數量）
                            current_load = WorkOrderProcess.objects.filter(
                                assigned_operator=op.name,
                                status='in_progress'
                            ).count()
                            operator_loads[op] = current_load
                        
                        # 選擇負載最輕的作業員
                        assigned_operator = min(operator_loads.items(), key=lambda x: x[1])[0]
                        process.assigned_operator = assigned_operator.name
                        print(f"✅ 自動分配作業員：{assigned_operator.name} (工序：{route.process_name.name})")
                    else:
                        print(f"⚠️ 找不到有 {route.process_name.name} 技能的作業員")
                except Exception as e:
                    print(f"⚠️ 分配作業員失敗：{str(e)}")

                # 2. 自動分配設備：根據工序名稱找到可用的設備
                try:
                    # 檢查工序是否有指定可用設備
                    if route.usable_equipment_ids:
                        # 解析可用設備ID列表
                        equipment_ids = [
                            int(eid.strip()) 
                            for eid in route.usable_equipment_ids.split(',') 
                            if eid.strip().isdigit()
                        ]
                        
                        if equipment_ids:
                            # 找到可用且狀態為閒置的設備
                            available_equipments = Equipment.objects.filter(
                                id__in=equipment_ids,
                                status='idle'
                            )
                            
                            if available_equipments.exists():
                                # 選擇第一個可用設備
                                assigned_equipment = available_equipments.first()
                                process.assigned_equipment = assigned_equipment.name
                                print(f"✅ 自動分配設備：{assigned_equipment.name} (工序：{route.process_name.name})")
                            else:
                                print(f"⚠️ 工序 {route.process_name.name} 的指定設備都不可用")
                        else:
                            print(f"⚠️ 工序 {route.process_name.name} 的可用設備ID格式錯誤")
                    else:
                        # 如果沒有指定設備，嘗試從工序設備對應表找
                        process_equipments = ProcessEquipment.objects.filter(
                            process_name__name=route.process_name.name
                        )
                        
                        if process_equipments.exists():
                            equipment_ids = [pe.equipment_id for pe in process_equipments]
                            available_equipments = Equipment.objects.filter(
                                id__in=equipment_ids,
                                status='idle'
                            )
                            
                            if available_equipments.exists():
                                assigned_equipment = available_equipments.first()
                                process.assigned_equipment = assigned_equipment.name
                                print(f"✅ 自動分配設備：{assigned_equipment.name} (工序：{route.process_name.name})")
                            else:
                                print(f"⚠️ 工序 {route.process_name.name} 的對應設備都不可用")
                        else:
                            print(f"⚠️ 工序 {route.process_name.name} 沒有對應的設備設定")
                except Exception as e:
                    print(f"⚠️ 分配設備失敗：{str(e)}")

                # 3. 如果有分配到作業員或設備，更新狀態並記錄
                if assigned_operator or assigned_equipment:
                    process.save()
                    auto_assigned_count += 1
                    
                    # 記錄分配日誌
                    try:
                        WorkOrderProcessLog.objects.create(
                            workorder_process=process,
                            action='auto_assignment',
                            operator=assigned_operator.name if assigned_operator else None,
                            equipment=assigned_equipment.name if assigned_equipment else None,
                            notes=f"建立工序時自動分配 - 工序：{route.process_name.name}",
                            quantity_before=0,
                            quantity_after=0,
                        )
                    except Exception as e:
                        print(f"⚠️ 記錄分配日誌失敗：{str(e)}")

            # 更新成功訊息，包含自動分配資訊
            auto_assignment_msg = f"，並自動分配 {auto_assigned_count} 個工序的作業員和設備" if auto_assigned_count > 0 else ""
            messages.success(
                request, f"成功建立 {created_count} 個工序明細（使用產品工藝路線）{auto_assignment_msg}"
            )
        else:
            # 使用標準工序建立工序明細
            standard_processes = get_standard_processes(workorder.product_code)

            for step_order, process_info in enumerate(standard_processes, 1):
                WorkOrderProcess.objects.create(
                    workorder=workorder,
                    process_name=process_info["name"],
                    step_order=step_order,
                    planned_quantity=workorder.quantity,
                    target_hourly_output=process_info["target_hourly_output"],
                )
                created_count += 1

            messages.success(
                request, f"成功建立 {created_count} 個工序明細（使用標準工序）"
            )

    except Exception as e:
        messages.error(request, f"建立工序明細失敗：{e}")

    return redirect("workorder:workorder_process_detail", workorder_id=workorder_id)


@require_GET
@csrf_exempt
def get_processes_only(request):
    """
    API：根據工單ID或工單編號回傳該工單所有工序（JSON格式），給前端 AJAX 用
    支援傳入數字型工單 id 或字串型工單編號（order_number）
    """
    workorder_id = request.GET.get("workorder_id")
    if not workorder_id:
        return JsonResponse({"success": False, "message": "缺少工單ID"})

    # 判斷傳入的是數字 id 還是工單編號
    workorder = None
    if workorder_id.isdigit():
        # 如果是數字，直接用 id 查
        try:
            workorder = WorkOrder.objects.get(id=int(workorder_id))
        except WorkOrder.DoesNotExist:
            return JsonResponse({"success": False, "message": "查無此工單"})
    else:
        # 如果是字串，改用工單編號查
        try:
            workorder = WorkOrder.objects.get(order_number=workorder_id)
        except WorkOrder.DoesNotExist:
            return JsonResponse({"success": False, "message": "查無此工單編號"})

    # 查詢該工單的所有工序
    processes = WorkOrderProcess.objects.filter(workorder=workorder).order_by(
        "step_order"
    )
    process_list = [
        {
            "id": p.id,
            "process_name": p.process_name,
            "step_order": p.step_order,
        }
        for p in processes
    ]
    return JsonResponse({"success": True, "processes": process_list})


def completed_workorders(request):
    """
    完工工單列表頁面：顯示所有狀態為 completed 的工單
    支援查詢、檢視、匯出功能
    """
    # 取得所有完工工單，按完工時間倒序排列
    completed_workorders = WorkOrder.objects.filter(status="completed").order_by(
        "-updated_at"
    )

    # 支援搜尋功能
    search_query = request.GET.get("search", "")
    if search_query:
        completed_workorders = completed_workorders.filter(
            Q(order_number__icontains=search_query)
            | Q(product_code__icontains=search_query)
            | Q(product_name__icontains=search_query)
            | Q(company_code__icontains=search_query)
        )

    # 分頁功能
    from django.core.paginator import Paginator

    paginator = Paginator(completed_workorders, 20)  # 每頁顯示20筆
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "total_count": completed_workorders.count(),
    }

    return render(request, "workorder/dispatch/completed_workorders.html", context)


def clear_completed_workorders(request):
    """
    清除完工工單確認頁面：確認是否要刪除所有完工工單
    只有管理員可以執行此操作
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:completed_workorders")

    if request.method == "POST":
        try:
            # 取得要刪除的完工工單數量
            completed_count = WorkOrder.objects.filter(status="completed").count()

            # 刪除所有完工工單
            WorkOrder.objects.filter(status="completed").delete()

            messages.success(
                request, f"成功清除所有完工工單！共刪除 {completed_count} 個工單"
            )
            return redirect("workorder:index")

        except Exception as e:
            messages.error(request, f"清除完工工單失敗：{str(e)}")
            return redirect("workorder:completed_workorders")

    # GET 請求顯示確認頁面
    completed_count = WorkOrder.objects.filter(status="completed").count()
    context = {
        "completed_count": completed_count,
    }

    return render(request, "workorder/clear_completed_confirm.html", context)


def clear_data(request):
    """
    清除數據頁面：清除派工單、完工工單、公司製令單等數據
    只有管理員可以執行此操作，需要確認頁面
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:index")

    if request.method == "POST":
        try:
            # 取得要清除的數據統計
            workorder_count = WorkOrder.objects.count()
            company_order_count = CompanyOrder.objects.count()
            dispatch_log_count = DispatchLog.objects.count()

            # 清除所有數據
            WorkOrder.objects.all().delete()
            CompanyOrder.objects.all().delete()
            DispatchLog.objects.all().delete()

            messages.success(
                request,
                f"成功清除所有數據！共清除：工單 {workorder_count} 筆、公司製令單 {company_order_count} 筆、"
                f"派工記錄 {dispatch_log_count} 筆",
            )
            return redirect("workorder:index")

        except Exception as e:
            messages.error(request, f"清除數據失敗：{str(e)}")
            return redirect("workorder:clear_data")

    # GET 請求顯示確認頁面
    context = {
        "workorder_count": WorkOrder.objects.count(),
        "company_order_count": CompanyOrder.objects.count(),
        "dispatch_log_count": DispatchLog.objects.count(),
    }

    return render(request, "workorder/clear_data_confirm.html", context)


def start_production(request, pk):
    """
    開始生產：將工單狀態從 pending 轉換為 in_progress
    只有管理員可以執行此操作
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:dispatch_list")

    if request.method != "POST":
        messages.error(request, "無效的請求方法")
        return redirect("workorder:dispatch_list")

    try:
        # 取得工單
        workorder = WorkOrder.objects.get(pk=pk)

        # 檢查工單狀態
        if workorder.status != "pending":
            messages.error(
                request, f"工單 {workorder.order_number} 狀態不是待生產，無法開始生產"
            )
            return redirect("workorder:dispatch_list")

        # 檢查是否有工序路線
        from process.models import ProductProcessRoute

        has_process_route = ProductProcessRoute.objects.filter(
            product_id=workorder.product_code
        ).exists()

        if not has_process_route:
            messages.error(
                request, f"工單 {workorder.order_number} 尚未設定工序路線，無法開始生產"
            )
            return redirect("workorder:dispatch_list")

        # 更新工單狀態
        workorder.status = "in_progress"
        workorder.updated_at = timezone.now()
        workorder.save()

        # 記錄派工日誌
        # 注意：DispatchLog 模型沒有 action 欄位，所以我們只記錄基本資訊
        # 如果需要記錄動作類型，可以考慮使用 WorkOrderProcessLog 或添加 action 欄位到 DispatchLog
        DispatchLog.objects.create(
            workorder=workorder,
            process=workorder.processes.first(),  # 使用第一個工序作為記錄
            operator=None,  # 暫時設為 None，因為需要 Operator 對象
            quantity=workorder.quantity,
            created_by=request.user.username,
        )

        messages.success(request, f"工單 {workorder.order_number} 已成功開始生產")

    except WorkOrder.DoesNotExist:
        messages.error(request, "工單不存在")
    except Exception as e:
        messages.error(request, f"開始生產失敗：{str(e)}")

    return redirect("workorder:dispatch_list")


def stop_production(request, pk):
    """
    停止生產：將工單狀態從 in_progress 轉換為 pending
    只有管理員可以執行此操作
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:dispatch_list")

    if request.method != "POST":
        messages.error(request, "無效的請求方法")
        return redirect("workorder:dispatch_list")

    try:
        # 取得工單
        workorder = WorkOrder.objects.get(pk=pk)

        # 檢查工單狀態
        if workorder.status != "in_progress":
            messages.error(
                request, f"工單 {workorder.order_number} 狀態不是生產中，無法停止生產"
            )
            return redirect("workorder:dispatch_list")

        # 更新工單狀態
        workorder.status = "pending"
        workorder.updated_at = timezone.now()
        workorder.save()

        # 記錄派工日誌
        # 注意：DispatchLog 模型沒有 action 欄位，所以我們只記錄基本資訊
        DispatchLog.objects.create(
            workorder=workorder,
            process=workorder.processes.first(),  # 使用第一個工序作為記錄
            operator=None,  # 暫時設為 None，因為需要 Operator 對象
            quantity=workorder.quantity,
            created_by=request.user.username,
        )

        messages.success(request, f"工單 {workorder.order_number} 已成功停止生產")

    except WorkOrder.DoesNotExist:
        messages.error(request, "工單不存在")
    except Exception as e:
        messages.error(request, f"停止生產失敗：{str(e)}")

    return redirect("workorder:dispatch_list")


def selective_revert_orders(request):
    """
    選擇性將已轉換的公司製令單退回（is_converted 設回 False）
    只有管理員可操作。
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:company_orders")

    from .models import CompanyOrder

    if request.method == "POST":
        ids = request.POST.getlist("order_ids")
        if ids:
            updated = CompanyOrder.objects.filter(id__in=ids, is_converted=True).update(
                is_converted=False
            )
            workorder_logger.info(
                f"管理員 {request.user} 選擇性退回 {updated} 筆製令單。IP: {request.META.get('REMOTE_ADDR')}"
            )
            messages.success(request, f"已成功退回 {updated} 筆製令單！")
        else:
            messages.warning(request, "請至少選擇一筆要退回的製令單！")
        return redirect("workorder:company_orders")

    # GET 顯示所有已轉換的製令單
    orders = CompanyOrder.objects.filter(is_converted=True).order_by("-sync_time")
    return render(request, "workorder/selective_revert_orders.html", {"orders": orders})





def user_supplement_form(request, workorder_id):
    """
    使用者補登表單 - 只能補登，不能核准
    """
    from django.shortcuts import get_object_or_404, redirect
    from datetime import datetime

    workorder = get_object_or_404(WorkOrder, id=workorder_id)
    processes = workorder.processes.all()
    # 取得所有作業員與設備
    operators = list(Operator.objects.all())
    equipments = list(Equipment.objects.all())
    error_msgs = []
    
    if request.method == "POST":
        for process in processes:
            completed_quantity = request.POST.get(f"completed_quantity_{process.id}")
            work_date = request.POST.get(f"work_date_{process.id}")
            start_time = request.POST.get(f"start_time_{process.id}")
            end_time = request.POST.get(f"end_time_{process.id}")
            operator_id = request.POST.get(f"operator_{process.id}")
            equipment_id = request.POST.get(f"equipment_{process.id}")
            notes = request.POST.get(f"notes_{process.id}")
            completed_flag = request.POST.get(f"completed_flag_{process.id}")

            # 判斷工序類型
            is_smt = (
                "SMT" in process.process_name
                or "smt" in process.process_name
                or "貼片" in process.process_name
            )
            # 驗證必填欄位
            if not is_smt and not operator_id:
                error_msgs.append(f"工序「{process.process_name}」作業員必填！")
            if is_smt and not equipment_id:
                error_msgs.append(f"工序「{process.process_name}」設備必填！")

            # 組合日期和時間為 datetime
            supplement_datetime = None
            end_datetime = None

            if work_date and start_time:
                try:
                    supplement_datetime = datetime.strptime(
                        f"{work_date} {start_time}", "%Y-%m-%d %H:%M"
                    )
                    supplement_datetime = timezone.make_aware(supplement_datetime)
                except ValueError:
                    error_msgs.append(
                        f"工序「{process.process_name}」開始時間格式錯誤！"
                    )

            if work_date and end_time:
                try:
                    end_datetime = datetime.strptime(
                        f"{work_date} {end_time}", "%Y-%m-%d %H:%M"
                    )
                    end_datetime = timezone.make_aware(end_datetime)
                except ValueError:
                    error_msgs.append(
                        f"工序「{process.process_name}」結束時間格式錯誤！"
                    )

            # 驗證時間邏輯
            if supplement_datetime and end_datetime:
                if supplement_datetime >= end_datetime:
                    error_msgs.append(
                        f"工序「{process.process_name}」結束時間必須晚於開始時間！"
                    )
                if (
                    supplement_datetime > timezone.now()
                    or end_datetime > timezone.now()
                ):
                    error_msgs.append(
                        f"工序「{process.process_name}」補登時間不能超過現在時間！"
                    )

            # 只要有填寫完成數量才儲存
            if completed_quantity:
                # 取得作業員/設備物件
                operator_obj = (
                    Operator.objects.filter(id=operator_id).first()
                    if operator_id
                    else None
                )
                equipment_name = None
                if equipment_id:
                    eq_obj = Equipment.objects.filter(id=equipment_id).first()
                    equipment_name = eq_obj.name if eq_obj else None
                # 儲存補登紀錄
                QuickSupplementLog.objects.create(
                    product_code=workorder.product_code,
                    workorder=workorder,
                    process=process,
                    action_type="complete",
                    supplement_time=supplement_datetime or timezone.now(),
                    end_time=end_datetime,
                    completed_quantity=completed_quantity or 0,
                    defect_qty=0,  # 預設不良品數量為 0
                    notes=notes,
                    created_by=request.user.username,
                    operator=operator_obj.name if operator_obj else None,
                    equipment=equipment_name,
                )
                # 若勾選已完工，直接設工序狀態為已完成
                if completed_flag:
                    process.status = "completed"
                    process.save()
        if error_msgs:
            messages.error(request, "；".join(error_msgs))
        else:
            messages.success(request, "補登資料已提交，等待管理員核准")
            return redirect("workorder:user_supplement_index")
    
    return render(
        request,
        "workorder/user_supplement_form.html",
        {
            "workorder": workorder,
            "processes": processes,
            "operators": operators,
            "equipments": equipments,
            "today": datetime.now().date(),
        },
    )


def edit_my_supplement(request, supplement_id):
    """
    編輯自己的補登記錄 - 只能編輯未核准的記錄
    """
    from django.shortcuts import get_object_or_404, redirect
    from datetime import datetime
    
    supplement = get_object_or_404(QuickSupplementLog, id=supplement_id)
    
    # 檢查權限 - 只能編輯自己的未核准記錄
    if supplement.created_by != request.user.username:
        messages.error(request, "您只能編輯自己的補登記錄")
        return redirect('workorder:user_supplement_index')
    
    if supplement.is_approved:
        messages.error(request, "已核准的記錄無法修改")
        return redirect('workorder:user_supplement_index')
    
    if request.method == "POST":
        # 更新補登記錄
        supplement.completed_quantity = request.POST.get('completed_quantity', 0)
        supplement.defect_qty = request.POST.get('defect_qty', 0)
        supplement.notes = request.POST.get('notes', '')
        
        # 更新時間
        work_date = request.POST.get('work_date')
        start_time = request.POST.get('start_time')
        if work_date and start_time:
            try:
                supplement_datetime = datetime.strptime(
                    f"{work_date} {start_time}", "%Y-%m-%d %H:%M"
                )
                supplement.supplement_time = timezone.make_aware(supplement_datetime)
            except ValueError:
                messages.error(request, "時間格式錯誤")
                return redirect('workorder:edit_my_supplement', supplement_id=supplement_id)
        
        supplement.save()
        messages.success(request, "補登記錄已更新")
        return redirect('workorder:user_supplement_index')
    
    return render(
        request,
        "workorder/edit_my_supplement.html",
        {
            "supplement": supplement,
            "today": datetime.now().date(),
        },
    )


def delete_my_supplement(request, supplement_id):
    """
    刪除自己的補登記錄 - 只能刪除未核准的記錄
    """
    from django.shortcuts import get_object_or_404, redirect
    
    supplement = get_object_or_404(QuickSupplementLog, id=supplement_id)
    
    # 檢查權限 - 只能刪除自己的未核准記錄
    if supplement.created_by != request.user.username:
        messages.error(request, "您只能刪除自己的補登記錄")
        return redirect('workorder:user_supplement_index')
    
    if supplement.is_approved:
        messages.error(request, "已核准的記錄無法刪除")
        return redirect('workorder:user_supplement_index')
    
    supplement.delete()
    messages.success(request, "補登記錄已刪除")
    return redirect('workorder:user_supplement_index')


def process_logs(request, process_id):
    """
    顯示工序日誌頁面
    """
    from django.shortcuts import get_object_or_404

    process = get_object_or_404(WorkOrderProcess, pk=process_id)
    logs = DispatchLog.objects.filter(workorder_process=process).order_by("-created_at")

    return render(
        request,
        "workorder/process/process_logs.html",
        {
            "process": process,
            "logs": logs,
        },
    )


def edit_supplement_mobile(request):
    """
    行動裝置補登編輯頁面
    """
    log_id = request.GET.get("log_id")
    if log_id:
        log = get_object_or_404(QuickSupplementLog, pk=log_id)
        return render(request, "workorder/edit_supplement_mobile.html", {"log": log})
    else:
        messages.error(request, "缺少日誌ID")
        return redirect("workorder:index")


def pending_approval_list(request):
    """
    待審核報工列表頁面
    顯示所有類型的待審核報工記錄（管理者、作業員、SMT）
    """
    from .models import OperatorSupplementReport, SMTProductionReport
    
    # 取得所有類型的待審核記錄
    manager_pending = []  # 管理者審核功能已刪除
    
    operator_pending = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(approval_status='pending').order_by('-created_at')
    
    smt_pending = SMTProductionReport.objects.select_related(
        'workorder', 'equipment'
    ).filter(approval_status='pending').order_by('-created_at')
    
    # 合併所有待審核記錄
    all_pending = []
    
    # 管理者審核功能已刪除，跳過處理
    
    for report in operator_pending:
        all_pending.append({
            'type': '作業員報工',
            'id': report.id,
            'report_type': 'operator',
            'operator': report.operator.name if report.operator else '-',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process.name if report.process else '-',
            'quantity': report.work_quantity,
            'defect_quantity': report.defect_quantity,
            'work_date': report.work_date,
            'start_time': report.start_time,
            'end_time': report.end_time,
            'created_at': report.created_at,
            'remarks': report.remarks,
            'remarks': report.remarks,
        })
    
    for report in smt_pending:
        all_pending.append({
            'type': 'SMT報工',
            'id': report.id,
            'report_type': 'smt',
            'operator': 'SMT設備',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.operation,
            'quantity': report.work_quantity,
            'defect_quantity': getattr(report, 'defect_quantity', 0),
            'work_date': report.work_date,
            'start_time': report.start_time,
            'end_time': report.end_time,
            'created_at': report.created_at,
            'remarks': report.remarks,
            'remarks': getattr(report, 'remarks', ''),
        })
    
    # 按創建時間排序
    all_pending.sort(key=lambda x: x['created_at'], reverse=True)
    
    # 統計資料
    total_pending = len(all_pending)
    manager_count = 0  # 管理者審核功能已刪除
    operator_count = len(operator_pending)
    smt_count = len(smt_pending)

    return render(
        request,
        "workorder/pending_approval_list.html",
        {
            "all_pending": all_pending,
            "total_pending": total_pending,
            "manager_count": manager_count,
            "operator_count": operator_count,
            "smt_count": smt_count,
        },
    )


@csrf_exempt
def get_operators_and_equipments(request):
    """
    API：取得所有作業員和設備資料，供前端 AJAX 使用
    """
    try:
        from process.models import Operator
        from equip.models import Equipment
        # 取得作業員資料，包含技能
        operators = []
        for op in Operator.objects.all():
            skills = list(op.skills.all().values_list('process_name__name', flat=True))
            operators.append({
                "id": op.id,
                "name": op.name,
                "skills": skills,
            })
        # 取得設備資料，包含型別和狀態
        equipments = []
        for eq in Equipment.objects.all():
            equipments.append({
                "id": eq.id,
                "name": eq.name,
                "model": getattr(eq, 'model', ''),
                "type": getattr(eq, 'type', ''),
                "status": getattr(eq, 'status', ''),
            })
        return JsonResponse({
            "success": True,
            "operators": operators,
            "equipments": equipments,
        })
    except Exception as e:
        return JsonResponse({"success": False, "message": f"取得資料失敗：{str(e)}"})


@require_GET
@csrf_exempt
def get_operators_only(request):
    """
    API：取得所有作業員資料，包含技能清單，供前端 AJAX 使用
    作業員沒有指定技能就不顯示
    """
    try:
        from process.models import Operator, OperatorSkill, ProcessName
        
        # 取得工序名稱參數（可選）
        process_name = request.GET.get('process_name', '').strip()
        
        operators = []
        
        if process_name:
            # 查詢有該工序技能的作業員
            skilled_operators = Operator.objects.filter(
                skills__process_name__name=process_name
            ).distinct()
            
            for op in skilled_operators:
                # 取得技能清單
                skills = list(op.skills.all().values_list('process_name__name', flat=True))
                operators.append({
                    "id": op.id,
                    "name": op.name,
                    "skills": skills,
                })
            # 如果沒有作業員有該技能，operators 保持空列表，不顯示任何作業員
        else:
            # 如果沒有指定工序名稱，顯示所有作業員（用於一般查詢）
            for op in Operator.objects.all():
                skills = list(op.skills.all().values_list('process_name__name', flat=True))
                operators.append({
                    "id": op.id,
                    "name": op.name,
                    "skills": skills,
                })
        
        return JsonResponse({
            "success": True,
            "operators": operators,
        })
    except Exception as e:
        return JsonResponse({"success": False, "message": f"取得作業員資料失敗：{str(e)}"})


@require_GET
@csrf_exempt
def get_equipments_only(request):
    """
    API：取得所有設備資料，供前端 AJAX 使用
    工序沒有指定設備就不顯示
    """
    try:
        from equip.models import Equipment
        from process.models import ProcessEquipment, ProcessName
        
        # 取得工序名稱參數（可選）
        process_name = request.GET.get('process_name', '').strip()
        
        equipments = []
        
        if process_name:
            # 查詢工序是否有指定設備
            suitable_equipment_ids = ProcessEquipment.objects.filter(
                process_name__name=process_name
            ).values_list('equipment_id', flat=True)
            
            # 如果工序有指定設備，才顯示這些設備
            if suitable_equipment_ids:
                suitable_equipments = Equipment.objects.filter(id__in=suitable_equipment_ids)
                for eq in suitable_equipments:
                    equipments.append({
                        "id": eq.id,
                        "name": eq.name,
                        "model": getattr(eq, 'model', ''),
                        "status": getattr(eq, 'status', ''),
                    })
            # 如果工序沒有指定設備，equipments 保持空列表，不顯示任何設備
        
        return JsonResponse({
            "success": True,
            "equipments": equipments,
        })
    except Exception as e:
        return JsonResponse({"success": False, "message": f"取得設備資料失敗：{str(e)}"})


# ==================== 行動裝置補登管理作業 ====================


def mobile_quick_supplement_index(request):
    """
    行動裝置補登管理作業主頁
    針對行動裝置設計的簡潔介面，讓使用者依產品編號查詢工單進行補登
    """
    workorders = None
    product_code = request.GET.get("product_code")
    if product_code:
        workorders = WorkOrder.objects.filter(product_code__icontains=product_code)
        # 轉成列表並加上產品名稱欄位
        workorders = [
            {
                "id": wo.id,
                "order_number": wo.order_number,
                "product_name": wo.product_code,
                "quantity": wo.quantity,
                "status": wo.status,
                "get_status_display": wo.get_status_display(),
            }
            for wo in workorders
        ]
    return render(
        request,
        "workorder/mobile_quick_supplement_index.html",
        {"workorders": workorders, "product_code": product_code},
    )


def mobile_quick_supplement_form(request, workorder_id):
    """
    行動裝置補登管理作業表單
    針對行動裝置設計的表單，簡化操作流程，適合觸控操作
    """
    from django.shortcuts import get_object_or_404, redirect
    from datetime import datetime

    workorder = get_object_or_404(WorkOrder, id=workorder_id)
    processes = workorder.processes.all()
    # 取得所有作業員與設備
    operators = list(Operator.objects.all())
    equipments = list(Equipment.objects.all())
    error_msgs = []

    if request.method == "POST":
        for process in processes:
            completed_quantity = request.POST.get(f"completed_quantity_{process.id}")
            work_date = request.POST.get(f"work_date_{process.id}")
            start_time = request.POST.get(f"start_time_{process.id}")
            end_time = request.POST.get(f"end_time_{process.id}")
            operator_id = request.POST.get(f"operator_{process.id}")
            equipment_id = request.POST.get(f"equipment_{process.id}")
            notes = request.POST.get(f"notes_{process.id}")
            completed_flag = request.POST.get(f"completed_flag_{process.id}")

            # 判斷工序類型
            is_smt = (
                "SMT" in process.process_name
                or "smt" in process.process_name
                or "貼片" in process.process_name
            )

            # 驗證必填欄位
            if not is_smt and not operator_id:
                error_msgs.append(f"工序「{process.process_name}」作業員必填！")
            if is_smt and not equipment_id:
                error_msgs.append(f"工序「{process.process_name}」設備必填！")

            # 組合日期和時間為 datetime
            supplement_datetime = None
            end_datetime = None

            if work_date and start_time:
                try:
                    supplement_datetime = datetime.strptime(
                        f"{work_date} {start_time}", "%Y-%m-%d %H:%M"
                    )
                    supplement_datetime = timezone.make_aware(supplement_datetime)
                except ValueError:
                    error_msgs.append(
                        f"工序「{process.process_name}」開始時間格式錯誤！"
                    )

            if work_date and end_time:
                try:
                    end_datetime = datetime.strptime(
                        f"{work_date} {end_time}", "%Y-%m-%d %H:%M"
                    )
                    end_datetime = timezone.make_aware(end_datetime)
                except ValueError:
                    error_msgs.append(
                        f"工序「{process.process_name}」結束時間格式錯誤！"
                    )

            # 驗證時間邏輯
            if supplement_datetime and end_datetime:
                if supplement_datetime >= end_datetime:
                    error_msgs.append(
                        f"工序「{process.process_name}」結束時間必須晚於開始時間！"
                    )
                if (
                    supplement_datetime > timezone.now()
                    or end_datetime > timezone.now()
                ):
                    error_msgs.append(
                        f"工序「{process.process_name}」補登時間不能超過現在時間！"
                    )

            # 只要有填寫完成數量才儲存
            if completed_quantity:
                # 取得作業員/設備物件
                operator_obj = (
                    Operator.objects.filter(id=operator_id).first()
                    if operator_id
                    else None
                )
                equipment_name = None
                if equipment_id:
                    eq_obj = Equipment.objects.filter(id=equipment_id).first()
                    equipment_name = eq_obj.name if eq_obj else None

                # 儲存補登紀錄
                QuickSupplementLog.objects.create(
                    product_code=workorder.product_code,
                    workorder=workorder,
                    process=process,
                    action_type="complete",
                    supplement_time=supplement_datetime or timezone.now(),
                    end_time=end_datetime,
                    completed_quantity=completed_quantity or 0,
                    notes=notes,
                    created_by=request.user.username,
                    operator=operator_obj.name if operator_obj else None,
                    equipment=equipment_name,
                )

                # 若勾選已完工，直接設工序狀態為已完成
                if completed_flag:
                    process.status = "completed"
                    process.save()

        if error_msgs:
            messages.error(request, "；".join(error_msgs))
        else:
            messages.success(request, "補登資料已成功儲存！")
            return redirect("workorder:mobile_quick_supplement_index")

    return render(
        request,
        "workorder/mobile_quick_supplement_form.html",
        {
            "workorder": workorder,
            "processes": processes,
            "operators": operators,
            "equipments": equipments,
        },
    )


@require_GET
@csrf_exempt
def mobile_get_workorder_info(request):
    """
    行動裝置 API：根據產品編號取得工單資訊
    """
    product_code = request.GET.get("product_code")
    if not product_code:
        return JsonResponse({"success": False, "message": "請提供產品編號"})

    try:
        workorders = WorkOrder.objects.filter(product_code__icontains=product_code)
        workorder_list = []

        for wo in workorders:
            workorder_list.append(
                {
                    "id": wo.id,
                    "order_number": wo.order_number,
                    "product_code": wo.product_code,
                    "quantity": wo.quantity,
                    "status": wo.status,
                    "status_display": wo.get_status_display(),
                    "created_at": (
                        wo.created_at.strftime("%Y-%m-%d %H:%M")
                        if wo.created_at
                        else ""
                    ),
                }
            )

        return JsonResponse(
            {
                "success": True,
                "workorders": workorder_list,
                "count": len(workorder_list),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": f"查詢失敗：{str(e)}"})


@require_GET
@csrf_exempt
def mobile_get_process_info(request):
    """
    行動裝置 API：取得指定工單的工序資訊
    """
    workorder_id = request.GET.get("workorder_id")
    if not workorder_id:
        return JsonResponse({"success": False, "message": "請提供工單ID"})

    try:
        workorder = WorkOrder.objects.get(id=workorder_id)
        processes = workorder.processes.all()
        process_list = []

        for process in processes:
            process_list.append(
                {
                    "id": process.id,
                    "process_name": process.process_name,
                    "status": process.status,
                    "status_display": process.get_status_display(),
                    "is_smt": "SMT" in process.process_name
                    or "smt" in process.process_name
                    or "貼片" in process.process_name,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "workorder": {
                    "id": workorder.id,
                    "order_number": workorder.order_number,
                    "product_code": workorder.product_code,
                    "quantity": workorder.quantity,
                    "status": workorder.status,
                    "status_display": workorder.get_status_display(),
                },
                "processes": process_list,
            }
        )

    except WorkOrder.DoesNotExist:
        return JsonResponse({"success": False, "message": "找不到指定的工單"})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"查詢失敗：{str(e)}"})


@require_POST
@csrf_exempt
def mobile_submit_supplement(request):
    """
    行動裝置 API：提交補登資料
    """
    try:
        from datetime import datetime

        workorder_id = request.POST.get("workorder_id")
        process_id = request.POST.get("process_id")
        completed_quantity = request.POST.get("completed_quantity", 0)
        work_date = request.POST.get("work_date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        operator_id = request.POST.get("operator_id")
        equipment_id = request.POST.get("equipment_id")
        notes = request.POST.get("notes", "")
        completed_flag = request.POST.get("completed_flag") == "true"

        # 驗證必填欄位
        if not workorder_id or not process_id:
            return JsonResponse({"success": False, "message": "缺少必要參數"})

        workorder = WorkOrder.objects.get(id=workorder_id)
        process = WorkOrderProcess.objects.get(id=process_id)

        # 判斷工序類型並驗證
        is_smt = (
            "SMT" in process.process_name
            or "smt" in process.process_name
            or "貼片" in process.process_name
        )

        if not is_smt and not operator_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"工序「{process.process_name}」作業員必填！",
                }
            )

        if is_smt and not equipment_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"工序「{process.process_name}」設備必填！",
                }
            )

        # 組合日期和時間為 datetime
        supplement_datetime = None
        end_datetime = None

        if work_date and start_time:
            try:
                supplement_datetime = datetime.strptime(
                    f"{work_date} {start_time}", "%Y-%m-%d %H:%M"
                )
                supplement_datetime = timezone.make_aware(supplement_datetime)
            except ValueError:
                return JsonResponse({"success": False, "message": "開始時間格式錯誤！"})

        if work_date and end_time:
            try:
                end_datetime = datetime.strptime(
                    f"{work_date} {end_time}", "%Y-%m-%d %H:%M"
                )
                end_datetime = timezone.make_aware(end_datetime)
            except ValueError:
                return JsonResponse({"success": False, "message": "結束時間格式錯誤！"})

        # 驗證時間邏輯
        if supplement_datetime and end_datetime:
            if supplement_datetime >= end_datetime:
                return JsonResponse(
                    {"success": False, "message": "結束時間必須晚於開始時間！"}
                )
            if supplement_datetime > timezone.now() or end_datetime > timezone.now():
                return JsonResponse(
                    {"success": False, "message": "補登時間不能超過現在時間！"}
                )

        # 取得作業員/設備物件
        operator_obj = (
            Operator.objects.filter(id=operator_id).first() if operator_id else None
        )
        equipment_name = None
        if equipment_id:
            eq_obj = Equipment.objects.filter(id=equipment_id).first()
            equipment_name = eq_obj.name if eq_obj else None

        # 儲存補登紀錄
        QuickSupplementLog.objects.create(
            product_code=workorder.product_code,
            workorder=workorder,
            process=process,
            action_type="complete",
            supplement_time=supplement_datetime or timezone.now(),
            end_time=end_datetime,
            completed_quantity=completed_quantity or 0,
            notes=notes,
            created_by=request.user.username,
            operator=operator_obj.name if operator_obj else None,
            equipment=equipment_name,
        )

        # 若勾選已完工，直接設工序狀態為已完成
        if completed_flag:
            process.status = "completed"
            process.save()

        return JsonResponse({"success": True, "message": "補登資料已成功儲存！"})

    except WorkOrder.DoesNotExist:
        return JsonResponse({"success": False, "message": "找不到指定的工單"})
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({"success": False, "message": "找不到指定的工序"})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"儲存失敗：{str(e)}"})


def mobile_api_test(request):
    """
    行動裝置 API 測試頁面
    用於測試行動裝置快速補登的 API 功能，方便開發和除錯
    """
    return render(request, "workorder/mobile_api_test.html")


@require_GET
@csrf_exempt
def quick_get_product_codes(request):
    """
    一般快速補登 API：取得所有有工單的產品編號清單
    """
    try:
        codes = WorkOrder.objects.values_list("product_code", flat=True).distinct()
        codes = sorted(set(codes))
        return JsonResponse({"success": True, "product_codes": list(codes)})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"查詢失敗：{str(e)}"})


@require_GET
@csrf_exempt
def get_product_codes(request):
    """
    行動裝置 API：取得所有有工單的產品編號清單（去重、排序）
    """
    try:
        product_codes = (
            WorkOrder.objects.values_list("product_code", flat=True)
            .distinct()
            .order_by("product_code")
        )
        return JsonResponse(
            {
                "success": True,
                "product_codes": list(product_codes),
                "count": len(product_codes),
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": f"查詢失敗：{str(e)}"})


@require_POST
@csrf_exempt
def move_process(request):
    """
    移動工序順序（上下移動）
    修正：移動時使用臨時值避免唯一性約束衝突。
    """
    try:
        process_id = request.POST.get("process_id")
        direction = request.POST.get("direction")  # 'up' 或 'down'
        
        if not process_id or not direction:
            return JsonResponse({"success": False, "message": "缺少必要參數"})
        
        # 取得當前工序
        current_process = WorkOrderProcess.objects.get(id=process_id)
        current_order = current_process.step_order
        
        # 取得同工單的所有工序，按順序排序
        all_processes = WorkOrderProcess.objects.filter(
            workorder=current_process.workorder
        ).order_by("step_order")
        
        if direction == "up":
            # 向上移動：與前一個工序交換順序
            if current_order > 1:
                prev_process = all_processes.filter(step_order=current_order - 1).first()
                if prev_process:
                    # 使用臨時值避免唯一性約束衝突
                    temp_order = 999999
                    # 先將當前工序移到臨時位置
                    current_process.step_order = temp_order
                    current_process.save()
                    # 將前一個工序移到當前位置
                    prev_process.step_order = current_order
                    prev_process.save()
                    # 將當前工序移到前一個位置
                    current_process.step_order = current_order - 1
                    current_process.save()
                    workorder_logger.info(
                        f"使用者 {request.user} 將工序「{current_process.process_name}」向上移動。IP: {request.META.get('REMOTE_ADDR')}"
                    )
                    return JsonResponse({"success": True, "message": "工序順序已更新"})
        elif direction == "down":
            # 向下移動：與後一個工序交換順序
            max_order = all_processes.count()
            if current_order < max_order:
                next_process = all_processes.filter(step_order=current_order + 1).first()
                if next_process:
                    # 使用臨時值避免唯一性約束衝突
                    temp_order = 999999
                    # 先將當前工序移到臨時位置
                    current_process.step_order = temp_order
                    current_process.save()
                    # 將後一個工序移到當前位置
                    next_process.step_order = current_order
                    next_process.save()
                    # 將當前工序移到後一個位置
                    current_process.step_order = current_order + 1
                    current_process.save()
                    workorder_logger.info(
                        f"使用者 {request.user} 將工序「{current_process.process_name}」向下移動。IP: {request.META.get('REMOTE_ADDR')}"
                    )
                    return JsonResponse({"success": True, "message": "工序順序已更新"})
        
        return JsonResponse({"success": False, "message": "無法移動工序順序"})
        
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({"success": False, "message": "找不到指定的工序"})
    except Exception as e:
        workorder_logger.error(f"移動工序失敗：{str(e)}")
        return JsonResponse({"success": False, "message": f"移動失敗：{str(e)}"})


@require_POST
@csrf_exempt
def add_process(request, workorder_id):
    """
    新增工序到工單
    """
    try:
        # 取得工單
        workorder = WorkOrder.objects.get(id=workorder_id)
        
        # 取得表單資料
        process_name = request.POST.get("process_name")
        step_order = request.POST.get("step_order")
        planned_quantity = request.POST.get("planned_quantity")
        target_hourly_output = request.POST.get("target_hourly_output")
        
        # 驗證必填欄位
        if not process_name or not step_order:
            return JsonResponse({"status": "error", "message": "工序名稱和順序為必填欄位"})
        
        try:
            step_order = int(step_order)
            planned_quantity = int(planned_quantity) if planned_quantity else workorder.quantity
            target_hourly_output = int(target_hourly_output) if target_hourly_output else 100
        except ValueError:
            return JsonResponse({"status": "error", "message": "數值欄位格式錯誤"})
        
        # 檢查工序順序是否重複
        if WorkOrderProcess.objects.filter(workorder=workorder, step_order=step_order).exists():
            return JsonResponse({"status": "error", "message": f"工序順序 {step_order} 已存在"})
        
        # 調整後續工序的順序（使用臨時值避免唯一性約束衝突）
        existing_processes = WorkOrderProcess.objects.filter(
            workorder=workorder, 
            step_order__gte=step_order
        ).order_by("-step_order")
        
        # 先將所有需要調整的工序移到臨時位置
        temp_start = 999999
        for i, process in enumerate(existing_processes):
            process.step_order = temp_start + i
            process.save()
        
        # 再將工序移到正確的位置
        for i, process in enumerate(existing_processes):
            process.step_order = step_order + 1 + i
            process.save()
        
        # 建立新工序
        new_process = WorkOrderProcess.objects.create(
            workorder=workorder,
            process_name=process_name,
            step_order=step_order,
            planned_quantity=planned_quantity,
            target_hourly_output=target_hourly_output,
            status="pending"
        )
        
        # 計算預計工時
        if target_hourly_output > 0:
            estimated_hours = planned_quantity / target_hourly_output
            new_process.estimated_hours = round(estimated_hours, 2)
            new_process.save()
        
        workorder_logger.info(
            f"使用者 {request.user} 為工單 {workorder.order_number} 新增工序「{process_name}」。IP: {request.META.get('REMOTE_ADDR')}"
        )
        
        return JsonResponse({
            "status": "success", 
            "message": f"工序「{process_name}」新增成功"
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({"status": "error", "message": "找不到指定的工單"})
    except Exception as e:
        workorder_logger.error(f"新增工序失敗：{str(e)}")
        return JsonResponse({"status": "error", "message": f"新增失敗：{str(e)}"})


@require_POST
@csrf_exempt
def edit_process(request, process_id):
    """
    編輯工序
    """
    try:
        # 取得工序
        process = WorkOrderProcess.objects.get(id=process_id)
        
        # 取得表單資料
        process_name = request.POST.get("process_name")
        step_order = request.POST.get("step_order")
        planned_quantity = request.POST.get("planned_quantity")
        target_hourly_output = request.POST.get("target_hourly_output")
        
        # 驗證必填欄位
        if not process_name or not step_order:
            return JsonResponse({"status": "error", "message": "工序名稱和順序為必填欄位"})
        
        try:
            step_order = int(step_order)
            planned_quantity = int(planned_quantity) if planned_quantity else process.planned_quantity
            target_hourly_output = int(target_hourly_output) if target_hourly_output else process.target_hourly_output
        except ValueError:
            return JsonResponse({"status": "error", "message": "數值欄位格式錯誤"})
        
        # 檢查工序順序是否重複（排除自己）
        if WorkOrderProcess.objects.filter(
            workorder=process.workorder, 
            step_order=step_order
        ).exclude(id=process_id).exists():
            return JsonResponse({"status": "error", "message": f"工序順序 {step_order} 已存在"})
        
        # 如果工序順序有變更，需要重新排序
        old_step_order = process.step_order
        if step_order != old_step_order:
            # 先將當前工序移到臨時位置
            temp_order = 999999
            process.step_order = temp_order
            process.save()
            
            # 調整其他工序的順序
            if step_order > old_step_order:
                # 向下移動：將中間的工序向上移動
                processes_to_move = WorkOrderProcess.objects.filter(
                    workorder=process.workorder,
                    step_order__gt=old_step_order,
                    step_order__lte=step_order
                ).exclude(id=process_id).order_by('step_order')
                
                for proc in processes_to_move:
                    proc.step_order -= 1
                    proc.save()
            else:
                # 向上移動：將中間的工序向下移動
                processes_to_move = WorkOrderProcess.objects.filter(
                    workorder=process.workorder,
                    step_order__gte=step_order,
                    step_order__lt=old_step_order
                ).exclude(id=process_id).order_by('-step_order')
                
                for proc in processes_to_move:
                    proc.step_order += 1
                    proc.save()
        
        # 更新工序資料
        process.process_name = process_name
        process.step_order = step_order
        process.planned_quantity = planned_quantity
        process.target_hourly_output = target_hourly_output
        
        # 計算預計工時
        if target_hourly_output > 0:
            estimated_hours = planned_quantity / target_hourly_output
            process.estimated_hours = round(estimated_hours, 2)
        
        process.save()
        
        workorder_logger.info(
            f"使用者 {request.user} 編輯工序「{process_name}」。IP: {request.META.get('REMOTE_ADDR')}"
        )
        
        return JsonResponse({
            "status": "success", 
            "message": f"工序「{process_name}」更新成功"
        })
        
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({"status": "error", "message": "找不到指定的工序"})
    except Exception as e:
        workorder_logger.error(f"編輯工序失敗：{str(e)}")
        return JsonResponse({"status": "error", "message": f"編輯失敗：{str(e)}"})


@require_POST
@csrf_exempt
def delete_process(request, process_id):
    """
    刪除工序
    """
    try:
        # 取得工序
        process = WorkOrderProcess.objects.get(id=process_id)
        
        # 檢查工序狀態
        if process.status != "pending":
            return JsonResponse({"status": "error", "message": "只有待生產狀態的工序才能刪除"})
        
        process_name = process.process_name
        workorder = process.workorder
        
        # 刪除工序
        process.delete()
        
        # 重新排序剩餘工序
        remaining_processes = WorkOrderProcess.objects.filter(
            workorder=workorder
        ).order_by("step_order")
        
        for i, proc in enumerate(remaining_processes, 1):
            proc.step_order = i
            proc.save()
        
        workorder_logger.info(
            f"使用者 {request.user} 刪除工序「{process_name}」。IP: {request.META.get('REMOTE_ADDR')}"
        )
        
        return JsonResponse({
            "status": "success", 
            "message": f"工序「{process_name}」刪除成功"
        })
        
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({"status": "error", "message": "找不到指定的工序"})
    except Exception as e:
        workorder_logger.error(f"刪除工序失敗：{str(e)}")
        return JsonResponse({"status": "error", "message": f"刪除失敗：{str(e)}"})


@require_POST
@csrf_exempt
def batch_approve_supplements(request):
    """
    批量核准補登記錄 API
    """
    try:
        workorder_ids = request.POST.getlist('workorder_ids[]')
        if not workorder_ids:
            return JsonResponse({
                'success': False,
                'message': '請選擇要核准的工單'
            })
        
        approved_count = 0
        for workorder_id in workorder_ids:
            # 核准該工單的所有待核准補登記錄
            supplements = QuickSupplementLog.objects.filter(
                workorder_id=workorder_id,
                is_approved=False
            )
            supplements.update(
                is_approved=True,
                approved_at=timezone.now(),
                approved_by=request.user.username
            )
            approved_count += supplements.count()
        
        return JsonResponse({
            'success': True,
            'message': f'成功核准 {approved_count} 筆補登記錄',
            'approved_count': approved_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'核准失敗：{str(e)}'
        })


@require_POST
@csrf_exempt
def quick_approve_workorder(request, workorder_id):
    """
    快速核准指定工單的所有待核准補登記錄
    """
    try:
        workorder = get_object_or_404(WorkOrder, id=workorder_id)
        
        # 核准該工單的所有待核准補登記錄
        supplements = QuickSupplementLog.objects.filter(
            workorder=workorder,
            is_approved=False
        )
        
        if not supplements.exists():
            return JsonResponse({
                'success': False,
                'message': '該工單沒有待核准的補登記錄'
            })
        
        supplements.update(
            is_approved=True,
            approved_at=timezone.now(),
            approved_by=request.user.username
        )
        
        approved_count = supplements.count()
        
        return JsonResponse({
            'success': True,
            'message': f'成功核准工單 {workorder.order_number} 的 {approved_count} 筆補登記錄',
            'approved_count': approved_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'核准失敗：{str(e)}'
        })


@require_GET
@csrf_exempt
def supplement_statistics(request):
    """
    補登統計資料 API
    """
    from datetime import datetime, timedelta
    from django.db.models import Q, Count, Sum
    
    try:
        # 取得查詢參數
        period = request.GET.get('period', 'today')  # today, week, month
        product_code = request.GET.get('product_code', '')
        
        # 設定時間範圍
        today = datetime.now().date()
        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = today
            end_date = today
        
        # 建立查詢條件
        query = Q(supplement_time__date__gte=start_date, supplement_time__date__lte=end_date)
        if product_code:
            query &= Q(product_code__icontains=product_code)
        
        # 統計資料
        supplements = QuickSupplementLog.objects.filter(query)
        
        stats = supplements.aggregate(
            total_records=Count('id'),
            pending_records=Count('id', filter=Q(is_approved=False)),
            approved_records=Count('id', filter=Q(is_approved=True)),
            total_completed=Sum('completed_quantity'),
            total_defect=Sum('defect_qty'),
            total_workorders=Count('workorder', distinct=True)
        )
        
        # 按日期分組統計
        daily_stats = supplements.values('supplement_time__date').annotate(
            daily_records=Count('id'),
            daily_completed=Sum('completed_quantity'),
            daily_defect=Sum('defect_qty')
        ).order_by('supplement_time__date')
        
        return JsonResponse({
            'success': True,
            'data': {
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'summary': stats,
                'daily_stats': list(daily_stats)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'統計失敗：{str(e)}'
        })





@require_GET
@csrf_exempt
def get_process_capacity_info(request, process_id):
    """
    取得工序產能資訊 API
    回傳工序的標準產能、當前產能倍數、額外作業員和設備清單
    """
    from .models import WorkOrderProcess
    try:
        process = WorkOrderProcess.objects.get(id=process_id)
        # 取得標準產能（從產品工序標準產能表）
        from process.models import ProductProcessStandardCapacity
        capacity_data = ProductProcessStandardCapacity.objects.filter(
            product_code=process.workorder.product_code,
            process_name=process.process_name,
            is_active=True
        ).order_by('-version').first()
        standard_capacity = capacity_data.standard_capacity_per_hour if capacity_data else 1000
        # 取得額外作業員和設備清單
        additional_operators = process.get_additional_operators_list()
        additional_equipments = process.get_additional_equipments_list()
        # 取得所有可用作業員和設備供選擇
        from process.models import Operator
        from equip.models import Equipment
        all_operators = list(Operator.objects.values('id', 'name'))
        all_equipments = list(Equipment.objects.values('id', 'name'))
        return JsonResponse({
            'success': True,
            'capacity_info': {
                'standard_capacity': standard_capacity,
                'current_multiplier': process.capacity_multiplier,
                'current_target_hourly_output': process.target_hourly_output,
                'additional_operators': additional_operators,
                'additional_equipments': additional_equipments,
                'all_operators': all_operators,
                'all_equipments': all_equipments,
            }
        })
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({'success': False, 'message': '工序不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'取得產能資訊失敗：{str(e)}'}, status=500)

@require_POST
@csrf_exempt
def update_process_capacity(request, process_id):
    """
    更新工序產能設定 API
    更新產能倍數、目標每小時產出、額外作業員和設備
    """
    from .models import WorkOrderProcess
    try:
        process = WorkOrderProcess.objects.get(id=process_id)
        # 取得表單資料
        capacity_multiplier = int(request.POST.get('capacity_multiplier', 1))
        target_hourly_output = int(request.POST.get('target_hourly_output', 0))
        additional_operators = request.POST.get('additional_operators', '')
        additional_equipments = request.POST.get('additional_equipments', '')
        # 驗證產能倍數
        if capacity_multiplier < 1 or capacity_multiplier > 10:
            return JsonResponse({'success': False, 'message': '產能倍數必須在 1-10 之間'}, status=400)
        # 更新工序資料
        process.capacity_multiplier = capacity_multiplier
        process.target_hourly_output = target_hourly_output
        process.additional_operators = additional_operators
        process.additional_equipments = additional_equipments
        # 重新計算預計工時
        process.estimated_hours = process.calculate_estimated_hours()
        process.save()
        # 記錄操作日誌（如有 WorkOrderProcessLog 模型）
        try:
            from .models import WorkOrderProcessLog
            WorkOrderProcessLog.objects.create(
                workorder_process=process,
                action='capacity_update',
                description=f'更新產能設定：倍數={capacity_multiplier}x，目標產能={target_hourly_output}pcs/hr',
                created_by=request.user.username if request.user.is_authenticated else 'system'
            )
        except Exception:
            pass
        return JsonResponse({
            'success': True,
            'message': '產能設定更新成功',
            'updated_data': {
                'capacity_multiplier': capacity_multiplier,
                'target_hourly_output': target_hourly_output,
                'estimated_hours': float(process.estimated_hours),
                'completion_rate': process.completion_rate,
            }
        })
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({'success': False, 'message': '工序不存在'}, status=404)
    except ValueError as e:
        return JsonResponse({'success': False, 'message': f'資料格式錯誤：{str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'更新產能設定失敗：{str(e)}'}, status=500)

@require_GET
@csrf_exempt
def get_capacity_calculation_info(request, process_id):
    """
    取得產能計算資訊 API
    用於產能計算器的詳細資訊
    """
    from .models import WorkOrderProcess
    try:
        process = WorkOrderProcess.objects.get(id=process_id)
        # 取得標準產能資料
        from process.models import ProductProcessStandardCapacity
        capacity_data = ProductProcessStandardCapacity.objects.filter(
            product_code=process.workorder.product_code,
            process_name=process.process_name,
            is_active=True
        ).order_by('-version').first()
        if capacity_data:
            calculation_info = {
                'standard_capacity': capacity_data.standard_capacity_per_hour,
                'efficiency_factor': float(capacity_data.efficiency_factor),
                'learning_curve_factor': float(capacity_data.learning_curve_factor),
                'setup_time_minutes': capacity_data.setup_time_minutes,
                'teardown_time_minutes': capacity_data.teardown_time_minutes,
                'cycle_time_seconds': float(capacity_data.cycle_time_seconds),
                'optimal_batch_size': capacity_data.optimal_batch_size,
                'expected_defect_rate': float(capacity_data.expected_defect_rate),
                'rework_time_factor': float(capacity_data.rework_time_factor),
            }
        else:
            # 使用預設值
            calculation_info = {
                'standard_capacity': 1000,
                'efficiency_factor': 1.0,
                'learning_curve_factor': 1.0,
                'setup_time_minutes': 30,
                'teardown_time_minutes': 15,
                'cycle_time_seconds': 3.6,
                'optimal_batch_size': 100,
                'expected_defect_rate': 0.02,
                'rework_time_factor': 1.05,
            }
        # 加入當前工序資訊
        calculation_info.update({
            'current_multiplier': process.capacity_multiplier,
            'planned_quantity': process.planned_quantity,
            'completed_quantity': process.completed_quantity,
            'remaining_quantity': process.remaining_quantity,
        })
        return JsonResponse({'success': True, 'calculation_info': calculation_info})
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({'success': False, 'message': '工序不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'取得計算資訊失敗：{str(e)}'}, status=500)

@require_POST
@csrf_exempt
def update_process_status(request, process_id):
    """
    API：更新工序分配（作業員、設備、備註），並變更狀態為生產中
    純手動分配，不進行自動規範檢查
    """
    from workorder.models import WorkOrderProcess
    from equip.models import Equipment
    
    try:
        process = WorkOrderProcess.objects.get(id=process_id)
        operator_name = request.POST.get('operator', '').strip()
        equipment_name = request.POST.get('equipment', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        # 除錯資訊
        print(f"=== 手動分配 ===")
        print(f"工序ID: {process_id}")
        print(f"工序名稱: {process.process_name}")
        print(f"產品編號: {process.workorder.product_code}")
        print(f"收到的作業員: '{operator_name}'")
        print(f"收到的設備: '{equipment_name}'")
        
        # 基本驗證
        if not operator_name and not equipment_name:
            return JsonResponse({
                "status": "error", 
                "message": "請至少選擇作業員或設備其中一項"
            })
        
        # ====== 純手動分配，不進行自動檢查 ======
        print(f"✅ 執行手動分配")
        
        # 更新欄位
        process.assigned_operator = operator_name
        process.assigned_equipment = equipment_name
        process.status = 'in_progress'
        process.actual_start_time = timezone.now()
        process.save()
        
        # 如果有分配設備，更新設備狀態
        if equipment_name:
            try:
                equipment = Equipment.objects.get(name=equipment_name)
                equipment.status = 'running'
                equipment.save()
                print(f"✅ 設備狀態更新為運轉中：{equipment_name}")
            except Exception as e:
                print(f"⚠️ 設備狀態更新失敗：{str(e)}")
        
        # 重新讀取確認儲存
        process.refresh_from_db()
        print(f"✅ 分配完成")
        print(f"更新後的作業員: {process.assigned_operator}")
        print(f"更新後的設備: {process.assigned_equipment}")
        print(f"更新後的狀態: {process.status}")
        print(f"=== 手動分配結束 ===")
        
        # 記錄操作日誌
        try:
            from workorder.models import WorkOrderProcessLog
            WorkOrderProcessLog.objects.create(
                workorder_process=process,
                action='manual_assignment',
                operator=operator_name,
                equipment=equipment_name,
                notes=f"手動分配 - {notes}" if notes else "手動分配",
                quantity_before=process.completed_quantity,
                quantity_after=process.completed_quantity,
            )
            print(f"✅ 操作日誌記錄完成")
        except Exception as e:
            print(f"⚠️ 操作日誌記錄失敗：{str(e)}")
        
        return JsonResponse({
            "status": "success", 
            "message": "手動分配成功",
            "assigned_operator": operator_name,
            "assigned_equipment": equipment_name,
            "process_status": process.status
        })
        
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({"status": "error", "message": "找不到工序資料"})
    except Exception as e:
        print(f"❌ 分配過程發生錯誤：{str(e)}")
        return JsonResponse({"status": "error", "message": f"更新失敗：{str(e)}"})

def test_report_page(request):
    """
    測試報工頁面 - 不需要登入
    用於測試前端模板是否正常顯示
    """
    context = {
        'today_reports': 15,
        'month_reports': 245,
        'pending_reports': 8,
        'abnormal_reports': 3,
        'recent_reports': [
            {
                'report_time': '2025-07-24 12:30:00',
                'operator': '張小明',
                'workorder': 'WO-2025-001',
                'process': 'SMT',
                'quantity': 100,
                'work_hours': '2.5',
                'status': '已核准',
                'type': '作業員報工'
            },
            {
                'report_time': '2025-07-24 11:45:00',
                'operator': 'SMT設備',
                'workorder': 'WO-2025-002',
                'process': 'DIP',
                'quantity': 150,
                'work_hours': '3.0',
                'status': '待審核',
                'type': 'SMT報工'
            }
        ],
        'stats': {
            'total_pending': 8,
            'total_today': 15,
            'total_month': 245,
            'total_abnormal': 3,
            'pending_operator': 5,
            'pending_smt': 3,
            'today_operator': 10,
            'today_smt': 5,
            'month_operator': 180,
            'month_smt': 65,
            'abnormal_operator': 2,
            'abnormal_smt': 1,
        }
    }
    
    return render(request, 'workorder/report/index.html', context)

def report_index(request):
    """
    報工管理首頁視圖 - 重新設計版本
    顯示報工管理的主要功能卡片和統計資訊
    """
    from django.contrib.auth.decorators import login_required
    from django.shortcuts import redirect
    from datetime import date
    
    # 檢查用戶權限
    if not request.user.is_authenticated:
        return redirect('login')
    
    # 簡化的統計資料（暫時使用固定值，避免資料庫錯誤）
    context = {
        'today_reports': 0,
        'month_reports': 0,
        'pending_reports': 0,
        'abnormal_reports': 0,
        'recent_reports': [],
        'stats': {
            'total_pending': 0,
            'total_today': 0,
            'total_month': 0,
            'total_abnormal': 0,
            'pending_operator': 0,
            'pending_smt': 0,
            'today_operator': 0,
            'today_smt': 0,
            'month_operator': 0,
            'month_smt': 0,
            'abnormal_operator': 0,
            'abnormal_smt': 0,
        }
    }
    
    return render(request, 'workorder/report/index.html', context)

def manager_report_index(request):
    """
    管理者審核首頁 - 統計儀表板
    顯示所有報工類型的統計資訊和快速操作
    """
    from datetime import date, timedelta
    from django.db.models import Q
    from .models import OperatorSupplementReport, SMTProductionReport, ManagerProductionReport
    
    today = date.today()
    month_start = today.replace(day=1)
    
    # 統計所有類型的報工資料
    stats = {
        # 待審核統計
        'pending_manager': ManagerProductionReport.objects.filter(approval_status='pending').count(),
        'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
        
        # 今日統計
        'today_manager': ManagerProductionReport.objects.filter(work_date=today).count(),
        'today_operator': OperatorSupplementReport.objects.filter(work_date=today).count(),
        'today_smt': SMTProductionReport.objects.filter(work_date=today).count(),
        
        # 本月統計
        'month_manager': ManagerProductionReport.objects.filter(work_date__gte=month_start).count(),
        'month_operator': OperatorSupplementReport.objects.filter(work_date__gte=month_start).count(),
        'month_smt': SMTProductionReport.objects.filter(work_date__gte=month_start).count(),
        
        # 異常統計
        'abnormal_manager': ManagerProductionReport.objects.filter(
            Q(remarks__isnull=False) & ~Q(remarks='')
        ).count(),
        'abnormal_operator': OperatorSupplementReport.objects.filter(
            Q(remarks__isnull=False) & ~Q(remarks='')
        ).count(),
        'abnormal_smt': SMTProductionReport.objects.filter(
            Q(remarks__icontains='異常') | Q(remarks__icontains='異常')
        ).count(),
    }
    
    # 計算總計
    stats['total_pending'] = stats['pending_manager'] + stats['pending_operator'] + stats['pending_smt']
    stats['total_today'] = stats['today_manager'] + stats['today_operator'] + stats['today_smt']
    stats['total_month'] = stats['month_manager'] + stats['month_operator'] + stats['month_smt']
    stats['total_abnormal'] = stats['abnormal_manager'] + stats['abnormal_operator'] + stats['abnormal_smt']
    
    # 取得最近審核記錄
    recent_reviews = []
    
    # 管理者審核最近審核
    manager_reviews = ManagerProductionReport.objects.select_related(
        'workorder', 'process'
    ).filter(approval_status='approved').order_by('-approved_at')[:3]
    
    for review in manager_reviews:
        recent_reviews.append({
            'type': '管理者審核',
            'time': review.approved_at,
            'operator': review.manager,
            'workorder': review.workorder.order_number if review.workorder else '-',
            'process': review.process.name if review.process else '-',
            'quantity': review.work_quantity,
            'reviewer': review.approved_by,
        })
    
    # 作業員報工最近審核
    operator_reviews = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(approval_status='approved').order_by('-approved_at')[:3]
    
    for review in operator_reviews:
        recent_reviews.append({
            'type': '作業員報工',
            'time': review.approved_at,
            'operator': review.operator.name if review.operator else '-',
            'workorder': review.workorder.order_number if review.workorder else '-',
            'process': review.process.name if review.process else '-',
            'quantity': review.work_quantity,
            'reviewer': review.approved_by,
        })
    
    # SMT報工最近審核
    smt_reviews = SMTProductionReport.objects.select_related(
        'workorder'
    ).filter(approval_status='approved').order_by('-approved_at')[:3]
    
    for review in smt_reviews:
        recent_reviews.append({
            'type': 'SMT報工',
            'time': review.approved_at,
            'operator': 'SMT設備',
            'workorder': review.workorder.order_number if review.workorder else '-',
            'process': review.operation,
            'quantity': review.work_quantity,
            'reviewer': review.approved_by,
        })
    
    # 按時間排序
    recent_reviews.sort(key=lambda x: x['time'], reverse=True)
    recent_reviews = recent_reviews[:5]  # 只取前5筆
    
    context = {
        'stats': stats,
        'recent_reviews': recent_reviews,
    }
    
    return render(request, 'workorder/report/manager/index.html', context)

def operator_report_index(request):
    """
    作業員報工首頁視圖
    顯示作業員報工的主要功能卡片和統計資訊
    """
    from datetime import date, timedelta
    from django.db.models import Q
    from .models import OperatorSupplementReport
    
    today = date.today()
    month_start = today.replace(day=1)
    
    # 計算真實的統計資料
    today_reports = OperatorSupplementReport.objects.filter(
        work_date=today
    ).count()
    
    month_reports = OperatorSupplementReport.objects.filter(
        work_date__gte=month_start,
        work_date__lte=today
    ).count()
    
    pending_reviews = OperatorSupplementReport.objects.filter(
        approval_status='pending'
    ).count()
    
    approved_reports = OperatorSupplementReport.objects.filter(
        approval_status='approved'
    ).count()
    
    # 取得最近報工記錄
    recent_reports = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).order_by('-created_at')[:10]
    
    context = {
        'today_reports': today_reports,
        'month_reports': month_reports,
        'pending_reviews': pending_reviews,
        'approved_reports': approved_reports,
        'recent_reports': recent_reports,
    }
    
    return render(request, 'workorder/report/operator/index.html', context)

def smt_report_index(request):
    """
    SMT報工首頁視圖
    顯示SMT報工的主要功能卡片和統計資訊
    """
    from datetime import date
    from equip.models import Equipment
    from .models import SMTProductionReport
    
    today = date.today()
    
    # 取得 SMT 設備列表
    equipment_list = Equipment.objects.filter(
        models.Q(name__icontains='SMT') | 
        models.Q(name__icontains='貼片') |
        models.Q(name__icontains='Pick') |
        models.Q(name__icontains='Place')
    ).order_by('name')
    
    # 計算統計資料
    running_equipment = equipment_list.filter(status='running').count()
    today_output = SMTProductionReport.objects.filter(
        work_date=today
    ).aggregate(total=models.Sum('work_quantity'))['total'] or 0
    
    # 計算設備效率（運轉中設備的平均效率）
    if running_equipment > 0:
        equipment_efficiency = 95  # 假設運轉中設備效率為95%
    else:
        equipment_efficiency = 0
    
    abnormal_equipment = equipment_list.filter(status='maintenance').count()
    
    # 取得最近SMT報工記錄
    recent_reports = SMTProductionReport.objects.select_related(
        'workorder', 'equipment'
    ).order_by('-created_at')[:10]
    
    context = {
        'running_equipment': running_equipment,
        'today_output': today_output,
        'equipment_efficiency': equipment_efficiency,
        'abnormal_equipment': abnormal_equipment,
        'equipment_list': equipment_list,
        'recent_reports': recent_reports,
    }
    
    return render(request, 'workorder/report/smt/index.html', context)

def smt_on_site_report(request):
    """
    SMT現場報工首頁視圖
    顯示SMT現場報工的主要功能，包含即時報工表單和設備狀態
    SMT設備為自動化運作，不需要作業員
    """
    from equip.models import Equipment
    from datetime import date
    from .models import SMTProductionReport
    
    # 取得 SMT 設備列表（假設設備名稱包含 'SMT' 或 '貼片'）
    equipment_list = Equipment.objects.filter(
        models.Q(name__icontains='SMT') | 
        models.Q(name__icontains='貼片') |
        models.Q(name__icontains='Pick') |
        models.Q(name__icontains='Place')
    ).order_by('name')
    
    # 準備設備狀態資料（使用真實設備資料）
    equipment_status = []
    active_count = 0
    
    for equipment in equipment_list:
        # 使用真實的設備狀態
        status = equipment.status
        
        if status == 'running':
            active_count += 1
        
        # 查詢該設備的當前工單
        current_workorder = None
        try:
            # 查找分配給該設備且正在進行的工序
            current_process = WorkOrderProcess.objects.filter(
                assigned_equipment=equipment.name,
                status='in_progress'
            ).select_related('workorder').first()
            
            if current_process:
                current_workorder = current_process.workorder.order_number
        except:
            pass
        
            # 計算今日該設備的產出數量
    today_output = 0
    try:
        today_reports = SMTProductionReport.objects.filter(
            equipment=equipment,
            work_date=today
        )
        today_output = sum(report.work_quantity for report in today_reports)
    except:
        pass
        
        equipment_status.append({
            'id': equipment.id,
            'name': equipment.name,
            'status': status,
            'status_display': equipment.get_status_display(),
            'current_workorder': current_workorder,
            'running_hours': 0,  # 暫時設為0，實際應該從設備監控系統取得
            'output_quantity': today_output,
            'efficiency': 95 if status == 'running' else (85 if status == 'idle' else 0),  # 運轉中95%，閒置85%，維修0%
            'last_update': equipment.updated_at
        })
    
    # 取得今日的 SMT 報工記錄
    today = date.today()
    today_reports_list = SMTProductionReport.objects.filter(
        report_time__date=today
    ).select_related('equipment', 'workorder').order_by('-report_time')
    
    # 計算統計資料
    today_reports_count = today_reports_list.count()
    current_shift_output = sum(report.quantity for report in today_reports_list)
    
    # 準備統計資料
    context = {
        'active_equipment': active_count,
        'today_reports': today_reports_count,
        'current_shift_output': current_shift_output,
        'pending_reports': 0,  # 待處理報工（目前為0）
        'equipment_list': equipment_list,
        'equipment_status': equipment_status,
        'today_reports_list': today_reports_list,
    }
    
    return render(request, 'workorder/report/smt/on_site/index.html', context)


@require_POST
@csrf_exempt
def submit_smt_report(request):
    """
    API：提交 SMT 報工記錄
    SMT 設備為自動化運作，不需要作業員
    """
    try:
        equipment_id = request.POST.get('equipment_id')
        workorder_id = request.POST.get('workorder_id')
        quantity = request.POST.get('quantity')
        notes = request.POST.get('notes', '')
        
        # 基本驗證
        if not all([equipment_id, workorder_id, quantity]):
            return JsonResponse({
                'status': 'error',
                'message': '請填寫所有必要欄位'
            })
        
        # 取得設備和工單
        from equip.models import Equipment
        equipment = Equipment.objects.get(id=equipment_id)
        workorder = WorkOrder.objects.get(id=workorder_id)
        
        # 建立報工記錄
        from .models import SMTProductionReport
        report = SMTProductionReport.objects.create(
            equipment=equipment,
            workorder=workorder,
            work_quantity=int(quantity),
            remarks=notes
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'SMT 報工記錄提交成功',
            'report_id': report.id
        })
        
    except Equipment.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '找不到指定的設備'
        })
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '找不到指定的工單'
        })
    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': f'資料格式錯誤：{str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'提交失敗：{str(e)}'
        })

@require_GET
@csrf_exempt
def get_workorders_by_equipment(request):
    """
    API：根據設備 ID 獲取該設備的工單列表
    用於 SMT 現場報工系統中的工單選擇
    """
    try:
        equipment_id = request.GET.get('equipment_id')
        
        if not equipment_id:
            return JsonResponse({
                'status': 'error',
                'message': '請提供設備 ID'
            })
        
        # 取得設備
        from equip.models import Equipment
        try:
            equipment = Equipment.objects.get(id=equipment_id)
        except Equipment.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '找不到指定的設備'
            })
        
        # 查詢該設備相關的工單
        # 1. 從 WorkOrderProcess 中查找分配給該設備的工序
        # 2. 取得這些工序對應的工單
        workorder_processes = WorkOrderProcess.objects.filter(
            assigned_equipment=equipment.name,
            status__in=['pending', 'in_progress']
        ).select_related('workorder')
        
        # 去重並整理工單資料
        workorders = []
        seen_workorder_ids = set()
        
        for process in workorder_processes:
            workorder = process.workorder
            if workorder.id not in seen_workorder_ids:
                seen_workorder_ids.add(workorder.id)
                workorders.append({
                    'id': workorder.id,
                    'order_number': workorder.order_number,
                    'product_code': workorder.product_code,
                    'quantity': workorder.quantity,
                    'status': workorder.status,
                    'status_display': workorder.get_status_display(),
                    'process_name': process.process_name,
                    'process_status': process.status,
                    'process_status_display': process.get_status_display(),
                })
        
        # 如果沒有找到分配給該設備的工單，則顯示所有狀態為 pending 或 in_progress 的工單
        if not workorders:
            all_workorders = WorkOrder.objects.filter(
                status__in=['pending', 'in_progress']
            ).order_by('-created_at')[:20]  # 限制顯示前20筆
            
            for workorder in all_workorders:
                workorders.append({
                    'id': workorder.id,
                    'order_number': workorder.order_number,
                    'product_code': workorder.product_code,
                    'quantity': workorder.quantity,
                    'status': workorder.status,
                    'status_display': workorder.get_status_display(),
                    'process_name': '未分配',
                    'process_status': 'pending',
                    'process_status_display': '待生產',
                })
        
        return JsonResponse({
            'status': 'success',
            'equipment_name': equipment.name,
            'workorders': workorders,
            'count': len(workorders)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'獲取工單列表失敗：{str(e)}'
        })

# ==================== SMT 補登報工功能 ====================

def smt_supplement_report_index(request):
    """
    SMT補登報工首頁視圖
    顯示SMT補登報工的主要功能，包含補登記錄列表和統計資訊
    """
    from equip.models import Equipment
    from datetime import date, timedelta
    from .models import SMTProductionReport
    from django.db import models
    from django.core.paginator import Paginator
    
    # 取得查詢參數
    equipment_id = request.GET.get('equipment')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # 取得 SMT 設備列表
    equipment_list = Equipment.objects.filter(
        models.Q(name__icontains='SMT') | 
        models.Q(name__icontains='貼片') |
        models.Q(name__icontains='Pick') |
        models.Q(name__icontains='Place')
    ).order_by('name')
    
    # 查詢補登記錄
    supplement_reports = SMTProductionReport.objects.all()
    
    # 篩選條件
    if equipment_id:
        supplement_reports = supplement_reports.filter(equipment_id=equipment_id)
    if start_date:
        supplement_reports = supplement_reports.filter(work_date__gte=start_date)
    if end_date:
        supplement_reports = supplement_reports.filter(work_date__lte=end_date)
    
    # 排序
    supplement_reports = supplement_reports.order_by('-work_date', '-start_time')
    
    # 分頁
    paginator = Paginator(supplement_reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 統計資訊
    today = date.today()
    today_reports = SMTProductionReport.objects.filter(work_date=today)
    total_quantity = today_reports.aggregate(total=models.Sum('work_quantity'))['total'] or 0
    total_reports = today_reports.count()
    
    # 最近7天統計
    week_ago = today - timedelta(days=7)
    week_reports = SMTProductionReport.objects.filter(work_date__gte=week_ago)
    week_quantity = week_reports.aggregate(total=models.Sum('work_quantity'))['total'] or 0
    
    # 為每個記錄添加權限檢查
    for report in page_obj:
        report.can_edit = report.can_edit(request.user)
        report.can_delete = report.can_delete(request.user)
    
    context = {
        'page_obj': page_obj,
        'equipment_list': equipment_list,
        'selected_equipment': equipment_id,
        'start_date': start_date,
        'end_date': end_date,
        'today_quantity': total_quantity,
        'today_reports': total_reports,
        'week_quantity': week_quantity,
    }
    
    return render(request, 'workorder/report/smt/supplement/index.html', context)


def smt_supplement_report_create(request):
    """
    SMT補登報工創建視圖
    用於創建新的SMT補登報工記錄
    """
    from equip.models import Equipment
    from .forms import SMTSupplementReportForm
    
    if request.method == 'POST':
        # 處理 RD樣品模式下的產品編號
        post_data = request.POST.copy()
        
        # 只有在 RD樣品模式下才處理 rd_sample_product_id
        if post_data.get('rd_sample_mode') == 'on':
            # RD樣品模式：使用 rd_sample_product_id 的值
            rd_sample_product_id = post_data.get('rd_sample_product_id')
            if rd_sample_product_id:
                post_data['product_id'] = rd_sample_product_id
        else:
            # 非RD樣品模式：移除 rd_sample_product_id，避免驗證錯誤
            if 'rd_sample_product_id' in post_data:
                del post_data['rd_sample_product_id']
        
        form = SMTSupplementReportForm(post_data, user=request.user)
        if form.is_valid():
            supplement_report = form.save(commit=False)
            supplement_report.created_by = request.user.username
            supplement_report.save()
            
            messages.success(request, 'SMT補登報工記錄已成功創建！')
            return redirect('workorder:smt_supplement_report_index')
    else:
        form = SMTSupplementReportForm(user=request.user)
    
    # 取得 SMT 設備列表
    equipment_list = Equipment.objects.filter(
        models.Q(name__icontains='SMT') | 
        models.Q(name__icontains='貼片') |
        models.Q(name__icontains='Pick') |
        models.Q(name__icontains='Place')
    ).order_by('name')
    
    context = {
        'form': form,
        'equipment_list': equipment_list,
    }
    
    return render(request, 'workorder/report/smt/supplement/form.html', context)


def smt_supplement_report_edit(request, report_id):
    """
    SMT補登報工編輯視圖
    用於編輯現有的SMT補登報工記錄
    """
    from .models import SMTProductionReport
    from .forms import SMTSupplementReportForm
    from equip.models import Equipment
    
    supplement_report = get_object_or_404(SMTProductionReport, id=report_id)
    
    # 檢查編輯權限
    if not supplement_report.can_edit(request.user):
        messages.error(request, '此記錄已核准，只有超級管理員可以編輯！')
        return redirect('workorder:smt_supplement_report_index')
    
    if request.method == 'POST':
        # 處理 RD樣品模式下的產品編號
        post_data = request.POST.copy()
        
        # 只有在 RD樣品模式下才處理 rd_sample_product_id
        if post_data.get('rd_sample_mode') == 'on':
            # RD樣品模式：使用 rd_sample_product_id 的值
            rd_sample_product_id = post_data.get('rd_sample_product_id')
            if rd_sample_product_id:
                post_data['product_id'] = rd_sample_product_id
        else:
            # 非RD樣品模式：移除 rd_sample_product_id，避免驗證錯誤
            if 'rd_sample_product_id' in post_data:
                del post_data['rd_sample_product_id']
        
        form = SMTSupplementReportForm(post_data, instance=supplement_report, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'SMT補登報工記錄已成功更新！')
            return redirect('workorder:smt_supplement_report_index')
    else:
        form = SMTSupplementReportForm(instance=supplement_report, user=request.user)
    
    # 取得 SMT 設備列表
    equipment_list = Equipment.objects.filter(
        models.Q(name__icontains='SMT') | 
        models.Q(name__icontains='貼片') |
        models.Q(name__icontains='Pick') |
        models.Q(name__icontains='Place')
    ).order_by('name')
    
    context = {
        'form': form,
        'supplement_report': supplement_report,
        'equipment_list': equipment_list,
        'can_edit': supplement_report.can_edit(request.user),
        'can_delete': supplement_report.can_delete(request.user),
    }
    
    return render(request, 'workorder/report/smt/supplement/form.html', context)


def smt_supplement_report_delete(request, report_id):
    """
    SMT補登報工刪除視圖
    用於刪除SMT補登報工記錄
    """
    from .models import SMTProductionReport
    
    supplement_report = get_object_or_404(SMTProductionReport, id=report_id)
    
    # 檢查刪除權限
    if not supplement_report.can_delete(request.user):
        messages.error(request, '此記錄已核准，只有超級管理員可以刪除！')
        return redirect('workorder:smt_supplement_report_index')
    
    if request.method == 'POST':
        supplement_report.delete()
        messages.success(request, 'SMT補登報工記錄已成功刪除！')
        return redirect('workorder:smt_supplement_report_index')
    
    context = {
        'supplement_report': supplement_report,
        'can_delete': supplement_report.can_delete(request.user),
    }
    
    return render(request, 'workorder/report/smt/supplement/delete_confirm.html', context)


def smt_supplement_report_detail(request, report_id):
    """
    SMT補登報工詳情視圖
    用於查看SMT補登報工記錄的詳細資訊
    """
    from .models import SMTProductionReport
    
    supplement_report = get_object_or_404(SMTProductionReport, id=report_id)
    
    context = {
        'supplement_report': supplement_report,
    }
    
    context = {
        'supplement_report': supplement_report,
        'can_edit': supplement_report.can_edit(request.user),
        'can_delete': supplement_report.can_delete(request.user),
    }
    
    return render(request, 'workorder/report/smt/supplement/detail.html', context)





@require_POST
@csrf_exempt
def smt_supplement_report_approve(request, report_id):
    """
    AJAX：SMT補登報工審核通過
    """
    try:
        from .models import SMTProductionReport
        
        report = SMTProductionReport.objects.get(id=report_id)
        
        # 檢查權限
        if not report.can_approve(request.user):
            return JsonResponse({
                'success': False,
                'message': '您沒有權限審核此記錄'
            })
        
        # 審核通過
        remarks = request.POST.get('remarks', '')
        report.approve(request.user, remarks)
        
        return JsonResponse({
            'success': True,
            'message': '審核通過成功！'
        })
        
    except SMTProductionReport.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的SMT補登報工記錄'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'審核失敗：{str(e)}'
        })


@require_POST
@csrf_exempt
def smt_supplement_report_reject(request, report_id):
    """
    AJAX：SMT補登報工駁回
    """
    try:
        from .models import SMTProductionReport
        
        report = SMTProductionReport.objects.get(id=report_id)
        
        # 檢查權限
        if not report.can_approve(request.user):
            return JsonResponse({
                'success': False,
                'message': '您沒有權限駁回此記錄'
            })
        
        # 駁回
        reason = request.POST.get('reason', '')
        if not reason:
            return JsonResponse({
                'success': False,
                'message': '請填寫駁回原因'
            })
        
        report.reject(request.user, reason)
        
        return JsonResponse({
            'success': True,
            'message': '駁回成功！'
        })
        
    except SMTProductionReport.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的SMT補登報工記錄'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'駁回失敗：{str(e)}'
        })


@require_POST
@csrf_exempt
def smt_supplement_batch_create(request):
    """
    SMT補登報工批量創建API
    用於批量創建SMT補登報工記錄
    """
    try:
        from .models import SMTProductionReport
        from equip.models import Equipment
        
        data = json.loads(request.body)
        reports_data = data.get('reports', [])
        
        created_reports = []
        errors = []
        
        for report_data in reports_data:
            try:
                # 驗證必要欄位
                required_fields = ['equipment_id', 'workorder_id', 'quantity']
                for field in required_fields:
                    if not report_data.get(field):
                        errors.append(f'記錄缺少必要欄位: {field}')
                        continue
                
                # 取得設備和工單
                equipment = Equipment.objects.get(id=report_data['equipment_id'])
                workorder = WorkOrder.objects.get(id=report_data['workorder_id'])
                
                # 處理報工時間
                report_time = timezone.now()
                if report_data.get('report_time'):
                    try:
                        report_time = timezone.make_aware(
                            datetime.strptime(report_data['report_time'], '%Y-%m-%d %H:%M:%S')
                        )
                    except ValueError:
                        errors.append(f'報工時間格式錯誤: {report_data["report_time"]}')
                        continue
                
                # 創建補登記錄
                report = SMTProductionReport.objects.create(
                    equipment=equipment,
                    workorder=workorder,
                    work_quantity=report_data['quantity'],
                    remarks=report_data.get('notes', ''),
                )
                
                created_reports.append({
                    'id': report.id,
                    'equipment': equipment.name,
                    'workorder': workorder.order_number,
                    'quantity': report.work_quantity,
                })
                
            except Equipment.DoesNotExist:
                errors.append(f'找不到設備 ID: {report_data.get("equipment_id")}')
            except WorkOrder.DoesNotExist:
                errors.append(f'找不到工單 ID: {report_data.get("workorder_id")}')
            except Exception as e:
                errors.append(f'創建記錄失敗: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'created_reports': created_reports,
            'errors': errors,
            'message': f'成功創建 {len(created_reports)} 筆記錄，{len(errors)} 筆錯誤'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'JSON 格式錯誤'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'批量創建失敗: {str(e)}'
        })


@require_GET
@csrf_exempt
def get_workorders_by_product(request):
    """
    AJAX 視圖：根據產品編號取得相關工單
    用於 SMT 補登報工表單的產品編號和工單聯動
    """
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({
            'status': 'error',
            'message': '請提供產品編號'
        })
    
    try:
        from .models import WorkOrder
        
        # 查詢該產品編號的所有工單（補登報工應該能選擇所有派工單，不限狀態）
        workorders = WorkOrder.objects.filter(
            product_code=product_id
        ).order_by('-created_at')
        
        workorder_list = []
        for workorder in workorders:
            workorder_list.append({
                'id': workorder.id,
                'order_number': workorder.order_number,
                'company_code': workorder.company_code,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'status': workorder.get_status_display(),
                'created_at': workorder.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'status': 'success',
            'workorders': workorder_list,
            'count': len(workorder_list)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'查詢失敗：{str(e)}'
        })


@require_GET
@csrf_exempt
def get_workorder_details(request):
    """
    AJAX 視圖：根據工單ID或工單編號取得工單詳細資訊
    用於 SMT 補登報工表單的工單資訊顯示
    """
    workorder_id = request.GET.get('workorder_id')
    workorder_number = request.GET.get('workorder_number')
    
    if not workorder_id and not workorder_number:
        return JsonResponse({
            'status': 'error',
            'message': '請提供工單ID或工單編號'
        })
    
    try:
        from .models import WorkOrder
        
        # 優先使用工單編號查詢，如果沒有則使用ID
        if workorder_number:
            workorder = WorkOrder.objects.get(order_number=workorder_number)
        else:
            workorder = WorkOrder.objects.get(id=workorder_id)
        
        return JsonResponse({
            'status': 'success',
            'workorder': {
                'id': workorder.id,
                'order_number': workorder.order_number,
                'company_code': workorder.company_code,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'status': workorder.get_status_display(),
                'created_at': workorder.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'work_date': workorder.work_date.strftime('%Y-%m-%d') if hasattr(workorder, 'work_date') and workorder.work_date else '',
            }
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '找不到指定的工單'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'查詢失敗：{str(e)}'
        })


@require_GET
@csrf_exempt
def get_smt_workorders_by_equipment(request):
    """
    API：根據設備取得可用的工單列表
    用於SMT補登報工中的工單選擇
    """
    try:
        equipment_id = request.GET.get('equipment_id')
        
        if not equipment_id:
            return JsonResponse({
                'success': False,
                'message': '缺少設備ID參數'
            })
        
        # 取得該設備的相關工單
        from equip.models import Equipment
        equipment = Equipment.objects.get(id=equipment_id)
        
        # 取得該設備的工單（這裡可以根據實際業務邏輯調整）
        workorders = WorkOrder.objects.filter(
            status__in=['in_progress', 'completed']
        ).order_by('-created_at')[:50]  # 限制數量避免過載
        
        workorder_list = []
        for workorder in workorders:
            workorder_list.append({
                'id': workorder.id,
                'order_number': workorder.order_number,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'status': workorder.get_status_display(),
            })
        
        return JsonResponse({
            'success': True,
            'workorders': workorder_list,
            'equipment_name': equipment.name
        })
        
    except Equipment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的設備'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'取得工單列表失敗: {str(e)}'
        })

# ==================== 作業員報工功能 ====================

def operator_on_site_report(request):
    """
    作業員現場報工頁面
    """
    from datetime import datetime, date
    from django.db.models import Q, Count, Sum
    from process.models import Operator, ProcessName
    from .models import OperatorSupplementReport
    
    # 取得統計資料
    today = date.today()
    working_operators = Operator.objects.count()  # 暫時使用總數，因為沒有status欄位
    
    # 計算今日報工數量
    today_reports = OperatorSupplementReport.objects.filter(
        work_date=today
    ).count()
    
    active_workorders = WorkOrder.objects.filter(status__in=['in_progress', 'paused']).count()
    pending_workorders = WorkOrder.objects.filter(status='pending').count()
    available_workorders = WorkOrder.objects.filter(status__in=['pending', 'in_progress', 'paused']).count()
    
    # 取得作業員列表
    operator_list = Operator.objects.all().order_by('name')
    
    # 取得進行中的工單（包含正在生產中和暫停的工單）
    active_workorders_list = WorkOrder.objects.filter(
        status__in=['in_progress', 'paused']
    ).prefetch_related('processes').order_by('-created_at')[:10]
    
    # 調試資訊
    print(f"🔍 進行中工單數量：{active_workorders_list.count()}")
    for wo in active_workorders_list:
        print(f"  - {wo.order_number}: {wo.get_status_display()}")
    
    # 取得可選擇的工單（包含待生產、進行中和暫停的工單，供快速報工表單使用）
    available_workorders_list = WorkOrder.objects.filter(
        status__in=['pending', 'in_progress', 'paused']
    ).prefetch_related('processes').order_by('-created_at')[:10]
    
    # 取得工序列表
    process_list = ProcessName.objects.filter(
        ~Q(name__icontains='SMT')  # 排除SMT相關工序
    ).order_by('name')
    
    # 取得設備列表
    from equip.models import Equipment
    equipment_list = Equipment.objects.all().order_by('name')
    
    # 取得作業員狀態
    operator_status_list = []
    for operator in operator_list:
        # 查找該作業員正在進行的工序
        current_process = WorkOrderProcess.objects.filter(
            assigned_operator=operator.name,
            status='in_progress'
        ).first()
        
        current_workorder = current_process.workorder if current_process else None
        current_process_name = current_process.process_name if current_process else '-'
        
        # 計算該作業員今日報工數量
        today_operator_reports = OperatorSupplementReport.objects.filter(
            operator=operator,
            work_date=today
        ).count()
        
        operator_status_list.append({
            'id': operator.id,
            'name': operator.name,
            'employee_id': '-',  # Operator模型沒有employee_id欄位
            'status': 'working' if current_process else 'available',
            'current_workorder': current_workorder.order_number if current_workorder else '-',
            'current_process': current_process_name,
            'today_reports': today_operator_reports,
            'last_update': getattr(operator, 'updated_at', datetime.now())
        })
    
    # 取得最近報工記錄
    recent_reports = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).order_by('-created_at')[:10]
    
    context = {
        'working_operators': working_operators,
        'today_reports': today_reports,
        'active_workorders': active_workorders,
        'pending_workorders': pending_workorders,
        'operator_list': operator_list,
        'active_workorders_list': active_workorders_list,  # 進行中的工單（顯示用）
        'available_workorders_list': available_workorders_list,  # 可選擇的工單（表單用）
        'process_list': process_list,
        'equipment_list': equipment_list,  # 新增設備列表
        'operator_status_list': operator_status_list,
        'recent_reports': recent_reports,
    }
    
    return render(request, 'workorder/report/operator/on_site/index.html', context)


@require_GET
@csrf_exempt
def get_workorder_info(request):
    """
    AJAX：獲取工單資訊
    """
    try:
        workorder_id = request.GET.get('workorder_id')
        
        if not workorder_id:
            return JsonResponse({
                'success': False,
                'message': '請提供工單ID'
            })
        
        workorder = WorkOrder.objects.get(id=workorder_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'order_number': workorder.order_number,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'status': workorder.status,
            }
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的工單'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'獲取工單資訊失敗：{str(e)}'
        })


@require_POST
@csrf_exempt
def operator_change_status(request):
    """
    變更工單狀態：開始生產、暫停、完工
    """
    try:
        workorder_id = request.POST.get('workorder_id')
        action_type = request.POST.get('action_type')
        
        if not workorder_id or not action_type:
            return JsonResponse({
                'success': False,
                'message': '缺少必要參數！'
            })
        
        workorder = WorkOrder.objects.get(id=workorder_id)
        
        # 根據操作類型變更狀態
        if action_type == 'start':
            if workorder.status == 'pending':
                workorder.status = 'in_progress'
                message = '工單已開始生產！'
                
                # 更新第一個待生產的工序狀態
                try:
                    first_pending_process = workorder.processes.filter(status='pending').order_by('step_order').first()
                    if first_pending_process:
                        first_pending_process.status = 'in_progress'
                        first_pending_process.actual_start_time = timezone.now()
                        first_pending_process.save()
                        print(f"✅ 工序狀態已更新：{first_pending_process.process_name} -> 生產中")
                except Exception as e:
                    print(f"⚠️ 更新工序狀態失敗：{str(e)}")
                    
            elif workorder.status == 'paused':
                workorder.status = 'in_progress'
                message = '工單已恢復生產！'
                
                # 恢復暫停的工序狀態
                try:
                    paused_process = workorder.processes.filter(status='paused').first()
                    if paused_process:
                        paused_process.status = 'in_progress'
                        paused_process.save()
                        print(f"✅ 工序狀態已更新：{paused_process.process_name} -> 生產中")
                except Exception as e:
                    print(f"⚠️ 更新工序狀態失敗：{str(e)}")
            else:
                return JsonResponse({
                    'success': False,
                    'message': '當前狀態無法開始生產！'
                })
                
        elif action_type == 'pause':
            if workorder.status == 'in_progress':
                workorder.status = 'paused'
                message = '工單已暫停！'
                
                # 暫停進行中的工序
                try:
                    in_progress_process = workorder.processes.filter(status='in_progress').first()
                    if in_progress_process:
                        in_progress_process.status = 'paused'
                        in_progress_process.save()
                        print(f"✅ 工序狀態已更新：{in_progress_process.process_name} -> 暫停")
                except Exception as e:
                    print(f"⚠️ 更新工序狀態失敗：{str(e)}")
            else:
                return JsonResponse({
                    'success': False,
                    'message': '只有生產中的工單可以暫停！'
                })
                
        elif action_type == 'complete':
            if workorder.status in ['in_progress', 'paused']:
                workorder.status = 'completed'
                message = '工單已完工！'
                
                # 完成所有未完成的工序
                try:
                    unfinished_processes = workorder.processes.filter(status__in=['pending', 'in_progress', 'paused'])
                    for process in unfinished_processes:
                        process.status = 'completed'
                        if not process.actual_start_time:
                            process.actual_start_time = timezone.now()
                        process.actual_end_time = timezone.now()
                        process.save()
                        print(f"✅ 工序狀態已更新：{process.process_name} -> 已完成")
                except Exception as e:
                    print(f"⚠️ 更新工序狀態失敗：{str(e)}")
            else:
                return JsonResponse({
                    'success': False,
                    'message': '只有生產中或暫停的工單可以完工！'
                })
        else:
            return JsonResponse({
                'success': False,
                'message': '無效的操作類型！'
            })
        
        workorder.save()
        
        # 記錄操作日誌
        try:
            first_process = workorder.processes.first()
            if first_process:
                WorkOrderProcessLog.objects.create(
                    workorder_process=first_process,
                    action='status_change',
                    operator=request.user.username if request.user.is_authenticated else 'system',
                    notes=f'工單狀態變更為：{workorder.get_status_display()}'
                )
        except Exception as e:
            print(f"⚠️ 記錄操作日誌失敗：{str(e)}")
        
        print(f"✅ 工單狀態已更新：{workorder.order_number} -> {workorder.get_status_display()}")
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '工單不存在！'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'系統錯誤：{str(e)}'
        })

@require_POST
@csrf_exempt
def operator_quick_report(request):
    """
    AJAX：作業員快速報工 - 支援報工、開始生產、暫停、完工
    """
    try:
        operator_id = request.POST.get('operator')
        workorder_id = request.POST.get('workorder')
        process_id = request.POST.get('process')
        quantity = request.POST.get('quantity')
        equipment_id = request.POST.get('equipment', '')  # 新增設備參數，可選
        action_type = request.POST.get('action_type', 'start')  # 預設為開始生產
        
        if not all([operator_id, workorder_id, process_id, quantity]):
            return JsonResponse({
                'success': False,
                'message': '請填寫所有必要欄位'
            })
        
        # 取得相關物件
        from process.models import Operator
        from equip.models import Equipment
        
        operator = Operator.objects.get(id=operator_id)
        workorder = WorkOrder.objects.get(id=workorder_id)
        process = ProcessName.objects.get(id=process_id)
        
        # 如果有選擇設備，取得設備物件
        equipment = None
        if equipment_id:
            try:
                equipment = Equipment.objects.get(id=equipment_id)
            except Equipment.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': '找不到指定的設備'
                })
        
        # 根據操作類型執行不同邏輯
        if action_type == 'start':
            # 開始生產（現場報工的核心邏輯）
            if workorder.status == 'pending':
                # 從待生產狀態開始：直接開始生產並記錄報工
                workorder.status = 'in_progress'
                message = '工單已開始生產！'
            elif workorder.status == 'paused':
                # 從暫停狀態恢復：恢復生產並記錄報工
                workorder.status = 'in_progress'
                message = '工單已恢復生產！'
            elif workorder.status == 'in_progress':
                # 生產中狀態：繼續生產並記錄報工
                message = '繼續生產並記錄報工！'
            else:
                return JsonResponse({
                    'success': False,
                    'message': '當前狀態無法開始生產！'
                })
            
            workorder.save()
            
            # 更新對應的工序狀態
            try:
                # 找到對應的工序並更新狀態
                workorder_process = workorder.processes.filter(process_name=process.name).first()
                
                if workorder_process:
                    # 如果工序已存在，更新狀態
                    workorder_process.status = 'in_progress'
                    workorder_process.assigned_operator = operator.name
                    if equipment:
                        workorder_process.assigned_equipment = equipment.name
                    workorder_process.actual_start_time = timezone.now()
                    workorder_process.save()
                    print(f"✅ 工序狀態已更新：{process.name} -> 生產中")
                else:
                    # 如果工序不存在，自動建立
                    from workorder.models import WorkOrderProcess
                    
                    # 取得下一個工序順序
                    max_step_order = workorder.processes.aggregate(
                        models.Max('step_order')
                    )['step_order__max'] or 0
                    next_step_order = max_step_order + 1
                    
                    # 建立新的工序
                    workorder_process = WorkOrderProcess.objects.create(
                        workorder=workorder,
                        process_name=process.name,
                        step_order=next_step_order,
                        planned_quantity=int(quantity),
                        status='in_progress',
                        assigned_operator=operator.name,
                        assigned_equipment=equipment.name if equipment else None,
                        actual_start_time=timezone.now()
                    )
                    print(f"✅ 自動建立新工序：{process.name} -> 生產中")
                    
            except Exception as e:
                print(f"⚠️ 更新工序狀態失敗：{str(e)}")
            
            # 記錄現場報工資訊
            print(f"現場報工記錄：")
            print(f"  作業員：{operator.name}")
            print(f"  工單：{workorder.order_number}")
            print(f"  工序：{process.name}")
            print(f"  數量：{quantity}")
            print(f"  設備：{equipment.name if equipment else '未選擇'}")
            print(f"  操作：開始生產")
            
        elif action_type == 'pause':
            # 暫停生產
            if workorder.status == 'in_progress':
                workorder.status = 'paused'
                message = '工單已暫停生產！'
                
                # 更新對應的工序狀態
                try:
                    workorder_process = workorder.processes.filter(status='in_progress').first()
                    if workorder_process:
                        workorder_process.status = 'paused'
                        workorder_process.save()
                        print(f"✅ 工序狀態已更新：{workorder_process.process_name} -> 暫停")
                except Exception as e:
                    print(f"⚠️ 更新工序狀態失敗：{str(e)}")
            else:
                return JsonResponse({
                    'success': False,
                    'message': '只有生產中的工單可以暫停！'
                })
            workorder.save()
            
        elif action_type == 'complete':
            # 完工
            if workorder.status in ['in_progress', 'paused']:
                workorder.status = 'completed'
                message = '工單已完工！'
                
                # 更新對應的工序狀態
                try:
                    workorder_process = workorder.processes.filter(status__in=['in_progress', 'paused']).first()
                    if workorder_process:
                        workorder_process.status = 'completed'
                        workorder_process.actual_end_time = timezone.now()
                        workorder_process.completed_quantity = int(quantity)
                        workorder_process.save()
                        print(f"✅ 工序狀態已更新：{workorder_process.process_name} -> 已完成")
                except Exception as e:
                    print(f"⚠️ 更新工序狀態失敗：{str(e)}")
            else:
                return JsonResponse({
                    'success': False,
                    'message': '只有生產中或暫停的工單可以完工！'
                })
            workorder.save()
            
        else:
            return JsonResponse({
                'success': False,
                'message': '無效的操作類型！'
            })
        
        # 記錄操作日誌
        if workorder.processes.exists():
            log_action = 'start' if action_type == 'start' else 'status_change'
            WorkOrderProcessLog.objects.create(
                workorder_process=workorder.processes.first(),
                action=log_action,
                operator=operator.name,
                equipment=equipment.name if equipment else None,
                notes=f'現場報工：{action_type} - 數量：{quantity}'
            )
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except Operator.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的作業員'
        })
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的工單'
        })
    except ProcessName.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的工序'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'操作失敗：{str(e)}'
        })


@require_POST
@csrf_exempt
def operator_start_process(request):
    """
    AJAX：開始工序
    """
    try:
        workorder_id = request.POST.get('workorder_id')
        
        if not workorder_id:
            return JsonResponse({
                'success': False,
                'message': '請提供工單ID'
            })
        
        # 這裡需要實作實際的工序開始邏輯
        
        return JsonResponse({
            'success': True,
            'message': '工序已開始！'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'操作失敗：{str(e)}'
        })


@require_POST
@csrf_exempt
def operator_delete_workorder(request):
    """
    AJAX：刪除工單（只有超級管理員可以使用）
    """
    try:
        # 檢查權限
        if not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'message': '只有超級管理員可以刪除工單！'
            })
        
        workorder_id = request.POST.get('workorder_id')
        
        if not workorder_id:
            return JsonResponse({
                'success': False,
                'message': '請提供工單ID'
            })
        
        # 取得工單
        workorder = WorkOrder.objects.get(id=workorder_id)
        workorder_number = workorder.order_number
        
        # 刪除工單（會自動刪除相關的工序）
        workorder.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'工單 {workorder_number} 已成功刪除！'
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的工單'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'刪除工單失敗：{str(e)}'
        })


def operator_report_progress(request):
    """
    作業員進度報工頁面
    """
    workorder_id = request.GET.get('workorder_id')
    
    if not workorder_id:
        messages.error(request, '請提供工單ID')
        return redirect('workorder:operator_on_site_report')
    
    try:
        workorder = WorkOrder.objects.get(id=workorder_id)
        context = {
            'workorder': workorder,
        }
        return render(request, 'workorder/report/operator/progress_form.html', context)
    except WorkOrder.DoesNotExist:
        messages.error(request, '找不到指定的工單')
        return redirect('workorder:operator_on_site_report')


def operator_workorder_detail(request):
    """
    作業員工單詳情頁面
    """
    workorder_id = request.GET.get('workorder_id')
    
    if not workorder_id:
        messages.error(request, '請提供工單ID')
        return redirect('workorder:operator_on_site_report')
    
    try:
        workorder = WorkOrder.objects.prefetch_related('processes').get(id=workorder_id)
        context = {
            'workorder': workorder,
        }
        return render(request, 'workorder/report/operator/workorder_detail.html', context)
    except WorkOrder.DoesNotExist:
        messages.error(request, '找不到指定的工單')
        return redirect('workorder:operator_on_site_report')


def operator_assign_workorder(request):
    """
    作業員派工頁面 - 已移至派工單管理模組
    此功能已不在此模組處理，請使用派工單管理模組的派工功能
    """
    messages.warning(request, '派工功能已移至派工單管理模組，請使用派工單管理進行派工操作')
    return redirect('workorder:operator_on_site_report')


def operator_report_work(request):
    """
    作業員報工頁面
    """
    operator_id = request.GET.get('operator_id')
    
    if not operator_id:
        messages.error(request, '請提供作業員ID')
        return redirect('workorder:operator_on_site_report')
    
    try:
        from process.models import Operator
        operator = Operator.objects.get(id=operator_id)
        
        # 取得該作業員的工單
        workorders = WorkOrder.objects.filter(
            status='in_progress'
        ).order_by('-created_at')
        
        context = {
            'operator': operator,
            'workorders': workorders,
        }
        return render(request, 'workorder/report/operator/report_work.html', context)
    except Operator.DoesNotExist:
        messages.error(request, '找不到指定的作業員')
        return redirect('workorder:operator_on_site_report')


def operator_detail(request):
    """
    作業員詳情頁面
    """
    operator_id = request.GET.get('operator_id')
    
    if not operator_id:
        messages.error(request, '請提供作業員ID')
        return redirect('workorder:operator_on_site_report')
    
    try:
        from process.models import Operator
        from datetime import date
        from .models import OperatorSupplementReport
        
        operator = Operator.objects.get(id=operator_id)
        today = date.today()
        
        # 計算該作業員的統計資料
        # 今日工單數量
        today_workorders = OperatorSupplementReport.objects.filter(
            operator=operator,
            work_date=today
        ).values('workorder').distinct().count()
        
        # 今日工作時數
        today_reports = OperatorSupplementReport.objects.filter(
            operator=operator,
            work_date=today
        )
        total_hours = sum(report.work_hours or 0 for report in today_reports)
        
        # 完成率（今日完成的工單數 / 今日總工單數）
        completed_workorders = today_reports.filter(is_completed=True).count()
        completion_rate = (completed_workorders / today_workorders * 100) if today_workorders > 0 else 0
        
        # 最近工作記錄
        recent_reports = OperatorSupplementReport.objects.filter(
            operator=operator
        ).select_related('workorder', 'process').order_by('-created_at')[:10]
        
        context = {
            'operator': operator,
            'today_workorders': today_workorders,
            'total_hours': round(total_hours, 1),
            'completion_rate': round(completion_rate, 1),
            'recent_reports': recent_reports,
        }
        return render(request, 'workorder/report/operator/operator_detail.html', context)
    except Operator.DoesNotExist:
        messages.error(request, '找不到指定的作業員')
        return redirect('workorder:operator_on_site_report')


def operator_report_detail(request):
    """
    作業員報工詳情頁面
    """
    report_id = request.GET.get('report_id')
    
    if not report_id:
        messages.error(request, '請提供報工記錄ID')
        return redirect('workorder:operator_on_site_report')
    
    try:
        # 這裡需要根據實際的報工記錄模型取得資料
        context = {
            'report': None,  # 暫時設為None
        }
        return render(request, 'workorder/report/operator/report_detail.html', context)
    except Exception as e:
        messages.error(request, f'取得報工記錄失敗：{str(e)}')
        return redirect('workorder:operator_on_site_report')


# ==================== 作業員補登報工功能 ====================

def operator_supplement_report_index(request):
    """
    作業員補登報工列表頁面
    """
    from datetime import date
    from django.core.paginator import Paginator
    from django.db.models import Q
    from .models import OperatorSupplementReport
    
    # 取得篩選參數
    operator = request.GET.get('operator')
    workorder = request.GET.get('workorder')
    process = request.GET.get('process')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # 查詢補登報工記錄
    supplement_reports = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).all()
    
    # 應用篩選條件
    if operator:
        supplement_reports = supplement_reports.filter(operator__name__icontains=operator)
    if workorder:
        supplement_reports = supplement_reports.filter(workorder__order_number__icontains=workorder)
    if process:
        supplement_reports = supplement_reports.filter(process__name__icontains=process)
    if status:
        supplement_reports = supplement_reports.filter(approval_status=status)
    if date_from:
        supplement_reports = supplement_reports.filter(work_date__gte=date_from)
    if date_to:
        supplement_reports = supplement_reports.filter(work_date__lte=date_to)
    
    # 分頁
    paginator = Paginator(supplement_reports, 20)
    page_number = request.GET.get('page')
    supplement_reports_page = paginator.get_page(page_number)
    
    # 取得統計資料
    pending_reports = OperatorSupplementReport.objects.filter(approval_status='pending').count()
    approved_reports = OperatorSupplementReport.objects.filter(approval_status='approved').count()
    rejected_reports = OperatorSupplementReport.objects.filter(approval_status='rejected').count()
    
    # 取得篩選選項
    from process.models import Operator, ProcessName
    
    operator_list = Operator.objects.all().order_by('name')
    process_list = ProcessName.objects.filter(
        ~Q(name__icontains='SMT')  # 排除SMT相關工序
    ).order_by('name')
    
    context = {
        'supplement_reports': supplement_reports_page,
        'pending_reports': pending_reports,
        'approved_reports': approved_reports,
        'rejected_reports': rejected_reports,
        'operator_list': operator_list,
        'process_list': process_list,
        'selected_operator': operator,
        'selected_workorder': workorder,
        'selected_process': process,
        'selected_status': status,
        'selected_date_from': date_from,
        'selected_date_to': date_to,
    }
    
    return render(request, 'workorder/report/operator/supplement/index.html', context)


def operator_supplement_report_create(request):
    """
    作業員補登報工新增頁面
    支援兩種報工模式：正式報工和RD樣品報工
    """
    from datetime import date, time
    from process.models import Operator, ProcessName
    from .models import OperatorSupplementReport, WorkOrder
    from .forms import OperatorSupplementReportForm
    
    if request.method == 'POST':
        form = OperatorSupplementReportForm(request.POST)
        form.request = request  # 傳遞request給表單
        
        if form.is_valid():
            try:
                # 直接儲存表單，時間欄位已在表單的save()方法中處理
                supplement_report = form.save()
                
                messages.success(request, '作業員補登報工記錄建立成功！')
                return redirect('workorder:operator_supplement_report_index')
            except Exception as e:
                messages.error(request, f'儲存失敗：{str(e)}')
        else:
            # 顯示表單驗證錯誤
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{form.fields[field].label}: {error}")
            
            if error_messages:
                messages.error(request, f'表單驗證失敗：{"；".join(error_messages)}')
            else:
                messages.error(request, '表單驗證失敗，請檢查輸入資料')
    else:
        # 設定預設值
        initial_data = {
            'start_time': '08:30',
            'end_time': '17:30',
        }
        form = OperatorSupplementReportForm(initial=initial_data)
        form.request = request  # 傳遞request給表單
    
    context = {
        "form": form,
        "is_create": True,
        "page_title": "新增作業員補登報工記錄",
    }
    
    return render(request, 'workorder/report/operator/supplement/form.html', context)


def operator_supplement_report_edit(request, report_id):
    """
    作業員補登報工編輯頁面
    支援兩種報工模式：正式報工和RD樣品報工
    """
    from datetime import date, time
    from process.models import Operator, ProcessName
    from .models import OperatorSupplementReport, WorkOrder
    from .forms import OperatorSupplementReportForm
    
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的補登報工記錄')
        return redirect('workorder:operator_supplement_report_index')
    
    # 檢查權限
    if not report.can_edit(request.user):
        messages.error(request, '您沒有權限編輯此記錄')
        return redirect('workorder:operator_supplement_report_detail', report_id=report_id)
    
    if request.method == 'POST':
        form = OperatorSupplementReportForm(request.POST, instance=report)
        form.request = request  # 傳遞request給表單
        
        if form.is_valid():
            try:
                # 直接儲存表單，時間欄位已在表單的save()方法中處理
                supplement_report = form.save()
                
                messages.success(request, '作業員補登報工記錄更新成功！')
                return redirect('workorder:operator_supplement_report_index')
            except Exception as e:
                messages.error(request, f'更新失敗：{str(e)}')
        else:
            messages.error(request, '表單驗證失敗，請檢查輸入資料')
    else:
        # 初始化表單，將時間轉換為字串格式
        initial_data = {
            'start_time': report.start_time.strftime('%H:%M') if report.start_time else '16:00',
            'end_time': report.end_time.strftime('%H:%M') if report.end_time else '18:30',
        }
        
        # 根據記錄類型設定初始值
        if report.report_type == 'rd_sample':
            initial_data['report_type'] = 'rd_sample'
            initial_data['product_id'] = report.rd_product_code or ''
        else:
            initial_data['report_type'] = 'normal'
            if report.workorder:
                initial_data['product_id'] = report.workorder.product_code
                initial_data['workorder'] = report.workorder.id
        
        form = OperatorSupplementReportForm(instance=report, initial=initial_data)
        form.request = request  # 傳遞request給表單
    
    context = {
        'form': form,
        'report': report,
        'is_create': False,
        'page_title': '編輯作業員補登報工記錄',
    }
    
    return render(request, 'workorder/report/operator/supplement/form.html', context)


@require_POST
@csrf_exempt
def operator_supplement_report_delete(request, report_id):
    """
    AJAX：刪除作業員補登報工記錄
    """
    try:
        from .models import OperatorSupplementReport
        
        report = OperatorSupplementReport.objects.get(id=report_id)
        
        # 檢查權限
        if not report.can_delete(request.user):
            return JsonResponse({
                'success': False,
                'message': '您沒有權限刪除此記錄'
            })
        
        # 刪除記錄
        report.delete()
        
        return JsonResponse({
            'success': True,
            'message': '刪除成功！'
        })
        
    except OperatorSupplementReport.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的補登報工記錄'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'刪除失敗：{str(e)}'
        })


def operator_supplement_report_detail(request, report_id):
    """
    作業員補登報工詳情頁面
    """
    from .models import OperatorSupplementReport
    
    try:
        report = OperatorSupplementReport.objects.select_related(
            'operator', 'workorder', 'process'
        ).get(id=report_id)
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的補登報工記錄')
        return redirect('workorder:operator_supplement_report_index')
    
    context = {
        'report': report,
    }
    
    return render(request, 'workorder/report/operator/supplement/detail.html', context)


@require_POST
@csrf_exempt
def operator_supplement_report_approve(request, report_id):
    """
    AJAX：作業員補登報工審核通過
    """
    try:
        from .models import OperatorSupplementReport
        
        report = OperatorSupplementReport.objects.get(id=report_id)
        
        # 檢查權限
        if not report.can_approve(request.user):
            return JsonResponse({
                'success': False,
                'message': '您沒有權限審核此記錄'
            })
        
        # 審核通過
        remarks = request.POST.get('remarks', '')
        report.approve(request.user, remarks)
        
        return JsonResponse({
            'success': True,
            'message': '審核通過成功！'
        })
        
    except OperatorSupplementReport.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的補登報工記錄'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'審核失敗：{str(e)}'
        })


@require_POST
@csrf_exempt
def operator_supplement_report_reject(request, report_id):
    """
    AJAX：作業員補登報工駁回
    """
    try:
        from .models import OperatorSupplementReport
        
        report = OperatorSupplementReport.objects.get(id=report_id)
        
        # 檢查權限
        if not report.can_approve(request.user):
            return JsonResponse({
                'success': False,
                'message': '您沒有權限駁回此記錄'
            })
        
        # 駁回
        reason = request.POST.get('reason', '')
        if not reason:
            return JsonResponse({
                'success': False,
                'message': '請填寫駁回原因'
            })
        
        report.reject(request.user, reason)
        
        return JsonResponse({
            'success': True,
            'message': '駁回成功！'
        })
        
    except OperatorSupplementReport.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的補登報工記錄'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'駁回失敗：{str(e)}'
        })


def operator_supplement_batch(request):
    """
    作業員補登報工批量匯入頁面
    """
    if request.method == 'POST':
        # 這裡需要實作批量匯入邏輯
        messages.success(request, '批量匯入成功！')
        return redirect('workorder:operator_supplement_report_index')
    
    context = {}
    return render(request, 'workorder/report/operator/supplement/batch.html', context)


def operator_supplement_export(request):
    """
    作業員補登報工匯出功能
    """
    # 這裡需要實作匯出邏輯
    messages.success(request, '資料匯出成功！')
    return redirect('workorder:operator_supplement_report_index')


def operator_supplement_template(request):
    """
    作業員補登報工範本下載
    """
    # 這裡需要實作範本下載邏輯
    messages.success(request, '範本下載成功！')
    return redirect('workorder:operator_supplement_report_index')


@require_POST
@csrf_exempt
def operator_supplement_batch_create(request):
    """
    AJAX：批量建立作業員補登報工記錄
    """
    try:
        from .models import OperatorSupplementReport
        from .forms import OperatorSupplementBatchForm
        from datetime import datetime, timedelta
        
        form = OperatorSupplementBatchForm(request.POST)
        
        if not form.is_valid():
            return JsonResponse({
                'success': False,
                'message': '表單驗證失敗',
                'errors': form.errors
            })
        
        # 取得表單資料
        operator = form.cleaned_data['operator']
        workorder = form.cleaned_data['workorder']
        process = form.cleaned_data['process']
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        daily_quantity = form.cleaned_data['daily_quantity']
        start_time_str = form.cleaned_data['start_time']
        end_time_str = form.cleaned_data['end_time']
        notes = form.cleaned_data.get('notes', '')
        
        # 解析時間
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # 計算日期範圍
        current_date = start_date
        created_count = 0
        
        while current_date <= end_date:
            # 創建補登記錄
            supplement_report = OperatorSupplementReport(
                operator=operator,
                workorder=workorder,
                process=process,
                work_date=current_date,
                start_time=start_time,
                end_time=end_time,
                work_quantity=daily_quantity,
                defect_quantity=0,
                is_completed=False,
                remarks=notes,
                approval_status='pending',
                created_by=request.user.username
            )
            supplement_report.save()
            created_count += 1
            
            # 移到下一天
            current_date += timedelta(days=1)
        
        return JsonResponse({
            'success': True,
            'message': f'批量建立成功！共建立 {created_count} 筆記錄',
            'created_count': created_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'批量建立失敗：{str(e)}'
        })


@require_GET
@csrf_exempt
def get_workorders_by_operator(request):
    """
    API：根據作業員取得可用的工單列表
    """
    try:
        operator_id = request.GET.get('operator_id')
        
        if not operator_id:
            return JsonResponse({
                'success': False,
                'message': '缺少作業員ID參數'
            })
        
        # 取得該作業員的相關工單
        from process.models import Operator
        operator = Operator.objects.get(id=operator_id)
        
        # 取得可用的工單
        workorders = WorkOrder.objects.filter(
            status__in=['in_progress', 'completed']
        ).order_by('-created_at')[:50]  # 限制數量避免過載
        
        workorder_list = []
        for workorder in workorders:
            workorder_list.append({
                'id': workorder.id,
                'order_number': workorder.order_number,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'status': workorder.get_status_display(),
            })
        
        return JsonResponse({
            'success': True,
            'workorders': workorder_list,
            'operator_name': operator.name
        })
        
    except Operator.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的作業員'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'取得工單列表失敗: {str(e)}'
        })

# ==================== 管理者審核功能 ====================

from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import ManagerProductionReport
from .forms import (
    ManagerProductionReportForm, 
    ManagerProductionReportApprovalForm, 
    ManagerProductionReportRejectionForm,
    ManagerProductionReportBatchForm
)
from process.models import ProcessName, Operator
from equip.models import Equipment


class ManagerProductionReportListView(LoginRequiredMixin, ListView):
    """
    管理者生產報工記錄列表視圖
    顯示所有管理者審核記錄，支援搜尋、篩選和分頁
    """
    model = ManagerProductionReport
    template_name = 'workorder/manager_production_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        """取得查詢集"""
        queryset = ManagerProductionReport.objects.select_related(
            'workorder', 'process', 'equipment', 'operator'
        ).all()
        
        # 搜尋功能
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(manager__icontains=search) |
                Q(workorder__order_number__icontains=search) |
                Q(process__name__icontains=search) |
                Q(equipment__name__icontains=search) |
                Q(operator__name__icontains=search)
            )
        
        # 篩選功能
        manager = self.request.GET.get('manager')
        if manager:
            queryset = queryset.filter(manager__icontains=manager)
        
        workorder = self.request.GET.get('workorder')
        if workorder:
            queryset = queryset.filter(workorder__order_number__icontains=workorder)
        
        process = self.request.GET.get('process')
        if process:
            queryset = queryset.filter(process__name__icontains=process)
        
        approval_status = self.request.GET.get('approval_status')
        if approval_status:
            queryset = queryset.filter(approval_status=approval_status)
        
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(work_date__gte=start_date)
        
        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(work_date__lte=end_date)
        
        return queryset.order_by('-work_date', '-start_time')
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 統計資訊
        queryset = self.get_queryset()
        context['total_count'] = queryset.count()
        context['pending_count'] = queryset.filter(approval_status='pending').count()
        context['approved_count'] = queryset.filter(approval_status='approved').count()
        context['rejected_count'] = queryset.filter(approval_status='rejected').count()
        
        # 今日統計
        today = timezone.now().date()
        today_reports = queryset.filter(work_date=today)
        context['today_count'] = today_reports.count()
        context['today_quantity'] = sum(report.work_quantity for report in today_reports)
        
        # 本週統計
        week_start = today - timedelta(days=today.weekday())
        week_reports = queryset.filter(work_date__gte=week_start)
        context['week_count'] = week_reports.count()
        context['week_quantity'] = sum(report.work_quantity for report in week_reports)
        
        # 篩選選項
        context['managers'] = ManagerProductionReport.objects.values_list('manager', flat=True).distinct()
        context['processes'] = ProcessName.objects.all().order_by('name')
        context['approval_statuses'] = ManagerProductionReport.APPROVAL_STATUS_CHOICES
        
        return context


class ManagerProductionReportCreateView(LoginRequiredMixin, CreateView):
    """
    管理者生產報工記錄新增視圖
    """
    model = ManagerProductionReport
    form_class = ManagerProductionReportForm
    template_name = 'workorder/manager_production_form.html'
    success_url = reverse_lazy('workorder:manager_production_list')
    
    def form_valid(self, form):
        """表單驗證成功"""
        form.instance.created_by = self.request.user.username
        form.instance.planned_quantity = form.instance.workorder.quantity
        
        # 檢查自動完工狀態
        form.instance.check_auto_completion()
        
        response = super().form_valid(form)
        
        messages.success(self.request, '管理者生產報工記錄新增成功！')
        return response
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        context['title'] = '新增管理者生產報工記錄'
        context['submit_text'] = '新增記錄'
        return context


class ManagerProductionReportUpdateView(LoginRequiredMixin, UpdateView):
    """
    管理者生產報工記錄編輯視圖
    """
    model = ManagerProductionReport
    form_class = ManagerProductionReportForm
    template_name = 'workorder/manager_production_form.html'
    success_url = reverse_lazy('workorder:manager_production_list')
    
    def dispatch(self, request, *args, **kwargs):
        """檢查權限"""
        obj = self.get_object()
        if not obj.can_edit(request.user):
            messages.error(request, '您沒有權限編輯此記錄！')
            return redirect('workorder:manager_production_list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """表單驗證成功"""
        # 檢查自動完工狀態
        form.instance.check_auto_completion()
        
        response = super().form_valid(form)
        
        messages.success(self.request, '管理者生產報工記錄更新成功！')
        return response
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        context['title'] = '編輯管理者生產報工記錄'
        context['submit_text'] = '更新記錄'
        return context


class ManagerProductionReportDetailView(LoginRequiredMixin, DetailView):
    """
    管理者生產報工記錄詳情視圖
    """
    model = ManagerProductionReport
    template_name = 'workorder/manager_production_detail.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 檢查權限
        context['can_edit'] = self.object.can_edit(self.request.user)
        context['can_delete'] = self.object.can_delete(self.request.user)
        context['can_approve'] = self.object.can_approve(self.request.user)
        
        return context


class ManagerProductionReportDeleteView(LoginRequiredMixin, DeleteView):
    """
    管理者生產報工記錄刪除視圖
    """
    model = ManagerProductionReport
    template_name = 'workorder/manager_production_delete.html'
    success_url = reverse_lazy('workorder:manager_production_list')
    
    def dispatch(self, request, *args, **kwargs):
        """檢查權限"""
        obj = self.get_object()
        if not obj.can_delete(request.user):
            messages.error(request, '您沒有權限刪除此記錄！')
            return redirect('workorder:manager_production_list')
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        """刪除記錄"""
        messages.success(request, '管理者生產報工記錄刪除成功！')
        return super().delete(request, *args, **kwargs)


class ManagerProductionReportApproveView(LoginRequiredMixin, UpdateView):
    """
    管理者生產報工記錄審核通過視圖
    """
    model = ManagerProductionReport
    form_class = ManagerProductionReportApprovalForm
    template_name = 'workorder/manager_production_approve.html'
    success_url = reverse_lazy('workorder:manager_production_list')
    
    def dispatch(self, request, *args, **kwargs):
        """檢查權限"""
        obj = self.get_object()
        if not obj.can_approve(request.user):
            messages.error(request, '您沒有權限進行審核！')
            return redirect('workorder:manager_production_list')
        
        if obj.approval_status == 'approved':
            messages.error(request, '此記錄已經審核通過！')
            return redirect('workorder:manager_production_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """表單驗證成功"""
        remarks = form.cleaned_data.get('approval_remarks', '')
        
        try:
            self.object.approve(self.request.user, remarks)
            messages.success(self.request, '管理者生產報工記錄審核通過！')
        except PermissionError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        
        return redirect(self.success_url)


class ManagerProductionReportRejectView(LoginRequiredMixin, UpdateView):
    """
    管理者生產報工記錄駁回視圖
    """
    model = ManagerProductionReport
    form_class = ManagerProductionReportRejectionForm
    template_name = 'workorder/manager_production_reject.html'
    success_url = reverse_lazy('workorder:manager_production_list')
    
    def dispatch(self, request, *args, **kwargs):
        """檢查權限"""
        obj = self.get_object()
        if not obj.can_approve(request.user):
            messages.error(request, '您沒有權限進行審核！')
            return redirect('workorder:manager_production_list')
        
        if obj.approval_status == 'approved':
            messages.error(request, '此記錄已經審核通過！')
            return redirect('workorder:manager_production_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """表單驗證成功"""
        reason = form.cleaned_data.get('rejection_reason', '')
        
        try:
            self.object.reject(self.request.user, reason)
            messages.success(self.request, '管理者生產報工記錄已駁回！')
        except PermissionError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        
        return redirect(self.success_url)


class ManagerProductionReportBatchView(LoginRequiredMixin, CreateView):
    """
    管理者生產報工記錄批量創建視圖
    """
    model = ManagerProductionReport
    form_class = ManagerProductionReportBatchForm
    template_name = 'workorder/manager_production_batch.html'
    success_url = reverse_lazy('workorder:manager_production_list')
    
    def form_valid(self, form):
        """表單驗證成功"""
        # 取得表單資料
        manager = form.cleaned_data['manager']
        workorder = form.cleaned_data['workorder']
        process = form.cleaned_data['process']
        equipment = form.cleaned_data.get('equipment')
        operator = form.cleaned_data.get('operator')
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']
        daily_work_quantity = form.cleaned_data['daily_work_quantity']
        daily_defect_quantity = form.cleaned_data.get('daily_defect_quantity', 0)
        completion_method = form.cleaned_data['completion_method']
        remarks = form.cleaned_data.get('remarks', '')
        
        # 批量創建記錄
        created_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            report = ManagerProductionReport(
                manager=manager,
                workorder=workorder,
                planned_quantity=workorder.quantity,
                process=process,
                equipment=equipment,
                operator=operator,
                work_date=current_date,
                start_time=start_time,
                end_time=end_time,
                work_quantity=daily_work_quantity,
                defect_quantity=daily_defect_quantity,
                completion_method=completion_method,
                remarks=remarks,
                created_by=self.request.user.username
            )
            
            # 檢查自動完工狀態
            report.check_auto_completion()
            report.save()
            
            created_count += 1
            current_date += timedelta(days=1)
        
        messages.success(self.request, f'成功批量創建 {created_count} 筆管理者生產報工記錄！')
        return redirect(self.success_url)
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        context['title'] = '批量創建管理者生產報工記錄'
        context['submit_text'] = '批量創建'
        return context


# API 視圖
@csrf_exempt
def manager_get_workorders_by_product(request):
    """
    根據產品編號取得工單列表 API
    """
    if request.method == 'GET':
        product_id = request.GET.get('product_id', '')
        
        if not product_id:
            return JsonResponse({'error': '請提供產品編號'}, status=400)
        
        workorders = WorkOrder.objects.filter(
            product_code__icontains=product_id
        ).values('id', 'order_number', 'product_code', 'quantity', 'status')
        
        return JsonResponse({
            'workorders': list(workorders)
        })
    
    return JsonResponse({'error': '不支援的請求方法'}, status=405)


@csrf_exempt
def manager_batch_create_api(request):
    """
    批量創建管理者生產報工記錄 API
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 驗證必要欄位
            required_fields = ['manager', 'workorder_id', 'process_id', 'start_date', 'end_date', 
                             'start_time', 'end_time', 'daily_work_quantity']
            
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'error': f'缺少必要欄位: {field}'}, status=400)
            
            # 取得相關物件
            try:
                workorder = WorkOrder.objects.get(id=data['workorder_id'])
                process = ProcessName.objects.get(id=data['process_id'])
            except (WorkOrder.DoesNotExist, ProcessName.DoesNotExist):
                return JsonResponse({'error': '工單或工序不存在'}, status=400)
            
            # 取得可選物件
            equipment = None
            operator = None
            
            if data.get('equipment_id'):
                try:
                    equipment = Equipment.objects.get(id=data['equipment_id'])
                except Equipment.DoesNotExist:
                    return JsonResponse({'error': '設備不存在'}, status=400)
            
            if data.get('operator_id'):
                try:
                    operator = Operator.objects.get(id=data['operator_id'])
                except Operator.DoesNotExist:
                    return JsonResponse({'error': '作業員不存在'}, status=400)
            
            # 解析日期和時間
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            end_time = datetime.strptime(data['end_time'], '%H:%M').time()
            
            # 批量創建記錄
            created_reports = []
            current_date = start_date
            
            while current_date <= end_date:
                report = ManagerProductionReport(
                    manager=data['manager'],
                    workorder=workorder,
                    planned_quantity=workorder.quantity,
                    process=process,
                    equipment=equipment,
                    operator=operator,
                    work_date=current_date,
                    start_time=start_time,
                    end_time=end_time,
                    work_quantity=data['daily_work_quantity'],
                    defect_quantity=data.get('daily_defect_quantity', 0),
                    completion_method=data.get('completion_method', 'manual'),
                    remarks=data.get('remarks', ''),
                    created_by=request.user.username if request.user.is_authenticated else 'system'
                )
                
                # 檢查自動完工狀態
                report.check_auto_completion()
                report.save()
                
                created_reports.append({
                    'id': report.id,
                    'date': current_date.strftime('%Y-%m-%d'),
                    'work_quantity': report.work_quantity
                })
                
                current_date += timedelta(days=1)
            
            return JsonResponse({
                'success': True,
                'message': f'成功創建 {len(created_reports)} 筆記錄',
                'reports': created_reports
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON 格式錯誤'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'創建失敗: {str(e)}'}, status=500)
    
    return JsonResponse({'error': '不支援的請求方法'}, status=405)


@require_POST
@csrf_exempt
def manager_production_report_approve_ajax(request, report_id):
    """
    AJAX：管理者生產報工記錄審核通過
    """
    try:
        from .models import ManagerProductionReport
        
        report = ManagerProductionReport.objects.get(id=report_id)
        
        # 檢查權限
        if not report.can_approve(request.user):
            return JsonResponse({
                'success': False,
                'message': '您沒有權限審核此記錄'
            })
        
        # 審核通過
        remarks = request.POST.get('remarks', '')
        report.approve(request.user, remarks)
        
        return JsonResponse({
            'success': True,
            'message': '審核通過成功！'
        })
        
    except ManagerProductionReport.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的管理者生產報工記錄'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'審核失敗：{str(e)}'
        })


@require_POST
@csrf_exempt
def manager_production_report_reject_ajax(request, report_id):
    """
    AJAX：管理者生產報工記錄駁回
    """
    try:
        from .models import ManagerProductionReport
        
        report = ManagerProductionReport.objects.get(id=report_id)
        
        # 檢查權限
        if not report.can_approve(request.user):
            return JsonResponse({
                'success': False,
                'message': '您沒有權限駁回此記錄'
            })
        
        # 駁回
        reason = request.POST.get('reason', '')
        if not reason:
            return JsonResponse({
                'success': False,
                'message': '請填寫駁回原因'
            })
        
        report.reject(request.user, reason)
        
        return JsonResponse({
            'success': True,
            'message': '駁回成功！'
        })
        
    except ManagerProductionReport.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '找不到指定的管理者生產報工記錄'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'駁回失敗：{str(e)}'
        })

def rd_sample_supplement_report_create(request):
    """
    RD樣品補登報工新增頁面
    專門用於RD樣品的報工記錄
    """
    from datetime import date, time
    from process.models import Operator, ProcessName
    from .models import OperatorSupplementReport
    from .forms import RDSampleSupplementReportForm
    
    if request.method == 'POST':
        form = RDSampleSupplementReportForm(request.POST)
        
        if form.is_valid():
            # 處理時間欄位
            start_time_str = form.cleaned_data['start_time']
            end_time_str = form.cleaned_data['end_time']
            
            try:
                from datetime import datetime
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
                
                # 創建RD樣品補登記錄
                supplement_report = form.save(commit=False)
                supplement_report.start_time = start_time
                supplement_report.end_time = end_time
                supplement_report.created_by = request.user.username
                
                # 設定RD樣品報工相關欄位
                supplement_report.report_type = 'rd_sample'
                supplement_report.workorder = None
                supplement_report.planned_quantity = 0
                
                supplement_report.save()
                
                messages.success(request, 'RD樣品補登報工記錄建立成功！')
                return redirect('workorder:operator_supplement_report_index')
            except ValueError:
                form.add_error("start_time", "時間格式錯誤")
                form.add_error("end_time", "時間格式錯誤")
    else:
        # 設定預設值
        initial_data = {
            'start_time': '08:30',
            'end_time': '17:30',
        }
        form = RDSampleSupplementReportForm(initial=initial_data)
    
    context = {
        "form": form,
        "is_create": True,
        "is_rd_sample": True,
        "page_title": "新增RD樣品補登報工記錄",
    }
    
    return render(request, 'workorder/report/operator/supplement/rd_sample_form.html', context)


def smt_rd_sample_supplement_index(request):
    """
    SMTRD樣品補登管理頁面
    顯示SMT生產線的RD樣品補登記錄列表
    """
    from .models import SMTProductionReport
    
    # 取得RD樣品補登記錄（目前為空，因為還沒有實作）
    rd_sample_reports = []
    
    # 計算統計資料
    total_count = len(rd_sample_reports)
    pending_count = len([r for r in rd_sample_reports if r.approval_status == 'pending'])
    approved_count = len([r for r in rd_sample_reports if r.approval_status == 'approved'])
    rejected_count = len([r for r in rd_sample_reports if r.approval_status == 'rejected'])
    
    context = {
        'rd_sample_reports': rd_sample_reports,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'page_title': 'SMTRD樣品補登管理',
    }
    
    return render(request, 'workorder/report/smt/rd_sample_supplement/index.html', context)


def rd_sample_supplement_report_edit(request, report_id):
    """
    RD樣品補登報工編輯頁面
    專門用於編輯RD樣品的報工記錄
    """
    from datetime import date, time
    from process.models import Operator, ProcessName
    from .models import OperatorSupplementReport
    from .forms import RDSampleSupplementReportForm
    
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
        
        # 檢查是否為RD樣品報工記錄
        if report.report_type != 'rd_sample':
            messages.error(request, '此記錄不是RD樣品報工記錄，無法在此頁面編輯')
            return redirect('workorder:operator_supplement_report_index')
        
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的RD樣品補登報工記錄')
        return redirect('workorder:operator_supplement_report_index')
    
    if request.method == 'POST':
        form = RDSampleSupplementReportForm(request.POST, instance=report)
        
        if form.is_valid():
            # 處理時間欄位
            start_time_str = form.cleaned_data['start_time']
            end_time_str = form.cleaned_data['end_time']
            
            try:
                from datetime import datetime
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
                
                # 更新RD樣品補登記錄
                supplement_report = form.save(commit=False)
                supplement_report.start_time = start_time
                supplement_report.end_time = end_time
                
                # 設定RD樣品報工相關欄位
                supplement_report.report_type = 'rd_sample'
                supplement_report.workorder = None
                supplement_report.planned_quantity = 0
                
                supplement_report.save()
                
                messages.success(request, 'RD樣品補登報工記錄更新成功！')
                return redirect('workorder:operator_supplement_report_index')
            except ValueError:
                form.add_error("start_time", "時間格式錯誤")
                form.add_error("end_time", "時間格式錯誤")
    else:
        # 初始化表單時，將時間欄位轉換為字串格式
        initial_data = {
            'start_time': report.start_time.strftime('%H:%M') if report.start_time else '',
            'end_time': report.end_time.strftime('%H:%M') if report.end_time else '',
        }
        form = RDSampleSupplementReportForm(instance=report, initial=initial_data)
    
    context = {
        "form": form,
        'supplement_report': report,
        "is_create": False,
        "is_rd_sample": True,
        "page_title": "編輯RD樣品補登報工記錄",
    }
    
    return render(request, 'workorder/report/operator/supplement/rd_sample_form.html', context)


