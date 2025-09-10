"""
派工單管理子模組 - 管理介面
"""

from django.contrib import admin
from .models import WorkOrderDispatch, WorkOrderDispatchProcess


@admin.register(WorkOrderDispatch)
class WorkOrderDispatchAdmin(admin.ModelAdmin):
    """
    派工單管理介面
    """
    list_display = [
        'id', 'order_number', 'product_code', 'planned_quantity', 
        'status', 'dispatch_date', 'created_at'
    ]
    list_filter = ['status', 'dispatch_date', 'created_at']
    search_fields = ['order_number', 'product_code']  # 直接使用 order_number 和 product_code 欄位
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('基本資訊', {
            'fields': ('company_code', 'order_number', 'product_code', 'planned_quantity')
        }),
        ('派工資訊', {
            'fields': ('status', 'dispatch_date', 'planned_start_date', 'planned_end_date')
        }),
        ('備註', {
            'fields': ('notes',)
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkOrderDispatchProcess)
class WorkOrderDispatchProcessAdmin(admin.ModelAdmin):
    """
    派工單工序明細管理介面
    """
    list_display = [
        'workorder_dispatch_id', 'process_name', 'step_order', 'planned_quantity',
        'assigned_operator', 'assigned_equipment', 'dispatch_status'
    ]
    list_filter = ['dispatch_status', 'created_at']
    search_fields = ['process_name', 'assigned_operator', 'assigned_equipment']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['workorder_dispatch_id', 'step_order']

    fieldsets = (
        ('基本資訊', {
            'fields': ('workorder_dispatch_id', 'process_name', 'step_order', 'planned_quantity')
        }),
        ('派工分配', {
            'fields': ('assigned_operator', 'assigned_equipment', 'dispatch_status')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ) 