from django.db import models
from django.utils import timezone
from process.models import Operator
from equip.models import Equipment
import logging
from datetime import datetime

# 導入派工單子模組的模型（使用字串引用避免循環依賴）
# from .workorder_dispatch.models import WorkOrderDispatch, WorkOrderDispatchProcess

# 導入公司製令單子模組的模型
from .workorder_erp.models import PrdMKOrdMain, PrdMkOrdMats, CompanyOrder, SystemConfig

# 導入已完工工單子模組的模型
from .workorder_completed.models import WorkOrderCompleted, WorkOrderCompletedProcess

# 導入報工管理子模組的模型
from .workorder_reporting.models import SMTProductionReport, OperatorSupplementReport, SupervisorProductionReport


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
        # 格式化公司代號，確保是兩位數格式（例如：2 -> 02）
        formatted_company_code = self.company_code
        if formatted_company_code and formatted_company_code.isdigit():
            formatted_company_code = formatted_company_code.zfill(2)
        return f"[{formatted_company_code}] 工單 {self.order_number}"

    @classmethod
    def generate_order_number(cls, company_code):
        """
        自動生成工單號碼
        格式：WO-{公司代號}-{年份}{月份}{序號}
        例如：WO-01-202501001
        """
        # 格式化公司代號，確保是兩位數格式（例如：2 -> 02）
        formatted_company_code = company_code
        if formatted_company_code and formatted_company_code.isdigit():
            formatted_company_code = formatted_company_code.zfill(2)

        today = datetime.now()
        year_month = today.strftime("%Y%m")

        # 取得當月最後一個工單號碼
        last_order = (
            cls.objects.filter(
                company_code=company_code,
                order_number__startswith=f"WO-{formatted_company_code}-{year_month}",
            )
            .order_by("-order_number")
            .first()
        )

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

        return f"WO-{formatted_company_code}-{year_month}{sequence_str}"

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
        current_process = self.processes.filter(status="in_progress").first()
        if current_process and current_process.assigned_operator:
            return current_process.assigned_operator
        return "未分配"

    @property
    def current_process(self):
        """取得當前進行的工序"""
        current_process = self.processes.filter(status="in_progress").first()
        if current_process:
            return current_process.process_name
        return "無進行中工序"

    @property
    def start_time(self):
        """取得工單開始時間（第一個工序的開始時間或工單狀態變更時間）"""
        # 優先顯示第一個工序的實際開始時間
        first_process = (
            self.processes.filter(actual_start_time__isnull=False)
            .order_by("actual_start_time")
            .first()
        )
        if first_process and first_process.actual_start_time:
            return first_process.actual_start_time

        # 如果工單狀態是生產中或暫停，則顯示工單的更新時間（狀態變更時間）
        if self.status in ["in_progress", "paused"]:
            return self.updated_at

        # 如果都沒有，則顯示工單建立時間
        return self.created_at








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











# ============================================================================
# 重新設計的工單資料表架構
# ============================================================================

# 派工單相關模型已移動到 workorder_dispatch.models 子模組
class WorkOrderProduction(models.Model):
    """
    生產中工單表：專門記錄正在生產的工單
    當工單開始生產時，會在此表建立記錄
    """
    STATUS_CHOICES = [
        ("in_production", "生產中"),
        ("paused", "暫停"),
        ("completed", "已完工"),
    ]

    # 關聯工單
    workorder = models.OneToOneField(
        WorkOrder,
        on_delete=models.CASCADE,
        verbose_name="工單",
        related_name="production_record"
    )
    
    # 生產狀態
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_production", verbose_name="生產狀態")
    production_start_date = models.DateTimeField(verbose_name="生產開始時間", auto_now_add=True)
    production_end_date = models.DateTimeField(verbose_name="生產結束時間", null=True, blank=True)
    
    # 生產進度追蹤
    current_process = models.CharField(max_length=100, verbose_name="當前工序", null=True, blank=True)
    completed_processes = models.TextField(verbose_name="已完成工序", blank=True, help_text="JSON格式記錄已完成的工序")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "生產中工單"
        verbose_name_plural = "生產中工單"
        db_table = "workorder_production"
        ordering = ["-created_at"]

    def __str__(self):
        return f"生產中：{self.workorder.order_number}"


class WorkOrderProductionDetail(models.Model):
    """
    生產中工單報工明細：記錄生產過程中的所有報工記錄
    例如：電測報了幾次、出貨包裝包了幾次
    """
    workorder_production = models.ForeignKey(
        WorkOrderProduction,
        on_delete=models.CASCADE,
        verbose_name="生產中工單",
        related_name="production_details"
    )
    
    # 報工資訊
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    report_date = models.DateField(verbose_name="報工日期")
    report_time = models.DateTimeField(verbose_name="報工時間", auto_now_add=True)
    
    # 報工數量
    work_quantity = models.IntegerField(verbose_name="合格品數量", default=0)
    defect_quantity = models.IntegerField(verbose_name="不良品數量", default=0)
    
    # 報工人員和設備
    operator = models.CharField(max_length=100, verbose_name="作業員", null=True, blank=True)
    equipment = models.CharField(max_length=100, verbose_name="設備", null=True, blank=True)
    
    # 報工來源
    REPORT_SOURCE_CHOICES = [
        ("operator", "作業員現場報工"),
        ("operator_supplement", "作業員補登報工"),
        ("supervisor", "主管報工"),
        ("smt", "SMT報工"),
    ]
    report_source = models.CharField(max_length=20, choices=REPORT_SOURCE_CHOICES, verbose_name="報工來源")
    
    # 時間資訊
    start_time = models.TimeField(verbose_name="開始時間", null=True, blank=True)
    end_time = models.TimeField(verbose_name="結束時間", null=True, blank=True)
    
    # 備註
    remarks = models.TextField(verbose_name="備註", blank=True)
    abnormal_notes = models.TextField(verbose_name="異常記錄", blank=True)
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    created_by = models.CharField(max_length=100, verbose_name="建立人員", default="system")

    class Meta:
        verbose_name = "生產報工明細"
        verbose_name_plural = "生產報工明細"
        db_table = "workorder_production_detail"
        ordering = ["-report_date", "-report_time"]

    def __str__(self):
        return f"{self.workorder_production.workorder.order_number} - {self.process_name} - {self.report_date}"



