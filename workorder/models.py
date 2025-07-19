from django.db import models
from django.utils import timezone
from process.models import Operator
from equip.models import Equipment
import logging


class WorkOrder(models.Model):
    """
    工單管理模型：支援多公司唯一識別，記錄每一張工單的基本資料與狀態
    """

    # 狀態選項定義
    STATUS_CHOICES = [
        ("pending", "待生產"),
        ("in_progress", "生產中"),
        ("completed", "已完成"),
    ]

    company_code = models.CharField(
        max_length=10, verbose_name="公司代號", null=True, blank=True
    )  # 例如 01、02、03，可為空，方便資料庫遷移
    order_number = models.CharField(max_length=50, verbose_name="製令單號")
    product_code = models.CharField(
        max_length=100, verbose_name="產品編號"
    )  # 產品編號，原本是 product_name
    quantity = models.PositiveIntegerField(verbose_name="數量")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="狀態",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    objects = models.Manager()  # 明確宣告 objects manager，解決 linter 錯誤

    class Meta:
        verbose_name = "工單"
        verbose_name_plural = "工單管理"
        unique_together = (("company_code", "order_number"),)  # 公司代號+製令單號唯一

    def __str__(self):
        return f"[{self.company_code}] 製令單 {self.order_number}"


# 製令主檔（prdMKOrdMain）
class PrdMKOrdMain(models.Model):
    row_id = models.BigAutoField(primary_key=True, verbose_name="主鍵ID")
    Flag = models.IntegerField(verbose_name="狀態Flag")
    MKOrdNO = models.CharField(max_length=30, verbose_name="製令單號")
    MKOrdDate = models.CharField(
        max_length=20, verbose_name="製令日期", blank=True, null=True
    )
    MakeType = models.CharField(
        max_length=20, verbose_name="製令類型", blank=True, null=True
    )
    FromRowNO = models.CharField(
        max_length=20, verbose_name="來源行號", blank=True, null=True
    )
    ProductID = models.CharField(max_length=50, verbose_name="產品編號")
    ProductType = models.CharField(
        max_length=20, verbose_name="產品類型", blank=True, null=True
    )
    ProdtQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="生產數量"
    )
    Producer = models.CharField(
        max_length=20, verbose_name="生產人員", blank=True, null=True
    )
    CostType = models.CharField(
        max_length=20, verbose_name="成本類型", blank=True, null=True
    )
    SourceType = models.CharField(
        max_length=20, verbose_name="來源類型", blank=True, null=True
    )
    SourceNo = models.CharField(
        max_length=50, verbose_name="來源單號", blank=True, null=True
    )
    Functionary = models.CharField(
        max_length=20, verbose_name="負責人", blank=True, null=True
    )
    WareInType = models.CharField(
        max_length=20, verbose_name="入庫類型", blank=True, null=True
    )
    EstTakeMatDate = models.CharField(
        max_length=20, verbose_name="預計領料日", blank=True, null=True
    )
    EstWareInDate = models.CharField(
        max_length=20, verbose_name="預計入庫日", blank=True, null=True
    )
    CompleteStatus = models.IntegerField(verbose_name="完工狀態")
    ChangeDate = models.CharField(
        max_length=20, verbose_name="異動日期", blank=True, null=True
    )
    GoodsQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="良品數量"
    )
    BadsQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="不良品數量"
    )
    Remark = models.TextField(verbose_name="備註", blank=True, null=True)
    Maker = models.CharField(
        max_length=20, verbose_name="製單人", blank=True, null=True
    )
    Permitter = models.CharField(
        max_length=20, verbose_name="審核人", blank=True, null=True
    )
    updated_at = models.DateTimeField(verbose_name="更新時間")
    BillStatus = models.IntegerField(verbose_name="單況", blank=True, null=True)

    class Meta:
        verbose_name = "製令主檔"
        verbose_name_plural = "製令主檔"

    def __str__(self):
        return f"{self.MKOrdNO} - {self.ProductID}"


# 製令明細（prdMkOrdMats）
class PrdMkOrdMats(models.Model):
    row_id = models.BigAutoField(primary_key=True, verbose_name="主鍵ID")
    Flag = models.IntegerField(verbose_name="狀態Flag")
    MkOrdNO = models.CharField(max_length=30, verbose_name="製令單號")
    RowNO = models.IntegerField(verbose_name="表身行號")
    SerNO = models.IntegerField(verbose_name="序號")
    SubProdID = models.CharField(max_length=50, verbose_name="用料編號")
    OriginalQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="需求數量"
    )
    WestingRate = models.DecimalField(
        max_digits=8, decimal_places=3, verbose_name="損耗率", blank=True, null=True
    )
    MatsRemark = models.TextField(verbose_name="用料備註", blank=True, null=True)
    Detail = models.TextField(verbose_name="說明", blank=True, null=True)
    UnitOughtQty = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        verbose_name="單位應發數量",
        blank=True,
        null=True,
    )
    OughtQty = models.DecimalField(
        max_digits=16, decimal_places=4, verbose_name="應發數量", blank=True, null=True
    )
    updated_at = models.DateTimeField(verbose_name="更新時間")

    class Meta:
        verbose_name = "製令明細"
        verbose_name_plural = "製令明細"

    def __str__(self):
        return f"{self.MkOrdNO} - {self.SubProdID}"


class SystemConfig(models.Model):
    """
    系統設定表：存放全域設定，例如自動轉換工單間隔（分鐘）
    """

    key = models.CharField(
        max_length=50, unique=True, verbose_name="設定名稱"
    )  # 例如 auto_convert_interval
    value = models.CharField(max_length=100, verbose_name="設定值（分鐘）")

    class Meta:
        verbose_name = "系統設定"
        verbose_name_plural = "系統設定"

    def __str__(self):
        return f"{self.key}: {self.value}"

    @staticmethod
    def get_no_distribute_keywords():
        """
        取得不分攤產量的關鍵字清單
        預設值：只計算最後一天,不分攤,不分配
        """
        try:
            config = SystemConfig.objects.get(key="no_distribute_keywords")
            # 用逗號分隔關鍵字
            keywords = [kw.strip() for kw in config.value.split(",") if kw.strip()]
            return keywords
        except SystemConfig.DoesNotExist:
            # 預設關鍵字
            default_keywords = ["只計算最後一天", "不分攤", "不分配"]
            # 自動建立預設設定
            SystemConfig.objects.create(
                key="no_distribute_keywords", value=", ".join(default_keywords)
            )
            return default_keywords


class CompanyOrder(models.Model):
    """
    MES 專用公司製令單表，對應公司製令單頁面所有欄位
    """

    company_code = models.CharField(
        max_length=10, verbose_name="公司代號"
    )  # 例如 01、02、03
    mkordno = models.CharField(max_length=50, verbose_name="製令單號")
    product_id = models.CharField(max_length=100, verbose_name="產品編號")
    prodt_qty = models.PositiveIntegerField(verbose_name="生產數量")
    est_take_mat_date = models.CharField(max_length=20, verbose_name="預定開工日")
    est_stock_out_date = models.CharField(max_length=20, verbose_name="預定出貨日")
    complete_status = models.IntegerField(
        verbose_name="完工狀態", null=True, blank=True
    )
    bill_status = models.IntegerField(verbose_name="單況", null=True, blank=True)
    sync_time = models.DateTimeField(auto_now=True, verbose_name="同步時間")
    is_converted = models.BooleanField(default=False, verbose_name="已轉成 MES 工單")

    class Meta:
        verbose_name = "公司製令單"
        verbose_name_plural = "公司製令單"
        unique_together = (("company_code", "mkordno"),)

    def __str__(self):
        return f"[{self.company_code}] 製令單 {self.mkordno}"


class WorkOrderProcess(models.Model):
    """
    派工單工序明細：記錄每個工單的具體工序執行狀況
    """

    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        verbose_name="工單",
        related_name="processes",
    )
    process_name = models.CharField(
        max_length=100, verbose_name="工序名稱"
    )  # 例如：SMT、DIP、測試
    step_order = models.IntegerField(verbose_name="工序順序")  # 1, 2, 3...
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    completed_quantity = models.IntegerField(default=0, verbose_name="完成數量")
    status = models.CharField(
        max_length=20,
        default="pending",
        verbose_name="狀態",
        choices=[
            ("pending", "待生產"),
            ("in_progress", "生產中"),
            ("completed", "已完成"),
            ("paused", "暫停"),
            ("cancelled", "取消"),
        ],
    )
    assigned_operator = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="分配作業員"
    )
    assigned_equipment = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="分配設備"
    )
    actual_start_time = models.DateTimeField(
        blank=True, null=True, verbose_name="實際開始時間"
    )
    actual_end_time = models.DateTimeField(
        blank=True, null=True, verbose_name="實際結束時間"
    )

    # 新增產能提升欄位
    capacity_multiplier = models.IntegerField(
        default=1, verbose_name="產能倍數", help_text="1=單人, 2=雙人, 3=三人..."
    )
    additional_operators = models.TextField(
        blank=True,
        null=True,
        verbose_name="額外作業員",
        help_text="JSON格式儲存額外作業員清單",
    )
    additional_equipments = models.TextField(
        blank=True,
        null=True,
        verbose_name="額外設備",
        help_text="JSON格式儲存額外設備清單",
    )
    target_hourly_output = models.IntegerField(default=0, verbose_name="目標每小時產出")
    estimated_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="預計工時"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "工單工序明細"
        verbose_name_plural = "工單工序明細"
        unique_together = (("workorder", "step_order"),)
        ordering = ["workorder", "step_order"]

    def __str__(self):
        # 只顯示工序名稱和步驟，不顯示工單號
        return f"{self.process_name} (步驟{self.step_order})"

    @property
    def completion_rate(self):
        """完成率"""
        if self.planned_quantity > 0:
            return f"{(self.completed_quantity / self.planned_quantity * 100):.1f}%"
        return "0%"

    @property
    def remaining_quantity(self):
        """剩餘數量"""
        return self.planned_quantity - self.completed_quantity

    @property
    def equipment_display_name(self):
        """設備顯示名稱"""
        if self.assigned_equipment:
            try:
                from equip.models import Equipment

                equipment = Equipment.objects.get(id=self.assigned_equipment)
                return equipment.name
            except (Equipment.DoesNotExist, ValueError):
                return f"設備{self.assigned_equipment}"
        return "-"

    def get_additional_operators_list(self):
        """獲取額外作業員清單"""
        import json

        if self.additional_operators:
            try:
                return json.loads(self.additional_operators)
            except:
                return []
        return []

    def get_additional_equipments_list(self):
        """獲取額外設備清單"""
        import json

        if self.additional_equipments:
            try:
                return json.loads(self.additional_equipments)
            except:
                return []
        return []

    def calculate_estimated_hours(self):
        """計算預計工時"""
        if self.target_hourly_output > 0 and self.capacity_multiplier > 0:
            remaining = self.planned_quantity - self.completed_quantity
            if remaining > 0:
                return round(
                    remaining / (self.target_hourly_output * self.capacity_multiplier),
                    2,
                )
        return 0


class WorkOrderProcessLog(models.Model):
    """
    工單工序執行日誌：記錄每個工序的詳細執行記錄
    """

    workorder_process = models.ForeignKey(
        WorkOrderProcess,
        on_delete=models.CASCADE,
        verbose_name="工單工序",
        related_name="logs",
    )
    action = models.CharField(
        max_length=50,
        verbose_name="操作類型",
        choices=[
            ("start", "開始生產"),
            ("pause", "暫停生產"),
            ("resume", "恢復生產"),
            ("complete", "完成生產"),
            ("quality_check", "品質檢查"),
            ("equipment_change", "設備更換"),
            ("operator_change", "作業員更換"),
            ("quantity_update", "數量更新"),
            ("note", "備註"),
            ("auto_assignment", "自動分配"),
        ],
    )
    quantity_before = models.PositiveIntegerField(default=0, verbose_name="操作前數量")
    quantity_after = models.PositiveIntegerField(default=0, verbose_name="操作後數量")
    operator = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="操作員"
    )
    equipment = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="設備"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="備註")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="記錄時間")

    class Meta:
        verbose_name = "工單工序日誌"
        verbose_name_plural = "工單工序日誌"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.workorder_process} - {self.action} - {self.created_at}"


# 工單分配記錄模型
class WorkOrderAssignment(models.Model):
    """工單分配記錄：記錄工單與設備、作業員的分配關係"""

    workorder = models.ForeignKey(
        "WorkOrder", on_delete=models.CASCADE, verbose_name="工單"
    )
    equipment_id = models.CharField(max_length=50, verbose_name="分配設備ID")
    operator_id = models.CharField(max_length=50, verbose_name="分配作業員ID")
    assigned_at = models.DateTimeField("分配時間", auto_now_add=True)
    company_code = models.CharField("公司代號", max_length=10, blank=True)

    class Meta:
        db_table = "workorder_assignment"
        verbose_name = "工單分配"
        verbose_name_plural = "工單分配記錄"

    def __str__(self):
        return (
            f"{self.workorder.order_number} - {self.equipment_id} - {self.operator_id}"
        )


# 工序產能設定表
class WorkOrderProcessCapacity(models.Model):
    """工序產能設定表 - 定義工序的產能參數"""

    workorder_process = models.OneToOneField(
        WorkOrderProcess, on_delete=models.CASCADE, related_name="capacity"
    )
    max_operators = models.IntegerField(default=1, verbose_name="最大作業員數")
    max_equipments = models.IntegerField(default=1, verbose_name="最大設備數")
    target_hourly_output = models.IntegerField(default=0, verbose_name="目標每小時產出")
    overtime_enabled = models.BooleanField(default=False, verbose_name="啟用加班")
    parallel_work_enabled = models.BooleanField(
        default=True, verbose_name="啟用並行作業"
    )

    class Meta:
        db_table = "workorder_process_capacity"
        verbose_name = "工序產能設定"
        verbose_name_plural = "工序產能設定"

    def __str__(self):
        return f"{self.workorder_process.process_name} - 產能設定"


# 新增：只在最後一天計算產量的工序關鍵字設定
# key: final_day_only_process_keywords，value: 以逗號分隔的關鍵字字串
# 例如 value: "包裝,出貨包裝,PACK,PACKING"





# 注意：ERP同步相關功能已移至 erp_integration 模組
# 請使用 erp_integration.models.ERPSyncConfig 和 erp_integration.models.ERPSyncLog


class DispatchLog(models.Model):
    """
    派工單記錄：每次派工都會產生一筆記錄，方便追蹤與查詢。
    包含工單、工序、作業員、派工數量、建立人員、建立時間。
    """

    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        verbose_name="工單",
        related_name="dispatch_logs",
    )
    process = models.ForeignKey(
        WorkOrderProcess,
        on_delete=models.CASCADE,
        verbose_name="工序",
        related_name="dispatch_logs",
    )
    operator = models.ForeignKey(
        Operator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="作業員",
        help_text="派工時選擇的作業員，可空白",
    )
    quantity = models.PositiveIntegerField(default=0, verbose_name="派工數量")
    created_by = models.CharField(max_length=100, verbose_name="建立人員")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    class Meta:
        verbose_name = "派工單記錄"
        verbose_name_plural = "派工單記錄"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.workorder} - {self.process} - {self.operator} - {self.quantity}"


class SMTProductionReport(models.Model):
    """
    SMT 生產報工記錄模型
    SMT 設備為自動化運作，不需要作業員
    """
    PRODUCTION_STATUS_CHOICES = [
        ('start', '開始生產'),
        ('pause', '暫停'),
        ('complete', '完工'),
    ]
    
    equipment = models.ForeignKey(
        'equip.Equipment',
        on_delete=models.CASCADE,
        verbose_name="設備"
    )
    
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        verbose_name="工單"
    )
    
    report_time = models.DateTimeField(
        default=timezone.now,
        verbose_name="報工時間"
    )
    
    quantity = models.IntegerField(
        verbose_name="報工數量"
    )
    
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        verbose_name="工作時數"
    )
    
    production_status = models.CharField(
        max_length=10,
        choices=PRODUCTION_STATUS_CHOICES,
        verbose_name="報工狀態"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="備註說明"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="建立時間"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新時間"
    )
    
    class Meta:
        verbose_name = "SMT 報工記錄"
        verbose_name_plural = "SMT 報工記錄"
        db_table = 'workorder_smt_production_report'
        ordering = ['-report_time']
    
    def __str__(self):
        return f"{self.equipment.name} - {self.workorder.order_number} - {self.report_time.strftime('%Y-%m-%d %H:%M')}"
    
    def get_production_status_display(self):
        """取得報工狀態顯示名稱"""
        return dict(self.PRODUCTION_STATUS_CHOICES).get(self.production_status, self.production_status)
    
    @property
    def equipment_name(self):
        """設備名稱"""
        return self.equipment.name
    
    @property
    def workorder_number(self):
        """工單號"""
        return self.workorder.order_number






