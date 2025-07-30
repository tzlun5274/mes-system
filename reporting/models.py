"""
報表模組資料模型
提供工作報表、工單報表、工時報表等核心報表功能的資料結構
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import logging

# 報表類型選擇
REPORT_TYPE_CHOICES = [
    ('WORK_REPORT', '工作報表'),
    ('WORKORDER_REPORT', '工單報表'),
    ('WORK_HOUR_REPORT', '工時報表'),
]

# 報表格式選擇
REPORT_FORMAT_CHOICES = [
    ('EXCEL', 'Excel'),
    ('CSV', 'CSV'),
    ('PDF', 'PDF'),
]

# 日期範圍選擇
DATE_RANGE_CHOICES = [
    ('TODAY', '今日'),
    ('YESTERDAY', '昨日'),
    ('THIS_WEEK', '本週'),
    ('LAST_WEEK', '上週'),
    ('THIS_MONTH', '本月'),
    ('LAST_MONTH', '上月'),
    ('CUSTOM', '自訂範圍'),
]


class BaseReportModel(models.Model):
    """報表基礎模型"""
    
    # 報表基本資訊
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES, verbose_name="報表類型")
    report_date = models.DateField(verbose_name="報表日期")
    report_period_start = models.DateField(verbose_name="報表期間開始", null=True, blank=True)
    report_period_end = models.DateField(verbose_name="報表期間結束", null=True, blank=True)
    
    # 數據來源標示
    data_source = models.CharField(max_length=100, verbose_name="數據來源", default="原始報工數據")
    calculation_method = models.CharField(max_length=100, verbose_name="計算方法", default="無或按工時分配")
    
    # 系統資訊
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    created_by = models.CharField(max_length=100, verbose_name="建立者", default="系統")

    class Meta:
        abstract = True
        ordering = ['-report_date']
        verbose_name = "報表基礎模型"
        verbose_name_plural = "報表基礎模型"


class WorkReport(BaseReportModel):
    """工作報表模型"""
    
    # 作業員資訊
    operator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="作業員")
    work_order_no = models.CharField(max_length=100, verbose_name="工單號")
    product_sn = models.CharField(max_length=100, null=True, blank=True, verbose_name="產品編號")
    process = models.CharField(max_length=100, verbose_name="工序")
    
    # 時間資訊
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="開始時間")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="結束時間")
    
    # 數量資訊
    work_quantity = models.IntegerField(default=0, verbose_name="工作數量")
    defect_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    
    # 異常紀錄
    abnormal_notes = models.TextField(null=True, blank=True, verbose_name="異常紀錄")

    class Meta:
        verbose_name = "工作報表"
        verbose_name_plural = "工作報表"
        db_table = 'reporting_work_report'
        indexes = [
            models.Index(fields=['report_date']),
            models.Index(fields=['operator']),
            models.Index(fields=['work_order_no']),
            models.Index(fields=['process']),
        ]

    def __str__(self):
        return f"{self.operator.username} - {self.work_order_no} - {self.report_date}"


class WorkOrderReport(BaseReportModel):
    """工單報表模型"""
    
    # 工單資訊
    work_order_no = models.CharField(max_length=100, verbose_name="工單號")
    product_sn = models.CharField(max_length=100, verbose_name="產品編號")
    product_name = models.CharField(max_length=200, verbose_name="產品名稱")
    
    # 進度資訊
    total_quantity = models.IntegerField(verbose_name="總數量")
    completed_quantity = models.IntegerField(default=0, verbose_name="完成數量")
    defect_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    
    # 時間資訊
    start_date = models.DateField(null=True, blank=True, verbose_name="開始日期")
    end_date = models.DateField(null=True, blank=True, verbose_name="結束日期")
    planned_duration = models.IntegerField(null=True, blank=True, verbose_name="計劃工期(天)")
    actual_duration = models.IntegerField(null=True, blank=True, verbose_name="實際工期(天)")
    
    # 狀態資訊
    STATUS_CHOICES = [
        ('PLANNED', '計劃中'),
        ('IN_PROGRESS', '進行中'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED', verbose_name="狀態")

    class Meta:
        verbose_name = "工單報表"
        verbose_name_plural = "工單報表"
        db_table = 'reporting_workorder_report'
        indexes = [
            models.Index(fields=['work_order_no']),
            models.Index(fields=['product_sn']),
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
        ]

    def __str__(self):
        return f"{self.work_order_no} - {self.product_name}"


class WorkHourReport(BaseReportModel):
    """工時報表模型"""
    
    # 人員/設備資訊
    operator = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="作業員")
    equipment_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="設備名稱")
    
    # 工時資訊
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="總工時")
    normal_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="正常工時")
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="加班工時")
    break_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="休息時間")
    
    # 效率資訊
    efficiency_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="效率率(%)")
    utilization_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="利用率(%)")

    class Meta:
        verbose_name = "工時報表"
        verbose_name_plural = "工時報表"
        db_table = 'reporting_work_hour_report'
        indexes = [
            models.Index(fields=['report_date']),
            models.Index(fields=['operator']),
            models.Index(fields=['equipment_name']),
        ]

    def __str__(self):
        if self.operator:
            return f"{self.operator.username} - {self.report_date}"
        else:
            return f"{self.equipment_name} - {self.report_date}"


class ReportExportLog(models.Model):
    """報表匯出日誌"""
    
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES, verbose_name="報表類型")
    export_format = models.CharField(max_length=10, choices=REPORT_FORMAT_CHOICES, verbose_name="匯出格式")
    date_range = models.CharField(max_length=20, choices=DATE_RANGE_CHOICES, verbose_name="日期範圍")
    custom_start_date = models.DateField(null=True, blank=True, verbose_name="自訂開始日期")
    custom_end_date = models.DateField(null=True, blank=True, verbose_name="自訂結束日期")
    
    # 匯出結果
    file_path = models.CharField(max_length=500, null=True, blank=True, verbose_name="檔案路徑")
    file_size = models.IntegerField(null=True, blank=True, verbose_name="檔案大小(位元組)")
    export_status = models.CharField(max_length=20, default='SUCCESS', verbose_name="匯出狀態")
    error_message = models.TextField(null=True, blank=True, verbose_name="錯誤訊息")
    
    # 操作資訊
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="操作者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="匯出時間")

    class Meta:
        verbose_name = "報表匯出日誌"
        verbose_name_plural = "報表匯出日誌"
        db_table = 'reporting_export_log'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report_type} - {self.export_format} - {self.created_at}" 