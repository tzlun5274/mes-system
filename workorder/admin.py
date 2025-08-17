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
        "get_workorder_number",
        "process_name",
        "step_order",
        "planned_quantity",
        "completed_quantity",
        "status",
    ]
    list_filter = ["status", "step_order"]
    search_fields = ["process_name"]
    
    def get_workorder_number(self, obj):
        from .models import WorkOrder
        workorder = WorkOrder.objects.filter(id=obj.workorder_id).first()
        return workorder.order_number if workorder else f"工單{obj.workorder_id}"
    get_workorder_number.short_description = "工單號碼"

@admin.register(WorkOrderProcessLog)
class WorkOrderProcessLogAdmin(admin.ModelAdmin):
    list_display = ["get_process_name", "action", "created_at"]
    list_filter = ["action", "created_at"]
    search_fields = ["action"]
    ordering = ["-created_at"]
    
    def get_process_name(self, obj):
        from .models import WorkOrderProcess
        process = WorkOrderProcess.objects.filter(id=obj.workorder_process_id).first()
        return process.process_name if process else f"工序{obj.workorder_process_id}"
    get_process_name.short_description = "工序名稱"

@admin.register(WorkOrderAssignment)
class WorkOrderAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "get_workorder_number",
        "equipment_id",
        "operator_id",
        "assigned_at",
        "company_code",
    ]
    list_filter = ["assigned_at", "company_code"]
    search_fields = ["equipment_id", "operator_id"]
    ordering = ["-assigned_at"]
    
    def get_workorder_number(self, obj):
        from .models import WorkOrder
        workorder = WorkOrder.objects.filter(id=obj.workorder_id).first()
        return workorder.order_number if workorder else f"工單{obj.workorder_id}"
    get_workorder_number.short_description = "工單號碼"

# ============================================================================
# 重新設計的工單模組 Admin 管理介面
# ============================================================================

@admin.register(WorkOrderProduction)
class WorkOrderProductionAdmin(admin.ModelAdmin):
    """生產中工單管理介面"""
    list_display = [
        "get_workorder_number",
        "status",
        "current_process",
        "production_start_date",
        "production_end_date",
        "created_at",
    ]
    list_filter = ["status", "production_start_date", "created_at"]
    search_fields = ["status", "current_process"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]
    
    def get_workorder_number(self, obj):
        from .models import WorkOrder
        workorder = WorkOrder.objects.filter(id=obj.workorder_id).first()
        return workorder.order_number if workorder else f"工單{obj.workorder_id}"
    get_workorder_number.short_description = "工單號碼"

@admin.register(WorkOrderProductionDetail)
class WorkOrderProductionDetailAdmin(admin.ModelAdmin):
    """生產報工明細管理介面"""
    list_display = [
        "get_workorder_number",
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
        "process_name",
        "operator",
        "equipment",
    ]
    ordering = ["-report_date", "-report_time"]
    readonly_fields = ["created_at", "updated_at", "created_by"]
    
    def get_workorder_number(self, obj):
        from .models import WorkOrderProduction, WorkOrder
        production = WorkOrderProduction.objects.filter(id=obj.workorder_production_id).first()
        if production:
            workorder = WorkOrder.objects.filter(id=production.workorder_id).first()
            return workorder.order_number if workorder else f"工單{production.workorder_id}"
        return f"生產記錄{obj.workorder_production_id}"
    get_workorder_number.short_description = "工單號碼"

