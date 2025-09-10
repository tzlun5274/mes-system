"""
現場報工子模組 - 管理介面配置
負責現場報工的 Django Admin 配置
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import OnsiteReport, OnsiteReportHistory, OnsiteReportConfig, OnsiteReportSession


@admin.register(OnsiteReport)
class OnsiteReportAdmin(admin.ModelAdmin):
    """現場報工記錄管理介面"""
    
    list_display = [
        'id', 'operator', 'workorder', 'product_id', 'company_code',
        'report_type', 'status', 'work_quantity', 'planned_quantity',
        'progress_display', 'work_date', 'created_at'
    ]
    
    list_filter = [
        'report_type', 'status', 'company_code',
        'created_at'
    ]
    
    search_fields = [
        'operator', 'workorder', 'product_id', 'company_code', 'process'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('report_type', 'operator', 'company_code')
        }),
        ('工單資訊', {
            'fields': ('workorder', 'product_id', 'planned_quantity')
        }),
        ('製程資訊', {
            'fields': ('process', 'operation', 'equipment')
        }),
        ('時間資訊', {
            'fields': ('work_date', 'start_datetime', 'end_datetime', 'work_minutes')
        }),
        ('數量資訊', {
            'fields': ('status', 'work_quantity', 'defect_quantity')
        }),
        ('備註資訊', {
            'fields': ('remarks', 'abnormal_notes'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        """顯示進度百分比"""
        percentage = obj.get_progress_percentage()
        if percentage >= 100:
            color = 'green'
        elif percentage >= 80:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, percentage
        )
    progress_display.short_description = '進度'
    
    def get_queryset(self, request):
        """優化查詢"""
        return super().get_queryset(request).select_related()
    
    def has_add_permission(self, request):
        """控制新增權限"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """控制修改權限"""
        return request.user.is_superuser or request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """控制刪除權限"""
        return request.user.is_superuser


@admin.register(OnsiteReportSession)
class OnsiteReportSessionAdmin(admin.ModelAdmin):
    """現場報工工作時段管理介面"""
    
    list_display = [
        'id', 'operator', 'workorder', 'product_id', 'company_code',
        'session_count', 'total_work_minutes', 'total_quantity_produced',
        'is_active', 'created_at'
    ]
    
    list_filter = [
        'company_code', 'is_active', 'created_at'
    ]
    
    search_fields = [
        'operator', 'workorder', 'product_id', 'company_code'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('operator', 'workorder', 'product_id', 'company_code')
        }),
        ('製程資訊', {
            'fields': ('process', 'operation', 'equipment')
        }),
        ('工單資訊', {
            'fields': ('planned_quantity',)
        }),
        ('統計資訊', {
            'fields': ('total_work_minutes', 'total_quantity_produced', 'total_defect_quantity', 'session_count')
        }),
        ('狀態', {
            'fields': ('is_active',)
        }),
        ('系統資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """控制新增權限"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """控制修改權限"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """控制刪除權限"""
        return request.user.is_superuser


@admin.register(OnsiteReportHistory)
class OnsiteReportHistoryAdmin(admin.ModelAdmin):
    """現場報工歷史記錄管理介面"""
    
    list_display = [
        'id', 'onsite_report_link', 'change_type', 'old_status', 'new_status',
        'old_quantity', 'new_quantity', 'changed_by', 'changed_at'
    ]
    
    list_filter = [
        'change_type', 'changed_at', 'changed_by'
    ]
    
    search_fields = [
        'onsite_report__operator', 'onsite_report__order_number', 'changed_by'
    ]
    
    readonly_fields = [
        'onsite_report_id', 'changed_at'
    ]
    
    def onsite_report_link(self, obj):
        """顯示現場報工記錄連結"""
        if obj.onsite_report:
            url = reverse('admin:workorder_onsite_report_onsitereport_change', args=[obj.onsite_report.id])
            return format_html('<a href="{}">{}</a>', url, obj.onsite_report)
        return '-'
    onsite_report_link.short_description = '現場報工記錄'
    
    def has_add_permission(self, request):
        """禁止手動新增歷史記錄"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改歷史記錄"""
        return False


@admin.register(OnsiteReportConfig)
class OnsiteReportConfigAdmin(admin.ModelAdmin):
    """現場報工配置管理介面"""
    
    list_display = [
        'id', 'config_type', 'config_key', 'config_value_preview', 
        'is_active', 'created_by', 'created_at'
    ]
    
    list_filter = [
        'config_type', 'is_active', 'created_at'
    ]
    
    search_fields = [
        'config_key', 'config_value', 'config_description'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('配置資訊', {
            'fields': ('config_type', 'config_key', 'config_value', 'config_description')
        }),
        ('狀態', {
            'fields': ('is_active',)
        }),
        ('系統資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def config_value_preview(self, obj):
        """顯示配置值預覽"""
        if len(obj.config_value) > 50:
            return obj.config_value[:50] + '...'
        return obj.config_value
    config_value_preview.short_description = '配置值預覽'
    
    def has_add_permission(self, request):
        """控制新增權限"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """控制修改權限"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """控制刪除權限"""
        return request.user.is_superuser 