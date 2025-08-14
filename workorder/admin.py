from django.contrib import admin
from .models import (
    WorkOrder,
    WorkOrderProcess,
    WorkOrderProcessLog,
    WorkOrderAssignment,
    WorkOrderProduction,
    WorkOrderProductionDetail,
)

# 導入子模組的模型
# from django.utils import timezone

# 將工單管理模型註冊到 Django 後台，方便管理
@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "product_code",
        "quantity",
        "status",
        "company_code",
        "created_at",
    ]
    list_filter = ["status", "company_code", "created_at"]
    search_fields = ["order_number", "product_code", "status"]
    ordering = ["-created_at"]

@admin.register(WorkOrderProcess)
class WorkOrderProcessAdmin(admin.ModelAdmin):
    list_display = [
        "workorder",
        "process_name",
        "step_order",
        "planned_quantity",
        "completed_quantity",
        "status",
    ]
    list_filter = ["status", "step_order"]
    search_fields = ["workorder__order_number", "process_name"]

@admin.register(WorkOrderProcessLog)
class WorkOrderProcessLogAdmin(admin.ModelAdmin):
    list_display = ["workorder_process", "action", "created_at"]
    list_filter = ["action", "created_at"]
    search_fields = ["workorder_process__workorder__order_number"]
    ordering = ["-created_at"]

@admin.register(WorkOrderAssignment)
class WorkOrderAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "workorder",
        "equipment_id",
        "operator_id",
        "assigned_at",
        "company_code",
    ]
    list_filter = ["assigned_at", "company_code"]
    search_fields = ["workorder__order_number", "equipment_id", "operator_id"]
    ordering = ["-assigned_at"]

# ============================================================================
# 重新設計的工單模組 Admin 管理介面
# ============================================================================

@admin.register(WorkOrderProduction)
class WorkOrderProductionAdmin(admin.ModelAdmin):
    """生產中工單管理介面"""
    list_display = [
        "workorder",
        "status",
        "current_process",
        "production_start_date",
        "production_end_date",
        "created_at",
    ]
    list_filter = ["status", "production_start_date", "created_at"]
    search_fields = ["workorder__order_number", "status", "current_process"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

@admin.register(WorkOrderProductionDetail)
class WorkOrderProductionDetailAdmin(admin.ModelAdmin):
    """生產報工明細管理介面"""
    list_display = [
        "workorder_production",
        "process_name",
        "report_date",
        "work_quantity",
        "defect_quantity",
        "operator",
        "equipment",
        "report_source",
        "report_time",
    ]
    list_filter = [
        "process_name",
        "report_date",
        "report_source",
        "operator",
        "equipment",
    ]
    search_fields = [
        "workorder_production__workorder_dispatch__order_number",
        "process_name",
        "operator",
        "equipment",
    ]
    ordering = ["-report_date", "-report_time"]
    readonly_fields = ["created_at", "updated_at", "created_by"]

