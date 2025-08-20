"""
公司製令單管理子模組 - 管理介面
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import CompanyOrder, ERPSystemConfig, ERPPrdMKOrdMain, ERPPrdMkOrdMats


@admin.register(CompanyOrder)
class CompanyOrderAdmin(admin.ModelAdmin):
    """公司製令單管理介面"""
    
    list_display = [
        'formatted_company_code', 
        'mkordno', 
        'product_id', 
        'prodt_qty', 
        'est_take_mat_date', 
        'est_stock_out_date',
        'is_converted_display',
        'sync_time'
    ]
    
    list_filter = [
        'company_code',
        'is_converted',
        'sync_time'
    ]
    
    search_fields = [
        'company_code',
        'mkordno',
        'product_id'
    ]
    
    readonly_fields = [
        'sync_time'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('company_code', 'mkordno', 'product_id', 'prodt_qty')
        }),
        ('時間資訊', {
            'fields': ('est_take_mat_date', 'est_stock_out_date')
        }),
        ('狀態資訊', {
            'fields': ('complete_status', 'bill_status', 'is_converted')
        }),
        ('系統資訊', {
            'fields': ('sync_time',),
            'classes': ('collapse',)
        }),
    )
    
    def formatted_company_code(self, obj):
        """格式化公司代號顯示"""
        if obj.company_code and obj.company_code.isdigit():
            return f"[{obj.company_code.zfill(2)}]"
        return obj.company_code
    formatted_company_code.short_description = "公司代號"
    
    def is_converted_display(self, obj):
        """轉換狀態顯示"""
        if obj.is_converted:
            return format_html('<span style="color: green;">✓ 已轉換</span>')
        else:
            return format_html('<span style="color: red;">✗ 未轉換</span>')
    is_converted_display.short_description = "轉換狀態"
    
    class Meta:
        verbose_name = "公司製令單"
        verbose_name_plural = "公司製令單管理"


@admin.register(ERPSystemConfig)
class ERPSystemConfigAdmin(admin.ModelAdmin):
    """ERP系統配置管理介面"""
    
    list_display = [
        'formatted_company_code',
        'server_name',
        'database_name',
        'username',
        'sync_interval',
        'is_active_display',
        'updated_at'
    ]
    
    list_filter = [
        'company_code',
        'is_active',
        'sync_interval',
        'created_at'
    ]
    
    search_fields = [
        'company_code',
        'server_name',
        'database_name'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('company_code',)
        }),
        ('ERP連線設定', {
            'fields': ('server_name', 'database_name', 'username', 'password')
        }),
        ('同步設定', {
            'fields': ('sync_interval', 'is_active')
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def formatted_company_code(self, obj):
        """格式化公司代號顯示"""
        if obj.company_code and obj.company_code.isdigit():
            return f"[{obj.company_code.zfill(2)}]"
        return obj.company_code
    formatted_company_code.short_description = "公司代號"
    
    def is_active_display(self, obj):
        """啟用狀態顯示"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ 啟用</span>')
        else:
            return format_html('<span style="color: red;">✗ 停用</span>')
    is_active_display.short_description = "啟用狀態"
    
    class Meta:
        verbose_name = "ERP系統配置"
        verbose_name_plural = "ERP系統配置管理"


@admin.register(ERPPrdMKOrdMain)
class ERPPrdMKOrdMainAdmin(admin.ModelAdmin):
    """ERP製令主檔管理介面"""
    
    list_display = [
        'formatted_company_code',
        'MKOrdNO',
        'ProductID',
        'ProdtQty',
        'CompleteStatus',
        'BillStatus',
        'updated_at'
    ]
    
    list_filter = [
        'company_code',
        'CompleteStatus',
        'BillStatus',
        'updated_at'
    ]
    
    search_fields = [
        'company_code',
        'MKOrdNO',
        'ProductID'
    ]
    
    readonly_fields = [
        'row_id',
        'updated_at'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('company_code', 'MKOrdNO', 'ProductID', 'ProdtQty')
        }),
        ('製令資訊', {
            'fields': ('MKOrdDate', 'MakeType', 'FromRowNO', 'ProductType')
        }),
        ('人員資訊', {
            'fields': ('Producer', 'Functionary', 'Maker', 'Permitter')
        }),
        ('狀態資訊', {
            'fields': ('CompleteStatus', 'BillStatus', 'Flag')
        }),
        ('數量資訊', {
            'fields': ('GoodsQty', 'BadsQty')
        }),
        ('其他資訊', {
            'fields': ('CostType', 'SourceType', 'SourceNo', 'WareInType', 'Remark'),
            'classes': ('collapse',)
        }),
        ('時間資訊', {
            'fields': ('EstTakeMatDate', 'EstWareInDate', 'ChangeDate', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def formatted_company_code(self, obj):
        """格式化公司代號顯示"""
        if obj.company_code and obj.company_code.isdigit():
            return f"[{obj.company_code.zfill(2)}]"
        return obj.company_code
    formatted_company_code.short_description = "公司代號"
    
    class Meta:
        verbose_name = "ERP製令主檔"
        verbose_name_plural = "ERP製令主檔管理"


@admin.register(ERPPrdMkOrdMats)
class ERPPrdMkOrdMatsAdmin(admin.ModelAdmin):
    """ERP製令明細管理介面"""
    
    list_display = [
        'formatted_company_code',
        'MkOrdNO',
        'SubProdID',
        'OriginalQty',
        'OughtQty',
        'RowNO',
        'updated_at'
    ]
    
    list_filter = [
        'company_code',
        'updated_at'
    ]
    
    search_fields = [
        'company_code',
        'MkOrdNO',
        'SubProdID'
    ]
    
    readonly_fields = [
        'row_id',
        'updated_at'
    ]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('company_code', 'MkOrdNO', 'SubProdID', 'OriginalQty')
        }),
        ('明細資訊', {
            'fields': ('RowNO', 'SerNO', 'OughtQty', 'UnitOughtQty')
        }),
        ('其他資訊', {
            'fields': ('WestingRate', 'MatsRemark', 'Detail'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('Flag', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def formatted_company_code(self, obj):
        """格式化公司代號顯示"""
        if obj.company_code and obj.company_code.isdigit():
            return f"[{obj.company_code.zfill(2)}]"
        return obj.company_code
    formatted_company_code.short_description = "公司代號"
    
    class Meta:
        verbose_name = "ERP製令明細"
        verbose_name_plural = "ERP製令明細管理" 