"""
報表模組管理介面
提供報表數據的管理功能
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import WorkReport, WorkOrderReport, WorkHourReport, ReportExportLog


@admin.register(WorkReport)
class WorkReportAdmin(admin.ModelAdmin):
    """工作報表管理"""
    list_display = [
        'operator', 'work_order_no', 'product_sn', 'process', 
        'report_date', 'work_quantity', 'defect_quantity', 'work_duration_display'
    ]
    list_filter = ['report_date', 'operator', 'process', 'work_order_no']
    search_fields = ['operator__username', 'work_order_no', 'product_sn', 'process']
    date_hierarchy = 'report_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('report_type', 'report_date', 'operator', 'work_order_no', 'product_sn', 'process')
        }),
        ('時間資訊', {
            'fields': ('start_time', 'end_time')
        }),
        ('數量資訊', {
            'fields': ('work_quantity', 'defect_quantity')
        }),
        ('其他資訊', {
            'fields': ('abnormal_notes', 'data_source', 'calculation_method')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def work_duration_display(self, obj):
        """顯示工作時長"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            hours = duration.total_seconds() / 3600
            return f"{hours:.2f} 小時"
        return "無時間記錄"
    work_duration_display.short_description = "工作時長"
    
    def get_queryset(self, request):
        """優化查詢"""
        return super().get_queryset(request).select_related('operator')


@admin.register(WorkOrderReport)
class WorkOrderReportAdmin(admin.ModelAdmin):
    """工單報表管理"""
    list_display = [
        'work_order_no', 'product_sn', 'product_name', 'status', 
        'total_quantity', 'completed_quantity', 'completion_rate_display',
        'start_date', 'end_date'
    ]
    list_filter = ['status', 'start_date', 'end_date']
    search_fields = ['work_order_no', 'product_sn', 'product_name']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('report_type', 'work_order_no', 'product_sn', 'product_name', 'status')
        }),
        ('數量資訊', {
            'fields': ('total_quantity', 'completed_quantity', 'defect_quantity')
        }),
        ('時間資訊', {
            'fields': ('start_date', 'end_date', 'planned_duration', 'actual_duration')
        }),
        ('其他資訊', {
            'fields': ('data_source', 'calculation_method')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def completion_rate_display(self, obj):
        """顯示完成率"""
        if obj.total_quantity > 0:
            rate = (obj.completed_quantity / obj.total_quantity) * 100
            return f"{rate:.1f}%"
        return "0%"
    completion_rate_display.short_description = "完成率"


@admin.register(WorkHourReport)
class WorkHourReportAdmin(admin.ModelAdmin):
    """工時報表管理"""
    list_display = [
        'report_date', 'operator_or_equipment', 'total_hours', 
        'normal_hours', 'overtime_hours', 'break_hours',
        'efficiency_rate', 'utilization_rate'
    ]
    list_filter = ['report_date']
    search_fields = ['operator__username', 'equipment_name']
    date_hierarchy = 'report_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('report_type', 'report_date', 'operator', 'equipment_name')
        }),
        ('工時資訊', {
            'fields': ('total_hours', 'normal_hours', 'overtime_hours', 'break_hours')
        }),
        ('效率資訊', {
            'fields': ('efficiency_rate', 'utilization_rate')
        }),
        ('其他資訊', {
            'fields': ('data_source', 'calculation_method')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def operator_or_equipment(self, obj):
        """顯示作業員或設備名稱"""
        if obj.operator:
            return f"作業員: {obj.operator.username}"
        elif obj.equipment_name:
            return f"設備: {obj.equipment_name}"
        return "未知"
    operator_or_equipment.short_description = "人員/設備"
    
    def get_queryset(self, request):
        """優化查詢"""
        return super().get_queryset(request).select_related('operator')


@admin.register(ReportExportLog)
class ReportExportLogAdmin(admin.ModelAdmin):
    """報表匯出日誌管理"""
    list_display = [
        'report_type', 'export_format', 'date_range', 'export_status',
        'created_by', 'created_at', 'file_size_display'
    ]
    list_filter = ['report_type', 'export_format', 'export_status', 'created_at']
    search_fields = ['created_by__username', 'report_type']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'created_by']
    
    fieldsets = (
        ('匯出資訊', {
            'fields': ('report_type', 'export_format', 'date_range', 'custom_start_date', 'custom_end_date')
        }),
        ('結果資訊', {
            'fields': ('file_path', 'file_size', 'export_status', 'error_message')
        }),
        ('操作資訊', {
            'fields': ('created_by', 'created_at')
        }),
    )
    
    def file_size_display(self, obj):
        """顯示檔案大小"""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "未知"
    file_size_display.short_description = "檔案大小"
    
    def get_queryset(self, request):
        """優化查詢"""
        return super().get_queryset(request).select_related('created_by')
    
    def has_add_permission(self, request):
        """禁止手動新增匯出日誌"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改匯出日誌"""
        return False


# 自定義管理站台標題
admin.site.site_header = "MES 系統管理後台"
admin.site.site_title = "MES 系統"
admin.site.index_title = "報表管理" 