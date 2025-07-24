from django.contrib import admin
from .models import (
    WorkOrder,
    WorkOrderProcess,
    WorkOrderProcessLog,
    WorkOrderAssignment,
    SMTProductionReport,
    OperatorSupplementReport,
    ManagerProductionReport,
)
from django.utils import timezone


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


@admin.register(SMTProductionReport)
class SMTProductionReportAdmin(admin.ModelAdmin):
    """SMT 補登報工記錄管理介面"""
    list_display = [
        'id', 'product_id', 'workorder', 'operation', 'equipment', 
        'work_date', 'work_quantity', 'approval_status', 'created_at'
    ]
    list_filter = [
        'equipment', 'operation', 'work_date', 'approval_status', 'created_at'
    ]
    search_fields = [
        'product_id', 'equipment__name', 'workorder__order_number', 'workorder__product_code'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'approved_by', 'approved_at']
    date_hierarchy = 'work_date'
    ordering = ['-work_date', '-start_time']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('product_id', 'workorder', 'planned_quantity', 'operation', 'equipment')
        }),
        ('時間資訊', {
            'fields': ('work_date', 'start_time', 'end_time')
        }),
        ('數量資訊', {
            'fields': ('work_quantity', 'defect_quantity')
        }),
        ('狀態資訊', {
            'fields': ('is_completed', 'remarks')
        }),
        ('核准資訊', {
            'fields': ('approval_status', 'approved_by', 'approved_at', 'approval_remarks'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """優化查詢效能"""
        return super().get_queryset(request).select_related('equipment', 'workorder')
    
    def get_readonly_fields(self, request, obj=None):
        """編輯時某些欄位為唯讀"""
        if obj:  # 編輯現有記錄
            return list(self.readonly_fields) + ['product_id', 'workorder', 'planned_quantity']
        return self.readonly_fields


@admin.register(OperatorSupplementReport)
class OperatorSupplementReportAdmin(admin.ModelAdmin):
    """作業員補登報工記錄管理介面"""
    list_display = [
        'id', 'operator', 'workorder', 'process', 'work_date', 
        'work_quantity', 'defect_quantity', 'approval_status', 'created_at'
    ]
    list_filter = [
        'operator', 'process', 'work_date', 'approval_status', 'created_at'
    ]
    search_fields = [
        'operator__name', 'workorder__order_number', 'workorder__product_code', 'process__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'approved_by', 'approved_at']
    date_hierarchy = 'work_date'
    ordering = ['-work_date', '-start_time']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('operator', 'workorder', 'process', 'equipment')
        }),
        ('時間資訊', {
            'fields': ('work_date', 'start_time', 'end_time')
        }),
        ('數量資訊', {
            'fields': ('work_quantity', 'defect_quantity', 'is_completed')
        }),
        ('完工判斷', {
            'fields': ('completion_method', 'auto_completed', 'completion_time', 'cumulative_quantity', 'cumulative_hours'),
            'classes': ('collapse',)
        }),
        ('備註資訊', {
            'fields': ('remarks',)
        }),
        ('審核資訊', {
            'fields': ('approval_status', 'approved_by', 'approved_at', 'approval_remarks', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """優化查詢效能"""
        return super().get_queryset(request).select_related('operator', 'workorder', 'process')
    
    def get_readonly_fields(self, request, obj=None):
        """編輯時某些欄位為唯讀"""
        if obj:  # 編輯現有記錄
            return list(self.readonly_fields) + ['operator', 'workorder', 'process']
        return self.readonly_fields
    
    def get_actions(self, request):
        """自定義批量操作"""
        actions = super().get_actions(request)
        if request.user.is_superuser:
            actions['batch_approve'] = self.batch_approve
            actions['batch_reject'] = self.batch_reject
        return actions
    
    def batch_approve(self, request, queryset):
        """批量審核通過"""
        updated = queryset.update(
            approval_status='approved',
            approved_by=request.user.username,
            approved_at=timezone.now()
        )
        self.message_user(request, f'成功審核通過 {updated} 筆記錄')
    batch_approve.short_description = "批量審核通過"
    
    def batch_reject(self, request, queryset):
        """批量駁回"""
        updated = queryset.update(
            approval_status='rejected',
            approved_by=request.user.username,
            approved_at=timezone.now()
        )
        self.message_user(request, f'成功駁回 {updated} 筆記錄')
    batch_reject.short_description = "批量駁回"


@admin.register(ManagerProductionReport)
class ManagerProductionReportAdmin(admin.ModelAdmin):
    """管理者生產報工記錄管理介面"""
    list_display = [
        'id', 'manager', 'workorder', 'process', 'work_date', 
        'work_quantity', 'defect_quantity', 'approval_status', 'created_at'
    ]
    list_filter = [
        'manager', 'process', 'work_date', 'approval_status', 'created_at'
    ]
    search_fields = [
        'manager', 'workorder__order_number', 'workorder__product_code', 'process__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'approved_by', 'approved_at']
    date_hierarchy = 'work_date'
    ordering = ['-work_date', '-start_time']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('manager', 'workorder', 'planned_quantity', 'process', 'equipment', 'operator')
        }),
        ('時間資訊', {
            'fields': ('work_date', 'start_time', 'end_time')
        }),
        ('數量資訊', {
            'fields': ('work_quantity', 'defect_quantity', 'is_completed')
        }),
        ('完工判斷', {
            'fields': ('completion_method', 'auto_completed', 'completion_time', 'cumulative_quantity', 'cumulative_hours'),
            'classes': ('collapse',)
        }),
        ('備註資訊', {
            'fields': ('remarks',)
        }),
        ('審核資訊', {
            'fields': ('approval_status', 'approved_by', 'approved_at', 'approval_remarks', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """優化查詢效能"""
        return super().get_queryset(request).select_related('workorder', 'process', 'equipment', 'operator')
    
    def get_readonly_fields(self, request, obj=None):
        """編輯時某些欄位為唯讀"""
        if obj:  # 編輯現有記錄
            return list(self.readonly_fields) + ['manager', 'workorder', 'planned_quantity']
        return self.readonly_fields
    
    def get_actions(self, request):
        """自定義批量操作"""
        actions = super().get_actions(request)
        if request.user.is_superuser:
            actions['batch_approve'] = self.batch_approve
            actions['batch_reject'] = self.batch_reject
        return actions
    
    def batch_approve(self, request, queryset):
        """批量審核通過"""
        updated = queryset.update(
            approval_status='approved',
            approved_by=request.user.username,
            approved_at=timezone.now()
        )
        self.message_user(request, f'成功審核通過 {updated} 筆記錄')
    batch_approve.short_description = "批量審核通過"
    
    def batch_reject(self, request, queryset):
        """批量駁回"""
        updated = queryset.update(
            approval_status='rejected',
            approved_by=request.user.username,
            approved_at=timezone.now()
        )
        self.message_user(request, f'成功駁回 {updated} 筆記錄')
    batch_reject.short_description = "批量駁回"
