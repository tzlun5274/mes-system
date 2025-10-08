"""
派工單管理子模組 - 模型定義
負責派工單的管理功能，包括派工單主表、工序明細等
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum


class WorkOrderDispatch(models.Model):
    """
    派工單主表：專門用於派工管理
    記錄工單的派工資訊，不包含報工記錄
    """
    STATUS_CHOICES = [
        ("pending", "待派工"),
        ("dispatched", "已派工"),
        ("in_production", "生產中"),
        ("completed", "已完工"),
        ("cancelled", "已取消"),
    ]

    # 基本資訊
    company_code = models.CharField(max_length=20, verbose_name="公司代號", null=True, blank=True)
    company_name = models.CharField(max_length=100, verbose_name="公司名稱", null=True, blank=True)
    order_number = models.CharField(max_length=100, verbose_name="工單號碼", db_index=True)
    product_code = models.CharField(max_length=100, verbose_name="產品編號", db_index=True)
    product_name = models.CharField(max_length=200, verbose_name="產品名稱", null=True, blank=True)
    planned_quantity = models.PositiveIntegerField(verbose_name="計劃數量", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_production", verbose_name="派工狀態")
    
    # 派工相關資訊
    dispatch_date = models.DateField(verbose_name="派工日期", null=True, blank=True)
    planned_start_date = models.DateField(verbose_name="計劃開始日期", null=True, blank=True)
    planned_end_date = models.DateField(verbose_name="計劃完成日期", null=True, blank=True)
    
    # 作業員和設備資訊
    assigned_operator = models.CharField(max_length=100, verbose_name="分配作業員", null=True, blank=True)
    assigned_equipment = models.CharField(max_length=100, verbose_name="分配設備", null=True, blank=True)
    process_name = models.CharField(max_length=100, verbose_name="工序名稱", null=True, blank=True)
    
    # 生產監控資料（合併自ProductionMonitoringData）
    # 基本統計資料
    total_work_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總工作時數")
    total_overtime_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總加班時數")
    total_all_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總時數")
    
    # 數量統計資料
    total_good_quantity = models.IntegerField(default=0, verbose_name="總良品數量")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="總不良品數量")
    total_quantity = models.IntegerField(default=0, verbose_name="總數量")
    
    # 出貨包裝專項統計
    packaging_good_quantity = models.IntegerField(default=0, verbose_name="出貨包裝良品數量")
    packaging_defect_quantity = models.IntegerField(default=0, verbose_name="出貨包裝不良品數量")
    packaging_total_quantity = models.IntegerField(default=0, verbose_name="出貨包裝總數量")
    
    # 填報記錄統計
    fillwork_report_count = models.IntegerField(default=0, verbose_name="填報記錄數量")
    fillwork_approved_count = models.IntegerField(default=0, verbose_name="已核准填報數量")
    fillwork_pending_count = models.IntegerField(default=0, verbose_name="待審核填報數量")
    
    # 現場報工統計
    onsite_report_count = models.IntegerField(default=0, verbose_name="現場報工記錄數量")
    onsite_completed_count = models.IntegerField(default=0, verbose_name="已完成現場報工數量")
    
    # 工序進度統計
    total_processes = models.IntegerField(default=0, verbose_name="總工序數")
    completed_processes = models.IntegerField(default=0, verbose_name="已完成工序數")
    in_progress_processes = models.IntegerField(default=0, verbose_name="進行中工序數")
    pending_processes = models.IntegerField(default=0, verbose_name="待開始工序數")
    
    # 人員和設備統計
    unique_operators = models.JSONField(default=list, verbose_name="參與作業員清單")
    unique_equipment = models.JSONField(default=list, verbose_name="使用設備清單")
    operator_count = models.IntegerField(default=0, verbose_name="參與作業員數量")
    equipment_count = models.IntegerField(default=0, verbose_name="使用設備數量")
    
    # 完成率計算
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="完成率(%)")
    packaging_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="出貨包裝完成率(%)")
    
    # 完工判斷
    can_complete = models.BooleanField(default=False, verbose_name="可完工")
    completion_threshold_met = models.BooleanField(default=False, verbose_name="達到完工閾值")
    
    # 最後更新資訊
    last_fillwork_update = models.DateTimeField(null=True, blank=True, verbose_name="最後填報更新時間")
    last_onsite_update = models.DateTimeField(null=True, blank=True, verbose_name="最後現場報工更新時間")
    last_process_update = models.DateTimeField(null=True, blank=True, verbose_name="最後工序更新時間")
    
    # 備註
    notes = models.TextField(verbose_name="備註", blank=True)
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    created_by = models.CharField(max_length=100, verbose_name="建立人員", default="system")

    class Meta:
        verbose_name = "派工單"
        verbose_name_plural = "派工單管理"
        db_table = "workorder_dispatch"
        ordering = ["-created_at"]
        unique_together = (("company_code", "order_number", "product_code"),)  # 公司代號+工單號碼+產品編號唯一
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['product_code']),
            models.Index(fields=['status']),
            models.Index(fields=['dispatch_date']),
        ]

    def __str__(self):
        return f"派工單 {self.order_number} - {self.product_code}"

    def clean(self):
        """資料驗證"""
        if self.planned_start_date and self.planned_end_date:
            if self.planned_start_date > self.planned_end_date:
                raise ValidationError(_('計劃開始日期不能晚於計劃完成日期'))

    def save(self, *args, **kwargs):
        """儲存前處理"""
        self.clean()
        super().save(*args, **kwargs)
    
    def update_all_statistics(self):
        """更新所有統計資料 - 委託給服務層"""
        from workorder.services.dispatch_statistics_service import DispatchStatisticsService
        return DispatchStatisticsService.update_all_statistics(self)
    
    
    
    
    
    
    

    


class WorkOrderDispatchProcess(models.Model):
    """
    派工單工序明細：記錄每個派工單的工序分配
    """
    workorder_dispatch_id = models.CharField(max_length=50, verbose_name="派工單ID")
    workorder_dispatch_name = models.CharField(max_length=200, verbose_name="派工單名稱")
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    step_order = models.IntegerField(verbose_name="工序順序")
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    
    # 派工分配資訊
    assigned_operator = models.CharField(max_length=100, blank=True, null=True, verbose_name="分配作業員")
    assigned_equipment = models.CharField(max_length=100, blank=True, null=True, verbose_name="分配設備")
    dispatch_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "待派工"),
            ("dispatched", "已派工"),
            ("in_progress", "進行中"),
            ("completed", "已完成"),
        ],
        default="pending",
        verbose_name="派工狀態"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "派工單工序"
        verbose_name_plural = "派工單工序明細"
        db_table = "workorder_dispatch_process"
        unique_together = (("workorder_dispatch_id", "step_order"),)
        ordering = ["workorder_dispatch_id", "step_order"]

    def __str__(self):
        return f"{self.workorder_dispatch_name} - {self.process_name}"


class DispatchHistory(models.Model):
    """
    派工歷史記錄：記錄每次派工操作的歷史
    """
    workorder_dispatch_id = models.CharField(max_length=50, verbose_name="派工單ID")
    workorder_dispatch_name = models.CharField(max_length=200, verbose_name="派工單名稱")
    action = models.CharField(max_length=50, verbose_name="操作類型")
    old_status = models.CharField(max_length=20, verbose_name="原狀態", null=True, blank=True)
    new_status = models.CharField(max_length=20, verbose_name="新狀態", null=True, blank=True)
    operator = models.CharField(max_length=100, verbose_name="操作人員")
    notes = models.TextField(verbose_name="備註", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="操作時間")

    class Meta:
        verbose_name = "派工歷史"
        verbose_name_plural = "派工歷史記錄"
        db_table = "workorder_dispatch_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.workorder_dispatch_name} - {self.action} - {self.created_at}" 