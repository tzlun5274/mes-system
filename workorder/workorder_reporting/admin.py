"""
報工管理子模組 - 管理介面
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SMTSupplementReport, OperatorSupplementReport


@admin.register(SMTSupplementReport)
class SMTSupplementReportAdmin(admin.ModelAdmin):
    """
    SMT補登報工記錄管理介面
    """
    list_display = [
        'workorder_number', 'operation', 'equipment_name', 'work_date',
        'work_quantity', 'defect_quantity', 'approval_status', 'created_at'
    ]
    list_filter = ['approval_status', 'work_date', 'created_at']
    search_fields = ['workorder_id__order_number', 'operation', 'equipment__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-work_date', '-start_time']

    fieldsets = (
        ('基本資訊', {
            'fields': ('workorder', 'operation', 'equipment')
        }),
        ('時間資訊', {
            'fields': ('work_date', 'start_time', 'end_time')
        }),
        ('數量資訊', {
            'fields': ('work_quantity', 'defect_quantity', 'is_completed')
        }),
        ('核准狀態', {
            'fields': ('approval_status', 'approved_by', 'approved_at', 'approval_remarks')
        }),
        ('備註', {
            'fields': ('remarks', 'abnormal_notes')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(OperatorSupplementReport)
class OperatorSupplementReportAdmin(admin.ModelAdmin):
    """
    作業員補登報工記錄管理介面
    """
    list_display = [
        'operator_name', 'workorder_number', 'process_name', 'work_date',
        'work_quantity', 'defect_quantity', 'approval_status', 'created_at'
    ]
    list_filter = ['approval_status', 'work_date', 'created_at']
    search_fields = ['operator__name', 'workorder_id__order_number', 'process__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-work_date', '-start_time']

    fieldsets = (
        ('基本資訊', {
            'fields': ('operator', 'workorder', 'process', 'equipment')
        }),
        ('時間資訊', {
            'fields': ('work_date', 'start_time', 'end_time', 'has_break')
        }),
        ('數量資訊', {
            'fields': ('work_quantity', 'defect_quantity', 'is_completed')
        }),
        ('分配資訊', {
            'fields': ('allocated_quantity', 'quantity_source', 'allocation_notes')
        }),
        ('核准狀態', {
            'fields': ('approval_status', 'approved_by', 'approved_at', 'approval_remarks')
        }),
        ('備註', {
            'fields': ('remarks', 'abnormal_notes')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at')
        }),
    ) 