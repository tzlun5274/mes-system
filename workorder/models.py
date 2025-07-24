from django.db import models
from django.utils import timezone
from process.models import Operator
from equip.models import Equipment
import logging
from datetime import datetime


class WorkOrder(models.Model):
    """
    工單管理模型：支援多公司唯一識別，記錄每一張工單的基本資料與狀態
    """

    # 狀態選項定義
    STATUS_CHOICES = [
        ("pending", "待生產"),
        ("in_progress", "生產中"),
        ("paused", "暫停"),
        ("completed", "已完成"),
    ]

    company_code = models.CharField(
        max_length=10, verbose_name="公司代號", null=True, blank=True
    )  # 例如 01、02、03，可為空，方便資料庫遷移
    order_number = models.CharField(max_length=50, verbose_name="工單號碼")
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
        unique_together = (("company_code", "order_number"),)  # 公司代號+工單號碼唯一

    def __str__(self):
        return f"[{self.company_code}] 工單 {self.order_number}"
    
    @classmethod
    def generate_order_number(cls, company_code):
        """
        自動生成工單號碼
        格式：WO-{公司代號}-{年份}{月份}{序號}
        例如：WO-01-202501001
        """
        today = datetime.now()
        year_month = today.strftime("%Y%m")
        
        # 取得當月最後一個工單號碼
        last_order = cls.objects.filter(
            company_code=company_code,
            order_number__startswith=f"WO-{company_code}-{year_month}"
        ).order_by('-order_number').first()
        
        if last_order:
            # 從最後一個號碼中提取序號
            try:
                last_sequence = int(last_order.order_number[-3:])
                new_sequence = last_sequence + 1
            except ValueError:
                new_sequence = 1
        else:
            new_sequence = 1
        
        # 格式化序號為3位數
        sequence_str = f"{new_sequence:03d}"
        
        return f"WO-{company_code}-{year_month}{sequence_str}"
    
    @property
    def completed_quantity(self):
        """計算工單總完成數量"""
        return sum(process.completed_quantity for process in self.processes.all())
    
    @property
    def progress(self):
        """計算工單進度百分比"""
        if self.quantity > 0:
            return round((self.completed_quantity / self.quantity) * 100, 1)
        return 0.0
    
    @property
    def current_operator(self):
        """取得當前負責的作業員"""
        current_process = self.processes.filter(status='in_progress').first()
        if current_process and current_process.assigned_operator:
            return current_process.assigned_operator
        return "未分配"
    
    @property
    def current_process(self):
        """取得當前進行的工序"""
        current_process = self.processes.filter(status='in_progress').first()
        if current_process:
            return current_process.process_name
        return "無進行中工序"
    
    @property
    def start_time(self):
        """取得工單開始時間（第一個工序的開始時間或工單狀態變更時間）"""
        # 優先顯示第一個工序的實際開始時間
        first_process = self.processes.filter(actual_start_time__isnull=False).order_by('actual_start_time').first()
        if first_process and first_process.actual_start_time:
            return first_process.actual_start_time
        
        # 如果工單狀態是生產中或暫停，則顯示工單的更新時間（狀態變更時間）
        if self.status in ['in_progress', 'paused']:
            return self.updated_at
        
        # 如果都沒有，則顯示工單建立時間
        return self.created_at


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
        max_length=20, verbose_name="核准人", blank=True, null=True
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
            ("status_change", "狀態變更"),
            ("quick_report", "快速報工"),
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
    
    # 報工類型
    REPORT_TYPE_CHOICES = [
        ('normal', '正式工單'),
        ('rd_sample', 'RD樣品'),
    ]
    
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default='normal',
        verbose_name="報工類型",
        help_text="請選擇報工類型：正式工單或RD樣品"
    )
    
    # 基本資訊
    product_id = models.CharField(
        max_length=100,
        verbose_name="產品編號",
        help_text="請選擇產品編號，將自動帶出相關工單",
        default=""
    )
    
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        verbose_name="工單號碼",
        help_text="請選擇工單號碼，或透過產品編號自動帶出",
        null=True,
        blank=True
    )
    
    # RD樣品專用欄位
    rd_workorder_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="RD樣品工單號碼",
        help_text="RD樣品模式的工單號碼"
    )
    

    
    rd_product_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="RD產品編號",
        help_text="請輸入RD樣品的產品編號，用於識別具體的RD樣品工序與設備資訊"
    )
    
    planned_quantity = models.IntegerField(
        verbose_name="工單預設生產數量",
        help_text="此為工單規劃的總生產數量，不可修改",
        default=0
    )
    
    operation = models.CharField(
        max_length=100,
        verbose_name="工序",
        help_text="請選擇此次補登的SMT工序",
        default=""
    )
    
    equipment = models.ForeignKey(
        'equip.Equipment',
        on_delete=models.CASCADE,
        verbose_name="設備",
        help_text="請選擇本次報工使用的SMT設備",
        null=True,
        blank=True
    )
    
    # 時間資訊
    work_date = models.DateField(
        verbose_name="日期",
        help_text="請選擇實際報工日期",
        default=timezone.now
    )
    
    start_time = models.TimeField(
        verbose_name="開始時間",
        help_text="請輸入實際開始時間 (24小時制)，例如 16:00",
        default=timezone.now
    )
    
    end_time = models.TimeField(
        verbose_name="結束時間",
        help_text="請輸入實際結束時間 (24小時制)，例如 18:30",
        default=timezone.now
    )
    
    # 數量資訊
    work_quantity = models.IntegerField(
        verbose_name="工作數量",
        help_text="請輸入該時段內實際完成的合格產品數量",
        default=0
    )
    
    defect_quantity = models.IntegerField(
        default=0,
        verbose_name="不良品數量",
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0"
    )
    
    # 狀態資訊
    is_completed = models.BooleanField(
        default=False,
        verbose_name="是否已完工",
        help_text="若此工單在此工序上已全部完成，請勾選"
    )
    
    # 備註
    remarks = models.TextField(
        blank=True,
        verbose_name="備註",
        help_text="請輸入任何需要補充的資訊，如異常、停機等"
    )
    
    # 核准相關欄位
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待核准'),
            ('approved', '已核准'),
            ('rejected', '已駁回'),
        ],
        default='pending',
        verbose_name="核准狀態",
        help_text="此補登記錄的核准狀態"
    )
    
    approved_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="核准人員",
        help_text="此補登記錄的核准人員"
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="核准時間",
        help_text="此補登記錄的核准時間"
    )
    
    approval_remarks = models.TextField(
        blank=True,
        verbose_name="核准備註",
        help_text="核准時的備註說明"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="駁回原因",
        help_text="駁回時的原因說明"
    )
    
    # 系統欄位
    created_by = models.CharField(
        max_length=100,
        verbose_name="建立人員",
        default="system"
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
        verbose_name = "SMT生產報工記錄"
        verbose_name_plural = "SMT生產報工記錄"
        db_table = 'workorder_smt_production_report'
        ordering = ['-work_date', '-start_time']

    def __str__(self):
        if self.report_type == 'rd_sample':
            rd_info = self.rd_product_code or self.product_id or 'RD樣品'
            return f"RD樣品 - {rd_info} - {self.work_date}"
        else:
            return f"{self.workorder.order_number if self.workorder else '無工單'} - {self.work_date}"

    @property
    def workorder_number(self):
        """取得工單號碼"""
        if self.report_type == 'rd_sample':
            # RD樣品工單號碼，優先使用rd_workorder_number
            return self.rd_workorder_number or 'RD樣品'
        elif self.workorder:
            return self.workorder.order_number
        elif self.product_id:
            # 如果有產品編號但沒有工單，可能是手動輸入的產品編號
            return f"產品編號：{self.product_id}"
        else:
            return ""

    def is_rd_sample_by_workorder(self):
        """根據工單號碼判斷是否為RD樣品"""
        if self.workorder and self.workorder.order_number:
            # 檢查工單號碼是否包含RD樣品相關關鍵字
            order_number = self.workorder.order_number.upper()
            rd_keywords = ['RD', '樣品', 'SAMPLE', 'RD樣品', 'RD-樣品', 'RD樣本']
            return any(keyword in order_number for keyword in rd_keywords)
        return False

    def auto_set_report_type(self):
        """自動設定報工類型"""
        if self.is_rd_sample_by_workorder():
            self.report_type = 'rd_sample'
        else:
            self.report_type = 'normal'

    @property
    def equipment_name(self):
        """取得設備名稱"""
        return self.equipment.name if self.equipment else ""

    @property
    def total_quantity(self):
        """取得總數量（工作數量 + 不良品數量）"""
        return self.work_quantity + self.defect_quantity

    @property
    def work_duration(self):
        """取得工作時數（小時）"""
        if self.start_time and self.end_time:
            from datetime import datetime, timedelta
            
            # 組合日期和時間
            start_dt = datetime.combine(self.work_date, self.start_time)
            end_dt = datetime.combine(self.work_date, self.end_time)
            
            # 如果結束時間小於開始時間，表示跨日
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            duration = end_dt - start_dt
            return duration.total_seconds() / 3600  # 轉換為小時
        
        return 0.0

    @property
    def efficiency_rate(self):
        """取得效率率（合格品數量 / 總數量）"""
        if self.total_quantity > 0:
            return (self.work_quantity / self.total_quantity) * 100
        return 0.0

    def can_edit(self, user):
        """
        檢查記錄是否可以編輯
        已核准的記錄只有超級管理員可以編輯
        RD樣品記錄不能修改
        """
        # RD樣品記錄不能修改
        if self.report_type == 'rd_sample':
            return False
        
        # 已核准的記錄只有超級管理員可以編輯
        if self.approval_status == 'approved':
            return user.is_superuser
        return True

    def can_delete(self, user):
        """
        檢查記錄是否可以刪除
        只有建立記錄的用戶和超級管理者可以刪除待核准和已駁回的記錄
        已核准的記錄只有超級管理者可以刪除
        """
        # 已核准的記錄只有超級管理者可以刪除
        if self.approval_status == 'approved':
            return user.is_superuser
        
        # 待核准和已駁回的記錄，只有建立者或超級管理者可以刪除
        return user.is_superuser or self.created_by == user.username

    def can_approve(self, user):
        """檢查是否可以核准"""
        # 只有超級用戶或管理者群組可以核准
        if user.is_superuser:
            return True
        
        # 檢查是否在管理者群組中
        return user.groups.filter(name='管理者').exists()

    def approve(self, user, remarks=''):
        """
        核准補登記錄
        """
        self.approval_status = 'approved'
        self.approved_by = user.username
        self.approved_at = timezone.now()
        self.approval_remarks = remarks
        self.save()

    def reject(self, user, reason=''):
        """
        駁回補登記錄
        """
        self.approval_status = 'rejected'
        self.approved_by = user.username
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()







class OperatorSupplementReport(models.Model):
    """
    作業員補登報工記錄模型
    專為作業員的歷史報工記錄管理而設計，支援離線數據輸入、歷史數據修正和批量數據處理
    """
    
    # 基本資訊
    operator = models.ForeignKey(
        'process.Operator',
        on_delete=models.CASCADE,
        verbose_name="作業員",
        help_text="請選擇進行補登報工的作業員"
    )
    
    # 報工類型
    REPORT_TYPE_CHOICES = [
        ('normal', '正式工單'),
        ('rd_sample', 'RD樣品'),
    ]
    
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default='normal',
        verbose_name="報工類型",
        help_text="請選擇報工類型：正式工單或RD樣品"
    )
    
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        verbose_name="工單號碼",
        help_text="請選擇要補登的工單號碼",
        null=True,
        blank=True
    )
    
    # 產品編號欄位（用於資料庫相容性）
    product_id = models.CharField(
        max_length=100,
        verbose_name="產品編號",
        help_text="產品編號（自動從工單取得）",
        default=""
    )
    
    # 工單預設生產數量（唯讀）
    planned_quantity = models.IntegerField(
        verbose_name="工單預設生產數量",
        help_text="此為工單規劃的總生產數量，不可修改",
        default=0
    )
    
    process = models.ForeignKey(
        'process.ProcessName',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="工序",
        help_text="請選擇此次補登的工序（排除SMT相關工序）"
    )
    
    # 工序名稱欄位（用於資料庫相容性）
    operation = models.CharField(
        max_length=100,
        verbose_name="工序名稱",
        help_text="工序名稱（自動從 process 欄位取得）",
        default=""
    )
    
    # 設備資訊（可選）
    equipment = models.ForeignKey(
        'equip.Equipment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="設備",
        help_text="請選擇此次補登的設備（排除SMT相關設備）"
    )
    
    # 時間資訊
    work_date = models.DateField(
        verbose_name="日期",
        help_text="請選擇實際報工日期",
        default=timezone.now
    )
    
    start_time = models.TimeField(
        verbose_name="開始時間",
        help_text="請輸入實際開始時間 (24小時制)，例如 16:00",
        default=timezone.now
    )
    
    end_time = models.TimeField(
        verbose_name="結束時間",
        help_text="請輸入實際結束時間 (24小時制)，例如 18:30",
        default=timezone.now
    )
    
    # 數量資訊
    work_quantity = models.IntegerField(
        verbose_name="工作數量",
        help_text="請輸入該時段內實際完成的合格產品數量",
        default=0
    )
    
    defect_quantity = models.IntegerField(
        default=0,
        verbose_name="不良品數量",
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0"
    )
    
    # 狀態資訊
    is_completed = models.BooleanField(
        default=False,
        verbose_name="是否已完工",
        help_text="若此工單在此工序上已全部完成，請勾選"
    )
    
    # 完工判斷方式
    COMPLETION_METHOD_CHOICES = [
        ('manual', '手動勾選'),
        ('auto_quantity', '自動依數量判斷'),
        ('auto_time', '自動依工時判斷'),
        ('auto_operator', '作業員確認'),
        ('auto_system', '系統自動判斷'),
    ]
    
    completion_method = models.CharField(
        max_length=20,
        choices=COMPLETION_METHOD_CHOICES,
        default='manual',
        verbose_name="完工判斷方式",
        help_text="選擇如何判斷此筆記錄是否代表工單完工"
    )
    
    # 自動完工狀態（系統計算）
    auto_completed = models.BooleanField(
        default=False,
        verbose_name="自動完工狀態",
        help_text="系統根據累積數量或工時自動判斷的完工狀態"
    )
    
    # 完工確認時間
    completion_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="完工確認時間",
        help_text="系統記錄的完工確認時間"
    )
    
    # 累積完成數量（用於自動完工判斷）
    cumulative_quantity = models.IntegerField(
        default=0,
        verbose_name="累積完成數量",
        help_text="此工單在此工序上的累積完成數量"
    )
    
    # 累積工時（用於自動完工判斷）
    cumulative_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="累積工時",
        help_text="此工單在此工序上的累積工時"
    )
    
    # 核准狀態
    APPROVAL_STATUS_CHOICES = [
        ('pending', '待核准'),
        ('approved', '已核准'),
        ('rejected', '已駁回'),
    ]
    
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending',
        verbose_name="核准狀態",
        help_text="補登記錄的核准狀態，已核准的記錄不可修改"
    )
    
    approved_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="核准人員",
        help_text="核准此補登記錄的人員"
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="核准時間",
        help_text="此補登記錄的核准時間"
    )
    
    approval_remarks = models.TextField(
        blank=True,
        verbose_name="核准備註",
        help_text="核准時的備註說明"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="駁回原因",
        help_text="駁回時的原因說明"
    )
    
    # 備註
    remarks = models.TextField(
        blank=True,
        verbose_name="備註",
        help_text="請輸入任何需要補充的資訊，如異常、停機等"
    )
    
    # 系統欄位
    created_by = models.CharField(
        max_length=100,
        verbose_name="建立人員",
        default="system"
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
        verbose_name = "作業員補登報工記錄"
        verbose_name_plural = "作業員補登報工記錄"
        db_table = 'workorder_operator_supplement_report'
        ordering = ['-work_date', '-start_time']

    def __str__(self):
        return f"{self.operator.name} - {self.workorder.order_number} - {self.work_date}"

    @property
    def operator_name(self):
        """取得作業員名稱"""
        return self.operator.name if self.operator else ""

    @property
    def workorder_number(self):
        """取得工單號碼"""
        return self.workorder.order_number if self.workorder else ""

    @property
    def process_name(self):
        """取得工序名稱"""
        return self.process.name if self.process else ""

    @property
    def total_quantity(self):
        """取得總數量（工作數量 + 不良品數量）"""
        return self.work_quantity + self.defect_quantity

    @property
    def work_hours(self):
        """計算工作時數"""
        if self.start_time and self.end_time:
            from datetime import datetime, timedelta
            start_dt = datetime.combine(self.work_date, self.start_time)
            end_dt = datetime.combine(self.work_date, self.end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            duration = end_dt - start_dt
            return round(duration.total_seconds() / 3600, 2)
        return 0.0

    @property
    def yield_rate(self):
        """計算良率"""
        if self.total_quantity > 0:
            return round((self.work_quantity / self.total_quantity) * 100, 2)
        return 0.0

    def can_edit(self, user):
        """
        檢查記錄是否可以編輯
        已核准的記錄只有超級管理員可以編輯
        """
        if self.approval_status == 'approved':
            return user.is_superuser
        return True

    def can_delete(self, user):
        """
        檢查記錄是否可以刪除
        只有建立記錄的用戶和超級管理者可以刪除待核准和已駁回的記錄
        已核准的記錄只有超級管理者可以刪除
        """
        # 已核准的記錄只有超級管理者可以刪除
        if self.approval_status == 'approved':
            return user.is_superuser
        
        # 待核准和已駁回的記錄，只有建立者或超級管理者可以刪除
        return user.is_superuser or self.created_by == user.username

    def can_approve(self, user):
        """
        檢查記錄是否可以核准
        只有管理員和超級管理員可以核准
        """
        return user.is_staff or user.is_superuser

    def approve(self, user, remarks=''):
        """
        核准通過補登記錄
        """
        self.approval_status = 'approved'
        self.approved_by = user.username
        self.approved_at = timezone.now()
        self.approval_remarks = remarks
        self.save()

    def reject(self, user, reason=''):
        """
        駁回補登記錄
        """
        self.approval_status = 'rejected'
        self.approved_by = user.username
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def submit_for_approval(self):
        """提交核准"""
        self.approval_status = 'pending'
        self.save()
    
    def check_auto_completion(self):
        """檢查是否自動完工"""
        from django.utils import timezone
        
        # 取得此工單在此工序上的所有記錄
        all_reports = OperatorSupplementReport.objects.filter(
            workorder=self.workorder,
            process=self.process
        ).order_by('work_date', 'start_time')
        
        # 計算累積數量
        total_quantity = sum(report.work_quantity for report in all_reports if report.work_quantity)
        
        # 計算累積工時
        total_hours = sum(report.work_hours for report in all_reports)
        
        # 更新累積數據
        self.cumulative_quantity = total_quantity
        self.cumulative_hours = total_hours
        
        # 自動完工判斷邏輯
        auto_completed = False
        completion_method = 'manual'
        
        # 1. 依數量判斷：累積數量 >= 工單預設數量
        if total_quantity >= self.workorder.quantity:
            auto_completed = True
            completion_method = 'auto_quantity'
        
        # 2. 依工時判斷：累積工時 >= 預估工時（假設每小時產出 50 件）
        estimated_hours = self.workorder.quantity / 50  # 可調整的預估標準
        if total_hours >= estimated_hours:
            auto_completed = True
            completion_method = 'auto_time'
        
        # 3. 作業員確認：在備註中提及完工
        if '完工' in (self.remarks or '') or '完成' in (self.remarks or ''):
            auto_completed = True
            completion_method = 'auto_operator'
        
        # 更新自動完工狀態
        self.auto_completed = auto_completed
        self.completion_method = completion_method
        
        # 如果自動完工，設定完工時間
        if auto_completed and not self.completion_time:
            self.completion_time = timezone.now()
        
        self.save()
        
        return auto_completed
    
    def get_completion_status_display(self):
        """取得完工狀態顯示文字"""
        if self.is_completed:
            return "手動完工"
        elif self.auto_completed:
            method_display = dict(self.COMPLETION_METHOD_CHOICES).get(self.completion_method, '')
            return f"自動完工({method_display})"
        else:
            return "未完工"
    
    def get_completion_summary(self):
        """取得完工摘要資訊"""
        return {
            'is_completed': self.is_completed,
            'auto_completed': self.auto_completed,
            'completion_method': self.completion_method,
            'completion_time': self.completion_time,
            'cumulative_quantity': self.cumulative_quantity,
            'cumulative_hours': self.cumulative_hours,
            'planned_quantity': self.workorder.quantity,
            'completion_rate': (self.cumulative_quantity / self.workorder.quantity * 100) if self.workorder.quantity > 0 else 0
        }







class ManagerProductionReport(models.Model):
    """
    管理者生產報工記錄模型
    專為管理者設計的報工記錄核准模組，結合了 SMT 補登報工和作業員補登報工的功能特點
    """
    
    # 基本資訊
    manager = models.CharField(
        max_length=100,
        verbose_name="管理者",
        help_text="請輸入管理者姓名"
    )
    
    workorder = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        verbose_name="工單號碼",
        help_text="請選擇要報工的工單號碼"
    )
    
    # 工單預設生產數量（唯讀）
    planned_quantity = models.IntegerField(
        verbose_name="工單預設生產數量",
        help_text="此為工單規劃的總生產數量，不可修改",
        default=0
    )
    
    process = models.ForeignKey(
        'process.ProcessName',
        on_delete=models.CASCADE,
        verbose_name="工序",
        help_text="請選擇此次報工的工序"
    )
    
    # 設備資訊（可選）
    equipment = models.ForeignKey(
        'equip.Equipment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="設備",
        help_text="請選擇此次報工的設備（可選）"
    )
    
    # 作業員資訊（可選）
    operator = models.ForeignKey(
        'process.Operator',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="作業員",
        help_text="請選擇此次報工的作業員（可選）"
    )
    
    # 時間資訊
    work_date = models.DateField(
        verbose_name="日期",
        help_text="請選擇實際報工日期",
        default=timezone.now
    )
    
    start_time = models.TimeField(
        verbose_name="開始時間",
        help_text="請輸入實際開始時間 (24小時制)，例如 16:00",
        default=timezone.now
    )
    
    end_time = models.TimeField(
        verbose_name="結束時間",
        help_text="請輸入實際結束時間 (24小時制)，例如 18:30",
        default=timezone.now
    )
    
    # 數量資訊
    work_quantity = models.IntegerField(
        verbose_name="工作數量",
        help_text="請輸入該時段內實際完成的合格產品數量",
        default=0
    )
    
    defect_quantity = models.IntegerField(
        default=0,
        verbose_name="不良品數量",
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0"
    )
    
    # 完工判斷
    is_completed = models.BooleanField(
        default=False,
        verbose_name="是否已完工",
        help_text="若此工單在此工序上已全部完成，請勾選"
    )
    
    # 完工判斷方式
    COMPLETION_METHOD_CHOICES = [
        ('manual', '手動勾選'),
        ('auto_quantity', '自動依數量判斷'),
        ('auto_time', '自動依工時判斷'),
        ('manager_confirm', '管理者確認'),
        ('auto_system', '系統自動判斷'),
    ]
    
    completion_method = models.CharField(
        max_length=20,
        choices=COMPLETION_METHOD_CHOICES,
        default='manual',
        verbose_name="完工判斷方式",
        help_text="選擇如何判斷此筆記錄是否代表工單完工"
    )
    
    # 自動完工狀態（系統計算）
    auto_completed = models.BooleanField(
        default=False,
        verbose_name="自動完工狀態",
        help_text="系統根據累積數量或工時自動判斷的完工狀態"
    )
    
    # 完工確認時間
    completion_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="完工確認時間",
        help_text="系統記錄的完工確認時間"
    )
    
    # 累積完成數量（用於自動完工判斷）
    cumulative_quantity = models.IntegerField(
        default=0,
        verbose_name="累積完成數量",
        help_text="此工單在此工序上的累積完成數量"
    )
    
    # 累積工時（用於自動完工判斷）
    cumulative_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="累積工時",
        help_text="此工單在此工序上的累積工時"
    )
    
    # 核准狀態
    APPROVAL_STATUS_CHOICES = [
        ('pending', '待核准'),
        ('approved', '已核准'),
        ('rejected', '已駁回'),
    ]
    
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending',
        verbose_name="核准狀態",
        help_text="報工記錄的核准狀態，已核准的記錄不可修改"
    )
    
    approved_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="核准人員",
        help_text="核准此報工記錄的人員"
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="核准時間",
        help_text="此報工記錄的核准時間"
    )
    
    approval_remarks = models.TextField(
        blank=True,
        verbose_name="核准備註",
        help_text="核准時的備註說明"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="駁回原因",
        help_text="駁回時的原因說明"
    )
    
    # 備註
    remarks = models.TextField(
        blank=True,
        verbose_name="備註",
        help_text="請輸入任何需要補充的資訊，如異常、停機等"
    )
    
    # 系統欄位
    created_by = models.CharField(
        max_length=100,
        verbose_name="建立人員",
        default="system"
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
        verbose_name = "管理者生產報工記錄"
        verbose_name_plural = "管理者生產報工記錄"
        db_table = 'workorder_manager_production_report'
        ordering = ['-work_date', '-start_time']
    
    def __str__(self):
        return f"{self.manager} - {self.workorder.order_number} - {self.process.name} - {self.work_date}"
    
    @property
    def workorder_number(self):
        """取得工單號碼"""
        return self.workorder.order_number if self.workorder else ""
    
    @property
    def process_name(self):
        """取得工序名稱"""
        return self.process.name if self.process else ""
    
    @property
    def equipment_name(self):
        """取得設備名稱"""
        return self.equipment.name if self.equipment else "未指定"
    
    @property
    def operator_name(self):
        """取得作業員姓名"""
        return self.operator.name if self.operator else "未指定"
    
    @property
    def total_quantity(self):
        """計算總數量（工作數量 + 不良品數量）"""
        return self.work_quantity + self.defect_quantity
    
    @property
    def work_hours(self):
        """計算工作時數"""
        if self.start_time and self.end_time:
            start_dt = timezone.datetime.combine(self.work_date, self.start_time)
            end_dt = timezone.datetime.combine(self.work_date, self.end_time)
            
            # 如果結束時間小於開始時間，表示跨日
            if end_dt < start_dt:
                end_dt += timezone.timedelta(days=1)
            
            duration = end_dt - start_dt
            hours = duration.total_seconds() / 3600
            return round(hours, 2)
        return 0.0
    
    @property
    def yield_rate(self):
        """計算良率"""
        if self.total_quantity > 0:
            return round((self.work_quantity / self.total_quantity) * 100, 2)
        return 0.0
    
    def can_edit(self, user):
        """檢查是否可以編輯"""
        # 已審核的記錄不可編輯
        if self.approval_status == 'approved':
            return False
        
        # 建立者或超級用戶可以編輯
        return user.is_superuser or self.created_by == user.username
    
    def can_delete(self, user):
        """
        檢查是否可以刪除
        只有建立記錄的用戶和超級管理者可以刪除待核准和已駁回的記錄
        已核准的記錄只有超級管理者可以刪除
        """
        # 已核准的記錄只有超級管理者可以刪除
        if self.approval_status == 'approved':
            return user.is_superuser
        
        # 待核准和已駁回的記錄，只有建立者或超級管理者可以刪除
        return user.is_superuser or self.created_by == user.username
    
    def can_approve(self, user):
        """檢查是否可以核准"""
        # 只有超級用戶或管理者群組可以核准
        if user.is_superuser:
            return True
        
        # 檢查是否在管理者群組中
        return user.groups.filter(name='管理者').exists()
    
    def approve(self, user, remarks=''):
        """核准通過"""
        if not self.can_approve(user):
            raise PermissionError("您沒有權限進行核准")
        
        self.approval_status = 'approved'
        self.approved_by = user.username
        self.approved_at = timezone.now()
        self.approval_remarks = remarks
        self.save()
    
    def reject(self, user, reason=''):
        """駁回"""
        if not self.can_approve(user):
            raise PermissionError("您沒有權限進行核准")
        
        self.approval_status = 'rejected'
        self.approved_by = user.username
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def submit_for_approval(self):
        """提交核准"""
        self.approval_status = 'pending'
        self.save()
    
    def check_auto_completion(self):
        """檢查自動完工狀態"""
        if self.completion_method == 'auto_quantity':
            # 根據累積數量判斷
            if self.cumulative_quantity >= self.planned_quantity:
                self.auto_completed = True
                self.completion_time = timezone.now()
        elif self.completion_method == 'auto_time':
            # 根據累積工時判斷（假設標準工時為8小時）
            if self.cumulative_hours >= 8.0:
                self.auto_completed = True
                self.completion_time = timezone.now()
        elif self.completion_method == 'auto_system':
            # 系統自動判斷（綜合考量）
            if (self.cumulative_quantity >= self.planned_quantity * 0.95 and 
                self.cumulative_hours >= 6.0):
                self.auto_completed = True
                self.completion_time = timezone.now()
        
        self.save()
    
    def get_completion_status_display(self):
        """取得完工狀態顯示"""
        if self.is_completed:
            return "已完工"
        elif self.auto_completed:
            return "自動完工"
        else:
            return "未完工"
    
    def get_completion_summary(self):
        """取得完工摘要"""
        summary = []
        
        if self.is_completed:
            summary.append("手動完工")
        
        if self.auto_completed:
            summary.append("自動完工")
        
        if self.completion_time:
            summary.append(f"完工時間: {self.completion_time.strftime('%Y-%m-%d %H:%M')}")
        
        return " | ".join(summary) if summary else "未完工"






