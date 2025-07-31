"""
已完工工單管理子模組 - 管理介面
"""

from django.contrib import admin
from .models import WorkOrderCompleted, WorkOrderCompletedProcess


@admin.register(WorkOrderCompleted)
class WorkOrderCompletedAdmin(admin.ModelAdmin):
    """
    已完工工單管理介面
    """
    list_display = [
        'workorder_dispatch', 'completion_date', 'completion_method',
        'total_work_quantity', 'total_defect_quantity', 'confirmed_by'
    ]
    list_filter = ['completion_method', 'completion_date', 'created_at']
    search_fields = ['workorder_dispatch__order_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-completion_date']

    fieldsets = (
        ('基本資訊', {
            'fields': ('workorder_dispatch', 'completion_method')
        }),
        ('完工統計', {
            'fields': ('total_work_quantity', 'total_defect_quantity', 'total_production_days')
        }),
        ('工序摘要', {
            'fields': ('process_completion_summary',)
        }),
        ('完工確認', {
            'fields': ('confirmed_by', 'confirmed_at')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(WorkOrderCompletedProcess)
class WorkOrderCompletedProcessAdmin(admin.ModelAdmin):
    """
    已完工工序統計管理介面
    """
    list_display = [
        'workorder_completed', 'process_name', 'step_order',
        'total_work_quantity', 'total_defect_quantity', 'report_count'
    ]
    list_filter = ['process_name', 'created_at']
    search_fields = ['workorder_completed__workorder_dispatch__order_number', 'process_name']
    readonly_fields = ['created_at']
    ordering = ['workorder_completed', 'step_order']

    fieldsets = (
        ('基本資訊', {
            'fields': ('workorder_completed', 'process_name', 'step_order')
        }),
        ('完工統計', {
            'fields': ('total_work_quantity', 'total_defect_quantity', 'report_count')
        }),
        ('時間統計', {
            'fields': ('first_report_date', 'last_report_date', 'total_work_hours')
        }),
        ('人員設備', {
            'fields': ('operators_used', 'equipments_used')
        }),
        ('系統資訊', {
            'fields': ('created_at',)
        }),
    ) 