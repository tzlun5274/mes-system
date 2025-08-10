"""
統一補登報工資料表模型
此模組提供統一的補登報工功能，完全獨立於現有系統，不會影響任何現有功能。
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class UnifiedWorkReport(models.Model):
    """
    統一補登報工資料表
    提供統一的補登報工功能，支援完整的報工資料記錄與核准流程
    """
    
    # 核准狀態選擇
    APPROVAL_STATUS_CHOICES = [
        ('pending', '待核准'),
        ('approved', '已核准'),
        ('rejected', '已駁回'),
        ('cancelled', '已取消'),
    ]
    
    # ==================== 基本資訊欄位 ====================
    operator = models.CharField(
        max_length=100, 
        verbose_name="作業員",
        help_text="作業員姓名（純文字輸入）"
    )
    company_code = models.CharField(
        max_length=10, 
        verbose_name="公司代號",
        help_text="公司代號，例如：01、02、03"
    )
    
    # ==================== 工單相關欄位 ====================
    workorder = models.ForeignKey(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        verbose_name="工單號碼",
        help_text="關聯到工單管理系統的工單"
    )
    original_workorder_number = models.CharField(
        max_length=50,
        verbose_name="原始工單號碼",
        help_text="原始工單號碼（字串格式）"
    )
    product_id = models.CharField(
        max_length=100,
        verbose_name="產品編號",
        help_text="產品編號"
    )
    planned_quantity = models.IntegerField(
        verbose_name="工單預設生產數量",
        help_text="工單預設的生產數量"
    )
    
    # ==================== 製程相關欄位 ====================
    process = models.ForeignKey(
        'process.ProcessName',
        on_delete=models.CASCADE,
        verbose_name="工序",
        help_text="關聯到製程管理的工序"
    )
    operation = models.CharField(
        max_length=100,
        verbose_name="工序名稱",
        help_text="工序名稱"
    )
    equipment = models.ForeignKey(
        'equip.Equipment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="使用的設備",
        help_text="選擇使用的設備"
    )
    
    # ==================== 時間相關欄位 ====================
    work_date = models.DateField(
        verbose_name="日期",
        help_text="工作日期"
    )
    start_time = models.TimeField(
        verbose_name="開始時間",
        help_text="工作開始時間"
    )
    end_time = models.TimeField(
        verbose_name="結束時間",
        help_text="工作結束時間"
    )
    
    # ==================== 休息時間相關欄位 ====================
    has_break = models.BooleanField(
        default=False,
        verbose_name="是否有休息時間",
        help_text="是否有休息時間"
    )
    break_start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="休息開始時間",
        help_text="休息開始時間"
    )
    break_end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="休息結束時間",
        help_text="休息結束時間"
    )
    break_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="休息時數",
        help_text="休息時數（小時）"
    )
    
    # ==================== 工時計算欄位 ====================
    work_hours_calculated = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="工作時數",
        help_text="計算得出的工作時數（小時）"
    )
    overtime_hours_calculated = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="加班時數",
        help_text="計算得出的加班時數（小時）"
    )
    
    # ==================== 數量相關欄位 ====================
    work_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="工作數量",
        help_text="工作數量（良品）"
    )
    defect_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="不良品數量",
        help_text="不良品數量"
    )
    
    # ==================== 狀態欄位 ====================
    is_completed = models.BooleanField(
        default=False,
        verbose_name="是否已完工",
        help_text="是否已完工"
    )
    
    # ==================== 核准相關欄位 ====================
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending',
        verbose_name="核准狀態",
        help_text="核准狀態"
    )
    approved_by = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="核准人員",
        help_text="核准人員姓名"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="核准時間",
        help_text="核准時間"
    )
    approval_remarks = models.TextField(
        blank=True,
        verbose_name="核准備註",
        help_text="核准備註"
    )
    
    # ==================== 駁回相關欄位 ====================
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="駁回原因",
        help_text="駁回原因"
    )
    rejected_by = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="駁回人員",
        help_text="駁回人員姓名"
    )
    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="駁回時間",
        help_text="駁回時間"
    )
    
    # ==================== 備註欄位 ====================
    remarks = models.TextField(
        blank=True,
        verbose_name="備註",
        help_text="一般備註"
    )
    abnormal_notes = models.TextField(
        blank=True,
        verbose_name="異常記錄",
        help_text="異常記錄"
    )
    
    # ==================== 系統欄位 ====================
    created_by = models.CharField(
        max_length=100,
        verbose_name="建立人員",
        help_text="建立人員姓名"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="建立時間",
        help_text="建立時間"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新時間",
        help_text="更新時間"
    )
    
    class Meta:
        verbose_name = "統一補登報工"
        verbose_name_plural = "統一補登報工管理"
        db_table = 'unified_work_report'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['operator']),
            models.Index(fields=['company_code']),
            models.Index(fields=['work_date']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['workorder']),
            models.Index(fields=['process']),
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ("can_view_unified_work_report", "可以查看統一補登報工"),
            ("can_add_unified_work_report", "可以新增統一補登報工"),
            ("can_edit_unified_work_report", "可以編輯統一補登報工"),
            ("can_delete_unified_work_report", "可以刪除統一補登報工"),
            ("can_approve_unified_work_report", "可以核准統一補登報工"),
            ("can_reject_unified_work_report", "可以駁回統一補登報工"),
        ]
    
    def __str__(self):
        return f"[{self.company_code}] {self.operator} - {self.original_workorder_number} - {self.work_date}"
    
    def save(self, *args, **kwargs):
        """儲存時自動計算工時"""
        self._calculate_work_hours()
        super().save(*args, **kwargs)
    
    def _calculate_work_hours(self):
        """計算工作時數和加班時數"""
        try:
            if self.start_time and self.end_time:
                # 計算總工作時間
                from datetime import datetime, timedelta
                
                # 建立完整的日期時間
                start_datetime = datetime.combine(self.work_date, self.start_time)
                end_datetime = datetime.combine(self.work_date, self.end_time)
                
                # 如果結束時間小於開始時間，表示跨日
                if end_datetime < start_datetime:
                    end_datetime += timedelta(days=1)
                
                # 計算總工作時間（小時）
                total_work_time = end_datetime - start_datetime
                total_hours = total_work_time.total_seconds() / 3600
                
                # 扣除休息時間
                if self.has_break and self.break_start_time and self.break_end_time:
                    break_start = datetime.combine(self.work_date, self.break_start_time)
                    break_end = datetime.combine(self.work_date, self.break_end_time)
                    
                    if break_end < break_start:
                        break_end += timedelta(days=1)
                    
                    break_duration = break_end - break_start
                    break_hours = break_duration.total_seconds() / 3600
                    self.break_hours = Decimal(str(round(break_hours, 2)))
                    
                    # 扣除休息時間
                    total_hours -= break_hours
                else:
                    self.break_hours = Decimal('0.00')
                
                # 假設正常工時為8小時，超過部分為加班
                normal_hours = 8.0
                if total_hours > normal_hours:
                    self.work_hours_calculated = Decimal(str(round(normal_hours, 2)))
                    self.overtime_hours_calculated = Decimal(str(round(total_hours - normal_hours, 2)))
                else:
                    self.work_hours_calculated = Decimal(str(round(total_hours, 2)))
                    self.overtime_hours_calculated = Decimal('0.00')
            else:
                self.work_hours_calculated = Decimal('0.00')
                self.overtime_hours_calculated = Decimal('0.00')
                self.break_hours = Decimal('0.00')
                
        except Exception as e:
            logger.error(f"計算工時時發生錯誤: {e}")
            self.work_hours_calculated = Decimal('0.00')
            self.overtime_hours_calculated = Decimal('0.00')
            self.break_hours = Decimal('0.00')
    
    @property
    def total_quantity(self):
        """總數量（良品 + 不良品）"""
        return self.work_quantity + self.defect_quantity
    
    @property
    def total_hours(self):
        """總工時（正常工時 + 加班時數）"""
        return self.work_hours_calculated + self.overtime_hours_calculated
    
    @property
    def approval_status_display(self):
        """核准狀態顯示文字"""
        return dict(self.APPROVAL_STATUS_CHOICES).get(self.approval_status, self.approval_status)
    
    def approve(self, approved_by, remarks=""):
        """核准報工"""
        self.approval_status = 'approved'
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.approval_remarks = remarks
        self.save()
    
    def reject(self, rejected_by, reason):
        """駁回報工"""
        self.approval_status = 'rejected'
        self.rejected_by = rejected_by
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def cancel(self):
        """取消報工"""
        self.approval_status = 'cancelled'
        self.save()


class UnifiedWorkReportLog(models.Model):
    """
    統一補登報工操作日誌
    記錄所有對統一補登報工的操作歷史
    """
    
    # 操作類型選擇
    ACTION_CHOICES = [
        ('created', '建立'),
        ('updated', '更新'),
        ('deleted', '刪除'),
        ('approved', '核准'),
        ('rejected', '駁回'),
        ('cancelled', '取消'),
    ]
    
    work_report = models.ForeignKey(
        UnifiedWorkReport,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="統一補登報工"
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name="操作類型"
    )
    operator = models.CharField(
        max_length=100,
        verbose_name="操作人員"
    )
    remarks = models.TextField(
        blank=True,
        verbose_name="操作備註"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="操作時間"
    )
    
    class Meta:
        verbose_name = "統一補登報工操作日誌"
        verbose_name_plural = "統一補登報工操作日誌"
        db_table = 'unified_work_report_log'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.work_report} - {self.get_action_display()} - {self.operator}"
