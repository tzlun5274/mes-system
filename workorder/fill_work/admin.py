"""
填報作業管理子模組 - 管理介面配置
負責填報作業的 Django Admin 介面配置
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import FillWork
from django.utils import timezone


@admin.register(FillWork)
class FillWorkAdmin(admin.ModelAdmin):
    """填報作業管理介面"""
    
    list_display = [
        'id', 'operator', 'work_date', 'operation', 'workorder', 
        'work_quantity', 'defect_quantity', 'approval_status', 
        'is_completed', 'created_at'
    ]
    
    list_filter = [
        'approval_status', 'is_completed', 'work_date', 'process', 
        'equipment', 'has_break'
    ]
    
    search_fields = [
        'operator', 'workorder__workorder_number',
        'product_id', 'operation', 'remarks', 'abnormal_notes'
    ]
    
    readonly_fields = [
        'work_hours_calculated', 'overtime_hours_calculated', 
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('operator', 'company_name')
        }),
        ('工單資訊', {
            'fields': ('workorder', 'product_id', 'planned_quantity')
        }),
        ('製程資訊', {
            'fields': ('process', 'operation', 'equipment')
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
            'fields': ('work_quantity', 'defect_quantity')
        }),
        ('狀態資訊', {
            'fields': ('is_completed', 'approval_status')
        }),
        ('核准資訊', {
            'fields': ('approved_by', 'approved_at', 'approval_remarks'),
            'classes': ('collapse',)
        }),
        ('駁回資訊', {
            'fields': ('rejected_by', 'rejected_at', 'rejection_reason'),
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
        """優化查詢"""
        return super().get_queryset(request).select_related(
            'workorder', 'process', 'equipment'
        )
    
    def approval_status_colored(self, obj):
        """核准狀態彩色顯示"""
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        color = colors.get(obj.approval_status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_approval_status_display()
        )
    approval_status_colored.short_description = '核准狀態'
    
    def total_quantity(self, obj):
        """總數量"""
        return obj.get_total_quantity()
    total_quantity.short_description = '總數量'
    
    def work_duration(self, obj):
        """工作時長"""
        return f"{obj.get_work_duration():.2f} 小時"
    work_duration.short_description = '工作時長'
    
    actions = ['approve_selected', 'reject_selected', 'mark_completed']
    
    def approve_selected(self, request, queryset):
        """批量核准"""
        updated = queryset.update(
            approval_status='approved',
            approved_by=request.user.username,
            approved_at=timezone.now()
        )
        self.message_user(request, f'已核准 {updated} 筆填報作業')
    approve_selected.short_description = '核准選中的填報作業'
    
    def reject_selected(self, request, queryset):
        """批量駁回"""
        updated = queryset.update(
            approval_status='rejected',
            rejected_by=request.user.username,
            rejected_at=timezone.now()
        )
        self.message_user(request, f'已駁回 {updated} 筆填報作業')
    reject_selected.short_description = '駁回選中的填報作業'
    
    def mark_completed(self, request, queryset):
        """標記為完工"""
        updated = queryset.update(is_completed=True)
        self.message_user(request, f'已標記 {updated} 筆填報作業為完工')
    mark_completed.short_description = '標記選中的填報作業為完工' 