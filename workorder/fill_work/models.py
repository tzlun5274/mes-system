"""
填報作業管理子模組 - 模型定義
負責填報作業功能，包括作業員填報、SMT填報等
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal


class FillWork(models.Model):
    """
    統一填報作業記錄模型 (Fill Work Model)
    支援所有類型的填報作業，包括一般作業員和SMT作業員
    """

    # 基本資訊欄位
    operator = models.CharField(
        max_length=100,
        verbose_name="作業員",
        help_text="作業員姓名",
        default="",
    )
    
    company_name = models.CharField(
        max_length=100,
        verbose_name="公司名稱",
        help_text="公司名稱",
        default="",
    )

    # 工單相關欄位
    workorder = models.ForeignKey(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        verbose_name="工單號碼",
        help_text="請選擇工單號碼，或透過產品編號自動帶出",
        null=True,
        blank=True,
    )
    
    product_id = models.CharField(
        max_length=100,
        verbose_name="產品編號",
        help_text="請選擇產品編號，將自動帶出相關工單",
        default="",
    )
    
    planned_quantity = models.IntegerField(
        verbose_name="工單預設生產數量",
        help_text="此為工單規劃的總生產數量，不可修改",
        default=0,
    )

    # 製程相關欄位
    process = models.ForeignKey(
        "process.ProcessName",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="工序",
        help_text="請選擇此次填報的工序",
    )
    
    operation = models.CharField(
        max_length=100,
        verbose_name="工序名稱",
        help_text="工序名稱",
        blank=True,
        null=True,
    )
    
    equipment = models.ForeignKey(
        'equip.Equipment',
        on_delete=models.CASCADE,
        verbose_name="使用的設備",
        help_text="請選擇使用的設備（可選）",
        null=True,
        blank=True,
    )

    # 時間相關欄位
    work_date = models.DateField(
        verbose_name="工作日期",
        help_text="請選擇填報作業的日期",
        default=timezone.now,
    )
    
    start_time = models.TimeField(
        verbose_name="開始時間",
        help_text="請選擇填報作業的開始時間",
        null=True,
        blank=True,
    )
    
    end_time = models.TimeField(
        verbose_name="結束時間",
        help_text="請選擇填報作業的結束時間",
        null=True,
        blank=True,
    )

    # 休息時間相關欄位
    has_break = models.BooleanField(
        verbose_name="是否有休息時間",
        default=False,
        help_text="是否有休息時間",
    )
    
    break_start_time = models.TimeField(
        verbose_name="休息開始時間",
        help_text="休息開始時間",
        null=True,
        blank=True,
    )
    
    break_end_time = models.TimeField(
        verbose_name="休息結束時間",
        help_text="休息結束時間",
        null=True,
        blank=True,
    )
    
    break_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="休息時數",
        help_text="休息時數（小時）",
        default=Decimal('0.00'),
    )

    # 工時計算欄位
    work_hours_calculated = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="工作時數",
        help_text="工作時數（小時）",
        default=Decimal('0.00'),
    )
    
    overtime_hours_calculated = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="加班時數",
        help_text="加班時數（小時）",
        default=Decimal('0.00'),
    )

    # 數量相關欄位
    work_quantity = models.IntegerField(
        verbose_name="工作數量",
        help_text="請輸入此次填報的工作數量",
        default=0,
    )
    
    defect_quantity = models.IntegerField(
        verbose_name="不良品數量",
        help_text="請輸入此次填報的不良品數量",
        default=0,
    )

    # 狀態欄位
    is_completed = models.BooleanField(
        verbose_name="是否已完工",
        default=False,
        help_text="是否已完工",
    )

    # 核准相關欄位
    approval_status = models.CharField(
        max_length=20,
        verbose_name="核准狀態",
        choices=[
            ('pending', '待核准'),
            ('approved', '已核准'),
            ('rejected', '已駁回'),
        ],
        default='pending',
        help_text="核准狀態",
    )
    
    approved_by = models.CharField(
        max_length=100,
        verbose_name="核准人員",
        help_text="核准人員姓名",
        blank=True,
        null=True,
    )
    
    approved_at = models.DateTimeField(
        verbose_name="核准時間",
        help_text="核准時間",
        null=True,
        blank=True,
    )
    
    approval_remarks = models.TextField(
        verbose_name="核准備註",
        help_text="核准備註",
        blank=True,
        null=True,
    )

    # 駁回相關欄位
    rejection_reason = models.TextField(
        verbose_name="駁回原因",
        help_text="駁回原因",
        blank=True,
        null=True,
    )
    
    rejected_by = models.CharField(
        max_length=100,
        verbose_name="駁回人員",
        help_text="駁回人員姓名",
        blank=True,
        null=True,
    )
    
    rejected_at = models.DateTimeField(
        verbose_name="駁回時間",
        help_text="駁回時間",
        null=True,
        blank=True,
    )

    # 備註欄位
    remarks = models.TextField(
        verbose_name="備註",
        help_text="請輸入填報作業的相關備註",
        blank=True,
        null=True,
    )
    
    abnormal_notes = models.TextField(
        verbose_name="異常記錄",
        help_text="請記錄填報作業中的異常情況",
        blank=True,
        null=True,
    )

    # 系統欄位
    created_by = models.CharField(
        max_length=100,
        verbose_name="建立人員",
        help_text="建立人員姓名",
        default="",
    )
    
    created_at = models.DateTimeField(
        verbose_name="建立時間",
        auto_now_add=True,
    )
    
    updated_at = models.DateTimeField(
        verbose_name="更新時間",
        auto_now=True,
    )

    class Meta:
        verbose_name = "填報作業"
        verbose_name_plural = "填報作業"
        db_table = 'fill_work'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['operator']),
            models.Index(fields=['work_date']),
            models.Index(fields=['workorder']),
            models.Index(fields=['process']),
            models.Index(fields=['equipment']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['is_completed']),
        ]

    def __str__(self):
        return f"{self.operator} - {self.work_date} - {self.operation or '未知工序'}"

    def get_total_quantity(self):
        """取得總數量（工作數量+不良品數量）"""
        return self.work_quantity + self.defect_quantity

    def get_work_duration(self):
        """取得工作時長（小時）"""
        if self.start_time and self.end_time:
            # 將 TimeField 轉換為 datetime 進行計算
            from datetime import datetime, date
            start_dt = datetime.combine(date.today(), self.start_time)
            end_dt = datetime.combine(date.today(), self.end_time)
            
            # 如果結束時間小於開始時間，表示跨日
            if end_dt < start_dt:
                end_dt = datetime.combine(date.today() + timezone.timedelta(days=1), self.end_time)
            
            duration = end_dt - start_dt
            return duration.total_seconds() / 3600
        return 0

    def calculate_work_hours(self):
        """計算工作時數（扣除休息時間）"""
        total_duration = self.get_work_duration()
        break_hours = float(self.break_hours) if self.break_hours else 0
        return max(0, total_duration - break_hours)

    def save(self, *args, **kwargs):
        """儲存時自動計算工作時數"""
        if self.start_time and self.end_time:
            self.work_hours_calculated = Decimal(str(self.calculate_work_hours()))
        super().save(*args, **kwargs) 