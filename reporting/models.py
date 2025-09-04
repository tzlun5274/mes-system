"""
報表模組資料模型
提供各種報表功能的資料結構
"""

from django.db import models
from django.utils import timezone
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
    
    @classmethod
    def create_from_fill_work(cls, fill_work):
        """從填報資料建立報表資料"""
        from datetime import datetime
        import calendar
        
        work_date = fill_work.work_date
        if not work_date:
            return None
        
        # 計算時間維度
        work_year = work_date.year
        work_month = work_date.month
        
        # 計算週數
        week_num = work_date.isocalendar()[1]
        
        # 計算季度
        work_quarter = (work_month - 1) // 3 + 1
        
        # 計算工作時數
        daily_work_hours = fill_work.work_hours_calculated or Decimal('0')
        
        # 計算詳細時數
        work_hours = fill_work.work_hours_calculated or Decimal('0')
        overtime_hours = fill_work.overtime_hours_calculated or Decimal('0')
        total_hours = work_hours + overtime_hours
        
        # 建立或更新報表資料
        report_data, created = cls.objects.get_or_create(
            workorder_id=fill_work.workorder,
            company=fill_work.company_name,
            work_date=work_date,
            defaults={
                'operator_name': fill_work.operator,
                'product_code': fill_work.product_id,
                'process_name': fill_work.operation or (fill_work.process.name if fill_work.process else ''),
                'start_time': fill_work.start_time,
                'end_time': fill_work.end_time,
                'work_hours': work_hours,
                'overtime_hours': overtime_hours,
                'total_hours': total_hours,
                'work_week': week_num,
                'work_month': work_month,
                'work_quarter': work_quarter,
                'work_year': work_year,
                'daily_work_hours': daily_work_hours,
                'weekly_work_hours': daily_work_hours,
                'monthly_work_hours': daily_work_hours,
                'operator_count': 1,
                'equipment_hours': daily_work_hours,
            }
        )
        
        if not created:
            # 更新現有記錄
            report_data.operator_name = fill_work.operator
            report_data.product_code = fill_work.product_id
            report_data.process_name = fill_work.operation or (fill_work.process.name if fill_work.process else '')
            report_data.start_time = fill_work.start_time
            report_data.end_time = fill_work.end_time
            report_data.work_hours = work_hours
            report_data.overtime_hours = overtime_hours
            report_data.total_hours = total_hours
            report_data.daily_work_hours = daily_work_hours
            report_data.weekly_work_hours += daily_work_hours
            report_data.monthly_work_hours += daily_work_hours
            report_data.equipment_hours = daily_work_hours
            report_data.save()
        
        return report_data

    @classmethod
    def create_from_onsite_report(cls, onsite_report):
        """從現場報工資料建立報表資料"""
        from datetime import datetime
        import calendar
        
        # 檢查是否為已完成的報工記錄
        if onsite_report.status != 'completed':
            return None
        
        # 取得工作日期
        work_date = onsite_report.start_datetime.date()
        
        # 計算時間維度
        work_year = work_date.year
        work_month = work_date.month
        
        # 計算週數
        week_num = work_date.isocalendar()[1]
        
        # 計算季度
        work_quarter = (work_month - 1) // 3 + 1
        
        # 計算工作時數（分鐘轉小時）
        work_minutes = onsite_report.work_minutes or 0
        daily_work_hours = Decimal(str(work_minutes / 60)).quantize(Decimal('0.01'))
        
        # 計算詳細時數
        work_hours = daily_work_hours
        overtime_hours = Decimal('0')  # 現場報工暫時不計算加班時數
        total_hours = work_hours + overtime_hours
        
        # 建立或更新報表資料
        report_data, created = cls.objects.get_or_create(
            workorder_id=onsite_report.workorder,
            company=onsite_report.company_name,
            work_date=work_date,
            defaults={
                'operator_name': onsite_report.operator,
                'product_code': onsite_report.product_id,
                'process_name': onsite_report.process,
                'start_time': onsite_report.start_datetime.time(),
                'end_time': onsite_report.end_datetime.time() if onsite_report.end_datetime else None,
                'work_hours': work_hours,
                'overtime_hours': overtime_hours,
                'total_hours': total_hours,
                'work_week': week_num,
                'work_month': work_month,
                'work_quarter': work_quarter,
                'work_year': work_year,
                'daily_work_hours': daily_work_hours,
                'weekly_work_hours': daily_work_hours,
                'monthly_work_hours': daily_work_hours,
                'operator_count': 1,
                'equipment_hours': daily_work_hours,
            }
        )
        
        if not created:
            # 更新現有記錄
            report_data.operator_name = onsite_report.operator
            report_data.product_code = onsite_report.product_id
            report_data.process_name = onsite_report.process
            report_data.start_time = onsite_report.start_datetime.time()
            report_data.end_time = onsite_report.end_datetime.time() if onsite_report.end_datetime else None
            report_data.work_hours = work_hours
            report_data.overtime_hours = overtime_hours
            report_data.total_hours = total_hours
            report_data.daily_work_hours = daily_work_hours
            report_data.weekly_work_hours += daily_work_hours
            report_data.monthly_work_hours += daily_work_hours
            report_data.equipment_hours = daily_work_hours
            report_data.save()
        
        return report_data





class ReportSchedule(models.Model):
    """報表排程設定"""
    
    REPORT_TYPES = [
        ('data_sync', '資料同步'),
        ('previous_workday', '前一個工作日報表'),
        ('current_week', '本週報表'),
        ('previous_week', '上週報表'),
        ('current_month', '本月報表'),
        ('previous_month', '上月報表'),
        ('current_quarter', '本季報表'),
        ('previous_quarter', '上季報表'),
        ('current_year', '本年報表'),
        ('previous_year', '上年報表'),
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
    schedule_day = models.IntegerField(null=True, blank=True, verbose_name="執行日期", help_text="週報表：週幾(1-7)，月報表：每月幾號(1-31)")
    
    # 檔案格式設定
    file_format = models.CharField(
        max_length=20,
        choices=FILE_FORMATS,
        default='html',
        verbose_name="檔案格式"
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
    
    report_schedule = models.ForeignKey(ReportSchedule, on_delete=models.CASCADE, verbose_name="報表排程")
    execution_time = models.DateTimeField(auto_now_add=True, verbose_name="執行時間")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="執行狀態")
    message = models.TextField(blank=True, verbose_name="執行訊息")
    file_path = models.CharField(max_length=500, blank=True, verbose_name="檔案路徑")
    
    class Meta:
        verbose_name = "報表執行日誌"
        verbose_name_plural = "報表執行日誌"
        db_table = 'report_execution_log'
        ordering = ['-execution_time']
    
    def __str__(self):
        return f"{self.report_schedule.name} - {self.execution_time.strftime('%Y-%m-%d %H:%M')}" 


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
        # 生產效率權重：70%
        # 生產效率 = 產能評分（基於產能比率計算）
        production_score = self.capacity_score * Decimal('0.70')
        
        # 主管評分權重：30%
        # 如果主管已主動評分，使用實際評分；否則使用預設80分
        supervisor_weighted = self.supervisor_score * Decimal('0.30')
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
        
        # 品質評分不再自動計算，由主管手動評分
        
        if not self.total_score:
            self.total_score = self.calculate_total_score()
        
        if not self.grade:
            self.grade = self.get_grade(self.capacity_score)
        
        if not self.overall_grade:
            self.overall_grade = self.get_grade(self.total_score)
        
        super().save(*args, **kwargs) 


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