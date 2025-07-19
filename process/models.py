from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal

class ProcessEquipment(models.Model):
    """
    工序設備對應表：記錄每個工序可用的設備。
    """
    process_name = models.ForeignKey('ProcessName', on_delete=models.CASCADE, related_name='equipments', verbose_name="工序名稱")
    equipment_id = models.IntegerField(verbose_name="設備 ID")

    class Meta:
        verbose_name = "工序設備"
        verbose_name_plural = "工序設備"
        unique_together = ('process_name', 'equipment_id')  # 確保唯一性
        default_permissions = ()

    def __str__(self):
        return f"{self.process_name.name} - 設備 ID: {self.equipment_id}"

# 更新 ProcessName 模型，移除舊字段
class ProcessName(models.Model):
    """
    工序名稱表：定義所有工序的名稱與描述。
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="工序名稱")
    description = models.TextField(blank=True, verbose_name="描述")
    usable_equipment_ids = None  # 移除舊字段
    usable_smt_equipment_ids = None  # 移除舊字段

    class Meta:
        verbose_name = "工序名稱"
        verbose_name_plural = "工序名稱"
        default_permissions = ()
        permissions = [
            ("can_view_process_name", "可以查看工序名稱"),
            ("can_add_process_name", "可以添加工序名稱"),
            ("can_edit_process_name", "可以編輯工序名稱"),
            ("can_delete_process_name", "可以刪除工序名稱"),
        ]

    def __str__(self):
        return self.name

class Operator(models.Model):
    """
    作業員表：記錄所有作業員的基本資料。
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="作業員名稱")
    production_line = models.ForeignKey(
        'production.ProductionLine',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="所屬產線",
        help_text="此作業員所屬的生產線"
    )
    created_at = models.DateTimeField("建立時間", auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "作業員"
        verbose_name_plural = "作業員"
        default_permissions = ()
        permissions = [
            ("can_view_operator", "可以查看作業員"),
            ("can_add_operator", "可以添加作業員"),
            ("can_edit_operator", "可以編輯作業員"),
            ("can_delete_operator", "可以刪除作業員"),
        ]

    def __str__(self):
        return self.name

class OperatorSkill(models.Model):
    """
    作業員技能表：記錄每位作業員擅長的工序與優先順序。
    """
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, related_name="skills", verbose_name="作業員")
    process_name = models.ForeignKey(ProcessName, on_delete=models.CASCADE, verbose_name="工序名稱")
    priority = models.IntegerField(verbose_name="優先順序", validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "作業員技能"
        verbose_name_plural = "作業員技能"
        default_permissions = ()

    def __str__(self):
        return f"{self.operator.name} - {self.process_name.name} (優先順序: {self.priority})"

class ProductProcessRoute(models.Model):
    """
    產品工序路線表：定義每個產品的工序順序與可用設備。
    """
    product_id = models.CharField(max_length=100, verbose_name="產品編號")
    process_name = models.ForeignKey('ProcessName', on_delete=models.CASCADE, verbose_name="工序名稱")
    step_order = models.IntegerField(verbose_name="工序順序", validators=[MinValueValidator(1)])
    # capacity_per_hour = models.IntegerField(verbose_name="每小時產能", validators=[MinValueValidator(0)])  # 已移除，不再使用
    usable_equipment_ids = models.CharField(max_length=500, blank=True, verbose_name="指定可用設備 ID 列表")
    dependent_semi_product = models.CharField(max_length=100, blank=True, null=True, verbose_name="依賴半成品")

    class Meta:
        db_table = 'process_productroute'  # 明確指定表名
        verbose_name = "產品工序路線"
        verbose_name_plural = "產品工序路線"
        default_permissions = ()
        unique_together = ('product_id', 'step_order')
        permissions = [
            ("can_view_product_route", "可以查看產品工序路線"),
            ("can_add_product_route", "可以添加產品工序路線"),
            ("can_edit_product_route", "可以編輯產品工序路線"),
            ("can_delete_product_route", "可以刪除產品工序路線"),
        ]

    def __str__(self):
        return f"{self.product_id} - {self.process_name.name} (步驟 {self.step_order})"

class ProcessOperationLog(models.Model):
    """
    工序操作日誌：記錄用戶操作歷史。
    """
    user = models.CharField(max_length=100, verbose_name="用戶")
    action = models.TextField(verbose_name="操作")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="時間戳")

    class Meta:
        verbose_name = "工序操作日誌"
        verbose_name_plural = "工序操作日誌"
        default_permissions = ()

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"

class ProductProcessStandardCapacity(models.Model):
    """
    產品工序標準產能表：記錄每種產品、工序、設備、作業員等級的標準產能與相關參數。
    支援多維度產能設定，並可計算實際產能、總工時、設備利用率。
    """
    # 基本資訊
    product_code = models.CharField("產品編號", max_length=50, default="")
    process_name = models.CharField("工序名稱", max_length=50, default="")
    
    # 產能維度設定
    equipment_type = models.CharField(
        "設備類型", max_length=20, default="standard",
        choices=[
            ('standard', '標準設備'),
            ('smt', 'SMT設備'),
            ('dip', 'DIP設備'),
            ('test', '測試設備'),
            ('packaging', '包裝設備'),
        ]
    )
    operator_level = models.CharField(
        "作業員等級", max_length=20, default="standard",
        choices=[
            ('beginner', '新手'),
            ('standard', '標準'),
            ('expert', '熟手'),
            ('master', '大師'),
        ]
    )
    
    # 產能參數
    standard_capacity_per_hour = models.PositiveIntegerField("標準每小時產能")
    min_capacity_per_hour = models.PositiveIntegerField("最低每小時產能")
    max_capacity_per_hour = models.PositiveIntegerField("最高每小時產能")
    
    # 時間因素
    setup_time_minutes = models.PositiveIntegerField("換線準備時間(分鐘)")
    teardown_time_minutes = models.PositiveIntegerField("收線時間(分鐘)")
    cycle_time_seconds = models.DecimalField("標準週期時間(秒)", max_digits=6, decimal_places=2)
    
    # 批量設定
    optimal_batch_size = models.PositiveIntegerField("最佳批量大小")
    min_batch_size = models.PositiveIntegerField("最小批量大小")
    max_batch_size = models.PositiveIntegerField("最大批量大小")
    
    # 效率因子
    efficiency_factor = models.DecimalField("效率因子", max_digits=3, decimal_places=2)
    learning_curve_factor = models.DecimalField("學習曲線因子", max_digits=3, decimal_places=2)
    
    # 品質因素
    expected_defect_rate = models.DecimalField("預期不良率", max_digits=5, decimal_places=4)
    rework_time_factor = models.DecimalField("重工時間因子", max_digits=3, decimal_places=2)
    
    # 版本控制
    version = models.PositiveIntegerField("版本號", default=1)  # 預設為 1，避免為空值
    effective_date = models.DateField("生效日期", auto_now_add=True, null=True, blank=True)
    expiry_date = models.DateField("失效日期", null=True, blank=True)
    is_active = models.BooleanField("是否啟用", default=True)
    
    # 審核資訊
    created_by = models.CharField("建立者", max_length=100, blank=True)
    approved_by = models.CharField("核准者", max_length=100, blank=True)
    approval_date = models.DateTimeField("核准日期", null=True, blank=True)
    
    # 備註
    notes = models.TextField("備註", blank=True)
    
    # 時間戳
    created_at = models.DateTimeField("建立時間", auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("product_code", "process_name", "equipment_type", "operator_level", "version")
        verbose_name = "產品工序標準產能"
        verbose_name_plural = "產品工序標準產能"
        ordering = ['product_code', 'process_name', 'equipment_type', 'operator_level', '-version']

    def __str__(self):
        return f"{self.product_code} - {self.process_name} - {self.equipment_type} - {self.operator_level} (v{self.version})"
    
    def get_effective_capacity(self, batch_size=None, actual_efficiency=None):
        """
        計算實際有效產能
        :param batch_size: 實際批量大小
        :param actual_efficiency: 實際效率因子
        :return: 每小時有效產能
        """
        base_capacity = self.standard_capacity_per_hour or 0
        
        # 應用效率因子
        efficiency = Decimal(str(actual_efficiency)) if actual_efficiency is not None else (self.efficiency_factor or Decimal('1.00'))
        effective_capacity = Decimal(str(base_capacity)) * efficiency
        
        # 應用學習曲線因子
        effective_capacity *= self.learning_curve_factor or Decimal('1.00')
        
        # 批量調整（如果指定）
        if batch_size:
            batch_size = int(batch_size)
            if batch_size < (self.min_batch_size or 1):
                batch_factor = Decimal(str(batch_size)) / Decimal(str(self.min_batch_size or 1))
                effective_capacity *= batch_factor
            elif batch_size > (self.optimal_batch_size or 1):
                batch_factor = min(Decimal('1.2'), Decimal('1') + (Decimal(str(batch_size)) - Decimal(str(self.optimal_batch_size or 1))) / Decimal(str(self.optimal_batch_size or 1)) * Decimal('0.1'))
                effective_capacity *= batch_factor
        
        return round(effective_capacity, 2)
    
    def get_total_time_for_batch(self, batch_size):
        """
        計算完成指定批量所需的總時間（分鐘）
        :param batch_size: 批量大小
        :return: 總時間（分鐘）
        """
        # 準備時間
        total_time = Decimal(str(self.setup_time_minutes or 0))
        
        # 生產時間
        effective_capacity = self.get_effective_capacity(batch_size)
        if effective_capacity > 0:
            production_time = (Decimal(str(batch_size)) / effective_capacity) * Decimal('60')  # 轉換為分鐘
            total_time += production_time
        
        # 收線時間
        total_time += Decimal(str(self.teardown_time_minutes or 0))
        
        # 考慮重工時間
        if self.expected_defect_rate and self.expected_defect_rate > 0:
            defect_quantity = Decimal(str(batch_size)) * self.expected_defect_rate
            rework_time = (defect_quantity / effective_capacity) * Decimal('60') * (self.rework_time_factor or Decimal('1.00'))
            total_time += rework_time
        
        return round(total_time, 2)
    
    def get_utilization_rate(self, actual_output, actual_time_hours):
        """
        計算設備利用率
        :param actual_output: 實際產出
        :param actual_time_hours: 實際工時
        :return: 利用率百分比
        """
        if not actual_time_hours or actual_time_hours <= 0:
            return 0
        
        actual_capacity = Decimal(str(actual_output)) / Decimal(str(actual_time_hours))
        theoretical_capacity = Decimal(str(self.standard_capacity_per_hour or 0))
        
        if theoretical_capacity <= 0:
            return 0
        
        utilization = (actual_capacity / theoretical_capacity) * Decimal('100')
        return round(utilization, 2)

class CapacityHistory(models.Model):
    """
    產能歷史記錄表：追蹤產能標準的變更歷史。
    """
    capacity = models.ForeignKey(ProductProcessStandardCapacity, on_delete=models.CASCADE, related_name='history')
    change_type = models.CharField("變更類型", max_length=20, choices=[
        ('created', '建立'),
        ('updated', '更新'),
        ('deactivated', '停用'),
        ('reactivated', '重新啟用'),
    ])
    old_values = models.JSONField("舊值", null=True, blank=True)
    new_values = models.JSONField("新值", null=True, blank=True)
    change_reason = models.TextField("變更原因", blank=True)
    changed_by = models.CharField("變更者", max_length=100)
    changed_at = models.DateTimeField("變更時間", auto_now_add=True)
    
    class Meta:
        verbose_name = "產能歷史記錄"
        verbose_name_plural = "產能歷史記錄"
        ordering = ['-changed_at']

class CapacityTemplate(models.Model):
    """
    產能模板表：預定義的產能設定模板，方便快速建立標準產能。
    """
    template_name = models.CharField("模板名稱", max_length=100)
    process_name = models.CharField("工序名稱", max_length=50)
    equipment_type = models.CharField("設備類型", max_length=20)
    operator_level = models.CharField("作業員等級", max_length=20)
    
    # 標準參數
    standard_capacity_per_hour = models.PositiveIntegerField("標準每小時產能")
    setup_time_minutes = models.PositiveIntegerField("換線準備時間(分鐘)", default=0)
    cycle_time_seconds = models.DecimalField("標準週期時間(秒)", max_digits=6, decimal_places=2, default=0)
    efficiency_factor = models.DecimalField("效率因子", max_digits=3, decimal_places=2, default=1.0)
    
    # 適用範圍
    applicable_products = models.TextField("適用產品類型", blank=True, help_text="產品編號前綴或關鍵字，用逗號分隔")
    description = models.TextField("描述", blank=True)
    
    is_active = models.BooleanField("是否啟用", default=True)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    
    class Meta:
        verbose_name = "產能模板"
        verbose_name_plural = "產能模板"
        unique_together = ("template_name", "process_name", "equipment_type", "operator_level")

    def __str__(self):
        return f"{self.template_name} - {self.process_name} - {self.equipment_type}"
