# 報表系統數據模型
# 本檔案定義了 MES 系統的所有報表相關數據模型
# 包含基礎報表模型、工作時間報表、工單機種報表、人員績效報表等

from django.db import models
from django.utils import timezone
from django.core.cache import cache
import logging

# 設定日誌記錄器
logger = logging.getLogger(__name__)


class BaseReportModel(models.Model):
    """報表基礎模型 - 所有報表模型的基礎類別"""
    
    # 報表基本資訊
    REPORT_TYPE_CHOICES = [
        ('daily', '日報表'),
        ('weekly', '週報表'),
        ('monthly', '月報表'),
        ('custom', '自訂期間報表'),
    ]
    
    report_type = models.CharField(
        max_length=20, 
        choices=REPORT_TYPE_CHOICES,
        verbose_name="報表類型"
    )
    report_date = models.DateField(verbose_name="報表日期")
    report_period_start = models.DateField(verbose_name="報表期間開始")
    report_period_end = models.DateField(verbose_name="報表期間結束")
    
    # 數據來源標示
    data_source = models.CharField(
        max_length=50, 
        verbose_name="數據來源",
        help_text="數據來源模組名稱"
    )
    calculation_method = models.CharField(
        max_length=50, 
        verbose_name="計算方法",
        help_text="統計數據的計算邏輯"
    )
    
    # 系統資訊
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    created_by = models.CharField(max_length=100, verbose_name="建立者")
    
    class Meta:
        abstract = True
        ordering = ['-report_date']
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.report_date}"
    
    def save(self, *args, **kwargs):
        """儲存時記錄操作日誌"""
        super().save(*args, **kwargs)
        logger.info(f"報表數據已儲存: {self.__class__.__name__} - {self.report_date}")


class WorkTimeReport(BaseReportModel):
    """工作時間報表模型 - 記錄作業員和設備的工作時間統計"""
    
    WORKER_TYPE_CHOICES = [
        ('operator', '作業員'),
        ('smt', 'SMT設備'),
        ('general', '一般設備'),
    ]
    
    # 工作人員資訊
    worker_name = models.CharField(max_length=100, verbose_name="作業員/設備名稱")
    worker_type = models.CharField(
        max_length=10, 
        choices=WORKER_TYPE_CHOICES,
        verbose_name="工作人員類型"
    )
    
    # 工單資訊
    workorder_number = models.CharField(
        max_length=100, 
        verbose_name="工單號碼",
        blank=True
    )
    product_code = models.CharField(
        max_length=100, 
        verbose_name="產品編號",
        blank=True
    )
    process_name = models.CharField(
        max_length=100, 
        verbose_name="工序名稱",
        blank=True
    )
    
    # 時間資訊
    start_time = models.TimeField(
        verbose_name="開始時間", 
        null=True, 
        blank=True
    )
    end_time = models.TimeField(
        verbose_name="結束時間", 
        null=True, 
        blank=True
    )
    total_work_hours = models.FloatField(verbose_name="總工作時數")
    actual_work_hours = models.FloatField(verbose_name="實際工作時數")
    break_hours = models.FloatField(
        default=0.0, 
        verbose_name="休息時數"
    )
    overtime_hours = models.FloatField(
        default=0.0, 
        verbose_name="加班時數"
    )
    
    # 產量資訊
    completed_quantity = models.IntegerField(verbose_name="完成數量")
    defect_quantity = models.IntegerField(
        default=0, 
        verbose_name="不良品數量"
    )
    yield_rate = models.FloatField(verbose_name="良率 (%)")
    efficiency_rate = models.FloatField(verbose_name="效率 (件/小時)")
    
    # 數量分配資訊
    original_quantity = models.IntegerField(
        default=0, 
        verbose_name="原始數量"
    )
    allocated_quantity = models.IntegerField(
        default=0, 
        verbose_name="分配數量"
    )
    quantity_source = models.CharField(
        max_length=20, 
        choices=[
            ('original', '原始數量'),
            ('allocated', '智能分配'),
        ], 
        default='original', 
        verbose_name="數量來源"
    )
    allocation_notes = models.TextField(
        blank=True, 
        verbose_name="分配計算說明"
    )
    
    # 異常記錄
    abnormal_notes = models.TextField(
        blank=True, 
        verbose_name="異常記錄"
    )
    
    class Meta:
        verbose_name = "工作時間報表"
        verbose_name_plural = "工作時間報表"
        unique_together = [
            ['report_type', 'report_date', 'worker_name', 'workorder_number']
        ]
        db_table = 'reporting_work_time_report'
    
    def __str__(self):
        return f"{self.report_date} - {self.worker_name} - {self.workorder_number}"
    
    def calculate_efficiency(self):
        """計算效率率"""
        if self.actual_work_hours > 0:
            self.efficiency_rate = round(
                self.completed_quantity / self.actual_work_hours, 2
            )
        return self.efficiency_rate
    
    def calculate_yield_rate(self):
        """計算良率"""
        total_quantity = self.completed_quantity + self.defect_quantity
        if total_quantity > 0:
            self.yield_rate = round(
                (self.completed_quantity / total_quantity) * 100, 2
            )
        return self.yield_rate


class WorkOrderProductReport(BaseReportModel):
    """工單機種報表模型 - 記錄工單和產品的完成狀況統計"""
    
    # 工單資訊
    workorder_number = models.CharField(
        max_length=100, 
        verbose_name="工單號碼"
    )
    product_code = models.CharField(
        max_length=100, 
        verbose_name="產品編號"
    )
    product_name = models.CharField(
        max_length=200, 
        verbose_name="產品名稱"
    )
    
    # 計劃資訊
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    planned_start_date = models.DateField(verbose_name="計劃開始日期")
    planned_end_date = models.DateField(verbose_name="計劃完成日期")
    
    # 完成狀況
    completed_quantity = models.IntegerField(verbose_name="實際完成數量")
    completion_rate = models.FloatField(verbose_name="完成率 (%)")
    actual_start_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="實際開始日期"
    )
    actual_end_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="實際完成日期"
    )
    
    # 人員分配
    assigned_operators = models.TextField(
        blank=True, 
        verbose_name="作業員清單"
    )
    total_work_hours = models.FloatField(verbose_name="總工作時數")
    
    # 設備使用
    assigned_equipment = models.TextField(
        blank=True, 
        verbose_name="設備清單"
    )
    equipment_usage_rate = models.FloatField(verbose_name="設備使用率 (%)")
    
    # 品質統計
    defect_quantity = models.IntegerField(
        default=0, 
        verbose_name="不良品數量"
    )
    yield_rate = models.FloatField(verbose_name="良率 (%)")
    quality_score = models.FloatField(
        default=0.0, 
        verbose_name="品質評分"
    )
    
    # 成本資訊
    material_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="材料成本"
    )
    labor_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="人工成本"
    )
    total_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="總成本"
    )
    
    class Meta:
        verbose_name = "工單機種報表"
        verbose_name_plural = "工單機種報表"
        unique_together = [
            ['report_type', 'report_date', 'workorder_number']
        ]
        db_table = 'reporting_work_order_product_report'
    
    def __str__(self):
        return f"{self.workorder_number} - {self.product_name} - {self.report_date}"
    
    def calculate_completion_rate(self):
        """計算完成率"""
        if self.planned_quantity > 0:
            self.completion_rate = round(
                (self.completed_quantity / self.planned_quantity) * 100, 2
            )
        return self.completion_rate
    
    def calculate_yield_rate(self):
        """計算良率"""
        total_quantity = self.completed_quantity + self.defect_quantity
        if total_quantity > 0:
            self.yield_rate = round(
                (self.completed_quantity / total_quantity) * 100, 2
            )
        return self.yield_rate


class PersonnelPerformanceReport(BaseReportModel):
    """人員績效報表模型 - 記錄作業員和主管的績效統計"""
    
    PERSONNEL_TYPE_CHOICES = [
        ('operator', '作業員'),
        ('supervisor', '主管'),
        ('team', '團隊'),
    ]
    
    # 人員資訊
    personnel_name = models.CharField(max_length=100, verbose_name="人員姓名")
    personnel_type = models.CharField(
        max_length=10, 
        choices=PERSONNEL_TYPE_CHOICES,
        verbose_name="人員類型"
    )
    department = models.CharField(
        max_length=100, 
        verbose_name="部門",
        blank=True
    )
    position = models.CharField(
        max_length=100, 
        verbose_name="職位",
        blank=True
    )
    
    # 工作統計
    total_work_hours = models.FloatField(verbose_name="總工作時數")
    overtime_hours = models.FloatField(
        default=0.0, 
        verbose_name="加班時數"
    )
    work_days = models.IntegerField(verbose_name="工作天數")
    attendance_rate = models.FloatField(verbose_name="出勤率 (%)")
    
    # 產量統計
    total_completed_quantity = models.IntegerField(verbose_name="總完成數量")
    total_defect_quantity = models.IntegerField(
        default=0, 
        verbose_name="總不良品數量"
    )
    average_efficiency = models.FloatField(verbose_name="平均效率 (件/小時)")
    quality_score = models.FloatField(verbose_name="品質評分")
    
    # 績效指標
    productivity_score = models.FloatField(verbose_name="生產力評分")
    quality_score = models.FloatField(verbose_name="品質評分")
    attendance_score = models.FloatField(verbose_name="出勤評分")
    overall_score = models.FloatField(verbose_name="綜合評分")
    
    # 工單統計
    completed_workorders = models.IntegerField(verbose_name="完成工單數")
    total_workorders = models.IntegerField(verbose_name="總工單數")
    workorder_completion_rate = models.FloatField(verbose_name="工單完成率 (%)")
    
    # 異常記錄
    abnormal_count = models.IntegerField(
        default=0, 
        verbose_name="異常次數"
    )
    abnormal_hours = models.FloatField(
        default=0.0, 
        verbose_name="異常時數"
    )
    
    class Meta:
        verbose_name = "人員績效報表"
        verbose_name_plural = "人員績效報表"
        unique_together = [
            ['report_type', 'report_date', 'personnel_name']
        ]
        db_table = 'reporting_personnel_performance_report'
    
    def __str__(self):
        return f"{self.personnel_name} - {self.report_date} - {self.get_personnel_type_display()}"
    
    def calculate_overall_score(self):
        """計算綜合評分"""
        self.overall_score = round(
            (self.productivity_score + self.quality_score + self.attendance_score) / 3, 2
        )
        return self.overall_score
    
    def calculate_workorder_completion_rate(self):
        """計算工單完成率"""
        if self.total_workorders > 0:
            self.workorder_completion_rate = round(
                (self.completed_workorders / self.total_workorders) * 100, 2
            )
        return self.workorder_completion_rate


class EquipmentEfficiencyReport(BaseReportModel):
    """設備效率報表模型 - 記錄設備的使用效率和維護狀況"""
    
    EQUIPMENT_TYPE_CHOICES = [
        ('smt', 'SMT設備'),
        ('general', '一般設備'),
        ('test', '測試設備'),
    ]
    
    # 設備資訊
    equipment_name = models.CharField(max_length=100, verbose_name="設備名稱")
    equipment_type = models.CharField(
        max_length=10, 
        choices=EQUIPMENT_TYPE_CHOICES,
        verbose_name="設備類型"
    )
    equipment_model = models.CharField(
        max_length=100, 
        verbose_name="設備型號",
        blank=True
    )
    production_line = models.CharField(
        max_length=50, 
        verbose_name="生產線",
        blank=True
    )
    
    # 使用統計
    total_operation_hours = models.FloatField(verbose_name="總運作時數")
    actual_operation_hours = models.FloatField(verbose_name="實際運作時數")
    idle_hours = models.FloatField(verbose_name="閒置時數")
    maintenance_hours = models.FloatField(verbose_name="維護時數")
    
    # 效率指標
    availability_rate = models.FloatField(verbose_name="可用率 (%)")
    performance_rate = models.FloatField(verbose_name="性能率 (%)")
    quality_rate = models.FloatField(verbose_name="品質率 (%)")
    oee_rate = models.FloatField(verbose_name="整體設備效率 (OEE) (%)")
    
    # 產量統計
    total_output = models.IntegerField(verbose_name="總產出")
    defect_output = models.IntegerField(
        default=0, 
        verbose_name="不良品產出"
    )
    yield_rate = models.FloatField(verbose_name="良率 (%)")
    throughput_rate = models.FloatField(verbose_name="產能利用率 (%)")
    
    # 維護統計
    maintenance_count = models.IntegerField(
        default=0, 
        verbose_name="維護次數"
    )
    breakdown_count = models.IntegerField(
        default=0, 
        verbose_name="故障次數"
    )
    mttr_hours = models.FloatField(
        default=0.0, 
        verbose_name="平均修復時間 (小時)"
    )
    mtbf_hours = models.FloatField(
        default=0.0, 
        verbose_name="平均故障間隔 (小時)"
    )
    
    # 成本統計
    energy_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="能源成本"
    )
    maintenance_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="維護成本"
    )
    total_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="總成本"
    )
    
    class Meta:
        verbose_name = "設備效率報表"
        verbose_name_plural = "設備效率報表"
        unique_together = [
            ['report_type', 'report_date', 'equipment_name']
        ]
        db_table = 'reporting_equipment_efficiency_report'
    
    def __str__(self):
        return f"{self.equipment_name} - {self.report_date}"
    
    def calculate_oee(self):
        """計算整體設備效率 (OEE)"""
        self.oee_rate = round(
            self.availability_rate * self.performance_rate * self.quality_rate / 10000, 2
        )
        return self.oee_rate
    
    def calculate_availability_rate(self):
        """計算可用率"""
        if self.total_operation_hours > 0:
            self.availability_rate = round(
                (self.actual_operation_hours / self.total_operation_hours) * 100, 2
            )
        return self.availability_rate


class QualityAnalysisReport(BaseReportModel):
    """品質分析報表模型 - 記錄品質相關的統計分析"""
    
    # 品質統計
    total_inspected = models.IntegerField(verbose_name="總檢驗數量")
    passed_quantity = models.IntegerField(verbose_name="合格數量")
    failed_quantity = models.IntegerField(verbose_name="不合格數量")
    yield_rate = models.FloatField(verbose_name="良率 (%)")
    
    # 不良品分析
    defect_categories = models.JSONField(
        default=dict, 
        verbose_name="不良品分類統計"
    )
    top_defect_types = models.JSONField(
        default=list, 
        verbose_name="主要不良品類型"
    )
    
    # 品質指標
    customer_complaints = models.IntegerField(
        default=0, 
        verbose_name="客戶投訴數"
    )
    return_rate = models.FloatField(verbose_name="退貨率 (%)")
    quality_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="品質成本"
    )
    
    # 趨勢分析
    quality_trend = models.JSONField(
        default=list, 
        verbose_name="品質趨勢數據"
    )
    improvement_suggestions = models.TextField(
        blank=True, 
        verbose_name="改善建議"
    )
    
    class Meta:
        verbose_name = "品質分析報表"
        verbose_name_plural = "品質分析報表"
        unique_together = [
            ['report_type', 'report_date']
        ]
        db_table = 'reporting_quality_analysis_report'
    
    def __str__(self):
        return f"品質分析報表 - {self.report_date}"
    
    def calculate_yield_rate(self):
        """計算良率"""
        if self.total_inspected > 0:
            self.yield_rate = round(
                (self.passed_quantity / self.total_inspected) * 100, 2
            )
        return self.yield_rate


class ComprehensiveAnalysisReport(BaseReportModel):
    """綜合分析報表模型 - 整合多個維度的綜合分析"""
    
    # 生產效率分析
    total_production_quantity = models.IntegerField(verbose_name="總生產數量")
    total_work_hours = models.FloatField(verbose_name="總工作時數")
    overall_efficiency = models.FloatField(verbose_name="整體效率 (%)")
    capacity_utilization = models.FloatField(verbose_name="產能利用率 (%)")
    
    # 成本分析
    material_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        verbose_name="材料成本"
    )
    labor_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        verbose_name="人工成本"
    )
    overhead_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        verbose_name="間接成本"
    )
    total_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        verbose_name="總成本"
    )
    unit_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="單位成本"
    )
    
    # 品質分析
    overall_yield_rate = models.FloatField(verbose_name="整體良率 (%)")
    quality_cost_rate = models.FloatField(verbose_name="品質成本率 (%)")
    
    # 交期分析
    on_time_delivery_rate = models.FloatField(verbose_name="準時交貨率 (%)")
    average_lead_time = models.FloatField(verbose_name="平均交期 (天)")
    
    # 綜合評分
    production_score = models.FloatField(verbose_name="生產評分")
    quality_score = models.FloatField(verbose_name="品質評分")
    cost_score = models.FloatField(verbose_name="成本評分")
    delivery_score = models.FloatField(verbose_name="交期評分")
    overall_score = models.FloatField(verbose_name="綜合評分")
    
    # 改善建議
    key_improvements = models.JSONField(
        default=list, 
        verbose_name="關鍵改善項目"
    )
    action_plans = models.TextField(
        blank=True, 
        verbose_name="行動計劃"
    )
    
    class Meta:
        verbose_name = "綜合分析報表"
        verbose_name_plural = "綜合分析報表"
        unique_together = [
            ['report_type', 'report_date']
        ]
        db_table = 'reporting_comprehensive_analysis_report'
    
    def __str__(self):
        return f"綜合分析報表 - {self.report_date}"
    
    def calculate_overall_score(self):
        """計算綜合評分"""
        self.overall_score = round(
            (self.production_score + self.quality_score + 
             self.cost_score + self.delivery_score) / 4, 2
        )
        return self.overall_score
    
    def calculate_unit_cost(self):
        """計算單位成本"""
        if self.total_production_quantity > 0:
            self.unit_cost = round(
                self.total_cost / self.total_production_quantity, 2
            )
        return self.unit_cost


# 保留原有的模型以維持向後相容性
class ProductionDailyReport(models.Model):
    """生產日報表數據 - 保留原有模型以維持向後相容性"""
    date = models.DateField(verbose_name="日期")
    operator_or_line = models.CharField(
        max_length=100, verbose_name="作業員/SMT產線", default="未指定"
    )
    equipment_name = models.CharField(
        max_length=100, verbose_name="設備名稱", default="未分配設備"
    )
    line = models.CharField(
        max_length=50,
        verbose_name="生產線",
        choices=[
            ("SMT1", "SMT 線 1"),
            ("SMT2", "SMT 線 2"),
            ("SMT3", "SMT 線 3"),
            ("TEST", "測試設備"),
        ],
    )
    production_quantity = models.IntegerField(verbose_name="生產數量")
    completed_quantity = models.IntegerField(verbose_name="完成數量")
    completion_rate = models.FloatField(verbose_name="完成率 (%)")
    work_hours = models.FloatField(default=0.0, verbose_name="工作時數")
    efficiency_rate = models.FloatField(default=0.0, verbose_name="效率 (%)")
    process_name = models.CharField(
        max_length=100, verbose_name="工序名稱", default="", blank=True
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "生產日報表數據"
        verbose_name_plural = "生產日報表數據"
        unique_together = [["date", "operator_or_line", "equipment_name"]]

    def __str__(self):
        return f"{self.date} - {self.operator_or_line} - {self.equipment_name}"


class OperatorPerformance(models.Model):
    """作業員生產報表數據 - 保留原有模型以維持向後相容性"""
    operator_name = models.CharField(max_length=100, verbose_name="作業員名稱")
    equipment_name = models.CharField(max_length=100, verbose_name="設備名稱")
    production_quantity = models.IntegerField(verbose_name="生產數量")
    equipment_usage_rate = models.FloatField(verbose_name="設備使用率 (%)")
    work_order = models.CharField(
        max_length=100, verbose_name="工單", default="", blank=True
    )
    product_name = models.CharField(
        max_length=100, verbose_name="產品名稱", default="", blank=True
    )
    start_time = models.DateTimeField(verbose_name="開始時間", null=True, blank=True)
    end_time = models.DateTimeField(verbose_name="結束時間", null=True, blank=True)
    date = models.DateField(verbose_name="日期")
    process_name = models.CharField(
        max_length=100, verbose_name="工序名稱", default="", blank=True
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "作業員生產報表數據"
        verbose_name_plural = "作業員生產報表數據"

    def __str__(self):
        return f"{self.operator_name} - {self.equipment_name} - {self.date}"


class ReportingOperationLog(models.Model):
    """報表操作日誌 - 記錄所有報表相關操作"""
    user = models.CharField(max_length=100, verbose_name="用戶")
    action = models.TextField(verbose_name="操作")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="時間戳")

    class Meta:
        verbose_name = "報表操作日誌"
        verbose_name_plural = "報表操作日誌"
        default_permissions = ()

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"


# 移除重複的 ReportSyncSettings 模型定義
# 使用 system.models.ReportSyncSettings 替代


class ReportEmailSchedule(models.Model):
    """報表郵件發送排程設定模型"""
    REPORT_TYPE_CHOICES = [
        ("smt", "SMT生產報表"),
        ("operator", "作業員生產報表"),
        ("production_daily", "生產日報表"),
        ("all", "所有報表"),
    ]

    SCHEDULE_CHOICES = [
        ("daily", "每天"),
        ("weekly", "每週"),
        ("monthly", "每月"),
    ]

    report_type = models.CharField(
        max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name="報表類型"
    )
    schedule_type = models.CharField(
        max_length=10,
        choices=SCHEDULE_CHOICES,
        default="daily",
        verbose_name="發送頻率",
    )
    send_time = models.TimeField(
        verbose_name="發送時間", help_text="每天發送報表的時間"
    )
    recipients = models.TextField(
        verbose_name="收件人郵箱", help_text="多個郵箱請用逗號分隔"
    )
    cc_recipients = models.TextField(
        blank=True, verbose_name="副本收件人", help_text="多個郵箱請用逗號分隔"
    )
    subject_template = models.CharField(
        max_length=200,
        default="MES 系統 - {report_type} - {date}",
        verbose_name="郵件主旨模板",
    )
    is_active = models.BooleanField(default=True, verbose_name="啟用發送")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "報表郵件發送設定"
        verbose_name_plural = "報表郵件發送設定"
        unique_together = [["report_type", "schedule_type"]]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.get_schedule_type_display()} - {self.send_time}"

    def get_recipient_list(self):
        """取得收件人列表"""
        if not self.recipients:
            return []
        return [email.strip() for email in self.recipients.split(",") if email.strip()]

    def get_cc_list(self):
        """取得副本收件人列表"""
        if not self.cc_recipients:
            return []
        return [
            email.strip() for email in self.cc_recipients.split(",") if email.strip()
        ]


class ReportEmailLog(models.Model):
    """報表郵件發送記錄模型"""
    STATUS_CHOICES = [
        ("success", "發送成功"),
        ("failed", "發送失敗"),
        ("pending", "等待發送"),
    ]

    schedule = models.ForeignKey(
        ReportEmailSchedule, on_delete=models.CASCADE, verbose_name="發送設定"
    )
    report_type = models.CharField(max_length=20, verbose_name="報表類型")
    recipients = models.TextField(verbose_name="收件人")
    subject = models.CharField(max_length=200, verbose_name="郵件主旨")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="發送狀態",
    )
    error_message = models.TextField(blank=True, verbose_name="錯誤訊息")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="發送時間")

    class Meta:
        verbose_name = "報表郵件發送記錄"
        verbose_name_plural = "報表郵件發送記錄"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.report_type} - {self.status} - {self.sent_at}"


class ManufacturingWorkHour(models.Model):
    """製造工時單模型 - 對應 Excel 匯入欄位"""
    operator = models.CharField(max_length=50, verbose_name="作業員")
    company = models.CharField(max_length=50, verbose_name="公司別")
    date = models.DateField(verbose_name="日期")
    start_time = models.CharField(max_length=10, verbose_name="開始時間")
    end_time = models.CharField(max_length=10, verbose_name="完成時間")
    order_number = models.CharField(max_length=50, verbose_name="製令號碼")
    equipment_name = models.CharField(max_length=100, verbose_name="機種名稱")
    work_content = models.CharField(max_length=100, verbose_name="工作內容")
    good_qty = models.IntegerField(verbose_name="良品數量（只填數字）")
    defect_qty = models.IntegerField(verbose_name="不良品數量（沒有請填0）")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "製造工時單"
        verbose_name_plural = "製造工時單"

    def __str__(self):
        return f"{self.date} {self.operator} {self.order_number}"


# 在現有模型後面新增報表資料儲存模型

class WorkTimeReportCache(models.Model):
    """
    工作時間報表快取模型
    用於儲存預計算的報表數據，提升查詢效能
    """
    
    # 報表類型
    REPORT_TYPE_CHOICES = [
        ('daily', '日報'),
        ('weekly', '週報'),
        ('monthly', '月報'),
    ]
    
    # 基本資訊
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name="報表類型")
    report_date = models.DateField(verbose_name="報表日期")
    period_start = models.DateField(verbose_name="期間開始")
    period_end = models.DateField(verbose_name="期間結束")
    
    # 統計數據
    total_work_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總工作時數")
    total_completed_quantity = models.IntegerField(default=0, verbose_name="總完成數量")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="總不良品數量")
    worker_count = models.IntegerField(default=0, verbose_name="參與作業員數")
    workorder_count = models.IntegerField(default=0, verbose_name="工單數量")
    avg_efficiency_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="平均效率")
    avg_yield_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="平均良率")
    
    # 詳細數據（JSON格式儲存）
    detail_data = models.JSONField(default=dict, verbose_name="詳細數據")
    
    # 快取資訊
    cache_key = models.CharField(max_length=100, unique=True, verbose_name="快取鍵值")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")
    data_source = models.CharField(max_length=50, default="workorder", verbose_name="數據來源")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "工作時間報表快取"
        verbose_name_plural = "工作時間報表快取"
        db_table = 'reporting_work_time_cache'
        indexes = [
            models.Index(fields=['report_type', 'report_date']),
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['cache_key']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.report_date}"
    
    @classmethod
    def generate_cache_key(cls, report_type, start_date, end_date, **kwargs):
        """生成快取鍵值"""
        key_parts = [report_type, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d')]
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}_{value}")
        return "_".join(key_parts)


class WorkerPerformanceCache(models.Model):
    """
    作業員績效快取模型
    用於儲存作業員績效統計數據
    """
    
    # 基本資訊
    worker_name = models.CharField(max_length=100, verbose_name="作業員姓名")
    worker_type = models.CharField(max_length=20, verbose_name="作業員類型")
    period_start = models.DateField(verbose_name="期間開始")
    period_end = models.DateField(verbose_name="期間結束")
    
    # 績效數據
    total_work_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總工作時數")
    total_completed_quantity = models.IntegerField(default=0, verbose_name="總完成數量")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="總不良品數量")
    workorder_count = models.IntegerField(default=0, verbose_name="工單數量")
    report_count = models.IntegerField(default=0, verbose_name="報工次數")
    efficiency_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="效率")
    yield_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="良率")
    avg_hourly_output = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="平均每小時產出")
    
    # 快取資訊
    cache_key = models.CharField(max_length=100, unique=True, verbose_name="快取鍵值")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "作業員績效快取"
        verbose_name_plural = "作業員績效快取"
        db_table = 'reporting_worker_performance_cache'
        indexes = [
            models.Index(fields=['worker_name', 'period_start', 'period_end']),
            models.Index(fields=['worker_type']),
            models.Index(fields=['cache_key']),
        ]
    
    def __str__(self):
        return f"{self.worker_name} - {self.period_start} ~ {self.period_end}"


class WorkOrderSummaryCache(models.Model):
    """
    工單摘要快取模型
    用於儲存工單統計數據
    """
    
    # 基本資訊
    workorder_number = models.CharField(max_length=50, verbose_name="工單號碼")
    product_code = models.CharField(max_length=100, verbose_name="產品編號")
    period_start = models.DateField(verbose_name="期間開始")
    period_end = models.DateField(verbose_name="期間結束")
    
    # 統計數據
    total_work_hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="總工作時數")
    total_completed_quantity = models.IntegerField(default=0, verbose_name="總完成數量")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="總不良品數量")
    worker_count = models.IntegerField(default=0, verbose_name="參與作業員數")
    process_count = models.IntegerField(default=0, verbose_name="工序數量")
    report_count = models.IntegerField(default=0, verbose_name="報工次數")
    efficiency_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="效率")
    yield_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="良率")
    avg_hourly_output = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="平均每小時產出")
    
    # 快取資訊
    cache_key = models.CharField(max_length=100, unique=True, verbose_name="快取鍵值")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "工單摘要快取"
        verbose_name_plural = "工單摘要快取"
        db_table = 'reporting_workorder_summary_cache'
        indexes = [
            models.Index(fields=['workorder_number', 'period_start', 'period_end']),
            models.Index(fields=['product_code']),
            models.Index(fields=['cache_key']),
        ]
    
    def __str__(self):
        return f"{self.workorder_number} - {self.period_start} ~ {self.period_end}"


# 移除重複的 ReportDataSyncLog 模型定義
# 使用 system.models.ReportDataSyncLog 替代
