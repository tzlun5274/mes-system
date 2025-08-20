"""
已完工工單管理子模組 - 管理介面
負責在 Django Admin 中管理已完工工單相關資料
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    CompletedWorkOrder, CompletedWorkOrderProcess, 
    CompletedProductionReport, AutoAllocationSettings, AutoAllocationLog
)


@admin.register(CompletedWorkOrder)
class CompletedWorkOrderAdmin(admin.ModelAdmin):
    """已完工工單管理介面"""
    
    list_display = [
        'company_code', 'order_number', 'product_code', 'product_name',
        'order_quantity', 'completed_quantity', 'defective_quantity',
        'completion_rate_display', 'defect_rate_display', 'completion_date', 'status'
    ]
    
    list_filter = [
        'company_code', 'status', 'completion_date', 'created_at'
    ]
    
    search_fields = [
        'company_code', 'order_number', 'product_code', 'product_name'
    ]
    
    readonly_fields = [
        'completion_rate_display', 'defect_rate_display', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本識別資訊', {
            'fields': ('company_code', 'order_number', 'product_code', 'product_name')
        }),
        ('數量資訊', {
            'fields': ('order_quantity', 'completed_quantity', 'defective_quantity')
        }),
        ('時間資訊', {
            'fields': ('start_date', 'completion_date')
        }),
        ('狀態與統計', {
            'fields': ('status', 'completion_rate_display', 'defect_rate_display')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('備註', {
            'fields': ('remarks',)
        }),
    )
    
    def completion_rate_display(self, obj):
        """顯示完工率"""
        return f"{obj.completion_rate:.1f}%"
    completion_rate_display.short_description = "完工率"
    
    def defect_rate_display(self, obj):
        """顯示不良率"""
        return f"{obj.defect_rate:.1f}%"
    defect_rate_display.short_description = "不良率"
    
    def get_queryset(self, request):
        """優化查詢"""
        return super().get_queryset(request).select_related()


@admin.register(CompletedWorkOrderProcess)
class CompletedWorkOrderProcessAdmin(admin.ModelAdmin):
    """已完工工單工序管理介面"""
    
    list_display = [
        'completed_workorder_link', 'process_name', 'process_sequence',
        'planned_quantity', 'completed_quantity', 'defective_quantity',
        'completion_rate_display', 'duration_display', 'operator_name', 'equipment_name'
    ]
    
    list_filter = [
        'completed_workorder__company_code', 'process_name', 'operator_name', 'equipment_name'
    ]
    
    search_fields = [
        'completed_workorder__company_code', 'completed_workorder__order_number',
        'process_name', 'operator_name', 'equipment_name'
    ]
    
    readonly_fields = [
        'completion_rate_display', 'duration_display'
    ]
    
    fieldsets = (
        ('關聯工單', {
            'fields': ('completed_workorder',)
        }),
        ('工序資訊', {
            'fields': ('process_name', 'process_sequence')
        }),
        ('數量資訊', {
            'fields': ('planned_quantity', 'completed_quantity', 'defective_quantity')
        }),
        ('時間資訊', {
            'fields': ('start_time', 'end_time', 'duration_display')
        }),
        ('作業資訊', {
            'fields': ('operator_name', 'equipment_name')
        }),
        ('統計資訊', {
            'fields': ('completion_rate_display',)
        }),
        ('備註', {
            'fields': ('remarks',)
        }),
    )
    
    def completed_workorder_link(self, obj):
        """顯示關聯工單連結"""
        if obj.completed_workorder:
            url = reverse('admin:workorder_completed_workorder_completedworkorder_change', args=[obj.completed_workorder.id])
            return format_html('<a href="{}">{}</a>', url, obj.completed_workorder)
        return '-'
    completed_workorder_link.short_description = "已完工工單"
    
    def completion_rate_display(self, obj):
        """顯示完工率"""
        return f"{obj.completion_rate:.1f}%"
    completion_rate_display.short_description = "完工率"
    
    def duration_display(self, obj):
        """顯示耗時"""
        return f"{obj.duration:.1f} 分鐘"
    duration_display.short_description = "耗時"
    
    def get_queryset(self, request):
        """優化查詢"""
        return super().get_queryset(request).select_related('completed_workorder')


@admin.register(CompletedProductionReport)
class CompletedProductionReportAdmin(admin.ModelAdmin):
    """已完工生產報表管理介面"""
    
    list_display = [
        'completed_workorder_link', 'report_date', 'report_type',
        'total_production', 'good_quantity', 'defective_quantity',
        'production_efficiency', 'quality_rate'
    ]
    
    list_filter = [
        'completed_workorder__company_code', 'report_type', 'report_date'
    ]
    
    search_fields = [
        'completed_workorder__company_code', 'completed_workorder__order_number',
        'report_type'
    ]
    
    fieldsets = (
        ('關聯工單', {
            'fields': ('completed_workorder',)
        }),
        ('報表資訊', {
            'fields': ('report_date', 'report_type')
        }),
        ('生產數據', {
            'fields': ('total_production', 'good_quantity', 'defective_quantity')
        }),
        ('效率指標', {
            'fields': ('production_efficiency', 'quality_rate')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('備註', {
            'fields': ('remarks',)
        }),
    )
    
    def completed_workorder_link(self, obj):
        """顯示關聯工單連結"""
        if obj.completed_workorder:
            url = reverse('admin:workorder_completed_workorder_completedworkorder_change', args=[obj.completed_workorder.id])
            return format_html('<a href="{}">{}</a>', url, obj.completed_workorder)
        return '-'
    completed_workorder_link.short_description = "已完工工單"
    
    def get_queryset(self, request):
        """優化查詢"""
        return super().get_queryset(request).select_related('completed_workorder')


@admin.register(AutoAllocationSettings)
class AutoAllocationSettingsAdmin(admin.ModelAdmin):
    """自動分配設定管理介面"""
    
    list_display = [
        'setting_name', 'is_active', 'allocation_type', 'check_interval',
        'created_by', 'created_at'
    ]
    
    list_filter = [
        'is_active', 'allocation_type', 'created_at'
    ]
    
    search_fields = [
        'setting_name', 'created_by__username'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本設定', {
            'fields': ('setting_name', 'is_active')
        }),
        ('分配規則', {
            'fields': ('allocation_type', 'priority_rules')
        }),
        ('時間設定', {
            'fields': ('check_interval', 'last_check_time')
        }),
        ('建立資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('備註', {
            'fields': ('remarks',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """儲存時自動設定建立者"""
        if not change:  # 新增時
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AutoAllocationLog)
class AutoAllocationLogAdmin(admin.ModelAdmin):
    """自動分配日誌管理介面"""
    
    list_display = [
        'allocation_settings_link', 'allocation_type', 'target_workorder',
        'assigned_operator', 'assigned_equipment', 'allocation_status',
        'allocation_time'
    ]
    
    list_filter = [
        'allocation_type', 'allocation_status', 'allocation_time'
    ]
    
    search_fields = [
        'allocation_settings__setting_name', 'target_workorder',
        'assigned_operator', 'assigned_equipment'
    ]
    
    readonly_fields = [
        'allocation_time'
    ]
    
    fieldsets = (
        ('分配設定', {
            'fields': ('allocation_settings',)
        }),
        ('分配結果', {
            'fields': ('allocation_type', 'target_workorder')
        }),
        ('分配對象', {
            'fields': ('assigned_operator', 'assigned_equipment')
        }),
        ('分配狀態', {
            'fields': ('allocation_status', 'error_message')
        }),
        ('時間資訊', {
            'fields': ('allocation_time',),
            'classes': ('collapse',)
        }),
        ('備註', {
            'fields': ('remarks',)
        }),
    )
    
    def allocation_settings_link(self, obj):
        """顯示分配設定連結"""
        if obj.allocation_settings:
            url = reverse('admin:workorder_completed_workorder_autoallocationsettings_change', args=[obj.allocation_settings.id])
            return format_html('<a href="{}">{}</a>', url, obj.allocation_settings)
        return '-'
    allocation_settings_link.short_description = "分配設定"
    
    def get_queryset(self, request):
        """優化查詢"""
        return super().get_queryset(request).select_related('allocation_settings')
    
    def has_add_permission(self, request):
        """禁止手動新增日誌"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改日誌"""
        return False 