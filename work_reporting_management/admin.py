"""
統一補登報工管理介面
提供 Django Admin 的管理功能
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import UnifiedWorkReport, UnifiedWorkReportLog


@admin.register(UnifiedWorkReport)
class UnifiedWorkReportAdmin(admin.ModelAdmin):
    """
    統一補登報工管理介面
    """
    list_display = [
        'id', 'operator', 'company_code', 'original_workorder_number', 
        'product_id', 'operation', 'work_date', 'start_time', 'end_time',
        'work_quantity', 'defect_quantity', 'total_quantity_display',
        'work_hours_calculated', 'overtime_hours_calculated', 'total_hours_display',
        'approval_status_display', 'is_completed_display', 'created_by', 'created_at'
    ]
    
    list_filter = [
        'company_code', 'approval_status', 'is_completed', 'has_break',
        'work_date', 'created_at', 'process'
    ]
    
    search_fields = [
        'operator', 'original_workorder_number', 'product_id', 
        'operation', 'equipment', 'remarks', 'abnormal_notes'
    ]
    
    readonly_fields = [
        'work_hours_calculated', 'overtime_hours_calculated', 'break_hours',
        'total_quantity', 'total_hours', 'approval_status_display',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('operator', 'company_code')
        }),
        ('工單相關', {
            'fields': ('workorder', 'original_workorder_number', 'product_id', 'planned_quantity')
        }),
        ('製程相關', {
            'fields': ('process', 'operation', 'equipment')
        }),
        ('時間相關', {
            'fields': ('work_date', 'start_time', 'end_time')
        }),
        ('休息時間', {
            'fields': ('has_break', 'break_start_time', 'break_end_time', 'break_hours'),
            'classes': ('collapse',)
        }),
        ('工時計算', {
            'fields': ('work_hours_calculated', 'overtime_hours_calculated', 'total_hours'),
            'classes': ('collapse',)
        }),
        ('數量相關', {
            'fields': ('work_quantity', 'defect_quantity', 'total_quantity')
        }),
        ('狀態', {
            'fields': ('is_completed', 'approval_status')
        }),
        ('核准資訊', {
            'fields': ('approved_by', 'approved_at', 'approval_remarks'),
            'classes': ('collapse',)
        }),
        ('駁回資訊', {
            'fields': ('rejection_reason', 'rejected_by', 'rejected_at'),
            'classes': ('collapse',)
        }),
        ('備註', {
            'fields': ('remarks', 'abnormal_notes'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_selected', 'reject_selected', 'mark_as_completed', 'mark_as_incomplete']
    
    def total_quantity_display(self, obj):
        """顯示總數量"""
        return obj.total_quantity
    total_quantity_display.short_description = '總數量'
    
    def total_hours_display(self, obj):
        """顯示總工時"""
        return f"{obj.total_hours:.2f} 小時"
    total_hours_display.short_description = '總工時'
    
    def approval_status_display(self, obj):
        """顯示核准狀態"""
        status_colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'cancelled': 'gray'
        }
        color = status_colors.get(obj.approval_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_approval_status_display()
        )
    approval_status_display.short_description = '核准狀態'
    
    def is_completed_display(self, obj):
        """顯示完工狀態"""
        if obj.is_completed:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ 已完工</span>'
            )
        else:
            return format_html(
                '<span style="color: orange; font-weight: bold;">○ 未完工</span>'
            )
    is_completed_display.short_description = '完工狀態'
    
    def approve_selected(self, request, queryset):
        """批量核准"""
        count = 0
        for report in queryset.filter(approval_status='pending'):
            report.approve(request.user.username, '批量核准')
            count += 1
        self.message_user(request, f'成功核准 {count} 筆記錄')
    approve_selected.short_description = '核准選中的記錄'
    
    def reject_selected(self, request, queryset):
        """批量駁回"""
        count = 0
        for report in queryset.filter(approval_status='pending'):
            report.reject(request.user.username, '批量駁回')
            count += 1
        self.message_user(request, f'成功駁回 {count} 筆記錄')
    reject_selected.short_description = '駁回選中的記錄'
    
    def mark_as_completed(self, request, queryset):
        """標記為已完工"""
        count = queryset.update(is_completed=True)
        self.message_user(request, f'成功標記 {count} 筆記錄為已完工')
    mark_as_completed.short_description = '標記為已完工'
    
    def mark_as_incomplete(self, request, queryset):
        """標記為未完工"""
        count = queryset.update(is_completed=False)
        self.message_user(request, f'成功標記 {count} 筆記錄為未完工')
    mark_as_incomplete.short_description = '標記為未完工'
    
    def get_queryset(self, request):
        """自定義查詢集"""
        qs = super().get_queryset(request)
        return qs.select_related('workorder', 'process')
    
    def save_model(self, request, obj, form, change):
        """儲存模型時設定建立人員"""
        if not change:  # 新增時
            obj.created_by = request.user.username
        super().save_model(request, obj, form, change)


@admin.register(UnifiedWorkReportLog)
class UnifiedWorkReportLogAdmin(admin.ModelAdmin):
    """
    統一補登報工操作日誌管理介面
    """
    list_display = [
        'id', 'work_report_link', 'action', 'operator', 'created_at'
    ]
    
    list_filter = [
        'action', 'created_at'
    ]
    
    search_fields = [
        'work_report__operator', 'work_report__original_workorder_number',
        'operator', 'remarks'
    ]
    
    readonly_fields = [
        'work_report', 'action', 'operator', 'remarks', 'created_at'
    ]
    
    def work_report_link(self, obj):
        """顯示工單連結"""
        if obj.work_report:
            url = reverse('admin:unified_work_reporting_unifiedworkreport_change', args=[obj.work_report.id])
            return format_html('<a href="{}">{}</a>', url, obj.work_report)
        return '-'
    work_report_link.short_description = '統一補登報工'
    
    def has_add_permission(self, request):
        """禁止手動新增日誌"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止編輯日誌"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """禁止刪除日誌"""
        return False
