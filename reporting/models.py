"""
報表模組資料模型
提供各種報表功能的資料結構
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class WorkOrderReportData(models.Model):
    """工單報表專用資料表 - 支援週月季年度統計"""
    
    # 基本識別資料
    workorder_id = models.CharField(max_length=50, verbose_name="工單編號")
    company = models.CharField(max_length=10, verbose_name="公司代號")
    operator_name = models.CharField(max_length=100, verbose_name="作業員姓名", null=True, blank=True)
    
    # 產品和工序資料
    product_code = models.CharField(max_length=100, verbose_name="產品編號", null=True, blank=True)
    process_name = models.CharField(max_length=100, verbose_name="工序名稱", null=True, blank=True)
    
    # 時間維度資料
    work_date = models.DateField(verbose_name="工作日期")
    work_week = models.IntegerField(verbose_name="工作週數")
    work_month = models.IntegerField(verbose_name="工作月份")
    work_quarter = models.IntegerField(verbose_name="工作季度")
    work_year = models.IntegerField(verbose_name="工作年度")
    
    # 時間詳細資料
    start_time = models.TimeField(verbose_name="開始時間", null=True, blank=True)
    end_time = models.TimeField(verbose_name="結束時間", null=True, blank=True)
    
    # 工作時數資料
    work_hours = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="工作時數", default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="加班時數", default=0)
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="合計時數", default=0)
    daily_work_hours = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="日工作時數")
    weekly_work_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="週工作時數")
    monthly_work_hours = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="月工作時數")
    
    # 統計資料
    operator_count = models.IntegerField(default=1, verbose_name="作業員人數")
    equipment_hours = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="設備使用時數")
    
    # 工作數量資料
    work_quantity = models.IntegerField(default=0, verbose_name="工作數量")
    defect_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    completed_quantity = models.IntegerField(default=0, verbose_name="完成數量")
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "工單報表資料"
        verbose_name_plural = "工單報表資料"
        db_table = 'workorder_report_data'
        indexes = [
            models.Index(fields=['company', 'work_date']),
            models.Index(fields=['operator_name', 'work_date']),
            models.Index(fields=['company', 'work_year', 'work_month']),
            models.Index(fields=['company', 'work_year', 'work_quarter']),
            models.Index(fields=['company', 'work_year']),
        ]
    
    def __str__(self):
        return f"{self.company}-{self.workorder_id}-{self.work_date}"
    





class ReportSchedule(models.Model):
    """報表排程設定"""
    
    REPORT_TYPES = [
        ('data_sync', '填報與現場記錄資料同步'),
        ('previous_workday', '前一個工作日報表'),
        ('previous_week', '上週報表'),
        ('previous_month', '上月報表'),
        ('previous_quarter', '上季報表'),
        ('previous_year', '去年報表'),
    ]
    
    FILE_FORMATS = [
        ('html', 'HTML格式'),
        ('excel', 'Excel格式'),
        ('both', 'HTML + Excel格式'),
    ]
    
    STATUS_CHOICES = [
        ('active', '啟用'),
        ('inactive', '停用'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="報表名稱")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name="報表類型")
    company = models.CharField(max_length=10, verbose_name="公司代號")
    
    # 排程設定
    schedule_time = models.TimeField(verbose_name="執行時間")
    schedule_day = models.IntegerField(null=True, blank=True, verbose_name="執行日期", help_text="週報表：週幾(1-7)，月報表：每月幾號(1-30)")
    
    # 檔案格式設定
    file_format = models.CharField(
        max_length=20,
        choices=FILE_FORMATS,
        default='html',
        verbose_name="檔案格式"
    )
    
    # 資料同步時間設定
    sync_execution_type = models.CharField(
        max_length=20,
        choices=[
            ('interval', '間隔執行'),
            ('fixed_time', '固定時間'),
        ],
        default='interval',
        verbose_name="執行方式",
        help_text="資料同步的執行方式"
    )
    
    sync_interval_minutes = models.IntegerField(
        default=60,
        verbose_name="同步間隔（分鐘）",
        help_text="每多少分鐘執行一次資料同步",
        validators=[MinValueValidator(1), MaxValueValidator(1440)]
    )
    
    sync_fixed_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="固定同步時間",
        help_text="每天固定時間執行資料同步"
    )
    
    # 狀態
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="狀態")
    
    # 收件人設定
    email_recipients = models.TextField(blank=True, verbose_name="收件人信箱", help_text="多個信箱用逗號分隔")
    
    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "報表排程"
        verbose_name_plural = "報表排程"
        db_table = 'report_schedule'
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class ReportExecutionLog(models.Model):
    """報表執行日誌"""
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失敗'),
        ('running', '執行中'),
    ]
    
    report_schedule_id = models.CharField(max_length=50, verbose_name="報表排程ID")
    report_schedule_name = models.CharField(max_length=200, verbose_name="報表排程名稱")
    execution_time = models.DateTimeField(auto_now_add=True, verbose_name="執行時間")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="執行狀態")
    message = models.TextField(blank=True, verbose_name="執行訊息")
    file_path = models.CharField(max_length=500, blank=True, null=True, verbose_name="檔案路徑")
    
    class Meta:
        verbose_name = "報表執行日誌"
        verbose_name_plural = "報表執行日誌"
        db_table = 'report_execution_log'
        ordering = ['-execution_time']
    
    def __str__(self):
        return f"{self.report_schedule_name} - {self.execution_time.strftime('%Y-%m-%d %H:%M')}" 


class OperatorProcessCapacityScore(models.Model):
    """作業員工序產能評分表"""
    operator_name = models.CharField(max_length=100, verbose_name="作業員姓名")
    operator_id = models.CharField(max_length=50, verbose_name="作業員編號")
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    product_code = models.CharField(max_length=50, verbose_name="產品代號")
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    workorder_id = models.CharField(max_length=50, verbose_name="工單編號")
    work_date = models.DateField(verbose_name="工作日期")
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="工作時數")
    
    # 標準產能相關
    standard_capacity_per_hour = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="標準每小時產能")
    actual_capacity_per_hour = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="實際每小時產能")
    completed_quantity = models.IntegerField(verbose_name="完成數量")
    capacity_ratio = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="產能比率")
    
    # 系統評分
    capacity_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="產能評分")
    grade = models.CharField(max_length=20, verbose_name="等級")
    
    # 效率因子
    efficiency_factor = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="效率因子")
    learning_curve_factor = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="學習曲線因子")
    
    # 品質相關
    defect_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    defect_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="不良率")
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="品質評分")
    
    # 主管評分 ⭐ 新增
    supervisor_score = models.DecimalField(max_digits=5, decimal_places=2, default=80, verbose_name="主管評分")
    supervisor_comment = models.TextField(blank=True, verbose_name="主管評語")
    supervisor_name = models.CharField(max_length=100, blank=True, verbose_name="評分主管")
    supervisor_date = models.DateTimeField(null=True, blank=True, verbose_name="評分日期")
    is_supervisor_scored = models.BooleanField(default=False, verbose_name="主管是否已評分")
    
    # 評分週期 ⭐ 新增
    score_period = models.CharField(
        max_length=20,
        choices=[
            ('monthly', '月評分'),
            ('quarterly', '季評分'),
            ('yearly', '年評分'),
        ],
        default='monthly',
        verbose_name="評分週期"
    )
    period_start_date = models.DateField(verbose_name="週期開始日期", default=timezone.now)
    period_end_date = models.DateField(verbose_name="週期結束日期", default=timezone.now)
    is_period_closed = models.BooleanField(default=False, verbose_name="週期是否已關閉")
    period_closed_date = models.DateTimeField(null=True, blank=True, verbose_name="週期關閉日期")
    
    # 總評分
    total_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="總評分")
    overall_grade = models.CharField(max_length=20, verbose_name="總體等級")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "作業員工序產能評分"
        verbose_name_plural = "作業員工序產能評分"
        db_table = 'reporting_operator_process_capacity_score'
        unique_together = ['operator_id', 'company_code', 'product_code', 'process_name', 'workorder_id', 'work_date']
        indexes = [
            models.Index(fields=['company_code', 'work_date']),
            models.Index(fields=['operator_id', 'work_date']),
            models.Index(fields=['process_name', 'work_date']),
        ]
    
    def __str__(self):
        return f"{self.operator_name} - {self.process_name} - {self.work_date}"
    


class CompletedWorkOrderAnalysis(models.Model):
    """已完工工單分析資料表"""
    workorder_id = models.CharField(max_length=50, verbose_name="工單編號")
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    company_name = models.CharField(max_length=100, verbose_name="公司名稱")
    product_code = models.CharField(max_length=100, verbose_name="產品編號")
    product_name = models.CharField(max_length=200, verbose_name="產品名稱")
    order_quantity = models.IntegerField(verbose_name="訂單數量")
    
    # 時間分析
    first_record_date = models.DateField(verbose_name="第一筆紀錄日期")
    last_record_date = models.DateField(verbose_name="最後一筆紀錄日期")
    total_execution_days = models.IntegerField(verbose_name="總執行天數")
    total_work_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="總工作時數")
    total_overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="總加班時數")
    average_daily_hours = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="平均每日工作時數")
    efficiency_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="效率比率")
    
    # 工序分析
    total_processes = models.IntegerField(verbose_name="總工序數")
    unique_processes = models.IntegerField(verbose_name="不重複工序數")
    total_operators = models.IntegerField(verbose_name="參與作業員數")
    
    # 完成資訊
    completion_date = models.DateField(verbose_name="完工日期")
    completion_status = models.CharField(max_length=20, verbose_name="完工狀態")
    
    # 詳細資料（JSON格式）
    process_details = models.JSONField(verbose_name="工序詳細資料", help_text="包含每個工序的執行順序、時間、作業員等詳細資訊")
    operator_details = models.JSONField(verbose_name="作業員詳細資料", help_text="包含每個作業員的工作時數、工序等資訊")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "已完工工單分析"
        verbose_name_plural = "已完工工單分析"
        db_table = 'completed_workorder_analysis'
        unique_together = ['workorder_id', 'company_code']
        indexes = [
            models.Index(fields=['company_code', 'completion_date']),
            models.Index(fields=['completion_date']),
            models.Index(fields=['workorder_id']),
        ]
    
    def __str__(self):
        return f"{self.workorder_id} - {self.company_name} - {self.completion_date}"


class AnalysisErrorLog(models.Model):
    """工單分析錯誤日誌"""
    workorder_id = models.CharField(max_length=50, verbose_name="工單編號")
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    product_code = models.CharField(max_length=100, verbose_name="產品編號", null=True, blank=True)
    error_message = models.TextField(verbose_name="錯誤訊息")
    error_type = models.CharField(max_length=100, verbose_name="錯誤類型")
    analysis_date = models.DateTimeField(verbose_name="分析時間")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "分析錯誤日誌"
        verbose_name_plural = "分析錯誤日誌"
        db_table = 'analysis_error_log'
        ordering = ['-analysis_date']
        indexes = [
            models.Index(fields=['workorder_id']),
            models.Index(fields=['company_code']),
            models.Index(fields=['analysis_date']),
            models.Index(fields=['error_type']),
        ]
    
    def __str__(self):
        return f"{self.workorder_id} - {self.error_type} - {self.analysis_date.strftime('%Y-%m-%d %H:%M')}" 