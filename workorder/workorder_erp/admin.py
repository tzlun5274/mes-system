"""
公司製令單管理子模組 - 管理介面
"""

from django.contrib import admin
from .models import PrdMKOrdMain, PrdMkOrdMats, CompanyOrder, SystemConfig


@admin.register(PrdMKOrdMain)
class PrdMKOrdMainAdmin(admin.ModelAdmin):
    """
    ERP製令主檔管理介面
    """
    list_display = [
        'MKOrdNO', 'ProductID', 'ProdtQty', 'CompleteStatus', 
        'GoodsQty', 'BadsQty', 'updated_at'
    ]
    list_filter = ['CompleteStatus', 'updated_at']
    search_fields = ['MKOrdNO', 'ProductID']
    readonly_fields = ['updated_at']
    ordering = ['-updated_at']


@admin.register(PrdMkOrdMats)
class PrdMkOrdMatsAdmin(admin.ModelAdmin):
    """
    ERP製令明細管理介面
    """
    list_display = [
        'MkOrdNO', 'SubProdID', 'OriginalQty', 'OughtQty', 
        'RowNO', 'updated_at'
    ]
    list_filter = ['updated_at']
    search_fields = ['MkOrdNO', 'SubProdID']
    readonly_fields = ['updated_at']
    ordering = ['-updated_at']


@admin.register(CompanyOrder)
class CompanyOrderAdmin(admin.ModelAdmin):
    """
    公司製令單管理介面
    """
    list_display = [
        'company_code', 'mkordno', 'product_id', 'prodt_qty',
        'complete_status', 'is_converted', 'sync_time'
    ]
    list_filter = ['company_code', 'complete_status', 'is_converted', 'sync_time']
    search_fields = ['mkordno', 'product_id']
    readonly_fields = ['sync_time']
    ordering = ['-sync_time']


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    """
    系統設定管理介面
    """
    list_display = ['key', 'value']
    search_fields = ['key']
    ordering = ['key'] 