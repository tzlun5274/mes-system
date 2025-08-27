# 產線管理視圖
# 此檔案定義產線管理模組的視圖函數，提供網頁介面

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import ProductionLineType, ProductionLine, ProductionLineSchedule
from .forms import (
    ProductionLineTypeForm,
    ProductionLineForm,
    ProductionLineScheduleForm,
)
import json

import os
# 設定生產管理模組的日誌記錄器
production_logger = logging.getLogger("production")
from django.conf import settings
production_handler = logging.FileHandler(os.path.join(settings.PRODUCTION_LOG_DIR, "production.log"))
production_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
production_logger.addHandler(production_handler)
production_logger.setLevel(logging.INFO)


@login_required
def index(request):
    """
    產線管理首頁
    顯示產線概覽和快速操作
    """
    # 統計資料
    total_lines = ProductionLine.objects.filter(is_active=True).count()
    total_types = ProductionLineType.objects.filter(is_active=True).count()

    # 最近建立的產線
    recent_lines = ProductionLine.objects.filter(is_active=True).order_by(
        "-created_at"
    )[:5]

    # 各類型產線統計
    type_stats = {}
    for line in ProductionLine.objects.filter(is_active=True):
        type_name = line.line_type.type_name
        if type_name not in type_stats:
            type_stats[type_name] = 0
        type_stats[type_name] += 1

    context = {
        "total_lines": total_lines,
        "total_types": total_types,
        "recent_lines": recent_lines,
        "type_stats": type_stats,
    }

    return render(request, "production/index.html", context)


@login_required
def line_type_list(request):
    """
    產線類型列表
    """
    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()

    # 查詢條件
    queryset = ProductionLineType.objects.all()

    if search:
        queryset = queryset.filter(
            Q(type_code__icontains=search)
            | Q(type_name__icontains=search)
            | Q(description__icontains=search)
        )

    if status_filter:
        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)

    # 分頁
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "status_filter": status_filter,
    }

    return render(request, "production/line_type_list.html", context)


@login_required
def line_type_create(request):
    """
    新增產線類型
    """
    if request.method == "POST":
        form = ProductionLineTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "產線類型建立成功！")
            return redirect("production:line_type_list")
    else:
        form = ProductionLineTypeForm()

    context = {"form": form, "title": "新增產線類型", "action": "create"}

    return render(request, "production/line_type_form.html", context)


@login_required
def line_type_edit(request, pk):
    """
    編輯產線類型
    """
    line_type = get_object_or_404(ProductionLineType, pk=pk)

    if request.method == "POST":
        form = ProductionLineTypeForm(request.POST, instance=line_type)
        if form.is_valid():
            form.save()
            messages.success(request, "產線類型更新成功！")
            return redirect("production:line_type_list")
    else:
        form = ProductionLineTypeForm(instance=line_type)

    context = {
        "form": form,
        "line_type": line_type,
        "title": "編輯產線類型",
        "action": "edit",
    }

    return render(request, "production/line_type_form.html", context)


@login_required
def line_type_delete(request, pk):
    """
    刪除產線類型
    """
    line_type = get_object_or_404(ProductionLineType, pk=pk)

    # 檢查是否有產線使用此類型
    if ProductionLine.objects.filter(line_type=line_type).exists():
        messages.error(request, "無法刪除：此類型已被產線使用")
        return redirect("production:line_type_list")

    if request.method == "POST":
        line_type.delete()
        messages.success(request, "產線類型刪除成功！")
        return redirect("production:line_type_list")

    context = {"line_type": line_type}

    return render(request, "production/line_type_confirm_delete.html", context)


@login_required
def line_list(request):
    """
    產線列表
    """
    search = request.GET.get("search", "").strip()
    type_filter = request.GET.get("type", "").strip()
    status_filter = request.GET.get("status", "").strip()

    # 查詢條件
    queryset = ProductionLine.objects.select_related("line_type").all()

    if search:
        queryset = queryset.filter(
            Q(line_code__icontains=search)
            | Q(line_name__icontains=search)
            | Q(description__icontains=search)
        )

    if type_filter:
        queryset = queryset.filter(line_type_id=type_filter)

    if status_filter:
        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)

    # 分頁
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 取得所有產線類型供篩選
    line_types = ProductionLineType.objects.filter(is_active=True)

    context = {
        "page_obj": page_obj,
        "search": search,
        "type_filter": type_filter,
        "status_filter": status_filter,
        "line_types": line_types,
    }

    return render(request, "production/line_list.html", context)


@login_required
def line_create(request):
    """
    新增產線
    """
    if request.method == "POST":
        form = ProductionLineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "產線建立成功！")
            return redirect("production:line_list")
    else:
        form = ProductionLineForm()

    context = {"form": form, "title": "新增產線", "action": "create"}

    return render(request, "production/line_form.html", context)


@login_required
def line_edit(request, pk):
    """
    編輯產線
    """
    production_line = get_object_or_404(ProductionLine, pk=pk)

    if request.method == "POST":
        form = ProductionLineForm(request.POST, instance=production_line)
        if form.is_valid():
            form.save()
            messages.success(request, "產線更新成功！")
            return redirect("production:line_list")
    else:
        form = ProductionLineForm(instance=production_line)

    context = {
        "form": form,
        "production_line": production_line,
        "title": "編輯產線",
        "action": "edit",
    }

    return render(request, "production/line_form.html", context)


@login_required
def line_detail(request, pk):
    """
    產線詳細資訊
    """
    production_line = get_object_or_404(ProductionLine, pk=pk)

    # 取得最近的排程記錄
    recent_schedules = production_line.schedules.order_by("-schedule_date")[:10]

    context = {
        "production_line": production_line,
        "recent_schedules": recent_schedules,
    }

    return render(request, "production/line_detail.html", context)


@login_required
def line_delete(request, pk):
    """
    刪除產線
    """
    production_line = get_object_or_404(ProductionLine, pk=pk)

    # 檢查是否有排程記錄
    if production_line.schedules.exists():
        messages.error(request, "無法刪除：此產線已有排程記錄")
        return redirect("production:line_list")

    if request.method == "POST":
        production_line.delete()
        messages.success(request, "產線刪除成功！")
        return redirect("production:line_list")

    context = {"production_line": production_line}

    return render(request, "production/line_confirm_delete.html", context)


@login_required
def schedule_list(request):
    """
    排程記錄列表
    """
    search = request.GET.get("search", "").strip()
    line_filter = request.GET.get("line", "").strip()
    date_filter = request.GET.get("date", "").strip()
    holiday_filter = request.GET.get("holiday", "").strip()

    # 查詢條件
    queryset = ProductionLineSchedule.objects.select_related(
        "production_line", "production_line__line_type"
    ).all()

    if search:
        queryset = queryset.filter(
            Q(production_line__line_code__icontains=search)
            | Q(production_line__line_name__icontains=search)
            | Q(created_by__icontains=search)
        )

    if line_filter:
        queryset = queryset.filter(production_line_id=line_filter)

    if date_filter:
        queryset = queryset.filter(schedule_date=date_filter)

    if holiday_filter:
        if holiday_filter == "holiday":
            queryset = queryset.filter(is_holiday=True)
        elif holiday_filter == "workday":
            queryset = queryset.filter(is_holiday=False)

    # 分頁
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 取得所有產線供篩選
    production_lines = ProductionLine.objects.filter(is_active=True)

    context = {
        "page_obj": page_obj,
        "search": search,
        "line_filter": line_filter,
        "date_filter": date_filter,
        "holiday_filter": holiday_filter,
        "production_lines": production_lines,
    }

    return render(request, "production/schedule_list.html", context)


@login_required
def schedule_create(request):
    """
    新增排程記錄
    """
    if request.method == "POST":
        form = ProductionLineScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user.username
            schedule.save()
            messages.success(request, "排程記錄建立成功！")
            return redirect("production:schedule_list")
    else:
        form = ProductionLineScheduleForm()

    context = {"form": form, "title": "新增排程記錄", "action": "create"}

    return render(request, "production/schedule_form.html", context)


@login_required
def schedule_edit(request, pk):
    """
    編輯排程記錄
    """
    schedule = get_object_or_404(ProductionLineSchedule, pk=pk)

    if request.method == "POST":
        form = ProductionLineScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, "排程記錄更新成功！")
            return redirect("production:schedule_list")
    else:
        form = ProductionLineScheduleForm(instance=schedule)

    context = {
        "form": form,
        "schedule": schedule,
        "title": "編輯排程記錄",
        "action": "edit",
    }

    return render(request, "production/schedule_form.html", context)


@login_required
def schedule_delete(request, pk):
    """
    刪除排程記錄
    """
    schedule = get_object_or_404(ProductionLineSchedule, pk=pk)

    if request.method == "POST":
        schedule.delete()
        messages.success(request, "排程記錄刪除成功！")
        return redirect("production:schedule_list")

    context = {"schedule": schedule}

    return render(request, "production/schedule_confirm_delete.html", context)


@login_required
def api_line_types(request):
    """
    API：取得產線類型列表
    """
    line_types = ProductionLineType.objects.filter(is_active=True).values(
        "id", "type_code", "type_name"
    )
    return JsonResponse({"line_types": list(line_types)})


@login_required
def api_production_lines(request):
    """
    API：取得產線列表
    """
    production_lines = ProductionLine.objects.filter(is_active=True).values(
        "id", "line_code", "line_name", "line_type__type_name"
    )
    return JsonResponse({"production_lines": list(production_lines)})
