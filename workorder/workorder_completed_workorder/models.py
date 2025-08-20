"""
已完工工單管理子模組 - 資料模型
負責管理已完成工單的資料儲存、查詢和報表功能
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class CompletedWorkOrder(models.Model):
    """已完工工單主表"""
    
    # 基本識別資訊
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    order_number = models.CharField(max_length=50, verbose_name="工單號碼")
    product_code = models.CharField(max_length=50, verbose_name="產品編號")
    
    # 工單基本資訊
    product_name = models.CharField(max_length=200, verbose_name="產品名稱")
    order_quantity = models.IntegerField(verbose_name="訂單數量")
    completed_quantity = models.IntegerField(verbose_name="完工數量")
    defective_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    
    # 時間資訊
    start_date = models.DateField(verbose_name="開始日期")
    completion_date = models.DateField(verbose_name="完工日期")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    # 狀態資訊
    status = models.CharField(
        max_length=20,
        choices=[
            ('completed', '已完工'),
            ('archived', '已封存'),
        ],
        default='completed',
        verbose_name="狀態"
    )
    
    # 備註
    remarks = models.TextField(blank=True, null=True, verbose_name="備註")
    
    class Meta:
        verbose_name = "已完工工單"
        verbose_name_plural = "已完工工單"
        db_table = 'workorder_completed_workorder'
        unique_together = ['company_code', 'order_number', 'product_code']
        ordering = ['-completion_date', '-created_at']
    
    def __str__(self):
        return f"{self.company_code}-{self.order_number}-{self.product_code}"
    
    @property
    def completion_rate(self):
        """完工率"""
        if self.order_quantity > 0:
            return (self.completed_quantity / self.order_quantity) * 100
        return 0
    
    @property
    def defect_rate(self):
        """不良率"""
        if self.completed_quantity > 0:
            return (self.defective_quantity / self.completed_quantity) * 100
        return 0


class CompletedWorkOrderProcess(models.Model):
    """已完工工單工序明細"""
    
    completed_workorder = models.ForeignKey(
        CompletedWorkOrder,
        on_delete=models.CASCADE,
        related_name='processes',
        verbose_name="已完工工單"
    )
    
    # 工序資訊
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    process_sequence = models.IntegerField(verbose_name="工序順序")
    
    # 數量資訊
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    completed_quantity = models.IntegerField(verbose_name="完工數量")
    defective_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    
    # 時間資訊
    start_time = models.DateTimeField(verbose_name="開始時間")
    end_time = models.DateTimeField(verbose_name="結束時間")
    
    # 作業資訊
    operator_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="作業員")
    equipment_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="設備")
    
    # 備註
    remarks = models.TextField(blank=True, null=True, verbose_name="備註")
    
    class Meta:
        verbose_name = "已完工工單工序"
        verbose_name_plural = "已完工工單工序"
        db_table = 'workorder_completed_workorder_process'
        ordering = ['process_sequence']
    
    def __str__(self):
        return f"{self.completed_workorder} - {self.process_name}"
    
    @property
    def duration(self):
        """工序耗時（分鐘）"""
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            return duration.total_seconds() / 60
        return 0
    
    @property
    def completion_rate(self):
        """工序完工率"""
        if self.planned_quantity > 0:
            return (self.completed_quantity / self.planned_quantity) * 100
        return 0


class CompletedProductionReport(models.Model):
    """已完工生產報表"""
    
    completed_workorder = models.ForeignKey(
        CompletedWorkOrder,
        on_delete=models.CASCADE,
        related_name='production_reports',
        verbose_name="已完工工單"
    )
    
    # 報表資訊
    report_date = models.DateField(verbose_name="報表日期")
    report_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', '日報'),
            ('weekly', '週報'),
            ('monthly', '月報'),
            ('final', '完工報表'),
        ],
        verbose_name="報表類型"
    )
    
    # 生產數據
    total_production = models.IntegerField(verbose_name="總生產量")
    good_quantity = models.IntegerField(verbose_name="良品數量")
    defective_quantity = models.IntegerField(verbose_name="不良品數量")
    
    # 效率指標
    production_efficiency = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="生產效率(%)"
    )
    quality_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="品質率(%)"
    )
    
    # 時間資訊
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    # 備註
    remarks = models.TextField(blank=True, null=True, verbose_name="備註")
    
    class Meta:
        verbose_name = "已完工生產報表"
        verbose_name_plural = "已完工生產報表"
        db_table = 'workorder_completed_production_report'
        ordering = ['-report_date', '-created_at']
    
    def __str__(self):
        return f"{self.completed_workorder} - {self.report_type} - {self.report_date}"


class AutoAllocationSettings(models.Model):
    """自動分配設定"""
    
    # 基本設定
    setting_name = models.CharField(max_length=100, unique=True, verbose_name="設定名稱")
    is_active = models.BooleanField(default=True, verbose_name="啟用狀態")
    
    # 分配規則
    allocation_type = models.CharField(
        max_length=20,
        choices=[
            ('operator', '作業員分配'),
            ('equipment', '設備分配'),
            ('both', '作業員和設備分配'),
        ],
        verbose_name="分配類型"
    )
    
    # 優先級設定
    priority_rules = models.JSONField(default=dict, verbose_name="優先級規則")
    
    # 時間設定
    check_interval = models.IntegerField(default=5, verbose_name="檢查間隔(分鐘)")
    last_check_time = models.DateTimeField(null=True, blank=True, verbose_name="最後檢查時間")
    
    # 建立資訊
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_auto_allocation_settings',
        verbose_name="建立者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    # 備註
    remarks = models.TextField(blank=True, null=True, verbose_name="備註")
    
    class Meta:
        verbose_name = "自動分配設定"
        verbose_name_plural = "自動分配設定"
        db_table = 'workorder_auto_allocation_settings'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.setting_name


class AutoAllocationLog(models.Model):
    """自動分配日誌"""
    
    # 基本資訊
    allocation_settings = models.ForeignKey(
        AutoAllocationSettings,
        on_delete=models.CASCADE,
        related_name='allocation_logs',
        verbose_name="分配設定"
    )
    
    # 分配結果
    allocation_type = models.CharField(
        max_length=20,
        choices=[
            ('operator', '作業員分配'),
            ('equipment', '設備分配'),
            ('both', '作業員和設備分配'),
        ],
        verbose_name="分配類型"
    )
    
    # 分配對象
    target_workorder = models.CharField(max_length=100, verbose_name="目標工單")
    assigned_operator = models.CharField(max_length=100, blank=True, null=True, verbose_name="分配作業員")
    assigned_equipment = models.CharField(max_length=100, blank=True, null=True, verbose_name="分配設備")
    
    # 分配結果
    allocation_status = models.CharField(
        max_length=20,
        choices=[
            ('success', '成功'),
            ('failed', '失敗'),
            ('partial', '部分成功'),
        ],
        verbose_name="分配狀態"
    )
    
    # 錯誤資訊
    error_message = models.TextField(blank=True, null=True, verbose_name="錯誤訊息")
    
    # 時間資訊
    allocation_time = models.DateTimeField(auto_now_add=True, verbose_name="分配時間")
    
    # 備註
    remarks = models.TextField(blank=True, null=True, verbose_name="備註")
    
    class Meta:
        verbose_name = "自動分配日誌"
        verbose_name_plural = "自動分配日誌"
        db_table = 'workorder_auto_allocation_log'
        ordering = ['-allocation_time']
    
    def __str__(self):
        return f"{self.allocation_settings} - {self.target_workorder} - {self.allocation_status}" 