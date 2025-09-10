from django.db import models
from django.utils import timezone
import logging


class Material(models.Model):
    """
    材料主檔：記錄所有材料的基本資料（從 ERP 同步）
    """

    name = models.CharField(
        max_length=200, verbose_name="材料名稱", null=True, blank=True
    )
    code = models.CharField(
        max_length=50, verbose_name="材料編號", null=True, blank=True
    )
    category = models.CharField(
        max_length=100, verbose_name="材料分類", null=True, blank=True
    )
    unit = models.CharField(max_length=20, verbose_name="單位", null=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="建立時間", null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    company_code = models.CharField(
        max_length=20, verbose_name="公司編號", null=True, blank=True
    )

    class Meta:
        verbose_name = "材料"
        verbose_name_plural = "材料管理"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Product(models.Model):
    """
    產品主檔：記錄所有產品的基本資料（從 ERP 同步）
    """

    name = models.CharField(
        max_length=200, verbose_name="產品名稱", null=True, blank=True
    )
    code = models.CharField(
        max_length=50, verbose_name="產品編號", null=True, blank=True
    )
    category = models.CharField(
        max_length=100, verbose_name="產品分類", null=True, blank=True
    )
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="建立時間", null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "產品"
        verbose_name_plural = "產品管理"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Process(models.Model):
    """
    工序資料：記錄生產工序的基本資料
    """

    name = models.CharField(
        max_length=100, verbose_name="工序名稱", null=True, blank=True
    )
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="建立時間", null=True, blank=True
    )

    class Meta:
        verbose_name = "工序"
        verbose_name_plural = "工序管理"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Route(models.Model):
    """
    工藝路線：記錄產品的生產工藝路線
    """

    name = models.CharField(
        max_length=200, verbose_name="路線名稱", null=True, blank=True
    )
    product_id = models.CharField(max_length=50, verbose_name="產品ID")
    product_name = models.CharField(max_length=200, verbose_name="產品名稱")
    step_order = models.IntegerField(verbose_name="步驟順序", null=True, blank=True)
    process_id = models.CharField(max_length=50, verbose_name="工序ID")
    process_name = models.CharField(max_length=200, verbose_name="工序名稱")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="建立時間", null=True, blank=True
    )

    class Meta:
        verbose_name = "工藝路線"
        verbose_name_plural = "工藝路線管理"
        ordering = ["product_id", "step_order"]
        unique_together = ["product_id", "step_order"]

    def __str__(self):
        return f"{self.product_name} - {self.name}"


class MaterialRequirement(models.Model):
    """
    物料需求：記錄產品的材料需求（BOM 結構）
    """

    product_id = models.CharField(max_length=50, verbose_name="產品ID")
    product_name = models.CharField(max_length=200, verbose_name="產品名稱")
    material_id = models.CharField(max_length=50, verbose_name="材料ID")
    material_name = models.CharField(max_length=200, verbose_name="材料名稱")
    quantity_per_unit = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="單位用量"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    class Meta:
        verbose_name = "物料需求"
        verbose_name_plural = "物料需求管理"
        unique_together = ["product_id", "material_id"]
        ordering = ["product_id", "material_id"]

    def __str__(self):
        return f"{self.product_name} - {self.material_name}"


class MaterialInventory(models.Model):
    """
    材料庫存：從 ERP 同步的即時庫存數量（唯讀）
    """

    material_id = models.CharField(max_length=50, verbose_name="材料ID")
    material_name = models.CharField(max_length=200, verbose_name="材料名稱")
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="庫存數量"
    )
    last_sync_time = models.DateTimeField(
        auto_now=True, verbose_name="最後同步時間", null=True, blank=True
    )
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ("synced", "已同步"),
            ("pending", "待同步"),
            ("error", "同步錯誤"),
        ],
        default="pending",
        verbose_name="同步狀態",
    )

    class Meta:
        verbose_name = "材料庫存"
        verbose_name_plural = "材料庫存管理"
        unique_together = ["material_id"]

    def __str__(self):
        return f"{self.material_name} - {self.quantity}"


class MaterialShortageAlert(models.Model):
    """
    缺料警告：當庫存不足以支援生產時發出警告
    """

    material_id = models.CharField(max_length=50, verbose_name="材料ID")
    material_name = models.CharField(max_length=200, verbose_name="材料名稱")
    work_order = models.CharField(
        max_length=50, verbose_name="影響工單", null=True, blank=True
    )
    required_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="需求數量"
    )
    available_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="可用數量"
    )
    shortage_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="短缺數量"
    )
    alert_level = models.CharField(
        max_length=20,
        choices=[
            ("low", "低"),
            ("medium", "中"),
            ("high", "高"),
            ("critical", "緊急"),
        ],
        default="medium",
        verbose_name="警告等級",
    )
    is_resolved = models.BooleanField(default=False, verbose_name="是否已解決")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="解決時間")

    class Meta:
        verbose_name = "缺料警告"
        verbose_name_plural = "缺料警告管理"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.material_name} - 短缺 {self.shortage_quantity}"


class MaterialSupplyPlan(models.Model):
    """
    物料供應計劃：根據生產排程規劃物料供應
    """

    work_order = models.CharField(
        max_length=50, verbose_name="工單號", null=True, blank=True
    )
    material_id = models.CharField(max_length=50, verbose_name="材料ID")
    material_name = models.CharField(max_length=200, verbose_name="材料名稱")
    planned_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="計劃用量"
    )
    supply_time = models.DateTimeField(verbose_name="供應時間")
    supply_location = models.CharField(
        max_length=100, verbose_name="供應位置", null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("planned", "已計劃"),
            ("in_transit", "運輸中"),
            ("arrived", "已到達"),
            ("consumed", "已消耗"),
            ("cancelled", "已取消"),
        ],
        default="planned",
        verbose_name="狀態",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    class Meta:
        verbose_name = "物料供應計劃"
        verbose_name_plural = "物料供應計劃管理"
        ordering = ["supply_time"]

    def __str__(self):
        return f"{self.work_order} - {self.material_name} - {self.planned_quantity}"


class MaterialKanban(models.Model):
    """
    物料看板：用於 JIT 供料的看板管理
    """

    material_id = models.CharField(max_length=50, verbose_name="材料ID")
    material_name = models.CharField(max_length=200, verbose_name="材料名稱")
    kanban_type = models.CharField(
        max_length=20,
        choices=[
            ("production", "生產看板"),
            ("withdrawal", "取料看板"),
            ("supplier", "供應商看板"),
        ],
        verbose_name="看板類型",
    )
    kanban_number = models.CharField(
        max_length=50, verbose_name="看板編號", unique=True
    )
    quantity_per_kanban = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="看板數量"
    )
    current_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="當前數量"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("full", "滿"),
            ("partial", "部分"),
            ("empty", "空"),
        ],
        default="full",
        verbose_name="狀態",
    )
    location = models.CharField(
        max_length=100, verbose_name="位置", null=True, blank=True
    )
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")

    class Meta:
        verbose_name = "物料看板"
        verbose_name_plural = "物料看板管理"
        ordering = ["kanban_number"]

    def __str__(self):
        return f"{self.kanban_number} - {self.material_name}"


class MaterialInventoryManagement(models.Model):
    """
    庫存管理：管理材料的庫存進出、盤點、安全庫存等
    """

    material_id = models.CharField(max_length=50, verbose_name="材料ID")
    material_name = models.CharField(max_length=200, verbose_name="材料名稱")
    warehouse = models.CharField(
        max_length=100, verbose_name="倉庫位置", null=True, blank=True
    )
    current_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="當前庫存"
    )
    safety_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="安全庫存"
    )
    max_stock = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="最大庫存"
    )
    reorder_point = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="補貨點"
    )
    reorder_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="補貨數量"
    )
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="單位成本"
    )
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")

    # 庫存狀態
    stock_status = models.CharField(
        max_length=20,
        choices=[
            ("normal", "正常"),
            ("low", "低庫存"),
            ("out", "缺貨"),
            ("excess", "過剩"),
        ],
        default="normal",
        verbose_name="庫存狀態",
    )

    class Meta:
        verbose_name = "庫存管理"
        verbose_name_plural = "庫存管理"
        unique_together = ["material_id", "warehouse"]
        ordering = ["material_name"]

    def __str__(self):
        return f"{self.material_name} - {self.warehouse} - {self.current_stock}"

    def calculate_stock_status(self):
        """計算庫存狀態"""
        if self.current_stock <= 0:
            return "out"
        elif self.current_stock <= self.safety_stock:
            return "low"
        elif self.current_stock >= self.max_stock:
            return "excess"
        else:
            return "normal"


class MaterialRequirementEstimation(models.Model):
    """
    物料需求估算：根據生產計劃和歷史數據估算物料需求
    """

    material_id = models.CharField(max_length=50, verbose_name="材料ID")
    material_name = models.CharField(max_length=200, verbose_name="材料名稱")
    estimation_date = models.DateField(verbose_name="估算日期")
    period_start = models.DateField(verbose_name="期間開始")
    period_end = models.DateField(verbose_name="期間結束")

    # 需求估算
    estimated_demand = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="估算需求"
    )
    actual_demand = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="實際需求"
    )
    forecast_accuracy = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="預測準確率(%)"
    )

    # 供應計劃
    planned_supply = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="計劃供應"
    )
    actual_supply = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="實際供應"
    )

    # 庫存預測
    beginning_stock = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="期初庫存"
    )
    ending_stock = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="期末庫存"
    )

    # 估算方法
    estimation_method = models.CharField(
        max_length=20,
        choices=[
            ("historical", "歷史平均"),
            ("trend", "趨勢分析"),
            ("seasonal", "季節性分析"),
            ("manual", "手動估算"),
            ("ai", "AI預測"),
        ],
        default="historical",
        verbose_name="估算方法",
    )

    # 狀態
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "草稿"),
            ("confirmed", "已確認"),
            ("in_progress", "執行中"),
            ("completed", "已完成"),
            ("cancelled", "已取消"),
        ],
        default="draft",
        verbose_name="狀態",
    )

    notes = models.TextField(blank=True, null=True, verbose_name="備註")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "物料需求估算"
        verbose_name_plural = "物料需求估算"
        ordering = ["-estimation_date", "material_name"]
        unique_together = ["material_id", "estimation_date", "period_start", "period_end"]

    def __str__(self):
        return f"{self.material_name} - {self.period_start} 至 {self.period_end}"

    def calculate_forecast_accuracy(self):
        """計算預測準確率"""
        if self.estimated_demand > 0:
            accuracy = (
                abs(self.actual_demand - self.estimated_demand)
                / self.estimated_demand
                * 100
            )
            return min(100, max(0, 100 - accuracy))
        return 0


class MaterialTransaction(models.Model):
    """
    物料交易記錄：記錄所有庫存進出交易
    """

    material_id = models.CharField(max_length=50, verbose_name="材料ID")
    material_name = models.CharField(max_length=200, verbose_name="材料名稱")
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ("in", "入庫"),
            ("out", "出庫"),
            ("transfer", "調撥"),
            ("adjustment", "調整"),
            ("return", "退貨"),
        ],
        verbose_name="交易類型",
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="數量")
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="單位成本"
    )
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="總成本"
    )

    # 來源和目標
    from_location = models.CharField(
        max_length=100, verbose_name="來源位置", null=True, blank=True
    )
    to_location = models.CharField(
        max_length=100, verbose_name="目標位置", null=True, blank=True
    )

    # 關聯單據
    reference_no = models.CharField(
        max_length=50, verbose_name="參考單號", null=True, blank=True
    )
    reference_type = models.CharField(
        max_length=20,
        choices=[
            ("purchase_order", "採購單"),
            ("work_order", "工單"),
            ("transfer_order", "調撥單"),
            ("adjustment", "調整單"),
            ("return", "退貨單"),
        ],
        verbose_name="參考類型",
    )

    # 批次和效期
    batch_no = models.CharField(
        max_length=50, verbose_name="批次號", null=True, blank=True
    )
    expiry_date = models.DateField(verbose_name="效期", null=True, blank=True)

    notes = models.TextField(blank=True, null=True, verbose_name="備註")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    created_by = models.CharField(
        max_length=50, verbose_name="建立者", null=True, blank=True
    )

    class Meta:
        verbose_name = "物料交易記錄"
        verbose_name_plural = "物料交易記錄"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.material_name} - {self.transaction_type} - {self.quantity}"

    def save(self, *args, **kwargs):
        """自動計算總成本"""
        if self.quantity and self.unit_cost:
            self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


# 以下為物料管理模組的操作日誌模型
class MaterialOperationLog(models.Model):
    """
    物料管理操作日誌：記錄用戶在物料管理模組的所有操作（如查詢、匯入、匯出、異常等）
    """

    user = models.CharField(
        max_length=50, 
        verbose_name="操作用戶",
        help_text="操作用戶名稱（非外鍵關係，純文字欄位）"
    )
    action = models.CharField(max_length=200, verbose_name="操作內容")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="操作時間")
    notes = models.TextField(blank=True, null=True, verbose_name="備註")

    class Meta:
        verbose_name = "物料操作日誌"
        verbose_name_plural = "物料操作日誌"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} {self.user} {self.action}"
