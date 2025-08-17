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
    
    # 時間維度資料
    work_date = models.DateField(verbose_name="工作日期")
    work_week = models.IntegerField(verbose_name="工作週數")
    work_month = models.IntegerField(verbose_name="工作月份")
    work_quarter = models.IntegerField(verbose_name="工作季度")
    work_year = models.IntegerField(verbose_name="工作年度")
    
    # 工作時數資料
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
        
        # 建立或更新報表資料
        report_data, created = cls.objects.get_or_create(
            workorder_id=fill_work.workorder,
            company=fill_work.company_name,
            work_date=work_date,
            defaults={
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
        
        # 建立或更新報表資料
        report_data, created = cls.objects.get_or_create(
            workorder_id=onsite_report.order_number,
            company=onsite_report.company_code or '',
            work_date=work_date,
            defaults={
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
            report_data.daily_work_hours = daily_work_hours
            report_data.weekly_work_hours += daily_work_hours
            report_data.monthly_work_hours += daily_work_hours
            report_data.equipment_hours = daily_work_hours
            report_data.save()
        
        return report_data


class CompletedWorkOrderReportData(models.Model):
    """
    已完工工單報表資料模型
    用於儲存已完工工單的報表統計資料
    """
    # 工單識別資訊
    workorder_id = models.CharField(max_length=100, verbose_name="工單編號")
    product_code = models.CharField(max_length=100, verbose_name="產品編號")
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    company_name = models.CharField(max_length=100, verbose_name="公司名稱")
    
    # 時間維度
    completion_date = models.DateField(verbose_name="完工日期")
    completion_week = models.IntegerField(verbose_name="完工週數")
    completion_month = models.IntegerField(verbose_name="完工月份")
    completion_quarter = models.IntegerField(verbose_name="完工季度")
    completion_year = models.IntegerField(verbose_name="完工年度")
    
    # 數量統計
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    completed_quantity = models.IntegerField(verbose_name="完成數量")
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="完工率")
    
    # 品質統計
    total_good_quantity = models.IntegerField(verbose_name="總合格品數量")
    total_defect_quantity = models.IntegerField(verbose_name="總不良品數量")
    defect_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="不良率")
    
    # 時數統計
    total_work_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="總工作時數")
    total_overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="總加班時數")
    total_all_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="全部總時數")
    
    # 效率統計
    efficiency_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="效率率")
    hourly_output = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="每小時產出")
    
    # 人員和設備統計
    unique_operators_count = models.IntegerField(verbose_name="參與作業員數")
    unique_equipment_count = models.IntegerField(verbose_name="使用設備數")
    total_report_count = models.IntegerField(verbose_name="總報工次數")
    
    # 工序統計
    total_processes = models.IntegerField(verbose_name="總工序數")
    completed_processes = models.IntegerField(verbose_name="完成工序數")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "已完工工單報表資料"
        verbose_name_plural = "已完工工單報表資料"
        db_table = 'completed_workorder_report_data'
        unique_together = ['workorder_id', 'company_code', 'completion_date']
        indexes = [
            models.Index(fields=['company_code', 'completion_date']),
            models.Index(fields=['company_code', 'completion_year', 'completion_month']),
            models.Index(fields=['company_code', 'completion_year', 'completion_quarter']),
            models.Index(fields=['company_code', 'completion_year']),
        ]
    
    def __str__(self):
        return f"{self.workorder_id} - {self.completion_date}"
    
    @classmethod
    def create_from_completed_workorder(cls, completed_workorder):
        """從已完工工單建立報表資料"""
        from datetime import datetime
        import calendar
        
        # 取得完工日期
        completion_date = completed_workorder.completed_at.date()
        
        # 計算時間維度
        completion_year = completion_date.year
        completion_month = completion_date.month
        
        # 計算週數
        week_num = completion_date.isocalendar()[1]
        
        # 計算季度
        completion_quarter = (completion_month - 1) // 3 + 1
        
        # 計算完工率
        completion_rate = Decimal('0.00')
        if completed_workorder.planned_quantity > 0:
            completion_rate = Decimal(str((completed_workorder.completed_quantity / completed_workorder.planned_quantity) * 100)).quantize(Decimal('0.01'))
        
        # 計算不良率
        defect_rate = Decimal('0.00')
        total_quantity = completed_workorder.total_good_quantity + completed_workorder.total_defect_quantity
        if total_quantity > 0:
            defect_rate = Decimal(str((completed_workorder.total_defect_quantity / total_quantity) * 100)).quantize(Decimal('0.01'))
        
        # 計算效率率（基於計劃時數，這裡簡化為100%）
        efficiency_rate = Decimal('100.00')
        
        # 計算每小時產出
        hourly_output = Decimal('0.00')
        if completed_workorder.total_all_hours > 0:
            hourly_output = Decimal(str(completed_workorder.completed_quantity / completed_workorder.total_all_hours)).quantize(Decimal('0.01'))
        
        # 計算參與人員和設備數
        unique_operators_count = len(completed_workorder.unique_operators) if completed_workorder.unique_operators else 0
        unique_equipment_count = len(completed_workorder.unique_equipment) if completed_workorder.unique_equipment else 0
        
        # 計算工序統計
        total_processes = completed_workorder.processes.count()
        completed_processes = completed_workorder.processes.filter(status='completed').count()
        
        # 建立或更新報表資料
        report_data, created = cls.objects.get_or_create(
            workorder_id=completed_workorder.order_number,
            company_code=completed_workorder.company_code,
            completion_date=completion_date,
            defaults={
                'product_code': completed_workorder.product_code,
                'company_name': completed_workorder.company_name,
                'completion_week': week_num,
                'completion_month': completion_month,
                'completion_quarter': completion_quarter,
                'completion_year': completion_year,
                'planned_quantity': completed_workorder.planned_quantity,
                'completed_quantity': completed_workorder.completed_quantity,
                'completion_rate': completion_rate,
                'total_good_quantity': completed_workorder.total_good_quantity,
                'total_defect_quantity': completed_workorder.total_defect_quantity,
                'defect_rate': defect_rate,
                'total_work_hours': completed_workorder.total_work_hours,
                'total_overtime_hours': completed_workorder.total_overtime_hours,
                'total_all_hours': completed_workorder.total_all_hours,
                'efficiency_rate': efficiency_rate,
                'hourly_output': hourly_output,
                'unique_operators_count': unique_operators_count,
                'unique_equipment_count': unique_equipment_count,
                'total_report_count': completed_workorder.total_report_count,
                'total_processes': total_processes,
                'completed_processes': completed_processes,
            }
        )
        
        if not created:
            # 更新現有記錄
            report_data.product_code = completed_workorder.product_code
            report_data.company_name = completed_workorder.company_name
            report_data.planned_quantity = completed_workorder.planned_quantity
            report_data.completed_quantity = completed_workorder.completed_quantity
            report_data.completion_rate = completion_rate
            report_data.total_good_quantity = completed_workorder.total_good_quantity
            report_data.total_defect_quantity = completed_workorder.total_defect_quantity
            report_data.defect_rate = defect_rate
            report_data.total_work_hours = completed_workorder.total_work_hours
            report_data.total_overtime_hours = completed_workorder.total_overtime_hours
            report_data.total_all_hours = completed_workorder.total_all_hours
            report_data.efficiency_rate = efficiency_rate
            report_data.hourly_output = hourly_output
            report_data.unique_operators_count = unique_operators_count
            report_data.unique_equipment_count = unique_equipment_count
            report_data.total_report_count = completed_workorder.total_report_count
            report_data.total_processes = total_processes
            report_data.completed_processes = completed_processes
            report_data.save()
        
        return report_data


class ReportSchedule(models.Model):
    """報表排程設定"""
    
    REPORT_TYPES = [
        ('weekly', '週報表'),
        ('monthly', '月報表'),
        ('quarterly', '季報表'),
        ('yearly', '年報表'),
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
        # 生產效率權重：80%
        # 生產效率 = 產能評分（基於產能比率計算）
        production_score = self.capacity_score * Decimal('0.80')
        
        # 主管評分權重：20%
        # 如果主管已主動評分，使用實際評分；否則使用預設80分
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