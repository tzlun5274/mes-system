"""
派工單管理子模組 - 模型定義
負責派工單的管理功能，包括派工單主表、工序明細等
"""

from django.db import models
from django.utils import timezone


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

    # 關聯工單
    work_order = models.ForeignKey(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        verbose_name="工單",
        related_name="dispatches"
    )
    
    # 派工相關資訊
    operator = models.CharField(max_length=100, verbose_name="作業員", null=True, blank=True)
    process = models.CharField(max_length=100, verbose_name="工序")
    planned_quantity = models.PositiveIntegerField(verbose_name="計劃數量")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="派工狀態")
    
    # 派工相關資訊
    dispatch_date = models.DateField(verbose_name="派工日期", null=True, blank=True)
    planned_start_date = models.DateField(verbose_name="計劃開始日期", null=True, blank=True)
    planned_end_date = models.DateField(verbose_name="計劃完成日期", null=True, blank=True)
    
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

    def __str__(self):
        return f"派工單 {self.work_order.order_number} - {self.process}"


class WorkOrderDispatchProcess(models.Model):
    """
    派工單工序明細：記錄每個派工單的工序分配
    """
    workorder_dispatch = models.ForeignKey(
        WorkOrderDispatch,
        on_delete=models.CASCADE,
        verbose_name="派工單",
        related_name="dispatch_processes"
    )
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
        unique_together = (("workorder_dispatch", "step_order"),)
        ordering = ["workorder_dispatch", "step_order"]

    def __str__(self):
        return f"{self.workorder_dispatch.order_number} - {self.process_name}" 