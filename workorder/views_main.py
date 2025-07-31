"""
工單模組視圖檔案
注意：此檔案中的函數式視圖已被標記為棄用，建議使用新的類別視圖
新的類別視圖位於 workorder/views/ 目錄下
"""

import logging
import warnings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.paginator import Paginator
from .models import (
    WorkOrder,
    WorkOrderProcess,
    WorkOrderProcessLog,
    WorkOrderAssignment,
    DispatchLog,
)

# 導入子模組的模型
from .workorder_erp.models import PrdMKOrdMain, SystemConfig, CompanyOrder
from .workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
from .tasks import get_standard_processes
from .forms import WorkOrderForm, OperatorSupplementReportForm, SMTProductionReportForm, OperatorOnSiteReportForm, SMTSupplementReportForm
from django.contrib import messages

from datetime import datetime, timedelta, date
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

# 棄用警告函數
def deprecated_warning(func_name):
    """顯示棄用警告"""
    warnings.warn(
        f"函數 {func_name} 已被標記為棄用，請使用新的類別視圖替代。"
        f"新的類別視圖位於 workorder/views/ 目錄下。",
        DeprecationWarning,
        stacklevel=2
    )

# 設定工單管理模組的日誌記錄器
workorder_logger = logging.getLogger("workorder")
workorder_handler = logging.FileHandler("/var/log/mes/workorder.log")
workorder_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
workorder_logger.addHandler(workorder_handler)
workorder_logger.setLevel(logging.INFO)

# Create your views here.


# 工單列表 (已棄用 - 請使用 WorkOrderListView)
def index(request):
    deprecated_warning('index')
    workorders = WorkOrder.objects.all().order_by("-created_at")
    context = {
        "workorders": workorders,
        "is_debug": settings.DEBUG,  # 傳遞是否為測試環境
    }
    return render(request, "workorder/workorder/workorder_list.html", context)

# 工單詳情 (已棄用 - 請使用 WorkOrderDetailView)
def detail(request, pk):
    deprecated_warning('detail')
    workorder = get_object_or_404(WorkOrder, pk=pk)
    context = {
        "workorder": workorder,
    }
    return render(request, "workorder/workorder/workorder_detail.html", context)

# 工單列表視圖 (已棄用 - 請使用 WorkOrderListView)
def list_view(request):
    deprecated_warning('list_view')
    workorders = WorkOrder.objects.all().order_by("-created_at")
    
    # 搜尋功能
    search = request.GET.get('search', '')
    if search:
        workorders = workorders.filter(
            Q(order_number__icontains=search) |
            Q(product_code__icontains=search) |
            Q(company_code__icontains=search)
        )
    
    # 分頁
    paginator = Paginator(workorders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "search": search,
        "total_count": workorders.count(),
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


@require_GET
@login_required
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
        request, "workorder/workorder/workorder_confirm_delete.html", {"workorder": workorder}
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
        "workorder/workorder/delete_pending_confirm.html",
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
        "workorder/workorder/delete_in_progress_confirm.html",
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

    # 只顯示待生產和生產中的工單，不顯示已完成工單
    all_orders = WorkOrder.objects.filter(status__in=["pending", "in_progress"]).order_by("-created_at")
    
    # 按狀態分組
    pending_orders = [order for order in all_orders if order.status == "pending"]
    in_progress_orders = [order for order in all_orders if order.status == "in_progress"]
    completed_orders = []  # 派工單管理頁面不顯示已完成工單
    other_orders = []  # 派工單管理頁面不顯示其他狀態工單

    # 計算統計數據（只計算待生產和生產中的工單）
    total_workorders = WorkOrder.objects.filter(status__in=["pending", "in_progress"]).count()
    pending_count = len(pending_orders)
    in_progress_count = len(in_progress_orders)
    completed_count = 0  # 派工單管理頁面不顯示已完成工單
    other_count = 0  # 派工單管理頁面不顯示其他狀態工單
    
    # 計算工藝路線已設定總數
    process_route_set_count = 0
    # 計算分配資訊已分配總數
    assignment_set_count = 0
    
    # 檢查待生產和生產中工單的工藝路線和分配狀態
    active_workorders = WorkOrder.objects.filter(status__in=["pending", "in_progress"])
    for workorder in active_workorders:
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
            new_sync_interval = request.POST.get("auto_sync_companyorder_interval")
            interval_changed = False
            
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
                interval_changed = True
                
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
                interval_changed = True
            
            # 如果間隔設定有變更，重新設定定時任務
            if interval_changed:
                try:
                    from django.core.management import call_command
                    call_command("setup_workorder_tasks")
                    workorder_logger.info(
                        f"管理員 {request.user} 重新設定定時任務成功。IP: {request.META.get('REMOTE_ADDR')}"
                    )
                    messages.success(request, "間隔設定已更新，定時任務已重新設定！")
                except Exception as e:
                    workorder_logger.error(
                        f"重新設定定時任務失敗：{str(e)}。IP: {request.META.get('REMOTE_ADDR')}"
                    )
                    messages.warning(request, f"間隔設定已更新，但重新設定定時任務失敗：{str(e)}")
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
        # 格式化公司代號，確保是兩位數格式（例如：2 -> 02）
        formatted_company_code = order.company_code
        if formatted_company_code and formatted_company_code.isdigit():
            formatted_company_code = formatted_company_code.zfill(2)
        
        workorder_dict = {
            "MKOrdNO": f"{formatted_company_code}_{order.mkordno}",
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
            # 檢查工單是否已存在（使用公司代號和製令單號的組合）
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
            
            # 建立工單（使用製令單號作為工單號碼）
            workorder = WorkOrder.objects.create(
                order_number=company_order.mkordno,  # 直接使用製令單號
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
    完工工單：從實際報工資料生成工序明細
    未完工工單：顯示預先建立的工序明細
    """
    workorder = get_object_or_404(WorkOrder, pk=workorder_id)
    
    # 檢查是否為完工工單
    if workorder.status == "completed":
        # 完工工單：從實際報工資料生成工序明細
        processes = generate_completed_workorder_processes(workorder)
        has_process_route = True  # 完工工單一定有實際工序
    else:
        # 未完工工單：顯示預先建立的工序明細
        processes = WorkOrderProcess.objects.filter(workorder=workorder).order_by("step_order")
        
        # 檢查產品是否有工藝路線設定
        from process.models import ProductProcessRoute
        has_process_route = ProductProcessRoute.objects.filter(
            product_id=workorder.product_code
        ).exists()

    # 計算整體進度
    total_planned = sum(p.planned_quantity for p in processes)
    total_completed = sum(p.completed_quantity for p in processes)
    overall_progress = round(
        (total_completed / total_planned * 100) if total_planned > 0 else 0, 2
    )

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
            "is_completed_workorder": workorder.status == "completed",
        },
    )


def generate_completed_workorder_processes(workorder):
    """
    為完工工單從實際報工資料生成工序明細
    整合作業員報工和SMT報工資料
    """
    from collections import defaultdict
    from datetime import datetime, time
    
    # 收集所有報工資料
    process_data = defaultdict(lambda: {
        'process_name': '',
        'planned_quantity': workorder.quantity,
        'completed_quantity': 0,
        'assigned_operators': set(),
        'assigned_equipments': set(),
        'actual_start_time': None,
        'actual_end_time': None,
        'total_work_hours': 0,
        'total_overtime_hours': 0,
        'defect_quantity': 0,
        'abnormal_notes': [],
        'step_order': 0
    })
    
    # 1. 收集作業員報工資料
    operator_reports = OperatorSupplementReport.objects.filter(
        workorder=workorder,
        approval_status='approved'
    ).select_related('operator', 'process', 'equipment')
    
    for report in operator_reports:
        process_name = report.process.name if report.process else report.operation
        if process_name:
            process_data[process_name]['process_name'] = process_name
            process_data[process_name]['completed_quantity'] += report.work_quantity
            process_data[process_name]['defect_quantity'] += report.defect_quantity
            
            if report.operator:
                process_data[process_name]['assigned_operators'].add(report.operator.name)
            if report.equipment:
                process_data[process_name]['assigned_equipments'].add(report.equipment.name)
            
            # 計算時間
            report_start_time = datetime.combine(report.work_date, report.start_time)
            report_end_time = datetime.combine(report.work_date, report.end_time)
            
            if not process_data[process_name]['actual_start_time'] or report_start_time < process_data[process_name]['actual_start_time']:
                process_data[process_name]['actual_start_time'] = report_start_time
            if not process_data[process_name]['actual_end_time'] or report_end_time > process_data[process_name]['actual_end_time']:
                process_data[process_name]['actual_end_time'] = report_end_time
            
            process_data[process_name]['total_work_hours'] += float(report.work_hours_calculated or 0)
            process_data[process_name]['total_overtime_hours'] += float(report.overtime_hours_calculated or 0)
            
            if report.abnormal_notes:
                process_data[process_name]['abnormal_notes'].append(report.abnormal_notes)
    
    # 2. 收集SMT報工資料
    smt_reports = SMTProductionReport.objects.filter(
        workorder=workorder,
        approval_status='approved'
    ).select_related('equipment')
    
    for report in smt_reports:
        process_name = report.operation
        if process_name:
            process_data[process_name]['process_name'] = process_name
            process_data[process_name]['completed_quantity'] += report.work_quantity
            process_data[process_name]['defect_quantity'] += report.defect_quantity
            
            if report.equipment:
                process_data[process_name]['assigned_equipments'].add(report.equipment.name)
            
            # 計算時間
            report_start_time = datetime.combine(report.work_date, report.start_time)
            report_end_time = datetime.combine(report.work_date, report.end_time)
            
            if not process_data[process_name]['actual_start_time'] or report_start_time < process_data[process_name]['actual_start_time']:
                process_data[process_name]['actual_start_time'] = report_start_time
            if not process_data[process_name]['actual_end_time'] or report_end_time > process_data[process_name]['actual_end_time']:
                process_data[process_name]['actual_end_time'] = report_end_time
            
            process_data[process_name]['total_work_hours'] += float(report.work_hours_calculated or 0)
            process_data[process_name]['total_overtime_hours'] += float(report.overtime_hours_calculated or 0)
            
            if report.abnormal_notes:
                process_data[process_name]['abnormal_notes'].append(report.abnormal_notes)
    
    # 3. 生成工序明細物件
    processes = []
    step_order = 1
    
    # 按開始時間排序工序
    sorted_processes = sorted(
        process_data.items(),
        key=lambda x: x[1]['actual_start_time'] or datetime.max
    )
    
    for process_name, data in sorted_processes:
        if data['completed_quantity'] > 0:  # 只顯示有實際產出的工序
            # 創建一個類似 WorkOrderProcess 的物件
            process_obj = type('CompletedProcess', (), {
                'step_order': step_order,
                'process_name': data['process_name'],
                'planned_quantity': data['planned_quantity'],
                'completed_quantity': data['completed_quantity'],
                'status': 'completed',
                'assigned_operator': ', '.join(data['assigned_operators']) if data['assigned_operators'] else '-',
                'assigned_equipment': ', '.join(data['assigned_equipments']) if data['assigned_equipments'] else '-',
                'actual_start_time': data['actual_start_time'],
                'actual_end_time': data['actual_end_time'],
                'capacity_multiplier': len(data['assigned_operators']) or 1,
                'target_hourly_output': 0,  # 完工工單不需要目標產能
                'estimated_hours': data['total_work_hours'] + data['total_overtime_hours'],
                'defect_quantity': data['defect_quantity'],
                'abnormal_notes': '; '.join(data['abnormal_notes']) if data['abnormal_notes'] else '',
                'completion_rate': f"{(data['completed_quantity'] / data['planned_quantity'] * 100):.1f}%" if data['planned_quantity'] > 0 else "100%",
                'get_status_display': lambda: "已完成",
                'equipment_display_name': ', '.join(data['assigned_equipments']) if data['assigned_equipments'] else '-',
            })()
            
            processes.append(process_obj)
            step_order += 1
    
    return processes


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
@login_required
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
    支援查詢、檢視、匯出功能，並支援排序功能
    """
    # 取得所有完工工單
    completed_workorders = WorkOrder.objects.filter(status="completed")
    
    # 支援搜尋功能
    search_query = request.GET.get("search", "")
    if search_query:
        completed_workorders = completed_workorders.filter(
            Q(order_number__icontains=search_query)
            | Q(product_code__icontains=search_query)
            | Q(company_code__icontains=search_query)
        )

    # 支援排序功能
    sort_by = request.GET.get("sort", "-updated_at")  # 預設按更新時間倒序
    sort_direction = request.GET.get("direction", "desc")  # 預設倒序
    
    # 驗證排序欄位，防止 SQL 注入
    allowed_sort_fields = {
        'order_number': 'order_number',
        'product_code': 'product_code', 
        'quantity': 'quantity',
        'created_at': 'created_at',
        'updated_at': 'updated_at'
    }
    
    if sort_by in allowed_sort_fields:
        field = allowed_sort_fields[sort_by]
        if sort_direction == "asc":
            completed_workorders = completed_workorders.order_by(field)
        else:
            completed_workorders = completed_workorders.order_by(f"-{field}")
    else:
        # 如果排序欄位無效，使用預設排序
        completed_workorders = completed_workorders.order_by("-updated_at")

    # 分頁功能
    from django.core.paginator import Paginator

    paginator = Paginator(completed_workorders, 20)  # 每頁顯示20筆
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "completed_orders": page_obj,
        "search_query": search_query,
        "total_count": completed_workorders.count(),
        "current_sort": sort_by,
        "current_direction": sort_direction,
    }

    return render(request, "workorder/dispatch/completed_workorders.html", context)


def completed_workorders_process_stats(request):
    """
    完工工單工序統計頁面：顯示所有完工工單的工序統計資訊
    支援按工序、時間範圍等條件篩選
    """
    from django.db.models import Count, Sum, Avg, Q
    from datetime import datetime, timedelta

    # 取得所有完工工單的工序統計
    process_stats = WorkOrderProcess.objects.filter(
        workorder__status="completed"
    ).values(
        'process_name'
    ).annotate(
        total_workorders=Count('workorder', distinct=True),
        total_planned_quantity=Sum('planned_quantity'),
        total_completed_quantity=Sum('completed_quantity'),
        avg_planned_quantity=Avg('planned_quantity'),
        avg_completed_quantity=Avg('completed_quantity'),
    ).order_by('-total_workorders')
    
    # 手動計算完成率，避免除零錯誤
    for stat in process_stats:
        if stat['avg_planned_quantity'] and stat['avg_planned_quantity'] > 0:
            stat['avg_completion_rate'] = (stat['avg_completed_quantity'] / stat['avg_planned_quantity']) * 100
        else:
            stat['avg_completion_rate'] = 0
        
        # 添加作業員和設備資訊（暫時設為空列表）
        stat['operators'] = []
        stat['equipments'] = []
    
    # 支援搜尋功能
    search_query = request.GET.get("search", "")
    if search_query:
        process_stats = process_stats.filter(
            Q(process_name__icontains=search_query)
        )
    
    # 支援時間範圍篩選
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    
    if date_from or date_to:
        date_filter = Q()
        if date_from:
            date_filter &= Q(workorder__updated_at__date__gte=date_from)
        if date_to:
            date_filter &= Q(workorder__updated_at__date__lte=date_to)
        process_stats = process_stats.filter(date_filter)
    
    # 支援排序功能
    sort_by = request.GET.get("sort", "-total_workorders")  # 預設按工單數量倒序
    sort_direction = request.GET.get("direction", "desc")  # 預設倒序
    
    # 驗證排序欄位
    allowed_sort_fields = {
        'process_name': 'process_name',
        'total_workorders': 'total_workorders',
        'total_planned_quantity': 'total_planned_quantity',
        'total_completed_quantity': 'total_completed_quantity',
        'avg_completion_rate': 'avg_completion_rate',
        'avg_planned_quantity': 'avg_planned_quantity',
        'avg_completed_quantity': 'avg_completed_quantity',
    }
    
    if sort_by in allowed_sort_fields:
        field = allowed_sort_fields[sort_by]
        if sort_direction == "asc":
            process_stats = process_stats.order_by(field)
        else:
            process_stats = process_stats.order_by(f"-{field}")
    else:
        # 如果排序欄位無效，使用預設排序
        process_stats = process_stats.order_by("-total_workorders")
    
    # 分頁功能
    from django.core.paginator import Paginator
    
    paginator = Paginator(process_stats, 20)  # 每頁顯示20筆
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    # 計算總統計
    total_processes = process_stats.count()
    total_workorders = sum(item['total_workorders'] for item in process_stats)
    total_quantity = sum(item['total_completed_quantity'] or 0 for item in process_stats)
    
    # 計算平均效率
    if total_processes > 0:
        completion_rates = []
        for item in process_stats:
            if item['avg_planned_quantity'] and item['avg_planned_quantity'] > 0:
                rate = (item['avg_completed_quantity'] / item['avg_planned_quantity']) * 100
            else:
                rate = 0
            completion_rates.append(rate)
        avg_efficiency = sum(completion_rates) / len(completion_rates)
    else:
        avg_efficiency = 0
    
    context = {
        "process_stats": page_obj,
        "total_processes": total_processes,
        "total_workorders": total_workorders,
        "total_quantity": total_quantity,
        "avg_efficiency": round(avg_efficiency, 1),
        "search_query": search_query,
        "date_from": date_from,
        "date_to": date_to,
        "current_sort": sort_by,
        "current_direction": sort_direction,
    }
    
    return render(request, "workorder/dispatch/completed_workorders_process_stats.html", context)


def import_historical_workorders(request):
    """
    匯入歷史派工單頁面：允許用戶匯入歷史的派工單資料
    支援 Excel 和 CSV 格式，以公司代號和工單號碼作為唯一性檢查
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:completed_workorders")

    if request.method == "POST":
        try:
            # 檢查是否有上傳檔案
            if "file" not in request.FILES:
                messages.error(request, "請選擇要匯入的檔案")
                return redirect("workorder:import_historical_workorders")

            uploaded_file = request.FILES["file"]
            
            # 檢查檔案格式
            file_name = uploaded_file.name.lower()
            if not (file_name.endswith('.xlsx') or file_name.endswith('.csv')):
                messages.error(request, "只支援 Excel (.xlsx) 和 CSV 格式的檔案")
                return redirect("workorder:import_historical_workorders")

            # 讀取檔案內容
            import pandas as pd
            import io
            
            if file_name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file, parse_dates=False)

            # 檢查必要欄位
            required_columns = ['公司代號', '工單號碼', '產品編號', '數量']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                messages.error(request, f"檔案缺少必要欄位：{', '.join(missing_columns)}")
                return redirect("workorder:import_historical_workorders")

            # 開始匯入處理
            success_count = 0
            skip_count = 0
            error_count = 0
            error_messages = []
            skip_details = []  # 記錄跳過的詳細資訊

            for index, row in df.iterrows():
                try:
                    company_code = str(row['公司代號']).strip()
                    order_number = str(row['工單號碼']).strip()
                    product_code = str(row['產品編號']).strip()
                    quantity = int(row['數量'])

                    # 檢查公司代號和工單號碼的唯一性（包括所有狀態的工單）
                    existing_workorder = WorkOrder.objects.filter(
                        company_code=company_code,
                        order_number=order_number
                    ).first()

                    if existing_workorder:
                        skip_count += 1
                        skip_detail = f"公司代號 {company_code}，工單號碼 {order_number}，現有狀態：{existing_workorder.status}"
                        skip_details.append(skip_detail)
                        workorder_logger.warning(f"跳過重複工單：{skip_detail}")
                        continue

                    # 建立新的完工工單
                    workorder = WorkOrder.objects.create(
                        company_code=company_code,
                        order_number=order_number,
                        product_code=product_code,
                        quantity=quantity,
                        status="completed",  # 直接設為完工狀態
                        created_at=timezone.now(),
                        updated_at=timezone.now(),
                    )

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    error_messages.append(f"第 {index + 1} 行：{str(e)}")

            # 顯示匯入結果
            if success_count > 0:
                messages.success(
                    request, 
                    f"匯入完成！成功匯入 {success_count} 筆歷史派工單"
                )
            
            if skip_count > 0:
                messages.warning(
                    request, 
                    f"跳過 {skip_count} 筆重複資料（公司代號和工單號碼已存在於任何狀態的工單中）"
                )
            
            if error_count > 0:
                messages.error(
                    request, 
                    f"匯入失敗 {error_count} 筆資料，請檢查檔案格式"
                )
                # 記錄詳細錯誤訊息
                workorder_logger.error(f"匯入歷史派工單錯誤：{error_messages}")
            
            # 記錄跳過的詳細資訊
            if skip_details:
                workorder_logger.info(f"匯入歷史派工單跳過詳情：{skip_details}")

            return redirect("workorder:completed_workorders")

        except Exception as e:
            messages.error(request, f"匯入失敗：{str(e)}")
            workorder_logger.error(f"匯入歷史派工單失敗：{str(e)}")
            return redirect("workorder:import_historical_workorders")

    # GET 請求顯示匯入頁面
    return render(request, "workorder/dispatch/import_historical_workorders.html")


def download_historical_workorder_template(request):
    """
    下載歷史派工單匯入範本
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:completed_workorders")

    try:
        import pandas as pd
        import io
        from django.http import HttpResponse
        
        # 建立範本資料
        template_data = {
            '公司代號': ['10', '20', '30'],
            '工單號碼': ['WO-2024-001', 'WO-2024-002', 'WO-2024-003'],
            '產品編號': ['PFP-001', 'PFP-002', 'PFP-003'],
            '數量': [100, 200, 300],
        }
        
        df = pd.DataFrame(template_data)
        
        # 建立 Excel 檔案
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='歷史派工單範本', index=False)
        
        output.seek(0)
        
        # 回傳檔案
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="歷史派工單匯入範本.xlsx"'
        
        return response

    except Exception as e:
        messages.error(request, f"下載範本失敗：{str(e)}")
        return redirect("workorder:import_historical_workorders")


def export_completed_workorders(request):
    """
    匯出完工工單資料
    支援 Excel 和 CSV 格式，可根據搜尋條件和日期範圍篩選
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:completed_workorders")

    try:
        # 取得匯出格式
        export_format = request.GET.get('format', 'excel').lower()
        if export_format not in ['excel', 'csv']:
            export_format = 'excel'

        # 取得篩選條件
        search_query = request.GET.get('search', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')

        # 查詢完工工單
        queryset = WorkOrder.objects.filter(status="completed")

        # 應用搜尋篩選
        if search_query:
            queryset = queryset.filter(
                Q(order_number__icontains=search_query) |
                Q(company_code__icontains=search_query) |
                Q(product_code__icontains=search_query)
            )

        # 應用日期篩選
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        # 排序
        queryset = queryset.order_by('-created_at')

        # 準備匯出資料
        data = []
        for workorder in queryset:
            data.append({
                '工單編號': workorder.order_number,
                '公司代號': workorder.company_code,
                '產品編號': workorder.product_code,
                '數量': workorder.quantity,
                '狀態': workorder.get_status_display(),
                '建立時間': workorder.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                '更新時間': workorder.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

        if export_format == 'excel':
            # 匯出 Excel
            import pandas as pd
            from io import BytesIO
            from django.http import HttpResponse

            df = pd.DataFrame(data)
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='完工工單', index=False)
            
            output.seek(0)
            
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="完工工單_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            
        else:
            # 匯出 CSV
            import csv
            from django.http import HttpResponse

            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="完工工單_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            # 寫入 BOM 以支援中文
            response.write('\ufeff')
            
            writer = csv.DictWriter(response, fieldnames=data[0].keys() if data else [])
            writer.writeheader()
            writer.writerows(data)

        return response

    except Exception as e:
        messages.error(request, f"匯出失敗：{str(e)}")
        return redirect("workorder:completed_workorders")


def batch_delete_completed_workorders(request):
    """
    批量刪除完工工單
    只有管理員可以執行此操作
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:completed_workorders")

    if request.method == "POST":
        try:
            # 取得要刪除的工單 ID 列表
            workorder_ids = request.POST.getlist('workorder_ids')
            
            if not workorder_ids:
                messages.warning(request, "請選擇要刪除的工單")
                return redirect("workorder:completed_workorders")

            # 刪除選中的完工工單
            deleted_count = WorkOrder.objects.filter(
                id__in=workorder_ids,
                status="completed"
            ).delete()[0]

            messages.success(request, f"成功刪除 {deleted_count} 個完工工單")
            return redirect("workorder:completed_workorders")

        except Exception as e:
            messages.error(request, f"批量刪除失敗：{str(e)}")
            return redirect("workorder:completed_workorders")

    # GET 請求重定向到完工工單列表
    return redirect("workorder:completed_workorders")


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
    workorder_count = WorkOrder.objects.count()
    company_order_count = CompanyOrder.objects.count()
    dispatch_log_count = DispatchLog.objects.count()
    
    context = {
        "workorder_count": workorder_count,
        "company_order_count": company_order_count,
        "dispatch_log_count": dispatch_log_count,
        "total_count": workorder_count + company_order_count + dispatch_log_count,
    }

    return render(request, "workorder/clear_data_confirm.html", context)


def check_workorder_completion(workorder):
    """
    檢查工單是否真正完工
    簡化邏輯：出貨包裝報工數量 ≥ 工單生產數量 = 完工
    """
    from workorder.models import WorkOrderProcess, OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport
    
    # 取得該工單的所有工序
    processes = WorkOrderProcess.objects.filter(workorder=workorder).order_by('step_order')
    
    if not processes.exists():
        # 如果沒有工序，檢查是否有其他完工依據
        # 例如：手動標記完工、歷史匯入等
        return True, "工單無工序設定，但已手動標記完工"
    
    # 檢查是否有出貨包裝工序
    packaging_processes = processes.filter(process_name__icontains='出貨包裝').order_by('step_order')
    has_packaging = packaging_processes.exists()
    
    # 取得所有出貨包裝的實際報工記錄（只計算 work_quantity，不考慮 defect_quantity）
    packaging_reports = []
    
    # 從作業員補登報工記錄中查找出貨包裝
    operator_packaging = OperatorSupplementReport.objects.filter(
        workorder=workorder,
        process__name__icontains='出貨包裝'
    )
    for report in operator_packaging:
        packaging_reports.append({
            'source': '作業員補登',
            'process': report.process.name,
            'quantity': report.work_quantity,  # 只計算合格品數量
            'defect_quantity': report.defect_quantity,  # 不良品數量（僅供顯示）
            'date': report.work_date,
            'operator': report.operator.username if report.operator else '未知'
        })
    
    # 從主管生產報工記錄中查找出貨包裝
    supervisor_packaging = SupervisorProductionReport.objects.filter(
        workorder=workorder,
        process__name__icontains='出貨包裝'
    )
    for report in supervisor_packaging:
        packaging_reports.append({
            'source': '主管報工',
            'process': report.process.name,
            'quantity': report.work_quantity,  # 只計算合格品數量
            'defect_quantity': report.defect_quantity,  # 不良品數量（僅供顯示）
            'date': report.work_date,
            'operator': report.operator.name if report.operator else '未知'
        })
    
    # 從SMT生產報工記錄中查找出貨包裝（如果有）
    smt_packaging = SMTProductionReport.objects.filter(
        workorder=workorder,
        process__name__icontains='出貨包裝'
    )
    for report in smt_packaging:
        packaging_reports.append({
            'source': 'SMT報工',
            'process': report.process.name,
            'quantity': report.work_quantity,  # 只計算合格品數量
            'defect_quantity': report.defect_quantity,  # 不良品數量（僅供顯示）
            'date': report.work_date,
            'equipment': report.equipment.name if report.equipment else '未知'
        })
    
    # 計算出貨包裝的總報工數量（只計算合格品）
    total_packaging_quantity = sum(report['quantity'] for report in packaging_reports)
    
    # 簡化的完工判斷邏輯
    if has_packaging:
        if packaging_reports:
            # 有出貨包裝報工記錄
            if total_packaging_quantity >= workorder.quantity:
                return True, f"出貨包裝報工數量達標（{total_packaging_quantity}/{workorder.quantity}）"
            else:
                return False, f"出貨包裝報工數量不足（{total_packaging_quantity}/{workorder.quantity}）"
        else:
            # 有出貨包裝工序但沒有報工記錄
            return False, "有出貨包裝工序但無報工記錄"
    
    # 如果沒有出貨包裝工序，檢查其他工序的完成數量
    # 取得所有工序的實際報工記錄（只計算合格品）
    all_reports_quantity = 0
    
    # 作業員補登報工
    operator_reports = OperatorSupplementReport.objects.filter(workorder=workorder)
    all_reports_quantity += sum(report.work_quantity for report in operator_reports)
    
    # 主管生產報工
    supervisor_reports = SupervisorProductionReport.objects.filter(workorder=workorder)
    all_reports_quantity += sum(report.work_quantity for report in supervisor_reports)
    
    # SMT生產報工
    smt_reports = SMTProductionReport.objects.filter(workorder=workorder)
    all_reports_quantity += sum(report.work_quantity for report in smt_reports)
    
    if all_reports_quantity >= workorder.quantity:
        return True, f"總報工數量達標（{all_reports_quantity}/{workorder.quantity}）"
    
    # 如果沒有任何報工記錄，但工單被標記為完工，可能是歷史匯入
    if all_reports_quantity == 0 and not packaging_reports:
        return True, "歷史匯入的完工工單"
    
    return False, f"報工數量不足（{all_reports_quantity}/{workorder.quantity}）"


def analyze_packaging_processes(workorder):
    """
    分析工單的出貨包裝工序情況
    基於實際報工記錄分析
    """
    from workorder.models import WorkOrderProcess, OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport
    
    processes = WorkOrderProcess.objects.filter(workorder=workorder).order_by('step_order')
    packaging_processes = processes.filter(process_name__icontains='出貨包裝').order_by('step_order')
    
    # 取得實際的出貨包裝報工記錄
    packaging_reports = []
    
    # 從作業員補登報工記錄中查找出貨包裝
    operator_packaging = OperatorSupplementReport.objects.filter(
        workorder=workorder,
        process__name__icontains='出貨包裝'
    )
    for report in operator_packaging:
        packaging_reports.append({
            'source': '作業員補登',
            'process': report.process.name,
            'quantity': report.work_quantity,
            'defect_quantity': report.defect_quantity,
            'date': report.work_date,
            'operator': report.operator.username if report.operator else '未知',
            'is_completed': report.is_completed
        })
    
    # 從主管生產報工記錄中查找出貨包裝
    supervisor_packaging = SupervisorProductionReport.objects.filter(
        workorder=workorder,
        process__name__icontains='出貨包裝'
    )
    for report in supervisor_packaging:
        packaging_reports.append({
            'source': '主管報工',
            'process': report.process.name,
            'quantity': report.work_quantity,
            'defect_quantity': report.defect_quantity,
            'date': report.work_date,
            'operator': report.operator.name if report.operator else '未知',
            'is_completed': report.is_completed
        })
    
    # 從SMT生產報工記錄中查找出貨包裝
    smt_packaging = SMTProductionReport.objects.filter(
        workorder=workorder,
        process__name__icontains='出貨包裝'
    )
    for report in smt_packaging:
        packaging_reports.append({
            'source': 'SMT報工',
            'process': report.process.name,
            'quantity': report.work_quantity,
            'defect_quantity': report.defect_quantity,
            'date': report.work_date,
            'equipment': report.equipment.name if report.equipment else '未知',
            'is_completed': report.is_completed
        })
    
    # 計算總報工數量
    total_packaging_quantity = sum(report['quantity'] for report in packaging_reports)
    completed_reports = [r for r in packaging_reports if r['is_completed']]
    
    analysis = {
        'total_processes': processes.count(),
        'packaging_processes': [],
        'packaging_count': packaging_processes.count(),
        'packaging_reports': packaging_reports,
        'total_packaging_quantity': total_packaging_quantity,
        'completed_reports_count': len(completed_reports),
        'analysis_summary': ''
    }
    
    # 生成分析摘要
    if packaging_reports:
        if len(packaging_reports) == 1:
            report = packaging_reports[0]
            analysis['analysis_summary'] = f"出貨包裝報工：{report['source']}，數量{report['quantity']}，{'已完工' if report['is_completed'] else '未完工'}"
        else:
            analysis['analysis_summary'] = f"多筆出貨包裝報工（共{len(packaging_reports)}筆），總數量{total_packaging_quantity}，完工記錄{len(completed_reports)}筆"
    else:
        if packaging_processes.exists():
            analysis['analysis_summary'] = f"有{packaging_processes.count()}個出貨包裝工序，但無報工記錄"
        else:
            analysis['analysis_summary'] = "無出貨包裝工序"
    
    return analysis


def fix_incorrect_completed_workorders():
    """
    修正錯誤的完工工單
    將不符合完工條件的工單狀態改回正確狀態
    """
    from workorder.models import WorkOrder
    
    # 取得所有完工狀態的工單
    completed_workorders = WorkOrder.objects.filter(status='completed')
    
    fixed_count = 0
    for workorder in completed_workorders:
        is_completed, message = check_workorder_completion(workorder)
        
        if not is_completed:
            # 根據工序狀態決定正確的狀態
            processes = workorder.processes.all()
            if processes.exists():
                # 檢查是否有正在進行的工序
                in_progress = processes.filter(status='in_progress').exists()
                if in_progress:
                    workorder.status = 'in_progress'
                else:
                    # 檢查是否有任何工序已完成
                    completed = processes.filter(status='completed').exists()
                    if completed:
                        workorder.status = 'in_progress'  # 有工序完成，但未達完工標準
                    else:
                        workorder.status = 'pending'
            else:
                # 沒有工序設定，可能是歷史匯入，保持完工狀態
                print(f"工單 {workorder.order_number} 無工序設定，保持完工狀態：{message}")
                continue
            
            workorder.save()
            fixed_count += 1
            print(f"工單 {workorder.order_number} 狀態已修正為 {workorder.status}：{message}")
    
    return fixed_count


def fix_completed_workorders_page(request):
    """
    修正完工工單狀態管理頁面
    檢查並修正錯誤的完工工單狀態
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:completed_workorders")
    
    from workorder.models import WorkOrder, WorkOrderProcess
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'check':
            # 檢查所有完工工單
            completed_workorders = WorkOrder.objects.filter(status='completed')
            incorrect_workorders = []
            
            for workorder in completed_workorders:
                is_completed, message = check_workorder_completion(workorder)
                if not is_completed:
                    # 分析出貨包裝工序
                    packaging_analysis = analyze_packaging_processes(workorder)
                    incorrect_workorders.append({
                        'workorder': workorder,
                        'reason': message,
                        'processes': workorder.processes.all(),
                        'packaging_analysis': packaging_analysis
                    })
            
            context = {
                'incorrect_workorders': incorrect_workorders,
                'total_checked': completed_workorders.count(),
                'incorrect_count': len(incorrect_workorders)
            }
            
            return render(request, "workorder/dispatch/fix_completed_workorders.html", context)
        
        elif action == 'fix':
            # 修正錯誤的完工工單
            fixed_count = fix_incorrect_completed_workorders()
            messages.success(request, f"已修正 {fixed_count} 個錯誤的完工工單狀態")
            return redirect("workorder:completed_workorders")
    
    # GET 請求顯示檢查頁面
    return render(request, "workorder/dispatch/fix_completed_workorders.html")


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
    """待審核報工列表 - 已移至 reporting 模組"""
    from django.shortcuts import redirect
    return redirect('reporting:pending_approval_list')


def approved_reports_list(request):
    """已核准報工列表 - 已移至 reporting 模組"""
    from django.shortcuts import redirect
    return redirect('reporting:approved_reports_list')
    all_approved = []
    
    # 主管審核功能已刪除，跳過處理
    
    for report in operator_approved:
        all_approved.append({
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
            'approved_at': report.approved_at,
            'approved_by': report.approved_by,
            'remarks': report.remarks,
        })
    
    for report in smt_approved:
        all_approved.append({
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
            'approved_at': report.approved_at,
            'approved_by': report.approved_by,
            'remarks': getattr(report, 'remarks', ''),
        })
    
    # 按核准時間排序
    all_approved.sort(key=lambda x: x['approved_at'], reverse=True)
    
    # 統計資料
    total_approved = len(all_approved)
    supervisor_count = 0  # 主管審核功能已刪除
    operator_count = len(operator_approved)
    smt_count = len(smt_approved)

    return render(
        request,
        "workorder/approved_reports_list.html",
        {
            "all_approved": all_approved,
            "total_approved": total_approved,
            "supervisor_count": supervisor_count,
            "operator_count": operator_count,
            "smt_count": smt_count,
        },
    )


@login_required
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
@login_required
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
@login_required
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


def clear_all_production_reports(request):
    """
    清除所有報工紀錄的視圖函數
    包括：作業員補登報工、SMT補登報工、SMT現場報工
    只有管理員可以執行此操作
    """
    from .models import OperatorSupplementReport, SMTProductionReport
    
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "只有管理員可以執行此操作")
        return redirect("workorder:index")

    if request.method == "POST":
        try:
            # 統計要清除的資料數量
            operator_reports_count = OperatorSupplementReport.objects.count()
            smt_supplement_count = SMTProductionReport.objects.filter(report_type__in=['normal', 'rd_sample']).count()
            smt_on_site_count = SMTProductionReport.objects.filter(report_type='on_site').count()
            
            total_count = operator_reports_count + smt_supplement_count + smt_on_site_count
            
            if total_count == 0:
                messages.info(request, "目前沒有任何報工紀錄需要清除")
                return redirect("workorder:index")
            
            # 清除所有報工紀錄
            OperatorSupplementReport.objects.all().delete()
            SMTProductionReport.objects.all().delete()
            
            # 記錄操作日誌
            from system.models import OperationLog
            OperationLog.objects.create(
                user=request.user.username,
                module="workorder",
                action=f"清除所有報工紀錄（作業員：{operator_reports_count}，SMT補登：{smt_supplement_count}，SMT現場：{smt_on_site_count}）",
                timestamp=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            
            messages.success(
                request, 
                f"成功清除所有報工紀錄！共清除 {total_count} 筆記錄：\n"
                f"• 作業員補登報工：{operator_reports_count} 筆\n"
                f"• SMT補登報工：{smt_supplement_count} 筆\n"
                f"• SMT現場報工：{smt_on_site_count} 筆"
            )
            return redirect("workorder:index")
            
        except Exception as e:
            messages.error(request, f"清除報工紀錄失敗：{str(e)}")
            return redirect("workorder:clear_all_production_reports")

    # GET 請求顯示確認頁面
    operator_reports_count = OperatorSupplementReport.objects.count()
    smt_supplement_count = SMTProductionReport.objects.filter(report_type__in=['normal', 'rd_sample']).count()
    smt_on_site_count = SMTProductionReport.objects.filter(report_type='on_site').count()
    
    total_count = operator_reports_count + smt_supplement_count + smt_on_site_count
    
    context = {
        "operator_reports_count": operator_reports_count,
        "smt_supplement_count": smt_supplement_count,
        "smt_on_site_count": smt_on_site_count,
        "total_count": total_count,
    }
    
    return render(request, "workorder/clear_production_reports_confirm.html", context)


@require_GET
@login_required
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
                    "company_code": wo.company_code,
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
@login_required
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
                    "company_code": workorder.company_code,
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
def batch_approve_pending(request):
    """
    批次審核所有待審核報工記錄 API
    只有超級管理員可以使用此功能
    """
    from .models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport
    
    # 檢查是否為超級管理員
    if not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'message': '只有超級管理員可以使用批次審核功能'
        })
    
    try:
        approved_count = 0
        
        # 批次審核主管生產報工記錄
        supervisor_reports = SupervisorProductionReport.objects.filter(
            approval_status='pending'
        )
        supervisor_count = supervisor_reports.count()
        supervisor_reports.update(
            approval_status='approved',
            approved_by=request.user.username,
            approved_at=timezone.now(),
            approval_remarks='批次審核'
        )
        approved_count += supervisor_count
        
        # 批次審核作業員補登報工記錄
        operator_reports = OperatorSupplementReport.objects.filter(
            approval_status='pending'
        )
        operator_count = operator_reports.count()
        operator_reports.update(
            approval_status='approved',
            approved_by=request.user.username,
            approved_at=timezone.now(),
            approval_remarks='批次審核'
        )
        approved_count += operator_count
        
        # 批次審核SMT生產報工記錄
        smt_reports = SMTProductionReport.objects.filter(
            approval_status='pending'
        )
        smt_count = smt_reports.count()
        smt_reports.update(
            approval_status='approved',
            approved_by=request.user.username,
            approved_at=timezone.now(),
            approval_remarks='批次審核'
        )
        approved_count += smt_count
        
        return JsonResponse({
            'success': True,
            'message': f'批次審核完成！成功審核 {approved_count} 筆記錄',
            'approved_count': approved_count,
            'details': {
                'supervisor_count': supervisor_count,
                'operator_count': operator_count,
                'smt_count': smt_count
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'批次審核失敗：{str(e)}'
        })


@require_POST
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
    from django.db.models import Q
    from .models import OperatorSupplementReport, SMTProductionReport
    
    # 檢查用戶權限
    if not request.user.is_authenticated:
        return redirect('login')
    
    today = date.today()
    month_start = today.replace(day=1)
    
    # 從補登報工記錄中取得真實統計資料
    # 作業員補登報工統計
    operator_today = OperatorSupplementReport.objects.filter(created_at__date=today).count()
    operator_month = OperatorSupplementReport.objects.filter(created_at__date__gte=month_start).count()
    operator_pending = OperatorSupplementReport.objects.filter(approval_status='pending').count()
    operator_abnormal = OperatorSupplementReport.objects.filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
    ).count()
    
    # SMT補登報工統計
    smt_today = SMTProductionReport.objects.filter(created_at__date=today).count()
    smt_month = SMTProductionReport.objects.filter(created_at__date__gte=month_start).count()
    smt_pending = SMTProductionReport.objects.filter(approval_status='pending').count()
    smt_abnormal = SMTProductionReport.objects.filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
    ).count()
    
    # 計算總計
    total_today = operator_today + smt_today
    total_month = operator_month + smt_month
    total_pending = operator_pending + smt_pending
    total_abnormal = operator_abnormal + smt_abnormal
    
    context = {
        'today_reports': total_today,
        'month_reports': total_month,
        'pending_reports': total_pending,
        'abnormal_reports': total_abnormal,
        'recent_reports': [],
        'stats': {
            'total_pending': total_pending,
            'total_today': total_today,
            'total_month': total_month,
            'total_abnormal': total_abnormal,
            'pending_operator': operator_pending,
            'pending_smt': smt_pending,
            'today_operator': operator_today,
            'today_smt': smt_today,
            'month_operator': operator_month,
            'month_smt': smt_month,
            'abnormal_operator': operator_abnormal,
            'abnormal_smt': smt_abnormal,
        }
    }
    
    return render(request, 'workorder/report/index.html', context)

def supervisor_report_index(request):
    """
    主管審核首頁 - 統計儀表板
    顯示所有報工類型的統計資訊和快速操作
    """
    from datetime import date, timedelta
    from django.db.models import Q
    from .models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport
    
    today = date.today()
    month_start = today.replace(day=1)
    
    # 統計所有類型的報工資料
    stats = {
        # 待審核統計
        'pending_supervisor': SupervisorProductionReport.objects.filter(approval_status='pending').count(),
        'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
        
        # 今日統計
        'today_supervisor': SupervisorProductionReport.objects.filter(created_at__date=today).count(),
        'today_operator': OperatorSupplementReport.objects.filter(created_at__date=today).count(),
        'today_smt': SMTProductionReport.objects.filter(created_at__date=today).count(),
        
        # 本月統計
        'month_supervisor': SupervisorProductionReport.objects.filter(created_at__date__gte=month_start).count(),
        'month_operator': OperatorSupplementReport.objects.filter(created_at__date__gte=month_start).count(),
        'month_smt': SMTProductionReport.objects.filter(created_at__date__gte=month_start).count(),
        
        # 異常統計
        'abnormal_supervisor': SupervisorProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
        ).count(),
        'abnormal_operator': OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
        ).count(),
        'abnormal_smt': SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
        ).count(),
    }
    
    # 計算總計
    stats['total_pending'] = stats['pending_supervisor'] + stats['pending_operator'] + stats['pending_smt']
    stats['total_today'] = stats['today_supervisor'] + stats['today_operator'] + stats['today_smt']
    stats['total_month'] = stats['month_supervisor'] + stats['month_operator'] + stats['month_smt']
    stats['total_abnormal'] = stats['abnormal_supervisor'] + stats['abnormal_operator'] + stats['abnormal_smt']
    
    # 計算已核准統計
    stats['approved_supervisor'] = SupervisorProductionReport.objects.filter(approval_status='approved').count()
    stats['approved_operator'] = OperatorSupplementReport.objects.filter(approval_status='approved').count()
    stats['approved_smt'] = SMTProductionReport.objects.filter(approval_status='approved').count()
    stats['total_approved'] = stats['approved_supervisor'] + stats['approved_operator'] + stats['approved_smt']
    
    # 取得最近審核記錄
    recent_reviews = []
    
    # 主管審核最近審核
    supervisor_reviews = SupervisorProductionReport.objects.select_related(
        'workorder', 'process'
    ).filter(approval_status='approved').order_by('-approved_at')[:3]
    
    for review in supervisor_reviews:
        recent_reviews.append({
            'type': '主管審核',
            'time': review.approved_at,
            'operator': review.supervisor,
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
    
    return render(request, 'workorder/report/supervisor/index.html', context)

def supervisor_functions(request):
    """
    主管功能首頁 - 主管專用功能
    包含報工統計、異常處理、系統設定等功能
    """
    from datetime import date, timedelta
    from django.db.models import Q, Count, Sum
    from .models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport
    
    today = date.today()
    month_start = today.replace(day=1)
    
    # 統計資訊
    stats = {
        # 報工統計
        'total_reports_today': 0,
        'total_reports_month': 0,
        'pending_reports': 0,
        'abnormal_reports': 0,
        
        # 各類型統計
        'operator_reports_today': OperatorSupplementReport.objects.filter(created_at__date=today).count(),
        'smt_reports_today': SMTProductionReport.objects.filter(created_at__date=today).count(),
        'supervisor_reports_today': SupervisorProductionReport.objects.filter(created_at__date=today).count(),
        
        'operator_reports_month': OperatorSupplementReport.objects.filter(created_at__date__gte=month_start).count(),
        'smt_reports_month': SMTProductionReport.objects.filter(created_at__date__gte=month_start).count(),
        'supervisor_reports_month': SupervisorProductionReport.objects.filter(created_at__date__gte=month_start).count(),
        
        # 待審核統計
        'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
        'pending_supervisor': SupervisorProductionReport.objects.filter(approval_status='pending').count(),
        
        # 異常統計
        'abnormal_operator': OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
        ).count(),
        'abnormal_smt': SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
        ).count(),
        'abnormal_supervisor': SupervisorProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
        ).count(),
    }
    
    # 計算總計
    stats['total_reports_today'] = stats['operator_reports_today'] + stats['smt_reports_today'] + stats['supervisor_reports_today']
    stats['total_reports_month'] = stats['operator_reports_month'] + stats['smt_reports_month'] + stats['supervisor_reports_month']
    stats['pending_reports'] = stats['pending_operator'] + stats['pending_smt'] + stats['pending_supervisor']
    stats['abnormal_reports'] = stats['abnormal_operator'] + stats['abnormal_smt'] + stats['abnormal_supervisor']
    
    # 取得最近異常記錄
    recent_abnormal = []
    
    # 作業員異常
    operator_abnormal = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
    ).order_by('-created_at')[:5]
    
    for report in operator_abnormal:
        recent_abnormal.append({
            'type': '作業員報工',
            'time': report.created_at,
            'operator': report.operator.name if report.operator else '-',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process.name if report.process else '-',
            'remarks': report.abnormal_notes,
            'status': report.approval_status,
        })
    
    # SMT異常
    smt_abnormal = SMTProductionReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
    ).order_by('-created_at')[:5]
    
    for report in smt_abnormal:
        recent_abnormal.append({
            'type': 'SMT報工',
            'time': report.created_at,
            'operator': report.equipment_name,
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.operation,
            'remarks': report.abnormal_notes,
            'status': report.approval_status,
        })
    
    # 主管異常
    supervisor_abnormal = SupervisorProductionReport.objects.select_related(
        'workorder', 'process'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
    ).order_by('-created_at')[:5]
    
    for report in supervisor_abnormal:
        recent_abnormal.append({
            'type': '主管審核',
            'time': report.created_at,
            'operator': report.supervisor,
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process.name if report.process else '-',
            'remarks': report.abnormal_notes,
            'status': report.approval_status,
        })
    
    # 按時間排序
    recent_abnormal.sort(key=lambda x: x['time'], reverse=True)
    recent_abnormal = recent_abnormal[:10]  # 只取前10筆
    
    context = {
        'stats': stats,
        'recent_abnormal': recent_abnormal,
    }
    
    return render(request, 'workorder/report/supervisor/functions.html', context)

def report_statistics(request):
    """
    報工統計分析頁面
    提供詳細的報工統計資訊、產能分析、效率評估等
    """
    from datetime import date, timedelta
    from django.db.models import Q, Count, Sum, Avg
    from .models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport
    
    today = date.today()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    
    # 基礎統計
    stats = {
        'total_reports_today': 0,
        'total_reports_week': 0,
        'total_reports_month': 0,
        'total_reports_year': 0,
        'avg_daily_reports': 0,
        'avg_weekly_reports': 0,
        'avg_monthly_reports': 0,
    }
    
    # 各類型統計
    operator_stats = {
        'today': OperatorSupplementReport.objects.filter(created_at__date=today).count(),
        'week': OperatorSupplementReport.objects.filter(created_at__date__gte=week_start).count(),
        'month': OperatorSupplementReport.objects.filter(created_at__date__gte=month_start).count(),
        'year': OperatorSupplementReport.objects.filter(created_at__year=today.year).count(),
        'pending': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'approved': OperatorSupplementReport.objects.filter(approval_status='approved').count(),
        'rejected': OperatorSupplementReport.objects.filter(approval_status='rejected').count(),
    }
    
    smt_stats = {
        'today': SMTProductionReport.objects.filter(created_at__date=today).count(),
        'week': SMTProductionReport.objects.filter(created_at__date__gte=week_start).count(),
        'month': SMTProductionReport.objects.filter(created_at__date__gte=month_start).count(),
        'year': SMTProductionReport.objects.filter(created_at__year=today.year).count(),
        'pending': SMTProductionReport.objects.filter(approval_status='pending').count(),
        'approved': SMTProductionReport.objects.filter(approval_status='approved').count(),
        'rejected': SMTProductionReport.objects.filter(approval_status='rejected').count(),
    }
    
    # 計算總計
    stats['total_reports_today'] = operator_stats['today'] + smt_stats['today']
    stats['total_reports_week'] = operator_stats['week'] + smt_stats['week']
    stats['total_reports_month'] = operator_stats['month'] + smt_stats['month']
    stats['total_reports_year'] = operator_stats['year'] + smt_stats['year']
    
    # 計算平均值
    if today.day > 1:
        stats['avg_daily_reports'] = round(stats['total_reports_month'] / today.day, 1)
    if today.weekday() > 0:
        stats['avg_weekly_reports'] = round(stats['total_reports_week'] / (today.weekday() + 1), 1)
    if today.month > 1:
        stats['avg_monthly_reports'] = round(stats['total_reports_year'] / today.month, 1)
    
    # 產能分析
    capacity_analysis = {
        'operator_efficiency': 0,
        'smt_efficiency': 0,
        'total_efficiency': 0,
    }
    
    # 取得最近30天的資料進行效率分析
    thirty_days_ago = today - timedelta(days=30)
    
    # 作業員報工統計
    operator_reports_30d = OperatorSupplementReport.objects.filter(
        created_at__date__gte=thirty_days_ago
    ).aggregate(
        total_quantity=Sum('work_quantity'),
        avg_quantity=Avg('work_quantity')
    )
    
    # 計算作業員總工作時數（使用Python計算）
    operator_reports_list = OperatorSupplementReport.objects.filter(
        created_at__date__gte=thirty_days_ago
    )
    operator_total_hours = sum(report.work_hours for report in operator_reports_list)
    operator_avg_hours = operator_total_hours / len(operator_reports_list) if operator_reports_list else 0
    
    # SMT報工統計
    smt_reports_30d = SMTProductionReport.objects.filter(
        created_at__date__gte=thirty_days_ago
    ).aggregate(
        total_quantity=Sum('work_quantity'),
        avg_quantity=Avg('work_quantity')
    )
    
    # 計算SMT總工作時數（使用Python計算）
    smt_reports_list = SMTProductionReport.objects.filter(
        created_at__date__gte=thirty_days_ago
    )
    smt_total_hours = sum(report.work_duration for report in smt_reports_list if report.work_duration)
    smt_avg_hours = smt_total_hours / len(smt_reports_list) if smt_reports_list else 0
    
    # 計算效率（假設標準產能）
    if operator_total_hours > 0:
        capacity_analysis['operator_efficiency'] = round(
            (operator_reports_30d['total_quantity'] or 0) / operator_total_hours, 2
        )
    
    if smt_total_hours > 0:
        capacity_analysis['smt_efficiency'] = round(
            (smt_reports_30d['total_quantity'] or 0) / smt_total_hours, 2
        )
    
    capacity_analysis['total_efficiency'] = round(
        (capacity_analysis['operator_efficiency'] + capacity_analysis['smt_efficiency']) / 2, 2
    )
    
    # 更新統計資料
    operator_reports_30d['total_hours'] = operator_total_hours
    operator_reports_30d['avg_hours'] = operator_avg_hours
    smt_reports_30d['total_hours'] = smt_total_hours
    smt_reports_30d['avg_hours'] = smt_avg_hours
    
    context = {
        'stats': stats,
        'operator_stats': operator_stats,
        'smt_stats': smt_stats,
        'capacity_analysis': capacity_analysis,
        'operator_reports_30d': operator_reports_30d,
        'smt_reports_30d': smt_reports_30d,
    }
    
    return render(request, 'workorder/report/supervisor/statistics.html', context)

@login_required
def abnormal_management(request):
    """
    異常處理頁面
    處理報工異常情況，包含異常原因分析、處理方案制定等
    """
    from datetime import date, timedelta
    from django.db.models import Q
    from .models import OperatorSupplementReport, SMTProductionReport
    
    today = date.today()
    week_start = today - timedelta(days=7)
    
    # 取得異常記錄
    operator_abnormal = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & 
        Q(created_at__gte=week_start)
    ).order_by('-created_at')
    
    smt_abnormal = SMTProductionReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & 
        Q(created_at__gte=week_start)
    ).order_by('-created_at')
    
    # 異常統計
    abnormal_stats = {
        'total_abnormal': operator_abnormal.count() + smt_abnormal.count(),
        'operator_abnormal': operator_abnormal.count(),
        'smt_abnormal': smt_abnormal.count(),
        'resolved': 0,
        'pending': 0,
        'critical': 0,
    }
    
    # 分類異常嚴重程度
    critical_keywords = ['嚴重', '緊急', '停機', '故障', '錯誤']
    for report in operator_abnormal:
        if any(keyword in report.remarks for keyword in critical_keywords):
            abnormal_stats['critical'] += 1
        if report.approval_status == 'approved':
            abnormal_stats['resolved'] += 1
        else:
            abnormal_stats['pending'] += 1
    
    for report in smt_abnormal:
        if any(keyword in report.remarks for keyword in critical_keywords):
            abnormal_stats['critical'] += 1
        if report.approval_status == 'approved':
            abnormal_stats['resolved'] += 1
        else:
            abnormal_stats['pending'] += 1
    
    context = {
        'operator_abnormal': operator_abnormal[:20],  # 只顯示最近20筆
        'smt_abnormal': smt_abnormal[:20],
        'abnormal_stats': abnormal_stats,
    }
    
    return render(request, 'workorder/report/supervisor/abnormal.html', context)

@require_POST
@login_required
def batch_resolve_abnormal(request):
    """
    批次解決異常 - 只有超級管理員可以使用
    將所有待處理的異常標記為已解決
    """
    import json
    from django.http import JsonResponse
    
    # 檢查權限
    if not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': '只有超級管理員可以使用此功能'
        }, status=403)
    
    try:
        # 解析請求資料
        data = json.loads(request.body)
        action = data.get('action')
        
        if action != 'batch_resolve':
            return JsonResponse({
                'success': False,
                'error': '無效的操作'
            })
        
        # 取得所有待處理的異常
        from datetime import date, timedelta
        from django.db.models import Q
        from django.utils import timezone
        
        today = date.today()
        week_start = today - timedelta(days=7)
        
        # 作業員異常 - 標記為已解決（包含所有狀態的異常）
        operator_abnormal = OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & 
            Q(created_at__gte=week_start)
        )
        
        # 批次更新作業員異常（只處理尚未解決的）
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        operator_resolved_count = 0
        for report in operator_abnormal:
            if report.approval_status != 'approved':
                report.approval_status = 'approved'
                report.approved_at = timezone.now()
                report.approved_by = request.user.username
                report.abnormal_notes = f"{report.abnormal_notes} [批次解決 - {request.user.username} - {current_time}]"
                report.save()
                operator_resolved_count += 1
        
        # SMT異常 - 標記為已解決（包含所有狀態的異常）
        smt_abnormal = SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & 
            Q(created_at__gte=week_start)
        )
        
        # 批次更新SMT異常（只處理尚未解決的）
        smt_resolved_count = 0
        for report in smt_abnormal:
            if report.approval_status != 'approved':
                report.approval_status = 'approved'
                report.approved_at = timezone.now()
                report.approved_by = request.user.username
                report.abnormal_notes = f"{report.abnormal_notes} [批次解決 - {request.user.username} - {current_time}]"
                report.save()
                smt_resolved_count += 1
        
        total_resolved = operator_resolved_count + smt_resolved_count
        
        # 記錄操作日誌
        from django.contrib import messages
        messages.success(request, f'批次解決完成！已解決 {total_resolved} 個異常')
        
        return JsonResponse({
            'success': True,
            'resolved_count': total_resolved,
            'operator_resolved': operator_resolved_count,
            'smt_resolved': smt_resolved_count,
            'message': f'批次解決完成！已解決 {total_resolved} 個異常'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '請求格式錯誤'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'處理過程中發生錯誤：{str(e)}'
        })

def abnormal_detail(request, abnormal_type, abnormal_id):
    """
    異常詳情頁面
    顯示特定異常的詳細資訊
    """
    from .models import OperatorSupplementReport, SMTProductionReport
    
    try:
        if abnormal_type == 'operator':
            abnormal = get_object_or_404(OperatorSupplementReport, id=abnormal_id)
            template_name = 'workorder/report/supervisor/abnormal_detail_operator.html'
        elif abnormal_type == 'smt':
            abnormal = get_object_or_404(SMTProductionReport, id=abnormal_id)
            template_name = 'workorder/report/supervisor/abnormal_detail_smt.html'
        else:
            messages.error(request, '無效的異常類型')
            return redirect('workorder:abnormal_management')
        
        context = {
            'abnormal': abnormal,
            'abnormal_type': abnormal_type,
        }
        
        return render(request, template_name, context)
        
    except Exception as e:
        messages.error(request, f'載入異常詳情時發生錯誤：{str(e)}')
        return redirect('workorder:abnormal_management')

# 系統設定功能已移至系統管理模組，請使用 system:workorder_settings



def data_maintenance(request):
    """
    資料維護頁面
    維護報工相關資料，包含資料清理、備份還原等
    """
    from datetime import date, timedelta
    from django.db.models import Q, Count
    from .models import OperatorSupplementReport, SMTProductionReport
    
    today = date.today()
    
    # 資料統計
    data_stats = {
        'total_operator_reports': OperatorSupplementReport.objects.count(),
        'total_smt_reports': SMTProductionReport.objects.count(),
        'old_reports_30d': OperatorSupplementReport.objects.filter(
            created_at__lt=today - timedelta(days=30)
        ).count() + SMTProductionReport.objects.filter(
            created_at__lt=today - timedelta(days=30)
        ).count(),
        'old_reports_90d': OperatorSupplementReport.objects.filter(
            created_at__lt=today - timedelta(days=90)
        ).count() + SMTProductionReport.objects.filter(
            created_at__lt=today - timedelta(days=90)
        ).count(),
        'duplicate_reports': 0,  # 將在下面實作重複檢查邏輯
        'orphaned_reports': 0,   # 將在下面實作孤立資料檢查邏輯
    }
    
    # 計算重複資料數量
    # 作業員報工重複：相同的作業員、工單、工序、日期、時間範圍
    operator_duplicates = OperatorSupplementReport.objects.values(
        'operator', 'workorder', 'process', 'work_date', 'start_time', 'end_time'
    ).annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    operator_duplicate_count = sum(duplicate['count'] - 1 for duplicate in operator_duplicates)
    
    # SMT報工重複：相同的設備、工單、產品、報工時間
    smt_duplicates = SMTProductionReport.objects.values(
        'equipment', 'workorder', 'rd_product_code', 'work_date', 'start_time', 'end_time'
    ).annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    smt_duplicate_count = sum(duplicate['count'] - 1 for duplicate in smt_duplicates)
    
    data_stats['duplicate_reports'] = operator_duplicate_count + smt_duplicate_count
    
    # 維護選項
    maintenance_options = [
        {'id': 'cleanup_old', 'name': '清理舊資料', 'description': '清理30天前的報工記錄'},
        {'id': 'cleanup_duplicates', 'name': '清理重複資料', 'description': '清理重複的報工記錄'},
        {'id': 'optimize_database', 'name': '資料庫優化', 'description': '優化資料庫效能'},
        {'id': 'export_archive', 'name': '匯出歸檔', 'description': '匯出舊資料進行歸檔'},
    ]
    
    # 系統狀態
    from django.db import connection
    import os
    
    # 計算資料庫大小
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
        """)
        db_size = cursor.fetchone()[0]
    
    # 檢查歸檔目錄
    archive_dir = os.path.join(settings.MEDIA_ROOT, 'archives')
    if os.path.exists(archive_dir):
        archive_files = [f for f in os.listdir(archive_dir) if f.endswith('.json')]
        last_archive = max(archive_files, key=lambda x: os.path.getctime(os.path.join(archive_dir, x))) if archive_files else None
        last_archive_time = os.path.getctime(os.path.join(archive_dir, last_archive)) if last_archive else None
    else:
        last_archive_time = None
    
    # 計算磁碟使用率
    try:
        statvfs = os.statvfs(settings.MEDIA_ROOT)
        disk_usage = (1 - statvfs.f_bavail / statvfs.f_blocks) * 100
        disk_usage_str = f"{disk_usage:.1f}%"
    except:
        disk_usage_str = "未知"
    
    system_status = {
        'database_size': db_size,
        'last_backup': '已移至系統管理模組' if last_archive_time else '無',
        'backup_status': 'success' if last_archive_time else 'none',
        'optimization_status': 'good',
        'disk_usage': disk_usage_str,
    }
    
    context = {
        'data_stats': data_stats,
        'maintenance_options': maintenance_options,
        'system_status': system_status,
    }
    return render(request, 'workorder/report/supervisor/maintenance.html', context)

@require_POST
@login_required
def execute_maintenance(request):
    """
    執行維護操作的API端點
    處理各種資料維護功能
    """
    from datetime import date, timedelta
    from django.db.models import Q, Count
    from django.db import connection
    from django.http import JsonResponse
    import json
    import os
    from django.conf import settings
    
    action = request.POST.get('action')
    
    if not action:
        return JsonResponse({'success': False, 'message': '缺少操作類型'})
    
    try:
        if action == 'cleanup_old':
            # 清理30天前的舊資料
            cutoff_date = date.today() - timedelta(days=30)
            
            # 清理作業員報工記錄
            old_operator_reports = OperatorSupplementReport.objects.filter(
                created_at__lt=cutoff_date
            )
            operator_count = old_operator_reports.count()
            old_operator_reports.delete()
            
            # 清理SMT報工記錄
            old_smt_reports = SMTProductionReport.objects.filter(
                created_at__lt=cutoff_date
            )
            smt_count = old_smt_reports.count()
            old_smt_reports.delete()
            
            total_deleted = operator_count + smt_count
            
            return JsonResponse({
                'success': True,
                'message': f'成功清理 {total_deleted} 筆舊資料（作業員報工：{operator_count}，SMT報工：{smt_count}）'
            })
            
        elif action == 'cleanup_duplicates':
            # 清理重複資料
            deleted_count = 0
            
            # 清理作業員報工重複記錄
            # 定義重複：相同的作業員、工單、工序、日期、時間範圍
            operator_duplicates = OperatorSupplementReport.objects.values(
                'operator', 'workorder', 'process', 'work_date', 'start_time', 'end_time'
            ).annotate(
                count=Count('id')
            ).filter(count__gt=1)
            
            for duplicate in operator_duplicates:
                # 保留最新的記錄，刪除其他重複記錄
                reports = OperatorSupplementReport.objects.filter(
                    operator=duplicate['operator'],
                    workorder=duplicate['workorder'],
                    process=duplicate['process'],
                    work_date=duplicate['work_date'],
                    start_time=duplicate['start_time'],
                    end_time=duplicate['end_time']
                ).order_by('-created_at')
                
                # 刪除除最新記錄外的所有重複記錄
                reports_to_delete = reports[1:]
                deleted_count += reports_to_delete.count()
                reports_to_delete.delete()
            
            # 清理SMT報工重複記錄
            # 定義重複：相同的設備、工單、產品、報工時間
            smt_duplicates = SMTProductionReport.objects.values(
                'equipment', 'workorder', 'rd_product_code', 'work_date', 'start_time', 'end_time'
            ).annotate(
                count=Count('id')
            ).filter(count__gt=1)
            
            for duplicate in smt_duplicates:
                # 保留最新的記錄，刪除其他重複記錄
                reports = SMTProductionReport.objects.filter(
                    equipment=duplicate['equipment'],
                    workorder=duplicate['workorder'],
                    rd_product_code=duplicate['rd_product_code'],
                    work_date=duplicate['work_date'],
                    start_time=duplicate['start_time'],
                    end_time=duplicate['end_time']
                ).order_by('-created_at')
                
                # 刪除除最新記錄外的所有重複記錄
                reports_to_delete = reports[1:]
                deleted_count += reports_to_delete.count()
                reports_to_delete.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'成功清理 {deleted_count} 筆重複資料'
            })
            
        elif action == 'optimize_database':
            # 資料庫優化
            with connection.cursor() as cursor:
                # 分析資料表
                cursor.execute("ANALYZE workorder_operatorsupplementreport;")
                cursor.execute("ANALYZE workorder_smtproductionreport;")
                cursor.execute("ANALYZE workorder_workorder;")
                cursor.execute("ANALYZE workorder_workorderprocess;")
                
                # 重新整理資料表
                cursor.execute("REINDEX TABLE workorder_operatorsupplementreport;")
                cursor.execute("REINDEX TABLE workorder_smtproductionreport;")
                cursor.execute("REINDEX TABLE workorder_workorder;")
                cursor.execute("REINDEX TABLE workorder_workorderprocess;")
                
                # 清理過期的統計資訊
                cursor.execute("VACUUM ANALYZE workorder_operatorsupplementreport;")
                cursor.execute("VACUUM ANALYZE workorder_smtproductionreport;")
                cursor.execute("VACUUM ANALYZE workorder_workorder;")
                cursor.execute("VACUUM ANALYZE workorder_workorderprocess;")
            
            return JsonResponse({
                'success': True,
                'message': '資料庫優化完成，已重新整理索引並更新統計資訊'
            })
            
        elif action == 'export_archive':
            # 匯出歸檔資料
            from django.core import serializers
            
            # 取得90天前的資料進行歸檔
            cutoff_date = date.today() - timedelta(days=90)
            
            # 收集要歸檔的資料
            archive_data = {
                'operator_reports': OperatorSupplementReport.objects.filter(
                    created_at__lt=cutoff_date
                ),
                'smt_reports': SMTProductionReport.objects.filter(
                    created_at__lt=cutoff_date
                ),
                'completed_workorders': WorkOrder.objects.filter(
                    status='completed',
                    created_at__lt=cutoff_date
                )
            }
            
            # 建立歸檔目錄
            archive_dir = os.path.join(settings.MEDIA_ROOT, 'archives')
            os.makedirs(archive_dir, exist_ok=True)
            
            # 建立歸檔檔案
            archive_filename = f'workorder_archive_{date.today().strftime("%Y%m%d")}.json'
            archive_path = os.path.join(archive_dir, archive_filename)
            
            # 序列化資料
            all_data = []
            for model_name, queryset in archive_data.items():
                for obj in queryset:
                    all_data.append({
                        'model': f'workorder.{obj._meta.model_name}',
                        'pk': obj.pk,
                        'fields': serializers.serialize('json', [obj])[1:-1]  # 移除外層的方括號
                    })
            
            # 寫入檔案
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
            total_records = (
                archive_data['operator_reports'].count() +
                archive_data['smt_reports'].count() +
                archive_data['completed_workorders'].count()
            )
            
            return JsonResponse({
                'success': True,
                'message': f'成功匯出 {total_records} 筆歸檔資料到 {archive_filename}',
                'download_url': f'/media/archives/{archive_filename}'
            })
            
        else:
            return JsonResponse({'success': False, 'message': '不支援的操作類型'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'執行失敗：{str(e)}'})

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
        work_date=today
    ).select_related('equipment', 'workorder').order_by('-created_at')
    
    # 計算統計資料
    today_reports_count = today_reports_list.count()
    current_shift_output = sum(report.work_quantity for report in today_reports_list)
    
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
@login_required
def submit_smt_report(request):
    """
    API：提交 SMT 報工記錄
    SMT 設備為自動化運作，不需要作業員
    """
    try:
        equipment_id = request.POST.get('equipment_id')
        workorder_id = request.POST.get('workorder_id')
        process_id = request.POST.get('process_id')
        quantity = request.POST.get('quantity')
        notes = request.POST.get('notes', '')
        
        # 基本驗證
        if not all([equipment_id, workorder_id, process_id]):
            return JsonResponse({
                'status': 'error',
                'message': '請填寫所有必要欄位'
            })
        
        # 處理報工數量，允許為 0
        if quantity is None or quantity == '':
            quantity = 0
        else:
            try:
                quantity = int(quantity)
                if quantity < 0:
                    return JsonResponse({
                        'status': 'error',
                        'message': '報工數量不能為負數'
                    })
            except ValueError:
                return JsonResponse({
                    'status': 'error',
                    'message': '報工數量格式錯誤'
                })
        
        # 取得設備和工單
        from equip.models import Equipment
        equipment = Equipment.objects.get(id=equipment_id)
        workorder = WorkOrder.objects.get(id=workorder_id)
        
        # 建立報工記錄
        from .models import SMTProductionReport
        from process.models import ProcessName
        from django.utils import timezone
        
        # 取得選擇的工序（從 WorkOrderProcess 讀取）
        try:
            selected_process = WorkOrderProcess.objects.get(id=process_id)
            process_name = selected_process.process_name
        except WorkOrderProcess.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '找不到指定的工序'
            })
        
        report = SMTProductionReport.objects.create(
            product_id=workorder.product_code,
            workorder=workorder,
            planned_quantity=workorder.quantity,
            operation=process_name,
            equipment=equipment,
            work_date=timezone.now().date(),
            start_time=timezone.now().time(),
            end_time=timezone.now().time(),
            work_quantity=quantity,
            defect_quantity=0,
            is_completed=False,
            remarks=notes,
            created_by=request.user.username if request.user.is_authenticated else 'system',
            report_type='normal',  # 明確設定 report_type
            # 新增：設定工單號碼欄位
            rd_workorder_number=workorder.order_number if workorder else None
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
    except WorkOrderProcess.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '找不到指定的工序'
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

# ============================================================================
# 作業員補登報工功能視圖函數
# ============================================================================

@login_required
def operator_supplement_report_index(request):
    """作業員補登報工記錄列表"""
    from django.db.models import Q
    from process.models import Operator
    from process.models import ProcessName
    
    reports = OperatorSupplementReport.objects.all().order_by('-work_date', '-created_at')
    
    # 篩選條件
    operator_id = request.GET.get('operator')
    if operator_id:
        reports = reports.filter(operator_id=operator_id)
    
    workorder_number = request.GET.get('workorder')
    if workorder_number:
        reports = reports.filter(workorder__order_number__icontains=workorder_number)
    
    process_id = request.GET.get('process')
    if process_id:
        reports = reports.filter(process_id=process_id)
    
    status = request.GET.get('status')
    if status:
        reports = reports.filter(approval_status=status)
    
    date_from = request.GET.get('date_from')
    if date_from:
        reports = reports.filter(work_date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        reports = reports.filter(work_date__lte=date_to)
    
    # 搜尋功能
    search = request.GET.get('search', '')
    if search:
        reports = reports.filter(
            Q(operator__name__icontains=search) |
            Q(workorder__order_number__icontains=search) |
            Q(process__name__icontains=search)
        )
    
    # 統計資料
    total_reports = reports.count()
    pending_reports = reports.filter(approval_status='pending').count()
    approved_reports = reports.filter(approval_status='approved').count()
    rejected_reports = reports.filter(approval_status='rejected').count()
    
    # 分頁
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 取得選項資料
    operator_list = Operator.objects.all().order_by('name')
    process_list = ProcessName.objects.all().order_by('name')
    
    context = {
        'supplement_reports': page_obj,
        'page_obj': page_obj,
        'search': search,
        'total_count': total_reports,
        'pending_count': pending_reports,
        'approved_count': approved_reports,
        'rejected_count': rejected_reports,
        'operator_list': operator_list,
        'process_list': process_list,
        'selected_operator': operator_id,
        'selected_workorder': workorder_number,
        'selected_process': process_id,
        'selected_status': status,
        'selected_date_from': date_from,
        'selected_date_to': date_to,
    }
    return render(request, 'workorder/report/operator/supplement/index.html', context)

@login_required
def operator_supplement_report_create(request):
    """新增作業員補登報工"""
    if request.method == 'POST':
        form = OperatorSupplementReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.created_by = request.user.username
            report.save()
            messages.success(request, '作業員報工記錄新增成功！')
            return redirect('workorder:operator_supplement_report_index')
    else:
        form = OperatorSupplementReportForm()
    
    context = {
        'form': form,
        'title': '新增作業員報工記錄',
    }
    return render(request, 'workorder/report/operator/supplement/form.html', context)

@login_required
def operator_supplement_report_edit(request, report_id):
    """編輯作業員補登報工"""
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的報工記錄！')
        return redirect('workorder:operator_supplement_report_index')
    
    if request.method == 'POST':
        form = OperatorSupplementReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, '作業員報工記錄更新成功！')
            return redirect('workorder:operator_supplement_report_index')
    else:
        form = OperatorSupplementReportForm(instance=report)
    
    context = {
        'form': form,
        'report': report,
        'title': '編輯作業員報工記錄',
    }
    return render(request, 'workorder/report/operator/supplement/form.html', context)

@login_required
def operator_supplement_report_delete(request, report_id):
    """刪除作業員補登報工"""
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
        report.delete()
        messages.success(request, '作業員報工記錄刪除成功！')
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的報工記錄！')
    
    return redirect('workorder:operator_supplement_report_index')

@login_required
def operator_supplement_report_detail(request, report_id):
    """作業員補登報工詳情"""
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的報工記錄！')
        return redirect('workorder:operator_supplement_report_index')
    
    context = {
        'report': report,
    }
    return render(request, 'workorder/report/operator/supplement/detail.html', context)

@login_required
def operator_on_site_report(request):
    """作業員現場報工"""
    if request.method == 'POST':
        form = OperatorOnSiteReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.created_by = request.user.username
            report.work_date = timezone.now().date()
            report.save()
            messages.success(request, '現場報工記錄提交成功！')
            return redirect('workorder:operator_on_site_report')
    else:
        form = OperatorOnSiteReportForm()
    
    # 獲取作業員列表 - 使用真正的作業員模型，而不是 Django User 模型
    from process.models import Operator
    operator_list = Operator.objects.all().order_by('name')
    
    # 獲取設備列表
    from equip.models import Equipment
    equipment_list = Equipment.objects.all()  # 獲取所有設備，因為 Equipment 模型沒有 is_active 欄位
    
    # 獲取當前時間
    from django.utils import timezone
    current_time = timezone.now()
    
    # 獲取統計資料
    from workorder.models import OperatorSupplementReport
    today_reports = OperatorSupplementReport.objects.filter(
        work_date=timezone.now().date()
    ).count()
    
    # 獲取進行中的工單數量
    from workorder.models import WorkOrder
    active_workorders = WorkOrder.objects.filter(status='in_progress').count()
    pending_workorders = WorkOrder.objects.filter(status='pending').count()
    
    # 獲取工作中作業員數量（這裡可以根據實際需求調整邏輯）
    working_operators = operator_list.count()  # 簡化計算，實際應該根據報工狀態
    
    context = {
        'form': form,
        'title': '作業員現場報工',
        'operator_list': operator_list,
        'equipment_list': equipment_list,
        'current_time': current_time,
        'working_operators': working_operators,
        'today_reports': today_reports,
        'active_workorders': active_workorders,
        'pending_workorders': pending_workorders,
        'operator_status_list': [],  # 可以根據需求實作作業員狀態
        'recent_reports': [],  # 可以根據需求實作最近報工記錄
    }
    return render(request, 'workorder/report/operator/on_site.html', context)

# ============================================================================
# SMT補登報工功能視圖函數
# ============================================================================

@login_required
def smt_supplement_report_index(request):
    """SMT補登報工記錄列表"""
    reports = SMTProductionReport.objects.all().order_by('-work_date', '-created_at')
    
    # 搜尋功能
    search = request.GET.get('search', '')
    if search:
        reports = reports.filter(
            Q(equipment__name__icontains=search) |
            Q(workorder__order_number__icontains=search) |
            Q(product_id__icontains=search)
        )
    
    # 分頁
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'total_count': reports.count(),
    }
    return render(request, 'workorder/report/smt/supplement/index.html', context)

@login_required
def smt_supplement_report_create(request):
    """新增SMT補登報工"""
    if request.method == 'POST':
        form = SMTSupplementReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.created_by = request.user.username
            report.save()
            messages.success(request, 'SMT補登報工記錄新增成功！')
            return redirect('workorder:smt_supplement_report_index')
    else:
        form = SMTSupplementReportForm()
    
    context = {
        'form': form,
        'title': '新增SMT補登報工記錄',
    }
    return render(request, 'workorder/report/smt/supplement/form.html', context)

@login_required
def smt_supplement_report_edit(request, report_id):
    """編輯SMT補登報工"""
    try:
        report = SMTProductionReport.objects.get(id=report_id)
    except SMTProductionReport.DoesNotExist:
        messages.error(request, '找不到指定的SMT補登報工記錄！')
        return redirect('workorder:smt_supplement_report_index')
    
    if request.method == 'POST':
        form = SMTSupplementReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, 'SMT補登報工記錄更新成功！')
            return redirect('workorder:smt_supplement_report_index')
    else:
        form = SMTSupplementReportForm(instance=report)
    
    context = {
        'form': form,
        'report': report,
        'title': '編輯SMT補登報工記錄',
    }
    return render(request, 'workorder/report/smt/supplement/form.html', context)

@login_required
def smt_supplement_report_delete(request, report_id):
    """刪除SMT補登報工"""
    try:
        report = SMTProductionReport.objects.get(id=report_id)
        report.delete()
        messages.success(request, 'SMT補登報工記錄刪除成功！')
    except SMTProductionReport.DoesNotExist:
        messages.error(request, '找不到指定的SMT補登報工記錄！')
    
    return redirect('workorder:smt_supplement_report_index')

@login_required
def smt_supplement_report_detail(request, report_id):
    """SMT補登報工詳情"""
    try:
        supplement_report = SMTProductionReport.objects.get(id=report_id)
    except SMTProductionReport.DoesNotExist:
        messages.error(request, '找不到指定的SMT補登報工記錄！')
        return redirect('workorder:smt_supplement_report_index')
    
    context = {
        'supplement_report': supplement_report,
    }
    return render(request, 'workorder/report/smt/supplement/detail.html', context)

# ============================================================================
# 主管審核功能視圖函數
# ============================================================================

@login_required
def supervisor_approve_reports(request):
    """主管審核報工記錄"""
    pending_reports = OperatorSupplementReport.objects.filter(
        is_approved=False
            ).order_by('-work_date', '-created_at')
    
    # 搜尋功能
    search = request.GET.get('search', '')
    if search:
        pending_reports = pending_reports.filter(
            Q(operator__username__icontains=search) |
            Q(workorder__order_number__icontains=search)
        )
    
    # 分頁
    paginator = Paginator(pending_reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'total_count': pending_reports.count(),
    }
    return render(request, 'workorder/report/supervisor/approve.html', context)

@login_required
def approve_report(request, report_id):
    """審核單筆報工記錄"""
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
        report.is_approved = True
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        messages.success(request, '報工記錄審核通過！')
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的報工記錄！')
    
    return redirect('workorder:supervisor_approve_reports')

@login_required
def reject_report(request, report_id):
    """駁回單筆報工記錄"""
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
        report.is_approved = False
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        messages.success(request, '報工記錄已駁回！')
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的報工記錄！')
    
    return redirect('workorder:supervisor_approve_reports')

# ============================================================================
# API功能視圖函數
# ============================================================================

@require_GET
@login_required
def api_get_operator_reports(request):
    """API：取得作業員報工記錄"""
    try:
        reports = OperatorSupplementReport.objects.all().order_by('-work_date')
        
        # 篩選條件
        operator_id = request.GET.get('operator_id')
        if operator_id:
            reports = reports.filter(operator_id=operator_id)
        
        workorder_id = request.GET.get('workorder_id')
        if workorder_id:
            reports = reports.filter(workorder_id=workorder_id)
        
        date_from = request.GET.get('date_from')
        if date_from:
            reports = reports.filter(work_date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            reports = reports.filter(work_date__lte=date_to)
        
        # 序列化資料
        data = []
        for report in reports:
            data.append({
                'id': report.id,
                'operator': report.operator.username,
                'workorder': report.workorder.order_number,
                'process': report.process,
                'quantity': report.quantity,
                'work_date': report.work_date.isoformat(),
                'is_approved': report.is_approved,
                'created_at': report.created_at.isoformat(),
            })
        
        return JsonResponse({
            'status': 'success',
            'data': data,
            'total_count': len(data)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@require_GET
@login_required
def api_get_smt_reports(request):
    """API：取得SMT報工記錄"""
    try:
        reports = SMTProductionReport.objects.all().order_by('-work_date')
        
        # 篩選條件
        equipment_id = request.GET.get('equipment_id')
        if equipment_id:
            reports = reports.filter(equipment_id=equipment_id)
        
        workorder_id = request.GET.get('workorder_id')
        if workorder_id:
            reports = reports.filter(workorder_id=workorder_id)
        
        date_from = request.GET.get('date_from')
        if date_from:
            reports = reports.filter(work_date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            reports = reports.filter(work_date__lte=date_to)
        
        # 序列化資料
        data = []
        for report in reports:
            data.append({
                'id': report.id,
                'equipment': report.equipment.name,
                'workorder': report.workorder.order_number,
                'product_id': report.product_id,
                'work_quantity': report.work_quantity,
                'defect_quantity': report.defect_quantity,
                'work_date': report.work_date.isoformat(),
                'created_at': report.created_at.isoformat(),
            })
        
        return JsonResponse({
            'status': 'success',
            'data': data,
            'total_count': len(data)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

# ============================================================================
# 報表匯出功能視圖函數
# ============================================================================

@login_required
def export_operator_reports(request):
    """匯出作業員報工記錄"""
    try:
        reports = OperatorSupplementReport.objects.all().order_by('-work_date')
        
        # 篩選條件
        date_from = request.GET.get('date_from')
        if date_from:
            reports = reports.filter(work_date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            reports = reports.filter(work_date__lte=date_to)
        
        # 建立Excel檔案
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        
        wb = Workbook()
        ws = wb.active
        ws.title = "作業員報工記錄"
        
        # 設定標題
        headers = ['作業員', '工單號', '工序', '數量', '報工日期', '審核狀態', '建立時間']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # 填入資料
        for row, report in enumerate(reports, 2):
            ws.cell(row=row, column=1, value=report.operator.username)
            ws.cell(row=row, column=2, value=report.workorder.order_number)
            ws.cell(row=row, column=3, value=report.process)
            ws.cell(row=row, column=4, value=report.quantity)
            ws.cell(row=row, column=5, value=report.work_date.strftime('%Y-%m-%d'))
            ws.cell(row=row, column=6, value='已審核' if report.is_approved else '待審核')
            ws.cell(row=row, column=7, value=report.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        
        # 調整欄寬
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # 儲存檔案
        from django.http import HttpResponse
        from io import BytesIO
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="作業員報工記錄_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'匯出失敗：{str(e)}')
        return redirect('workorder:operator_supplement_report_index')

@login_required
def export_smt_reports(request):
    """匯出SMT報工記錄"""
    try:
        reports = SMTProductionReport.objects.all().order_by('-work_date')
        
        # 篩選條件
        date_from = request.GET.get('date_from')
        if date_from:
            reports = reports.filter(work_date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            reports = reports.filter(work_date__lte=date_to)
        
        # 建立Excel檔案
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        
        wb = Workbook()
        ws = wb.active
        ws.title = "SMT報工記錄"
        
        # 設定標題
        headers = ['設備', '工單號', '產品編號', '良品數量', '不良品數量', '報工日期', '建立時間']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # 填入資料
        for row, report in enumerate(reports, 2):
            ws.cell(row=row, column=1, value=report.equipment.name)
            ws.cell(row=row, column=2, value=report.workorder.order_number)
            ws.cell(row=row, column=3, value=report.product_id)
            ws.cell(row=row, column=4, value=report.work_quantity)
            ws.cell(row=row, column=5, value=report.defect_quantity)
            ws.cell(row=row, column=6, value=report.work_date.strftime('%Y-%m-%d'))
            ws.cell(row=row, column=7, value=report.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        
        # 調整欄寬
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # 儲存檔案
        from django.http import HttpResponse
        from io import BytesIO
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="SMT報工記錄_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'匯出失敗：{str(e)}')
        return redirect('workorder:smt_supplement_report_index')

# ============================================================================
# 審核功能視圖函數
# ============================================================================

@login_required
def operator_supplement_report_approve(request, report_id):
    """審核作業員補登報工"""
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
        report.is_approved = True
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        messages.success(request, '作業員報工記錄審核通過！')
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的報工記錄！')
    
    return redirect('workorder:operator_supplement_report_index')

@login_required
def operator_supplement_report_reject(request, report_id):
    """駁回作業員補登報工"""
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
        report.is_approved = False
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        messages.success(request, '作業員報工記錄已駁回！')
    except OperatorSupplementReport.DoesNotExist:
        messages.error(request, '找不到指定的報工記錄！')
    
    return redirect('workorder:operator_supplement_report_index')

@login_required
def smt_supplement_report_approve(request, report_id):
    """審核SMT補登報工"""
    try:
        report = SMTProductionReport.objects.get(id=report_id)
        report.is_approved = True
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        messages.success(request, 'SMT報工記錄審核通過！')
    except SMTProductionReport.DoesNotExist:
        messages.error(request, '找不到指定的SMT報工記錄！')
    
    return redirect('workorder:smt_supplement_report_index')

@login_required
def smt_supplement_report_reject(request, report_id):
    """駁回SMT補登報工"""
    try:
        report = SMTProductionReport.objects.get(id=report_id)
        report.is_approved = False
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        messages.success(request, 'SMT報工記錄已駁回！')
    except SMTProductionReport.DoesNotExist:
        messages.error(request, '找不到指定的SMT報工記錄！')
    
    return redirect('workorder:smt_supplement_report_index')

# ============================================================================
# 批次處理功能視圖函數
# ============================================================================

@login_required
def operator_supplement_batch(request):
    """作業員補登報工批次處理"""
    if request.method == 'POST':
        action = request.POST.get('action')
        report_ids = request.POST.getlist('report_ids')
        
        if not report_ids:
            messages.error(request, '請選擇要處理的報工記錄！')
            return redirect('workorder:operator_supplement_report_index')
        
        try:
            reports = OperatorSupplementReport.objects.filter(id__in=report_ids)
            
            if action == 'approve':
                reports.update(
                    is_approved=True,
                    approved_by=request.user.username,
                    approved_at=timezone.now()
                )
                messages.success(request, f'已審核 {len(reports)} 筆作業員報工記錄！')
            elif action == 'reject':
                reports.update(
                    is_approved=False,
                    approved_by=request.user.username,
                    approved_at=timezone.now()
                )
                messages.success(request, f'已駁回 {len(reports)} 筆作業員報工記錄！')
            elif action == 'delete':
                count = reports.count()
                reports.delete()
                messages.success(request, f'已刪除 {count} 筆作業員報工記錄！')
            else:
                messages.error(request, '無效的操作！')
                
        except Exception as e:
            messages.error(request, f'批次處理失敗：{str(e)}')
    
    return redirect('workorder:operator_supplement_report_index')

@login_required
def smt_supplement_batch(request):
    """SMT補登報工批次處理"""
    if request.method == 'POST':
        action = request.POST.get('action')
        report_ids = request.POST.getlist('report_ids')
        
        if not report_ids:
            messages.error(request, '請選擇要處理的SMT報工記錄！')
            return redirect('workorder:smt_supplement_report_index')
        
        try:
            reports = SMTProductionReport.objects.filter(id__in=report_ids)
            
            if action == 'approve':
                reports.update(
                    is_approved=True,
                    approved_by=request.user.username,
                    approved_at=timezone.now()
                )
                messages.success(request, f'已審核 {len(reports)} 筆SMT報工記錄！')
            elif action == 'reject':
                reports.update(
                    is_approved=False,
                    approved_by=request.user.username,
                    approved_at=timezone.now()
                )
                messages.success(request, f'已駁回 {len(reports)} 筆SMT報工記錄！')
            elif action == 'delete':
                count = reports.count()
                reports.delete()
                messages.success(request, f'已刪除 {count} 筆SMT報工記錄！')
            else:
                messages.error(request, '無效的操作！')
                
        except Exception as e:
            messages.error(request, f'批次處理失敗：{str(e)}')
    
    return redirect('workorder:smt_supplement_report_index')

# ============================================================================
# 匯出功能視圖函數
# ============================================================================

@login_required
def operator_supplement_export(request):
    """匯出作業員補登報工記錄"""
    try:
        reports = OperatorSupplementReport.objects.all().order_by('-work_date')
        
        # 篩選條件
        date_from = request.GET.get('date_from')
        if date_from:
            reports = reports.filter(work_date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            reports = reports.filter(work_date__lte=date_to)
        
        operator_id = request.GET.get('operator_id')
        if operator_id:
            reports = reports.filter(operator_id=operator_id)
        
        # 建立Excel檔案
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        
        wb = Workbook()
        ws = wb.active
        ws.title = "作業員補登報工記錄"
        
        # 設定標題
        headers = ['作業員', '工單號', '工序', '數量', '報工日期', '審核狀態', '建立時間', '審核者', '審核時間']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # 填入資料
        for row, report in enumerate(reports, 2):
            ws.cell(row=row, column=1, value=report.operator.username)
            ws.cell(row=row, column=2, value=report.workorder.order_number)
            ws.cell(row=row, column=3, value=report.process)
            ws.cell(row=row, column=4, value=report.quantity)
            ws.cell(row=row, column=5, value=report.work_date.strftime('%Y-%m-%d'))
            ws.cell(row=row, column=6, value='已審核' if report.is_approved else '待審核')
            ws.cell(row=row, column=7, value=report.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            ws.cell(row=row, column=8, value=report.approved_by or '')
            ws.cell(row=row, column=9, value=report.approved_at.strftime('%Y-%m-%d %H:%M:%S') if report.approved_at else '')
        
        # 調整欄寬
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # 儲存檔案
        from django.http import HttpResponse
        from io import BytesIO
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="作業員補登報工記錄_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'匯出失敗：{str(e)}')
        return redirect('workorder:operator_supplement_report_index')

@login_required
def smt_supplement_export(request):
    """匯出SMT補登報工記錄"""
    try:
        reports = SMTProductionReport.objects.all().order_by('-work_date')
        
        # 篩選條件
        date_from = request.GET.get('date_from')
        if date_from:
            reports = reports.filter(work_date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            reports = reports.filter(work_date__lte=date_to)
        
        equipment_id = request.GET.get('equipment_id')
        if equipment_id:
            reports = reports.filter(equipment_id=equipment_id)
        
        # 建立Excel檔案
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        
        wb = Workbook()
        ws = wb.active
        ws.title = "SMT補登報工記錄"
        
        # 設定標題
        headers = ['設備', '工單號', '產品編號', '良品數量', '不良品數量', '報工日期', '建立時間', '審核者', '審核時間']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # 填入資料
        for row, report in enumerate(reports, 2):
            ws.cell(row=row, column=1, value=report.equipment.name)
            ws.cell(row=row, column=2, value=report.workorder.order_number)
            ws.cell(row=row, column=3, value=report.product_id)
            ws.cell(row=row, column=4, value=report.work_quantity)
            ws.cell(row=row, column=5, value=report.defect_quantity)
            ws.cell(row=row, column=6, value=report.work_date.strftime('%Y-%m-%d'))
            ws.cell(row=row, column=7, value=report.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            ws.cell(row=row, column=8, value=report.approved_by or '')
            ws.cell(row=row, column=9, value=report.approved_at.strftime('%Y-%m-%d %H:%M:%S') if report.approved_at else '')
        
        # 調整欄寬
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # 儲存檔案
        from django.http import HttpResponse
        from io import BytesIO
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="SMT補登報工記錄_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'匯出失敗：{str(e)}')
        return redirect('workorder:smt_supplement_report_index')

# ============================================================================
# 模板下載功能視圖函數
# ============================================================================

@login_required
def operator_supplement_template(request):
    """下載作業員補登報工模板"""
    try:
        # 建立Excel檔案
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        
        wb = Workbook()
        ws = wb.active
        ws.title = "作業員補登報工模板"
        
        # 設定標題
        headers = ['作業員', '工單號', '工序', '數量', '報工日期', '備註']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # 添加範例資料
        example_data = [
            ['張三', 'WO2024001', '組裝', 100, '2024-01-15', '正常生產'],
            ['李四', 'WO2024002', '測試', 50, '2024-01-15', '品質檢查'],
        ]
        
        for row, data in enumerate(example_data, 2):
            for col, value in enumerate(data, 1):
                ws.cell(row=row, column=col, value=value)
        
        # 調整欄寬
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # 儲存檔案
        from django.http import HttpResponse
        from io import BytesIO
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="作業員補登報工模板_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'模板下載失敗：{str(e)}')
        return redirect('workorder:operator_supplement_report_index')

@login_required
def smt_supplement_template(request):
    """下載SMT補登報工模板"""
    try:
        # 建立Excel檔案
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment
        
        wb = Workbook()
        ws = wb.active
        ws.title = "SMT補登報工模板"
        
        # 設定標題
        headers = ['設備', '工單號', '產品編號', '良品數量', '不良品數量', '報工日期', '備註']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # 添加範例資料
        example_data = [
            ['SMT-001', 'WO2024001', 'PROD001', 100, 2, '2024-01-15', '正常生產'],
            ['SMT-002', 'WO2024002', 'PROD002', 50, 1, '2024-01-15', '品質檢查'],
        ]
        
        for row, data in enumerate(example_data, 2):
            for col, value in enumerate(data, 1):
                ws.cell(row=row, column=col, value=value)
        
        # 調整欄寬
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # 儲存檔案
        from django.http import HttpResponse
        from io import BytesIO
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="SMT補登報工模板_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'模板下載失敗：{str(e)}')
        return redirect('workorder:smt_supplement_report_index')

# ============================================================================
# API功能視圖函數
# ============================================================================

@require_POST
@login_required
def operator_supplement_batch_create(request):
    """API：批次建立作業員補登報工"""
    try:
        data = json.loads(request.body)
        reports_data = data.get('reports', [])
        
        created_count = 0
        errors = []
        
        for report_data in reports_data:
            try:
                # 驗證必要欄位
                required_fields = ['operator_id', 'workorder_id', 'process', 'quantity', 'work_date']
                for field in required_fields:
                    if field not in report_data:
                        errors.append(f'缺少必要欄位：{field}')
                        continue
                
                # 建立報工記錄
                report = OperatorSupplementReport.objects.create(
                    operator_id=report_data['operator_id'],
                    workorder_id=report_data['workorder_id'],
                    process=report_data['process'],
                    quantity=report_data['quantity'],
                    work_date=report_data['work_date'],
                    notes=report_data.get('notes', ''),
                    created_by=request.user.username if request.user.is_authenticated else 'system'
                )
                created_count += 1
                
            except Exception as e:
                errors.append(f'建立記錄失敗：{str(e)}')
        
        return JsonResponse({
            'status': 'success',
            'created_count': created_count,
            'errors': errors
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@require_POST
@login_required
def smt_supplement_batch_create(request):
    """API：批次建立SMT補登報工"""
    try:
        data = json.loads(request.body)
        reports_data = data.get('reports', [])
        
        created_count = 0
        errors = []
        
        for report_data in reports_data:
            try:
                # 驗證必要欄位
                required_fields = ['equipment_id', 'workorder_id', 'product_id', 'work_quantity', 'work_date']
                for field in required_fields:
                    if field not in report_data:
                        errors.append(f'缺少必要欄位：{field}')
                        continue
                
                # 建立報工記錄
                report = SMTProductionReport.objects.create(
                    equipment_id=report_data['equipment_id'],
                    workorder_id=report_data['workorder_id'],
                    product_id=report_data['product_id'],
                    work_quantity=report_data['work_quantity'],
                    defect_quantity=report_data.get('defect_quantity', 0),
                    work_date=report_data['work_date'],
                    remarks=report_data.get('remarks', ''),
                    created_by=request.user.username if request.user.is_authenticated else 'system'
                )
                created_count += 1
                
            except Exception as e:
                errors.append(f'建立記錄失敗：{str(e)}')
        
        return JsonResponse({
            'status': 'success',
            'created_count': created_count,
            'errors': errors
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

# ============================================================================
# 主管功能視圖函數
# ============================================================================

@login_required
def supervisor_index(request):
    """主管功能首頁"""
    # 統計資料
    total_operator_reports = OperatorSupplementReport.objects.count()
    pending_operator_reports = OperatorSupplementReport.objects.filter(is_approved=False).count()
    approved_operator_reports = OperatorSupplementReport.objects.filter(is_approved=True).count()
    
    total_smt_reports = SMTProductionReport.objects.count()
    pending_smt_reports = SMTProductionReport.objects.filter(is_approved=False).count()
    approved_smt_reports = SMTProductionReport.objects.filter(is_approved=True).count()
    
    context = {
        'total_operator_reports': total_operator_reports,
        'pending_operator_reports': pending_operator_reports,
        'approved_operator_reports': approved_operator_reports,
        'total_smt_reports': total_smt_reports,
        'pending_smt_reports': pending_smt_reports,
        'approved_smt_reports': approved_smt_reports,
    }
    return render(request, 'workorder/report/supervisor/index.html', context)

# ============================================================================
# 其他API功能視圖函數
# ============================================================================

@require_GET
@login_required
def get_workorders_by_operator(request):
    """API：根據作業員取得工單"""
    try:
        operator_id = request.GET.get('operator_id')
        if not operator_id:
            return JsonResponse({
                'status': 'error',
                'message': '請提供作業員ID'
            })
        
        # 移除所有過濾：顯示所有工單，完全自由選擇
        workorders = WorkOrder.objects.all().distinct()
        
        workorders_data = []
        for workorder in workorders:
            # 檢查工單是否有進行中的工序
            has_in_progress = workorder.processes.filter(status='in_progress').exists()
            process_status = 'in_progress' if has_in_progress else 'pending'
            
            workorders_data.append({
                'id': workorder.id,
                'order_number': workorder.order_number,
                'company_code': workorder.company_code,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'status': workorder.status,
                'process_status': process_status
            })
        
        return JsonResponse({
            'status': 'success',
            'workorders': workorders_data
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@require_GET
@login_required
def get_processes_by_workorder_for_operator(request):
    """API：根據工單取得工序（作業員用），自動排除SMT工序"""
    try:
        workorder_id = request.GET.get('workorder_id')
        if not workorder_id:
            return JsonResponse({
                'status': 'error',
                'message': '請提供工單ID'
            })
        from workorder.models import WorkOrderProcess
        processes = WorkOrderProcess.objects.filter(
            workorder_id=workorder_id
        ).exclude(process_name__icontains='SMT').order_by('step_order')
        data = []
        for process in processes:
            data.append({
                'id': process.id,
                'process_name': process.process_name,
                'sequence': process.step_order,
                'status': process.status,
            })
        return JsonResponse({
            'status': 'success',
            'processes': data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'載入失敗:{str(e)}'
        })

@require_POST
@login_required
def submit_operator_report(request):
    """API：提交作業員報工"""
    try:
        data = json.loads(request.body)
        
        # 驗證必要欄位
        required_fields = ['operator_id', 'workorder_id', 'process_id', 'quantity']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'status': 'error',
                    'message': f'缺少必要欄位：{field}'
                })
        
        # 建立報工記錄
        report = OperatorSupplementReport.objects.create(
            operator_id=data['operator_id'],
            workorder_id=data['workorder_id'],
            process=data.get('process_name', ''),
            quantity=data['quantity'],
            work_date=data.get('work_date', timezone.now().date()),
            notes=data.get('notes', ''),
            created_by=request.user.username if request.user.is_authenticated else 'system'
        )
        
        return JsonResponse({
            'status': 'success',
            'message': '報工記錄提交成功',
            'report_id': report.id
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@require_GET
@login_required
def get_smt_workorders_by_equipment(request):
    """API：根據設備取得工單（SMT用）"""
    try:
        equipment_id = request.GET.get('equipment_id')
        if not equipment_id:
            return JsonResponse({
                'status': 'error',
                'message': '請提供設備ID'
            })
        
        # 修正查詢條件：使用 processes 作為 related_name
        workorders = WorkOrder.objects.filter(
            processes__assigned_equipment=equipment_id
        ).distinct()
        
        data = []
        for workorder in workorders:
            # 取得該工單的工序狀態
            processes = WorkOrderProcess.objects.filter(
                workorder=workorder,
                assigned_equipment=equipment_id
            ).order_by('step_order')
            
            # 檢查是否有正在進行的工序
            process_status = 'pending'
            for process in processes:
                if process.status == 'in_progress':
                    process_status = 'in_progress'
                    break
                elif process.status == 'completed':
                    process_status = 'completed'
            
            data.append({
                'id': workorder.id,
                'order_number': workorder.order_number,
                'company_code': workorder.company_code,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'process_status': process_status,
            })
        
        return JsonResponse({
            'status': 'success',
            'workorders': data
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'載入失敗:{str(e)}'
        })

@require_GET
@login_required
def get_workorders_by_product(request):
    """API：根據產品取得工單（從派工單取得）"""
    try:
        product_code = request.GET.get('product_id') or request.GET.get('product_code')
        if not product_code:
            return JsonResponse({
                'status': 'error',
                'message': '請提供產品編號'
            })
        
        # 從派工單中取得指定產品編號的工單號碼
        from .models import WorkOrderDispatch
        
        dispatch_queryset = WorkOrderDispatch.objects.filter(
            product_code__icontains=product_code,
            status__in=["dispatched", "in_production"]  # 只選擇已派工或生產中的派工單
        )
        
        # 取得派工單中的工單號碼列表
        order_numbers = dispatch_queryset.values_list('order_number', flat=True)
        
        # 根據派工單的工單號碼查詢工單
        workorders = WorkOrder.objects.filter(
            order_number__in=order_numbers
        ).exclude(
            order_number__icontains="RD樣品"
        ).exclude(
            order_number__icontains="RD-樣品"
        ).exclude(
            order_number__icontains="RD樣本"
        ).exclude(
            status="completed"
        )
        
        data = []
        for workorder in workorders:
            data.append({
                'id': workorder.id,
                'order_number': workorder.order_number,
                'company_code': workorder.company_code,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'status': workorder.status,
            })
        
        return JsonResponse({
            'status': 'success',
            'workorders': data
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@require_GET
@login_required
def get_workorder_details(request):
    """API：取得工單詳細資料"""
    try:
        workorder_id = request.GET.get('workorder_id')
        if not workorder_id:
            return JsonResponse({
                'status': 'error',
                'message': '請提供工單ID'
            })
        
        workorder = WorkOrder.objects.get(id=workorder_id)
        processes = WorkOrderProcess.objects.filter(workorder=workorder).order_by('step_order')
        
        process_data = []
        for process in processes:
            process_data.append({
                'id': process.id,
                'process_name': process.process_name,
                'sequence': process.step_order,  # 修正欄位名稱
                'assigned_equipment': process.assigned_equipment,  # 修正欄位名稱
                'assigned_operator': process.assigned_operator,  # 修正欄位名稱
            })
        
        data = {
            'id': workorder.id,
            'order_number': workorder.order_number,
            'company_code': workorder.company_code,
            'product_code': workorder.product_code,
            'quantity': workorder.quantity,
            'status': workorder.status,
            'processes': process_data,
        }
        
        return JsonResponse({
            'status': 'success',
            'workorder': data
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '找不到指定的工單'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'載入失敗:{str(e)}'
        })

@require_GET
@login_required
def get_workorder_info(request):
    """API：取得工單基本資訊"""
    try:
        workorder_id = request.GET.get('workorder_id')
        if not workorder_id:
            return JsonResponse({
                'status': 'error',
                'message': '請提供工單ID'
            })
        
        workorder = WorkOrder.objects.get(id=workorder_id)
        
        data = {
            'id': workorder.id,
            'order_number': workorder.order_number,
            'company_code': workorder.company_code,
            'product_code': workorder.product_code,
            'quantity': workorder.quantity,
            'status': workorder.status,
        }
        
        return JsonResponse({
            'status': 'success',
            'data': data
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '找不到指定的工單'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })
