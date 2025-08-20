"""
MES 工單作業子模組 - 資料模型定義
負責 MES 工單作業的管理功能，包括作業主表、作業明細、作業歷史
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class MesWorkorderOperation(models.Model):
    """
    MES 工單作業主表：記錄 MES 工單作業的基本資訊
    支援多公司架構，唯一識別：公司代號 + 工單號碼 + 產品編號
    """
    
    # 作業狀態選擇
    STATUS_CHOICES = [
        ('pending', '待作業'),
        ('in_progress', '作業中'),
        ('paused', '暫停'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    
    # 作業類型選擇
    OPERATION_TYPE_CHOICES = [
        ('production', '生產作業'),
        ('inspection', '檢驗作業'),
        ('packaging', '包裝作業'),
        ('maintenance', '維護作業'),
        ('other', '其他作業'),
    ]
    
    # 基本識別資訊（多公司架構）
    company_code = models.CharField(
        max_length=10, 
        verbose_name="公司代號",
        help_text="公司代號，例如：01、02、03"
    )
    company_name = models.CharField(
        max_length=100, 
        verbose_name="公司名稱",
        help_text="公司名稱"
    )
    
    # 工單相關資訊
    workorder_number = models.CharField(
        max_length=50, 
        verbose_name="工單號碼",
        help_text="工單號碼",
        db_index=True
    )
    product_code = models.CharField(
        max_length=100, 
        verbose_name="產品編號",
        help_text="產品編號",
        db_index=True
    )
    product_name = models.CharField(
        max_length=200, 
        verbose_name="產品名稱",
        help_text="產品名稱",
        null=True, 
        blank=True
    )
    
    # 作業資訊
    operation_type = models.CharField(
        max_length=20,
        choices=OPERATION_TYPE_CHOICES,
        default='production',
        verbose_name="作業類型",
        help_text="作業類型"
    )
    operation_name = models.CharField(
        max_length=100, 
        verbose_name="作業名稱",
        help_text="作業名稱"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="作業狀態",
        help_text="作業狀態"
    )
    
    # 數量資訊
    planned_quantity = models.PositiveIntegerField(
        verbose_name="計劃數量",
        help_text="計劃作業數量",
        default=0
    )
    completed_quantity = models.PositiveIntegerField(
        verbose_name="完成數量",
        help_text="已完成作業數量",
        default=0
    )
    defect_quantity = models.PositiveIntegerField(
        verbose_name="不良品數量",
        help_text="不良品數量",
        default=0
    )
    
    # 時間資訊
    planned_start_date = models.DateField(
        verbose_name="計劃開始日期",
        help_text="計劃開始日期",
        null=True, 
        blank=True
    )
    planned_end_date = models.DateField(
        verbose_name="計劃完成日期",
        help_text="計劃完成日期",
        null=True, 
        blank=True
    )
    actual_start_date = models.DateTimeField(
        verbose_name="實際開始時間",
        help_text="實際開始時間",
        null=True, 
        blank=True
    )
    actual_end_date = models.DateTimeField(
        verbose_name="實際完成時間",
        help_text="實際完成時間",
        null=True, 
        blank=True
    )
    
    # 人員和設備資訊
    assigned_operator = models.CharField(
        max_length=100, 
        verbose_name="分配作業員",
        help_text="分配作業員",
        null=True, 
        blank=True
    )
    assigned_equipment = models.CharField(
        max_length=100, 
        verbose_name="分配設備",
        help_text="分配設備",
        null=True, 
        blank=True
    )
    
    # 備註和說明
    notes = models.TextField(
        verbose_name="備註",
        help_text="作業備註",
        null=True, 
        blank=True
    )
    
    # 系統資訊
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
    created_by = models.CharField(
        max_length=100, 
        verbose_name="建立者",
        help_text="建立者",
        null=True, 
        blank=True
    )
    updated_by = models.CharField(
        max_length=100, 
        verbose_name="更新者",
        help_text="更新者",
        null=True, 
        blank=True
    )

    class Meta:
        verbose_name = "MES 工單作業"
        verbose_name_plural = "MES 工單作業"
        db_table = 'mes_workorder_operation'
        unique_together = (("company_code", "workorder_number", "product_code", "operation_name"),)
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company_code', 'workorder_number']),
            models.Index(fields=['status']),
            models.Index(fields=['operation_type']),
            models.Index(fields=['planned_start_date']),
        ]

    def __str__(self):
        """字串表示"""
        formatted_company_code = self.company_code.zfill(2) if self.company_code and self.company_code.isdigit() else self.company_code
        return f"[{formatted_company_code}] {self.workorder_number} - {self.operation_name}"

    def get_completion_rate(self):
        """取得完成率"""
        if self.planned_quantity == 0:
            return 0.0
        return (self.completed_quantity / self.planned_quantity) * 100

    def get_remaining_quantity(self):
        """取得剩餘數量"""
        return max(0, self.planned_quantity - self.completed_quantity)

    def is_completed(self):
        """檢查是否已完成"""
        return self.status == 'completed'

    def is_in_progress(self):
        """檢查是否作業中"""
        return self.status == 'in_progress'

    def can_start(self):
        """檢查是否可以開始作業"""
        return self.status == 'pending'

    def can_complete(self):
        """檢查是否可以完成作業"""
        return self.status in ['in_progress', 'paused'] and self.completed_quantity >= self.planned_quantity


class MesWorkorderOperationDetail(models.Model):
    """
    MES 工單作業明細：記錄 MES 工單作業的詳細資訊
    包含每個作業步驟的詳細記錄
    """
    
    # 明細類型選擇
    DETAIL_TYPE_CHOICES = [
        ('process', '工序'),
        ('material', '物料'),
        ('equipment', '設備'),
        ('quality', '品質'),
        ('other', '其他'),
    ]
    
    # 關聯到主表
    operation = models.ForeignKey(
        MesWorkorderOperation,
        on_delete=models.CASCADE,
        verbose_name="作業主表",
        help_text="關聯的作業主表",
        related_name='details'
    )
    
    # 明細資訊
    detail_type = models.CharField(
        max_length=20,
        choices=DETAIL_TYPE_CHOICES,
        default='process',
        verbose_name="明細類型",
        help_text="明細類型"
    )
    detail_name = models.CharField(
        max_length=100, 
        verbose_name="明細名稱",
        help_text="明細名稱"
    )
    detail_description = models.TextField(
        verbose_name="明細說明",
        help_text="明細說明",
        null=True, 
        blank=True
    )
    
    # 數量資訊
    planned_quantity = models.PositiveIntegerField(
        verbose_name="計劃數量",
        help_text="計劃數量",
        default=0
    )
    actual_quantity = models.PositiveIntegerField(
        verbose_name="實際數量",
        help_text="實際數量",
        default=0
    )
    
    # 時間資訊
    start_time = models.DateTimeField(
        verbose_name="開始時間",
        help_text="開始時間",
        null=True, 
        blank=True
    )
    end_time = models.DateTimeField(
        verbose_name="結束時間",
        help_text="結束時間",
        null=True, 
        blank=True
    )
    
    # 狀態資訊
    is_completed = models.BooleanField(
        default=False,
        verbose_name="是否完成",
        help_text="是否完成"
    )
    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="完成率",
        help_text="完成率（百分比）",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # 備註
    notes = models.TextField(
        verbose_name="備註",
        help_text="明細備註",
        null=True, 
        blank=True
    )
    
    # 系統資訊
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
        verbose_name = "MES 工單作業明細"
        verbose_name_plural = "MES 工單作業明細"
        db_table = 'mes_workorder_operation_detail'
        ordering = ['operation', 'created_at']
        indexes = [
            models.Index(fields=['operation', 'detail_type']),
            models.Index(fields=['is_completed']),
        ]

    def __str__(self):
        """字串表示"""
        return f"{self.operation} - {self.detail_name}"

    def get_duration(self):
        """取得作業時長（分鐘）"""
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            return duration.total_seconds() / 60
        return 0

    def update_completion_rate(self):
        """更新完成率"""
        if self.planned_quantity > 0:
            self.completion_rate = (self.actual_quantity / self.planned_quantity) * 100
        else:
            self.completion_rate = 0
        self.save(update_fields=['completion_rate'])


class MesWorkorderOperationHistory(models.Model):
    """
    MES 工單作業歷史：記錄 MES 工單作業的歷史記錄
    包含所有作業變更的歷史追蹤
    """
    
    # 歷史類型選擇
    HISTORY_TYPE_CHOICES = [
        ('created', '建立'),
        ('updated', '更新'),
        ('started', '開始'),
        ('paused', '暫停'),
        ('resumed', '重啟'),
        ('completed', '完成'),
        ('cancelled', '取消'),
        ('deleted', '刪除'),
    ]
    
    # 關聯到主表
    operation = models.ForeignKey(
        MesWorkorderOperation,
        on_delete=models.CASCADE,
        verbose_name="作業主表",
        help_text="關聯的作業主表",
        related_name='history'
    )
    
    # 歷史資訊
    history_type = models.CharField(
        max_length=20,
        choices=HISTORY_TYPE_CHOICES,
        verbose_name="歷史類型",
        help_text="歷史類型"
    )
    history_description = models.TextField(
        verbose_name="歷史說明",
        help_text="歷史說明"
    )
    
    # 變更前後資訊
    old_values = models.JSONField(
        verbose_name="變更前值",
        help_text="變更前的值（JSON格式）",
        null=True, 
        blank=True
    )
    new_values = models.JSONField(
        verbose_name="變更後值",
        help_text="變更後的值（JSON格式）",
        null=True, 
        blank=True
    )
    
    # 操作資訊
    operator = models.CharField(
        max_length=100, 
        verbose_name="操作者",
        help_text="操作者",
        null=True, 
        blank=True
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="IP位址",
        help_text="操作者IP位址",
        null=True, 
        blank=True
    )
    
    # 系統資訊
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="建立時間",
        help_text="建立時間"
    )

    class Meta:
        verbose_name = "MES 工單作業歷史"
        verbose_name_plural = "MES 工單作業歷史"
        db_table = 'mes_workorder_operation_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['operation', 'history_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['operator']),
        ]

    def __str__(self):
        """字串表示"""
        return f"{self.operation} - {self.get_history_type_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def get_changes_summary(self):
        """取得變更摘要"""
        if self.old_values and self.new_values:
            changes = []
            for key in set(self.old_values.keys()) | set(self.new_values.keys()):
                old_val = self.old_values.get(key)
                new_val = self.new_values.get(key)
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} → {new_val}")
            return "; ".join(changes)
        return self.history_description 