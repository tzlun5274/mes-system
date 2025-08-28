from django.db import models
from django.utils import timezone
from datetime import datetime
from .operation_log_models import SchedulingOperationLog
from .scheduling_models import Unit, Event
from .company_view_models import CompanyView
from .production_safety_settings import ProductionSafetySettings
from .process_interval_settings import ProcessIntervalSettings


class OrderUpdateSchedule(models.Model):
    """
    訂單自動同步排程設定：記錄訂單同步的間隔與最後更新時間
    """

    sync_interval_minutes = models.IntegerField(
        default=0, verbose_name="自動同步間隔（分鐘，0表示禁用）"
    )
    last_updated = models.DateTimeField(
        null=True, blank=True, verbose_name="上次更新時間"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "訂單更新排程"
        verbose_name_plural = "訂單更新排程"

    def __str__(self):
        if self.sync_interval_minutes > 0:
            return f"每 {self.sync_interval_minutes} 分鐘更新"
        return "自動同步已禁用"


class OrderMain(models.Model):
    """
    訂單主檔：記錄客戶訂單的基本資料與狀態
    """

    company_name = models.CharField(max_length=100, verbose_name="公司名稱")
    customer_short_name = models.CharField(max_length=100, verbose_name="客戶簡稱")
    bill_no = models.CharField(max_length=50, verbose_name="訂單號")
    product_id = models.CharField(max_length=50, verbose_name="產品編號")
    product_name = models.CharField(max_length=200, verbose_name="產品名稱")
    quantity = models.IntegerField(verbose_name="訂購數量")
    pre_in_date = models.CharField(max_length=10, verbose_name="預交貨日期")
    qty_remain = models.IntegerField(verbose_name="未交貨數量")
    order_type = models.CharField(max_length=20, verbose_name="訂單類型")
    bill_date = models.CharField(max_length=10, verbose_name="訂單日期")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "訂單主檔"
        verbose_name_plural = "訂單主檔"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.bill_no} - {self.product_name}"
    
    @property
    def delivered_quantity(self):
        """已交數量"""
        return self.quantity - self.qty_remain
    
    @property
    def is_overdue(self):
        """是否逾期"""
        try:
            delivery_date = datetime.strptime(self.pre_in_date, '%Y-%m-%d').date()
            return delivery_date < timezone.now().date()
        except:
            return False
    
    @property
    def is_urgent(self):
        """是否緊急（交期在3天內）"""
        try:
            delivery_date = datetime.strptime(self.pre_in_date, '%Y-%m-%d').date()
            today = timezone.now().date()
            days_until_delivery = (delivery_date - today).days
            return 0 <= days_until_delivery <= 3
        except:
            return False
