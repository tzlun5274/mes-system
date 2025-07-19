# kanban/views.py
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import (
    KanbanProductionProgress,
    KanbanEquipmentStatus,
    KanbanQualityMonitoring,
    KanbanMaterialStock,
    KanbanDeliverySchedule,
)
from .utils import log_user_operation
from collections import Counter

# 設定看板模組的日誌記錄器
kanban_logger = logging.getLogger("kanban")
kanban_handler = logging.FileHandler("/var/log/mes/kanban.log")
kanban_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
kanban_logger.addHandler(kanban_handler)
kanban_logger.setLevel(logging.INFO)


# 檢查用戶是否屬於「看板使用者」群組，或者是超級用戶
def kanban_user_required(user):
    return user.is_superuser or user.groups.filter(name="看板使用者").exists()


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def index(request):
    log_user_operation(request.user.username, "kanban", "訪問看板功能模組首頁")
    production_progress = KanbanProductionProgress.objects.all()[:5]
    equipment_status = KanbanEquipmentStatus.objects.all()[:5]
    quality_monitoring = KanbanQualityMonitoring.objects.all()[:5]
    material_stock = KanbanMaterialStock.objects.all()[:5]
    delivery_schedule = KanbanDeliverySchedule.objects.all()[:5]

    return render(
        request,
        "kanban/index.html",
        {
            "production_progress": production_progress,
            "equipment_status": equipment_status,
            "quality_monitoring": quality_monitoring,
            "material_stock": material_stock,
            "delivery_schedule": delivery_schedule,
        },
    )


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def production_progress(request):
    log_user_operation(request.user.username, "kanban", "查看生產進度看板")
    # 獲取排序參數
    sort_by = request.GET.get("sort_by", "-updated_at")  # 預設按更新時間降序
    production_progress = KanbanProductionProgress.objects.all().order_by(sort_by)

    # 添加分頁
    paginator = Paginator(production_progress, 10)  # 每頁顯示 10 條數據
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "kanban/production_progress.html",
        {
            "page_obj": page_obj,
            "sort_by": sort_by,
        },
    )


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def equipment_status(request):
    log_user_operation(request.user.username, "kanban", "查看設備狀態看板")
    # 獲取過濾參數
    line_filter = request.GET.get("line", "")
    if line_filter:
        equipment_status = KanbanEquipmentStatus.objects.filter(line=line_filter)
    else:
        equipment_status = KanbanEquipmentStatus.objects.all()

    # 生產線選項（用於過濾表單）
    line_choices = KanbanEquipmentStatus._meta.get_field("line").choices

    return render(
        request,
        "kanban/equipment_status.html",
        {
            "equipment_status": equipment_status,
            "line_choices": line_choices,
            "selected_line": line_filter,
        },
    )


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def quality_monitoring(request):
    log_user_operation(request.user.username, "kanban", "查看品質監控看板")
    quality_monitoring = KanbanQualityMonitoring.objects.all()
    return render(
        request,
        "kanban/quality_monitoring.html",
        {
            "quality_monitoring": quality_monitoring,
        },
    )


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def material_stock(request):
    log_user_operation(request.user.username, "kanban", "查看物料存量看板")
    material_stock = KanbanMaterialStock.objects.all()
    return render(
        request,
        "kanban/material_stock.html",
        {
            "material_stock": material_stock,
        },
    )


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def delivery_schedule(request):
    log_user_operation(request.user.username, "kanban", "查看預交貨日看板")
    delivery_schedule = KanbanDeliverySchedule.objects.all()
    return render(
        request,
        "kanban/delivery_schedule.html",
        {
            "delivery_schedule": delivery_schedule,
        },
    )


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def get_production_progress(request):
    log_user_operation(request.user.username, "kanban", "通過 API 獲取生產進度看板數據")
    production_progress = KanbanProductionProgress.objects.all()
    production_progress_data = [
        {
            "id": progress.id,
            "work_order_number": progress.work_order_number,
            "product_name": progress.product_name,
            "total_quantity": progress.total_quantity,
            "completed_quantity": progress.completed_quantity,
            "progress": progress.progress,
            "created_at": progress.created_at.isoformat(),
            "updated_at": progress.updated_at.isoformat(),
        }
        for progress in production_progress
    ]
    return JsonResponse({"production_progress": production_progress_data})


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def get_equipment_status(request):
    log_user_operation(request.user.username, "kanban", "通過 API 獲取設備狀態看板數據")
    equipment_status = KanbanEquipmentStatus.objects.all()
    equipment_status_data = [
        {
            "id": equipment.id,
            "equipment_name": equipment.equipment_name,
            "line": equipment.line,
            "status": equipment.status,
            "last_updated": equipment.last_updated.isoformat(),
        }
        for equipment in equipment_status
    ]
    return JsonResponse({"equipment_status": equipment_status_data})


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def get_quality_monitoring(request):
    log_user_operation(request.user.username, "kanban", "通過 API 獲取品質監控看板數據")
    quality_monitoring = KanbanQualityMonitoring.objects.all()
    quality_monitoring_data = [
        {
            "id": quality.id,
            "product_name": quality.product_name,
            "defect_rate": quality.defect_rate,
            "total_inspected": quality.total_inspected,
            "defective_count": quality.defective_count,
            "last_updated": quality.last_updated.isoformat(),
        }
        for quality in quality_monitoring
    ]
    return JsonResponse({"quality_monitoring": quality_monitoring_data})


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def get_material_stock(request):
    log_user_operation(request.user.username, "kanban", "通過 API 獲取物料存量看板數據")
    material_stock = KanbanMaterialStock.objects.all()
    material_stock_data = [
        {
            "id": material.id,
            "material_code": material.material_code,
            "material_name": material.material_name,
            "stock_quantity": material.stock_quantity,
            "unit": material.unit,
            "last_updated": material.last_updated.isoformat(),
        }
        for material in material_stock
    ]
    return JsonResponse({"material_stock": material_stock_data})


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def get_delivery_schedule(request):
    log_user_operation(request.user.username, "kanban", "通過 API 獲取預交貨日看板數據")
    delivery_schedule = KanbanDeliverySchedule.objects.all()
    delivery_schedule_data = [
        {
            "id": schedule.id,
            "order_number": schedule.order_number,
            "product_name": schedule.product_name,
            "quantity": schedule.quantity,
            "due_date": schedule.due_date.isoformat(),
            "created_at": schedule.created_at.isoformat(),
            "updated_at": schedule.updated_at.isoformat(),
        }
        for schedule in delivery_schedule
    ]
    return JsonResponse({"delivery_schedule": delivery_schedule_data})


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def schedule_warning_board(request):
    """
    排程警告看板：分頁顯示所有排程驗證警告（每頁 20 筆）
    """
    from scheduling.scheduling_models import (
        ScheduleWarning,
    )  # 只在函式內 import，避免啟動卡住

    warnings_list = ScheduleWarning.objects.all().order_by("-created_at")
    paginator = Paginator(warnings_list, 20)  # 每頁 20 筆
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "kanban/schedule_warning_board.html", {"page_obj": page_obj})


@login_required
@user_passes_test(kanban_user_required, login_url="/accounts/login/")
def schedule_warning_reason_stats(request):
    """
    統計所有排程警告的衝突原因，回傳每種原因的數量（繁體中文說明）。
    """
    from scheduling.scheduling_models import ScheduleWarning

    warnings = ScheduleWarning.objects.all()
    reason_counter = Counter()
    for w in warnings:
        msg = w.warning_message
        if "時間衝突" in msg:
            reason_counter["作業員時間衝突"] += 1
        elif "設備衝突" in msg:
            reason_counter["設備衝突"] += 1
        elif "工序未設定" in msg or "未設定工藝路線" in msg:
            reason_counter["工序未設定"] += 1
        elif "超過交期" in msg or "交貨日" in msg:
            reason_counter["超過交期"] += 1
        else:
            reason_counter["其他"] += 1
    # 轉成列表方便前端顯示
    result = [{"原因": k, "數量": v} for k, v in reason_counter.items()]
    return JsonResponse({"衝突原因統計": result})
