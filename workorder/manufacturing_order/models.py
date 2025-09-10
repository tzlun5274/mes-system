"""
公司製造命令管理子模組 - 模型定義
負責ERP整合功能，包括公司製造命令、ERP製令主檔等
"""

from django.db import models
from django.utils import timezone


class ManufacturingOrder(models.Model):
    """
    MES 專用公司製造命令主表
    負責製令單的業務管理、狀態管理和工單轉換
    """
    
    # 基本欄位
    company_code = models.CharField(max_length=10, verbose_name="公司代號", help_text="公司代號，例如：01、02、03")
    mkordno = models.CharField(max_length=50, verbose_name="製令單號", help_text="製令單號")
    product_id = models.CharField(max_length=100, verbose_name="產品編號", help_text="產品編號")
    prodt_qty = models.PositiveIntegerField(verbose_name="生產數量", help_text="生產數量")
    
    # 時間欄位
    est_take_mat_date = models.CharField(max_length=20, verbose_name="預定開工日", help_text="預定開工日")
    est_stock_out_date = models.CharField(max_length=20, verbose_name="預定出貨日", help_text="預定出貨日")
    sync_time = models.DateTimeField(auto_now=True, verbose_name="同步時間", help_text="同步時間")
    
    # 狀態欄位
    complete_status = models.IntegerField(verbose_name="完工狀態", null=True, blank=True, help_text="完工狀態")
    bill_status = models.IntegerField(verbose_name="單況", null=True, blank=True, help_text="單況")
    is_converted = models.BooleanField(default=False, verbose_name="是否已轉換成工單", help_text="是否已轉換成工單")
    
    # ERP 原始資料欄位（用於同步）
    flag = models.IntegerField(verbose_name="ERP狀態Flag", null=True, blank=True, help_text="ERP狀態Flag")
    mkord_date = models.CharField(max_length=20, verbose_name="製令日期", blank=True, null=True, help_text="製令日期")
    make_type = models.CharField(max_length=20, verbose_name="製令類型", blank=True, null=True, help_text="製令類型")
    producer = models.CharField(max_length=20, verbose_name="生產人員", blank=True, null=True, help_text="生產人員")
    functionary = models.CharField(max_length=20, verbose_name="負責人", blank=True, null=True, help_text="負責人")
    remark = models.TextField(verbose_name="備註", blank=True, null=True, help_text="備註")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間", help_text="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間", help_text="更新時間")

    class Meta:
        verbose_name = "公司製造命令"
        verbose_name_plural = "公司製造命令"
        db_table = 'workorder_manufacturing_order'
        unique_together = (("company_code", "mkordno", "product_id"),)
        ordering = ['-est_stock_out_date', '-created_at']
        indexes = [
            models.Index(fields=['company_code']),
            models.Index(fields=['mkordno']),
            models.Index(fields=['product_id']),
            models.Index(fields=['complete_status']),
            models.Index(fields=['bill_status']),
            models.Index(fields=['is_converted']),
            models.Index(fields=['est_stock_out_date']),
            models.Index(fields=['sync_time']),
        ]

    def __str__(self):
        """格式化顯示"""
        formatted_company_code = self.company_code.zfill(2) if self.company_code and self.company_code.isdigit() else self.company_code
        return f"[{formatted_company_code}] 製令單 {self.mkordno}"
    
    @property
    def status_display(self):
        """狀態顯示"""
        if self.is_converted:
            return "已轉換"
        return "未轉換"
    
    @property
    def is_pending(self):
        """是否為待處理製令單（未完工且未結案）"""
        return self.complete_status == 2 and self.bill_status != 1
    
    @property
    def is_completed(self):
        """是否已完工"""
        return self.complete_status == 1
    
    @property
    def is_closed(self):
        """是否已結案"""
        return self.bill_status == 1


 