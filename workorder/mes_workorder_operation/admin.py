"""
MES 工單作業子模組 - 管理介面
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import MesWorkorderOperation, MesWorkorderOperationDetail, MesWorkorderOperationHistory


@admin.register(MesWorkorderOperation)
class MesWorkorderOperationAdmin(admin.ModelAdmin):
    """MES 工單作業管理介面"""
    
    list_display = [
        'formatted_company_code',
        'workorder_number',
        'product_code',
        'operation_name',
        'operation_type_display',
        'status_display',
        'completion_rate_display',
        'assigned_operator',
        'planned_start_date',
        'created_at'
    ]
    
    list_filter = [
        'company_code',
        'operation_type',
        'status',
        'planned_start_date',
        'created_at'
    ]
    
    search_fields = [
        'company_code',
        'workorder_number',
        'product_code',
        'operation_name',
        'assigned_operator'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'completion_rate_display',
        'remaining_quantity_display'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('company_code', 'company_name', 'workorder_number', 'product_code', 'product_name')
        }),
        ('作業資訊', {
            'fields': ('operation_type', 'operation_name', 'status', 'notes')
        }),
        ('數量資訊', {
            'fields': ('planned_quantity', 'completed_quantity', 'defect_quantity', 'completion_rate_display', 'remaining_quantity_display')
        }),
        ('時間資訊', {
            'fields': ('planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date')
        }),
        ('人員和設備', {
            'fields': ('assigned_operator', 'assigned_equipment')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def formatted_company_code(self, obj):
        """格式化公司代號顯示"""
        if obj.company_code and obj.company_code.isdigit():
            return f"[{obj.company_code.zfill(2)}]"
        return obj.company_code
    formatted_company_code.short_description = "公司代號"
    
    def operation_type_display(self, obj):
        """作業類型顯示"""
        return obj.get_operation_type_display()
    operation_type_display.short_description = "作業類型"
    
    def status_display(self, obj):
        """狀態顯示"""
        status_colors = {
            'pending': 'warning',
            'in_progress': 'primary',
            'paused': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        }
        color = status_colors.get(obj.status, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_status_display())
    status_display.short_description = "狀態"
    
    def completion_rate_display(self, obj):
        """完成率顯示"""
        rate = obj.get_completion_rate()
        if rate >= 100:
            color = 'success'
        elif rate >= 80:
            color = 'info'
        elif rate >= 50:
            color = 'warning'
        else:
            color = 'danger'
        return format_html('<span class="badge bg-{}">{:.1f}%</span>', color, rate)
    completion_rate_display.short_description = "完成率"
    
    def remaining_quantity_display(self, obj):
        """剩餘數量顯示"""
        remaining = obj.get_remaining_quantity()
        return format_html('<span class="badge bg-info">{}</span>', remaining)
    remaining_quantity_display.short_description = "剩餘數量"
    
    class Meta:
        verbose_name = "MES 工單作業"
        verbose_name_plural = "MES 工單作業管理"


@admin.register(MesWorkorderOperationDetail)
class MesWorkorderOperationDetailAdmin(admin.ModelAdmin):
    """MES 工單作業明細管理介面"""
    
    list_display = [
        'operation_link',
        'detail_type_display',
        'detail_name',
        'planned_quantity',
        'actual_quantity',
        'completion_rate_display',
        'is_completed_display',
        'start_time',
        'end_time'
    ]
    
    list_filter = [
        'operation__company_code',
        'detail_type',
        'is_completed',
        'created_at'
    ]
    
    search_fields = [
        'operation__workorder_number',
        'operation__product_code',
        'detail_name',
        'detail_description'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'completion_rate_display',
        'duration_display'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('operation', 'detail_type', 'detail_name', 'detail_description')
        }),
        ('數量資訊', {
            'fields': ('planned_quantity', 'actual_quantity', 'completion_rate_display')
        }),
        ('時間資訊', {
            'fields': ('start_time', 'end_time', 'duration_display')
        }),
        ('狀態資訊', {
            'fields': ('is_completed', 'notes')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def operation_link(self, obj):
        """作業主表連結"""
        if obj.operation:
            url = reverse('admin:mes_workorder_operation_mesworkorderoperation_change', args=[obj.operation.id])
            return format_html('<a href="{}">{}</a>', url, obj.operation)
        return '-'
    operation_link.short_description = "作業主表"
    
    def detail_type_display(self, obj):
        """明細類型顯示"""
        return obj.get_detail_type_display()
    detail_type_display.short_description = "明細類型"
    
    def completion_rate_display(self, obj):
        """完成率顯示"""
        rate = float(obj.completion_rate)
        if rate >= 100:
            color = 'success'
        elif rate >= 80:
            color = 'info'
        elif rate >= 50:
            color = 'warning'
        else:
            color = 'danger'
        return format_html('<span class="badge bg-{}">{:.1f}%</span>', color, rate)
    completion_rate_display.short_description = "完成率"
    
    def is_completed_display(self, obj):
        """是否完成顯示"""
        if obj.is_completed:
            return format_html('<span class="badge bg-success">✓ 已完成</span>')
        else:
            return format_html('<span class="badge bg-warning">○ 未完成</span>')
    is_completed_display.short_description = "完成狀態"
    
    def duration_display(self, obj):
        """作業時長顯示"""
        duration = obj.get_duration()
        if duration > 0:
            hours = int(duration // 60)
            minutes = int(duration % 60)
            if hours > 0:
                return f"{hours}小時{minutes}分鐘"
            else:
                return f"{minutes}分鐘"
        return "-"
    duration_display.short_description = "作業時長"
    
    class Meta:
        verbose_name = "MES 工單作業明細"
        verbose_name_plural = "MES 工單作業明細管理"


@admin.register(MesWorkorderOperationHistory)
class MesWorkorderOperationHistoryAdmin(admin.ModelAdmin):
    """MES 工單作業歷史管理介面"""
    
    list_display = [
        'operation_link',
        'history_type_display',
        'history_description',
        'operator',
        'ip_address',
        'created_at'
    ]
    
    list_filter = [
        'operation__company_code',
        'history_type',
        'created_at'
    ]
    
    search_fields = [
        'operation__workorder_number',
        'operation__product_code',
        'history_description',
        'operator'
    ]
    
    readonly_fields = [
        'operation',
        'history_type',
        'history_description',
        'old_values',
        'new_values',
        'operator',
        'ip_address',
        'created_at',
        'changes_summary'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('operation', 'history_type', 'history_description')
        }),
        ('變更資訊', {
            'fields': ('old_values', 'new_values', 'changes_summary')
        }),
        ('操作資訊', {
            'fields': ('operator', 'ip_address', 'created_at')
        }),
    )
    
    def operation_link(self, obj):
        """作業主表連結"""
        if obj.operation:
            url = reverse('admin:mes_workorder_operation_mesworkorderoperation_change', args=[obj.operation.id])
            return format_html('<a href="{}">{}</a>', url, obj.operation)
        return '-'
    operation_link.short_description = "作業主表"
    
    def history_type_display(self, obj):
        """歷史類型顯示"""
        type_colors = {
            'created': 'success',
            'updated': 'info',
            'started': 'primary',
            'paused': 'warning',
            'resumed': 'info',
            'completed': 'success',
            'cancelled': 'danger',
            'deleted': 'danger'
        }
        color = type_colors.get(obj.history_type, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_history_type_display())
    history_type_display.short_description = "歷史類型"
    
    def changes_summary(self, obj):
        """變更摘要"""
        summary = obj.get_changes_summary()
        if summary:
            return format_html('<div class="alert alert-info">{}</div>', summary)
        return '-'
    changes_summary.short_description = "變更摘要"
    
    def has_add_permission(self, request):
        """禁止手動新增歷史記錄"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止修改歷史記錄"""
        return False
    
    class Meta:
        verbose_name = "MES 工單作業歷史"
        verbose_name_plural = "MES 工單作業歷史管理" 