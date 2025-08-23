"""
公司製令單管理子模組 - 管理介面
負責公司製令單的 Django Admin 介面
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import CompanyOrder, CompanyOrderSystemConfig


@admin.register(CompanyOrder)
class CompanyOrderAdmin(admin.ModelAdmin):
    """公司製令單管理介面"""
    
    list_display = [
        'company_code', 'mkordno', 'product_id', 'prodt_qty',
        'est_take_mat_date', 'est_stock_out_date', 'status_display',
        'complete_status', 'bill_status', 'sync_time'
    ]
    
    list_filter = [
        'company_code', 'is_converted', 'complete_status', 'bill_status',
        'est_stock_out_date', 'sync_time'
    ]
    
    search_fields = [
        'company_code', 'mkordno', 'product_id', 'producer', 'functionary'
    ]
    
    readonly_fields = [
        'sync_time', 'created_at', 'updated_at', 'status_display',
        'is_pending', 'is_completed', 'is_closed'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('company_code', 'mkordno', 'product_id', 'prodt_qty')
        }),
        ('時間資訊', {
            'fields': ('est_take_mat_date', 'est_stock_out_date', 'mkord_date')
        }),
        ('狀態資訊', {
            'fields': ('complete_status', 'bill_status', 'is_converted', 'flag')
        }),
        ('ERP 原始資料', {
            'fields': ('make_type', 'producer', 'functionary', 'remark'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('sync_time', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-est_stock_out_date', '-created_at']
    
    def status_display(self, obj):
        """狀態顯示"""
        if obj.is_converted:
            return format_html('<span style="color: green;">已轉換</span>')
        return format_html('<span style="color: orange;">未轉換</span>')
    status_display.short_description = "轉換狀態"
    
    def get_queryset(self, request):
        """自定義查詢集"""
        return super().get_queryset(request).select_related()


@admin.register(CompanyOrderSystemConfig)
class CompanyOrderSystemConfigAdmin(admin.ModelAdmin):
    """公司製令單系統設定管理介面"""
    
    list_display = ['key', 'value', 'description', 'updated_at']
    
    search_fields = ['key', 'value', 'description']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('設定資訊', {
            'fields': ('key', 'value', 'description')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['key']
    
    def has_delete_permission(self, request, obj=None):
        """禁止刪除系統設定"""
        return False 