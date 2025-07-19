from django.contrib import admin
from .models import (
    WorkOrder,
    WorkOrderProcess,
    WorkOrderProcessLog,
    WorkOrderAssignment,
)


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
    search_fields = ["order_number", "product_code"]
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
