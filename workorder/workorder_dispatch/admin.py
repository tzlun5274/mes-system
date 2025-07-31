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
        'id', 'work_order', 'operator', 'process', 'planned_quantity', 
        'status', 'dispatch_date', 'created_at'
    ]
    list_filter = ['status', 'dispatch_date', 'created_at']
    search_fields = ['work_order__order_number', 'operator', 'process']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('基本資訊', {
            'fields': ('work_order', 'operator', 'process', 'planned_quantity')
        }),
        ('派工資訊', {
            'fields': ('status', 'dispatch_date', 'planned_start_date', 'planned_end_date')
        }),
        ('備註', {
            'fields': ('notes',)
        }),
        ('系統資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkOrderDispatchProcess)
class WorkOrderDispatchProcessAdmin(admin.ModelAdmin):
    """
    派工單工序明細管理介面
    """
    list_display = [
        'workorder_dispatch', 'process_name', 'step_order', 
        'planned_quantity', 'dispatch_status'
    ]
    list_filter = ['dispatch_status', 'step_order']
    search_fields = ['workorder_dispatch__order_number', 'process_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['workorder_dispatch', 'step_order']

    fieldsets = (
        ('基本資訊', {
            'fields': ('workorder_dispatch', 'process_name', 'step_order', 'planned_quantity')
        }),
        ('分配資訊', {
            'fields': ('assigned_operator', 'assigned_equipment', 'dispatch_status')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ) 