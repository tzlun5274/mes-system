"""
報表模組資料模型
提供各種報表功能的資料結構
採用彙總+詳細分離策略，解決資料增長問題
"""

from django.db import models
from django.utils import timezone
from decimal import Decimal
import json


class WorkTimeReportSummary(models.Model):
    """
    工作時數報表彙總資料表 - 長期保留
    儲存日、週、月、季、年工作時數報表的關鍵統計資料，用於長期趨勢分析
    """
    
    # 基本識別
    report_date = models.DateField(verbose_name="報表日期")
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    company_name = models.CharField(max_length=100, verbose_name="公司名稱")
    
    # 報表類型
    report_type = models.CharField(
        max_length=20,
        choices=[
            ('work_time', '工作時數報表'),
            ('work_order', '工單報表'),
            ('equipment', '設備報表'),
            ('quality', '品質報表'),
            ('performance', '績效報表'),
            ('comprehensive', '綜合報表'),
        ],
        verbose_name="報表類型"
    )
    
    # 時間維度
    time_dimension = models.CharField(
        max_length=10,
        choices=[
            ('daily', '日報表'),
            ('weekly', '週報表'),
            ('monthly', '月報表'),
            ('quarterly', '季報表'),
            ('yearly', '年報表'),
        ],
        verbose_name="時間維度"
    )
    
    # 關鍵統計資料
    total_work_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="總工作時數")
    total_overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="總加班時數")
    total_work_quantity = models.IntegerField(default=0, verbose_name="總工作數量")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="總不良數量")
    total_good_quantity = models.IntegerField(default=0, verbose_name="總合格數量")
    
    # 效率指標
    efficiency_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="效率率")
    defect_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="不良率")
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="完工率")
    
    # 人員和設備統計
    unique_operators_count = models.IntegerField(default=0, verbose_name="參與作業員數")
    unique_equipment_count = models.IntegerField(default=0, verbose_name="使用設備數")
    total_workorders_count = models.IntegerField(default=0, verbose_name="工單數量")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    is_archived = models.BooleanField(default=False, verbose_name="是否已歸檔")
    
    class Meta:
        verbose_name = "工作時數報表彙總"
        verbose_name_plural = "工作時數報表彙總"
        db_table = 'work_time_report_summary'
        unique_together = ['report_date', 'company_code', 'report_type', 'time_dimension']
        indexes = [
            models.Index(fields=['company_code', 'report_date']),
            models.Index(fields=['report_type', 'time_dimension']),
            models.Index(fields=['company_code', 'report_type']),
        ]
        ordering = ['-report_date']
    
    def __str__(self):
        return f"{self.company_name} - {self.get_report_type_display()} - {self.get_time_dimension_display()} - {self.report_date}"
    
    @property
    def total_quantity(self):
        """總數量"""
        return self.total_good_quantity + self.total_defect_quantity
    
    @property
    def yield_rate(self):
        """良率"""
        if self.total_quantity > 0:
            return (self.total_good_quantity / self.total_quantity) * 100
        return 0


class WorkTimeReportDetail(models.Model):
    """
    工作時數報表詳細資料表 - 短期保留（3個月）
    儲存詳細資料，用於即時查詢和詳細分析
    """
    
    # 關聯彙總資料
    summary = models.ForeignKey(
        WorkTimeReportSummary,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name="彙總資料"
    )
    
    # 詳細資料（JSON格式）
    detailed_data = models.JSONField(verbose_name="詳細資料", help_text="儲存詳細的報表資料")
    
    # 資料來源
    data_source = models.CharField(max_length=50, verbose_name="資料來源")
    calculation_method = models.CharField(max_length=50, verbose_name="計算方法")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "工作時數報表詳細"
        verbose_name_plural = "工作時數報表詳細"
        db_table = 'work_time_report_detail'
        indexes = [
            models.Index(fields=['summary', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.summary} - 詳細資料"
    
    def get_detail_data(self):
        """獲取詳細資料"""
        return self.detailed_data if isinstance(self.detailed_data, dict) else {}


class ReportArchive(models.Model):
    """
    報表歸檔資料表 - 歷史資料（1年）
    儲存已歸檔的報表資料，用於歷史查詢
    """
    
    # 原始資料識別
    original_summary_id = models.IntegerField(verbose_name="原始彙總ID")
    original_detail_id = models.IntegerField(null=True, blank=True, verbose_name="原始詳細ID")
    
    # 歸檔資料
    archived_data = models.JSONField(verbose_name="歸檔資料")
    
    # 歸檔資訊
    archive_date = models.DateTimeField(auto_now_add=True, verbose_name="歸檔日期")
    archive_reason = models.CharField(max_length=100, verbose_name="歸檔原因")
    retention_days = models.IntegerField(default=365, verbose_name="保留天數")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "報表歸檔"
        verbose_name_plural = "報表歸檔"
        db_table = 'report_archive'
        indexes = [
            models.Index(fields=['archive_date']),
            models.Index(fields=['original_summary_id']),
        ]
        ordering = ['-archive_date']
    
    def __str__(self):
        return f"歸檔資料 - {self.archive_date.strftime('%Y-%m-%d')}"


class ReportSchedule(models.Model):
    """
    報表排程設定
    管理報表的自動生成和發送
    """
    
    # 基本資訊
    name = models.CharField(max_length=100, verbose_name="排程名稱")
    report_type = models.CharField(
        max_length=20,
        choices=[
            ('work_time', '工作時數報表'),
            ('work_order', '工單報表'),
            ('equipment', '設備報表'),
            ('quality', '品質報表'),
            ('performance', '績效報表'),
            ('comprehensive', '綜合報表'),
        ],
        verbose_name="報表類型"
    )
    
    # 時間維度
    time_dimension = models.CharField(
        max_length=10,
        choices=[
            ('daily', '日報表'),
            ('weekly', '週報表'),
            ('monthly', '月報表'),
            ('quarterly', '季報表'),
            ('yearly', '年報表'),
        ],
        verbose_name="時間維度"
    )
    
    # 排程設定
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    schedule_time = models.TimeField(verbose_name="執行時間")
    schedule_day = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="執行日期",
        help_text="週報表：週幾(1-7)，月報表：每月幾號(1-31)"
    )
    
    # 狀態設定
    is_active = models.BooleanField(default=True, verbose_name="是否啟用")
    last_execution = models.DateTimeField(null=True, blank=True, verbose_name="最後執行時間")
    next_execution = models.DateTimeField(null=True, blank=True, verbose_name="下次執行時間")
    
    # 收件人設定
    email_recipients = models.TextField(blank=True, verbose_name="收件人信箱", help_text="多個信箱用逗號分隔")
    export_format = models.CharField(
        max_length=10,
        choices=[
            ('excel', 'Excel'),
            ('csv', 'CSV'),
            ('pdf', 'PDF'),
        ],
        default='excel',
        verbose_name="匯出格式"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "報表排程"
        verbose_name_plural = "報表排程"
        db_table = 'report_schedule'
        indexes = [
            models.Index(fields=['company_code', 'is_active']),
            models.Index(fields=['next_execution']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class ReportExecutionLog(models.Model):
    """
    報表執行日誌
    記錄報表生成和發送的執行情況
    """
    
    # 關聯排程
    schedule = models.ForeignKey(
        ReportSchedule,
        on_delete=models.CASCADE,
        related_name='execution_logs',
        verbose_name="報表排程"
    )
    
    # 執行資訊
    execution_time = models.DateTimeField(auto_now_add=True, verbose_name="執行時間")
    execution_status = models.CharField(
        max_length=20,
        choices=[
            ('success', '成功'),
            ('failed', '失敗'),
            ('running', '執行中'),
            ('cancelled', '已取消'),
        ],
        verbose_name="執行狀態"
    )
    
    # 執行結果
    message = models.TextField(blank=True, verbose_name="執行訊息")
    file_path = models.CharField(max_length=500, blank=True, verbose_name="檔案路徑")
    file_size = models.IntegerField(null=True, blank=True, verbose_name="檔案大小")
    
    # 執行統計
    records_processed = models.IntegerField(default=0, verbose_name="處理記錄數")
    execution_duration = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="執行時間(秒)"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "報表執行日誌"
        verbose_name_plural = "報表執行日誌"
        db_table = 'report_execution_log'
        indexes = [
            models.Index(fields=['schedule', 'execution_time']),
            models.Index(fields=['execution_status']),
        ]
        ordering = ['-execution_time']
    
    def __str__(self):
        return f"{self.schedule.name} - {self.execution_time.strftime('%Y-%m-%d %H:%M')}"


class ReportExportHistory(models.Model):
    """
    報表匯出歷史
    記錄手動匯出報表的歷史記錄
    """
    
    # 匯出資訊
    report_type = models.CharField(max_length=20, verbose_name="報表類型")
    time_dimension = models.CharField(max_length=10, verbose_name="時間維度")
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    
    # 匯出參數
    start_date = models.DateField(verbose_name="開始日期")
    end_date = models.DateField(verbose_name="結束日期")
    export_format = models.CharField(max_length=10, verbose_name="匯出格式")
    
    # 匯出結果
    file_path = models.CharField(max_length=500, verbose_name="檔案路徑")
    file_size = models.IntegerField(verbose_name="檔案大小")
    download_count = models.IntegerField(default=0, verbose_name="下載次數")
    
    # 使用者資訊
    exported_by = models.CharField(max_length=100, verbose_name="匯出者")
    ip_address = models.GenericIPAddressField(verbose_name="IP位址")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="匯出時間")
    
    class Meta:
        verbose_name = "報表匯出歷史"
        verbose_name_plural = "報表匯出歷史"
        db_table = 'report_export_history'
        indexes = [
            models.Index(fields=['report_type', 'company_code']),
            models.Index(fields=['exported_by', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report_type} - {self.start_date} 至 {self.end_date}"


# 保留原有的評分模型
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
    
    # 主管評分
    supervisor_score = models.DecimalField(max_digits=5, decimal_places=2, default=80, verbose_name="主管評分")
    supervisor_comment = models.TextField(blank=True, verbose_name="主管評語")
    supervisor_name = models.CharField(max_length=100, blank=True, verbose_name="評分主管")
    supervisor_date = models.DateTimeField(null=True, blank=True, verbose_name="評分日期")
    is_supervisor_scored = models.BooleanField(default=False, verbose_name="主管是否已評分")
    
    # 評分週期
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
    
    def calculate_capacity_score(self):
        """計算產能評分"""
        if self.capacity_ratio >= 1.0:
            return Decimal('100.00')
        elif self.capacity_ratio >= 0.8:
            return Decimal('80.00') + (self.capacity_ratio - Decimal('0.8')) * Decimal('100.00')
        elif self.capacity_ratio >= 0.6:
            return Decimal('60.00') + (self.capacity_ratio - Decimal('0.6')) * Decimal('100.00')
        else:
            return self.capacity_ratio * Decimal('100.00')
    
    def calculate_quality_score(self):
        """計算品質評分"""
        if self.defect_rate == 0:
            return Decimal('100.00')
        elif self.defect_rate <= 0.02:  # 2%以下
            return Decimal('90.00') - (self.defect_rate * Decimal('500.00'))
        elif self.defect_rate <= 0.05:  # 5%以下
            return Decimal('80.00') - ((self.defect_rate - Decimal('0.02')) * Decimal('333.33'))
        else:
            return max(Decimal('0.00'), Decimal('60.00') - (self.defect_rate * Decimal('200.00')))
    
    def calculate_total_score(self):
        """計算總評分（包含主管評分）"""
        # 生產效率權重：80%
        production_score = self.capacity_score * Decimal('0.80')
        
        # 主管評分權重：20%
        supervisor_weighted = self.supervisor_score * Decimal('0.20')
        total = production_score + supervisor_weighted
        
        return total
    
    def get_grade(self, score):
        """根據分數取得等級"""
        if score >= 90:
            return '優秀'
        elif score >= 80:
            return '良好'
        elif score >= 70:
            return '及格'
        else:
            return '不及格'
    
    def save(self, *args, **kwargs):
        """儲存時自動計算評分"""
        if not self.capacity_score:
            self.capacity_score = self.calculate_capacity_score()
        
        if not self.quality_score:
            self.quality_score = self.calculate_quality_score()
        
        if not self.total_score:
            self.total_score = self.calculate_total_score()
        
        if not self.grade:
            self.grade = self.get_grade(self.capacity_score)
        
        if not self.overall_grade:
            self.overall_grade = self.get_grade(self.total_score)
        
        super().save(*args, **kwargs) 