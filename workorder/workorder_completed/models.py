"""
已完工工單管理子模組 - 模型定義
負責已完工工單的管理功能，包括完工記錄、工序統計等
"""

from django.db import models
from django.utils import timezone


class WorkOrderCompleted(models.Model):
    """
    已完工工單表：專門記錄已完工的工單
    只做記錄，不會頻繁修改數據
    """
    # 關聯工單
    workorder = models.OneToOneField(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        verbose_name="工單",
        related_name="completed_record"
    )
    
    # 完工資訊
    completion_date = models.DateTimeField(verbose_name="完工時間", auto_now_add=True)
    completion_method = models.CharField(
        max_length=20,
        choices=[
            ("quantity_reached", "數量達標"),
            ("manual_completion", "手動完工"),
            ("auto_completion", "自動完工"),
        ],
        verbose_name="完工方式"
    )
    
    # 完工統計（累計數據，不會頻繁修改）
    total_work_quantity = models.IntegerField(verbose_name="總合格品數量", default=0)
    total_defect_quantity = models.IntegerField(verbose_name="總不良品數量", default=0)
    total_production_days = models.IntegerField(verbose_name="總生產天數", default=0)
    
    # 工序完工統計（JSON格式記錄每個工序的完工情況）
    process_completion_summary = models.TextField(
        verbose_name="工序完工摘要",
        blank=True,
        help_text="JSON格式記錄每個工序的完工統計"
    )
    
    # 完工確認
    confirmed_by = models.CharField(max_length=100, verbose_name="完工確認人員", null=True, blank=True)
    confirmed_at = models.DateTimeField(verbose_name="完工確認時間", null=True, blank=True)
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "已完工工單"
        verbose_name_plural = "已完工工單"
        db_table = "workorder_completed"
        ordering = ["-completion_date"]

    def __str__(self):
        return f"已完工：{self.workorder.order_number}"


class WorkOrderCompletedProcess(models.Model):
    """
    已完工工單工序統計：記錄每個工序的完工統計
    只做記錄，不會頻繁修改
    """
    workorder_completed = models.ForeignKey(
        WorkOrderCompleted,
        on_delete=models.CASCADE,
        verbose_name="已完工工單",
        related_name="completed_processes"
    )
    
    # 工序資訊
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    step_order = models.IntegerField(verbose_name="工序順序")
    
    # 完工統計
    total_work_quantity = models.IntegerField(verbose_name="總合格品數量", default=0)
    total_defect_quantity = models.IntegerField(verbose_name="總不良品數量", default=0)
    report_count = models.IntegerField(verbose_name="報工次數", default=0)
    
    # 時間統計
    first_report_date = models.DateField(verbose_name="首次報工日期", null=True, blank=True)
    last_report_date = models.DateField(verbose_name="最後報工日期", null=True, blank=True)
    total_work_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="總工時", default=0)
    
    # 作業員和設備統計
    operators_used = models.TextField(verbose_name="使用作業員", blank=True, help_text="JSON格式記錄使用的作業員")
    equipments_used = models.TextField(verbose_name="使用設備", blank=True, help_text="JSON格式記錄使用的設備")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    class Meta:
        verbose_name = "已完工工序統計"
        verbose_name_plural = "已完工工序統計"
        db_table = "workorder_completed_process"
        unique_together = (("workorder_completed", "process_name"),)
        ordering = ["workorder_completed", "step_order"]

    def __str__(self):
        return f"{self.workorder_completed.workorder.order_number} - {self.process_name} 統計" 