"""
填報作業管理子模組 - 管理介面
負責填報作業的 Django Admin 配置
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import FillWork
from django.utils import timezone


@admin.register(FillWork)
class FillWorkAdmin(admin.ModelAdmin):
    """
    填報作業管理介面
    """
    list_display = [
        'id', 'operator', 'workorder', 'product_id', 'company_name',
        'work_date', 'start_time', 'end_time', 'work_quantity',
        'approval_status', 'created_at'
    ]
    
    list_filter = [
        'approval_status', 'work_date', 'created_at', 'company_name',
        'process_name', 'is_completed'
    ]
    
    search_fields = [
        'operator', 'workorder', 'product_id', 'company_name',
        'remarks', 'abnormal_notes'
    ]
    
    readonly_fields = [
        'created_at', 'updated_at', 'work_hours_calculated',
        'overtime_hours_calculated', 'break_hours'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('operator', 'company_name', 'workorder', 'product_id', 'planned_quantity')
        }),
        ('製程資訊', {
            'fields': ('process_id', 'process_name', 'operation', 'equipment')
        }),
        ('時間資訊', {
            'fields': ('work_date', 'start_time', 'end_time')
        }),
        ('休息時間', {
            'fields': ('has_break', 'break_start_time', 'break_end_time', 'break_hours'),
            'classes': ('collapse',)
        }),
        ('工時計算', {
            'fields': ('work_hours_calculated', 'overtime_hours_calculated'),
            'classes': ('collapse',)
        }),
        ('數量資訊', {
            'fields': ('work_quantity', 'defect_quantity', 'is_completed')
        }),
        ('核准狀態', {
            'fields': ('approval_status', 'approved_by', 'approved_at', 'approval_remarks'),
            'classes': ('collapse',)
        }),
        ('駁回資訊', {
            'fields': ('rejection_reason', 'rejected_by', 'rejected_at'),
            'classes': ('collapse',)
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
    
    def get_queryset(self, request):
        """自定義查詢集"""
        return super().get_queryset(request)
    
    def approval_status_colored(self, obj):
        """核准狀態彩色顯示"""
        status_colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        color = status_colors.get(obj.approval_status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_approval_status_display()
        )
    approval_status_colored.short_description = '核准狀態'
    
    def work_hours_display(self, obj):
        """工時顯示"""
        return f"{obj.work_hours_calculated}小時 (加班: {obj.overtime_hours_calculated}小時)"
    work_hours_display.short_description = '工時'
    
    def detail_link(self, obj):
        """詳情連結"""
        url = reverse('workorder:fill_work:fill_work_detail', args=[obj.pk])
        return format_html('<a href="{}">查看詳情</a>', url)
    detail_link.short_description = '操作'
    
    actions = ['approve_selected', 'reject_selected']
    
    def approve_selected(self, request, queryset):
        """批量核准"""
        updated = queryset.update(
            approval_status='approved',
            approved_by=request.user.username,
            approved_at=timezone.now()
        )
        self.message_user(request, f'成功核准 {updated} 筆填報作業')
    approve_selected.short_description = '核准選中的填報作業'
    
    def reject_selected(self, request, queryset):
        """批量駁回"""
        updated = queryset.update(
            approval_status='rejected',
            rejected_by=request.user.username,
            rejected_at=timezone.now()
        )
        self.message_user(request, f'成功駁回 {updated} 筆填報作業')
    reject_selected.short_description = '駁回選中的填報作業'
    
    class Media:
        css = {
            'all': ('admin/css/fill_work_admin.css',)
        }
        js = ('admin/js/fill_work_admin.js',) 