from django.db import models
from django.utils import timezone


class KanbanProductionProgress(models.Model):
    work_order_number = models.CharField(max_length=50, verbose_name="工單編號")
    product_name = models.CharField(max_length=100, verbose_name="產品名稱")
    total_quantity = models.IntegerField(verbose_name="總數量")
    completed_quantity = models.IntegerField(verbose_name="完成數量")
    progress = models.FloatField(verbose_name="進度 (%)")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "生產進度看板數據"
        verbose_name_plural = "生產進度看板數據"

    def __str__(self):
        return f"工單 {self.work_order_number}"


class KanbanEquipmentStatus(models.Model):
    equipment_name = models.CharField(max_length=100, verbose_name="設備名稱")
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
    status = models.CharField(
        max_length=20,
        verbose_name="狀態",
        choices=[
            ("running", "運行中"),
            ("stopped", "停機"),
            ("fault", "故障"),
        ],
    )
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")

    class Meta:
        verbose_name = "設備狀態看板數據"
        verbose_name_plural = "設備狀態看板數據"

    def __str__(self):
        return f"{self.line} - {self.equipment_name}"


class KanbanQualityMonitoring(models.Model):
    product_name = models.CharField(max_length=100, verbose_name="產品名稱")
    defect_rate = models.FloatField(verbose_name="不合格率 (%)")
    total_inspected = models.IntegerField(verbose_name="總檢驗數量")
    defective_count = models.IntegerField(verbose_name="不合格數量")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")

    class Meta:
        verbose_name = "品質監控看板數據"
        verbose_name_plural = "品質監控看板數據"

    def __str__(self):
        return f"產品 {self.product_name}"


class KanbanMaterialStock(models.Model):
    material_code = models.CharField(max_length=50, verbose_name="物料編號")
    material_name = models.CharField(max_length=100, verbose_name="物料名稱")
    stock_quantity = models.IntegerField(verbose_name="庫存數量")
    unit = models.CharField(max_length=20, verbose_name="單位")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")

    class Meta:
        verbose_name = "物料存量看板數據"
        verbose_name_plural = "物料存量看板數據"

    def __str__(self):
        return f"物料 {self.material_code}"


class KanbanDeliverySchedule(models.Model):
    order_number = models.CharField(max_length=50, verbose_name="訂單編號")
    product_name = models.CharField(max_length=100, verbose_name="產品名稱")
    quantity = models.IntegerField(verbose_name="訂單數量")
    due_date = models.DateField(verbose_name="預定交貨日期")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "預交貨日看板數據"
        verbose_name_plural = "預交貨日看板數據"

    def __str__(self):
        return f"訂單 {self.order_number}"


class KanbanOperationLog(models.Model):
    user = models.CharField(max_length=100, verbose_name="用戶")
    action = models.TextField(verbose_name="操作")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="時間戳")

    class Meta:
        verbose_name = "看板操作日誌"
        verbose_name_plural = "看板操作日誌"
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"
