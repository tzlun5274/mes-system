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
# from .workorder_completed.models import CompletedWorkOrder, CompletedWorkOrderProcess  # 已移除

# 導入報工管理子模組的模型
from .workorder_reporting.models import SMTProductionReport, OperatorSupplementReport


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
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完工時間")

    objects = models.Manager()  # 明確宣告 objects manager，解決 linter 錯誤

    class Meta:
        verbose_name = "工單"
        verbose_name_plural = "工單管理"
        unique_together = (("company_code", "order_number", "product_code"),)  # 公司代號+工單號碼+產品編號唯一

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
        """計算工單完成數量（所有工序完成數量的平均值）"""
        processes = self.processes.all()
        if processes.count() > 0:
            total_completed = sum(process.completed_quantity for process in processes)
            return round(total_completed / processes.count())
        return 0

    @property
    def progress(self):
        """計算工單進度百分比"""
        # 計算已完成工序的百分比
        total_processes = self.processes.count()
        if total_processes > 0:
            completed_processes = self.processes.filter(status='completed').count()
            return round((completed_processes / total_processes) * 100, 1)
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
        """完成率（數值）"""
        if self.planned_quantity > 0:
            return (self.completed_quantity / self.planned_quantity * 100)
        return 0.0

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
        related_name="production_record",
        null=True,
        blank=True
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
        ("smt", "SMT報工"),
    ]
    report_source = models.CharField(max_length=20, choices=REPORT_SOURCE_CHOICES, verbose_name="報工來源")
    
    # 時間資訊
    start_time = models.TimeField(verbose_name="開始時間", null=True, blank=True)
    end_time = models.TimeField(verbose_name="結束時間", null=True, blank=True)
    
    # 工時資訊（從報工資料表同步）
    work_hours = models.FloatField(default=0.0, verbose_name="工作時數")
    overtime_hours = models.FloatField(default=0.0, verbose_name="加班時數")
    
    # 休息時間相關欄位（從報工資料表同步）
    has_break = models.BooleanField(default=False, verbose_name="是否有休息時間")
    break_start_time = models.TimeField(blank=True, null=True, verbose_name="休息開始時間")
    break_end_time = models.TimeField(blank=True, null=True, verbose_name="休息結束時間")
    break_hours = models.FloatField(default=0.0, verbose_name="休息時數")
    
    # 報工類型（從報工資料表同步）
    report_type = models.CharField(max_length=20, verbose_name="報工類型", default="normal")
    
    # 數量相關欄位（從報工資料表同步）
    allocated_quantity = models.IntegerField(default=0, verbose_name="分配數量")
    quantity_source = models.CharField(max_length=20, verbose_name="數量來源", default="original")
    allocation_notes = models.TextField(blank=True, verbose_name="分配說明")
    
    # 完工相關欄位（從報工資料表同步）
    is_completed = models.BooleanField(default=False, verbose_name="是否已完工")
    completion_method = models.CharField(max_length=20, verbose_name="完工判斷方式", default="manual")
    auto_completed = models.BooleanField(default=False, verbose_name="自動完工狀態")
    completion_time = models.DateTimeField(blank=True, null=True, verbose_name="完工確認時間")
    cumulative_quantity = models.IntegerField(default=0, verbose_name="累積完成數量")
    cumulative_hours = models.FloatField(default=0.0, verbose_name="累積工時")
    
    # 核准相關欄位（從報工資料表同步）
    approval_status = models.CharField(max_length=20, verbose_name="核准狀態", default="approved")
    approved_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="核准人員")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="核准時間")
    approval_remarks = models.TextField(blank=True, verbose_name="核准備註")
    rejection_reason = models.TextField(blank=True, verbose_name="駁回原因")
    rejected_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="駁回人員")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="駁回時間")
    
    # 備註
    remarks = models.TextField(verbose_name="備註", blank=True)
    abnormal_notes = models.TextField(verbose_name="異常記錄", blank=True)
    
    # 原始報工記錄追蹤
    original_report_id = models.IntegerField(verbose_name="原始報工記錄ID", null=True, blank=True, help_text="對應的原始報工記錄ID")
    original_report_type = models.CharField(max_length=20, verbose_name="原始報工類型", null=True, blank=True, help_text="原始報工記錄的類型")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    created_by = models.CharField(max_length=100, verbose_name="建立人員", default="system")

    class Meta:
        verbose_name = "生產報工明細"
        verbose_name_plural = "生產報工明細"
        db_table = "workorder_production_detail"
        ordering = ["process_name", "start_time", "report_time"]  # 按工序名稱、開始時間、報工時間排序
        indexes = [
            # 優化完工判斷查詢的複合索引
            models.Index(fields=['workorder_production', 'process_name', 'report_source'], 
                        name='idx_prod_detail_completion'),
            # 優化按日期查詢的索引
            models.Index(fields=['report_date'], name='idx_prod_detail_date'),
            # 優化按工序查詢的索引
            models.Index(fields=['process_name'], name='idx_prod_detail_process'),
            # 優化按開始時間查詢的索引
            models.Index(fields=['start_time'], name='idx_prod_detail_start_time'),
        ]

    def __str__(self):
        return f"{self.workorder_production.workorder.order_number} - {self.process_name} - {self.report_date}"


class CompletedWorkOrder(models.Model):
    """
    已完工工單模型
    當工單狀態變更為 'completed' 時，資料會從 WorkOrder 轉移到此模型
    """
    # 原始工單資訊
    original_workorder_id = models.IntegerField(verbose_name="原始工單ID", help_text="對應的原始工單ID")
    order_number = models.CharField(max_length=100, verbose_name="工單號")
    product_code = models.CharField(max_length=100, verbose_name="產品編號")
    company_code = models.CharField(max_length=10, verbose_name="公司代號")
    
    # 工單基本資訊
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    completed_quantity = models.IntegerField(default=0, verbose_name="完成數量")
    status = models.CharField(max_length=20, default='completed', verbose_name="工單狀態")
    
    # 時間資訊
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="開始時間")
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name="完工時間")
    
    # 生產記錄資訊
    production_record = models.ForeignKey(
        'WorkOrderProduction', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="生產記錄"
    )
    
    # 統計資訊
    total_work_hours = models.FloatField(default=0.0, verbose_name="總工作時數")
    total_overtime_hours = models.FloatField(default=0.0, verbose_name="總加班時數")
    total_all_hours = models.FloatField(default=0.0, verbose_name="全部總時數")
    total_good_quantity = models.IntegerField(default=0, verbose_name="總合格品")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="總不良品")
    total_report_count = models.IntegerField(default=0, verbose_name="報工次數")
    
    # 參與人員和設備
    unique_operators = models.JSONField(default=list, verbose_name="參與作業員")
    unique_equipment = models.JSONField(default=list, verbose_name="使用設備")
    
    class Meta:
        verbose_name = "已完工工單"
        verbose_name_plural = "已完工工單"
        db_table = 'workorder_completed_workorder'
        ordering = ['-completed_at']
        unique_together = (("order_number", "product_code"),)  # 工單號+產品編號唯一
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['product_code']),
            models.Index(fields=['company_code']),
            models.Index(fields=['completed_at']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.product_code}"

    def get_completion_rate(self):
        """計算完工率"""
        if self.planned_quantity > 0:
            return (self.completed_quantity / self.planned_quantity) * 100
        return 0.0

    def get_completion_rate_display(self):
        """取得完工率顯示文字"""
        return f"{self.get_completion_rate():.1f}%"


class CompletedWorkOrderProcess(models.Model):
    """
    已完工工單工序模型
    儲存已完工工單的工序資訊
    """
    completed_workorder = models.ForeignKey(
        CompletedWorkOrder, 
        on_delete=models.CASCADE, 
        related_name='processes',
        verbose_name="已完工工單"
    )
    
    # 工序資訊
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    process_order = models.IntegerField(verbose_name="工序順序")
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    completed_quantity = models.IntegerField(default=0, verbose_name="完成數量")
    status = models.CharField(max_length=20, default='completed', verbose_name="工序狀態")
    
    # 分配資訊
    assigned_operator = models.CharField(max_length=100, null=True, blank=True, verbose_name="分配作業員")
    assigned_equipment = models.CharField(max_length=100, null=True, blank=True, verbose_name="分配設備")
    
    # 統計資訊
    total_work_hours = models.FloatField(default=0.0, verbose_name="工作時數")
    total_good_quantity = models.IntegerField(default=0, verbose_name="合格品數量")
    total_defect_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    report_count = models.IntegerField(default=0, verbose_name="報工次數")
    
    # 參與人員和設備
    operators = models.JSONField(default=list, verbose_name="參與作業員")
    equipment = models.JSONField(default=list, verbose_name="使用設備")
    
    class Meta:
        verbose_name = "已完工工單工序"
        verbose_name_plural = "已完工工單工序"
        db_table = 'workorder_completed_workorder_process'
        ordering = ['process_order']

    def __str__(self):
        return f"{self.completed_workorder.order_number} - {self.process_name}"

    def get_completion_rate(self):
        """計算工序完工率"""
        if self.planned_quantity > 0:
            return (self.completed_quantity / self.planned_quantity) * 100
        return 0.0


class CompletedProductionReport(models.Model):
    """
    已完工生產報工記錄模型
    儲存已完工工單的所有報工記錄
    """
    completed_workorder = models.ForeignKey(
        CompletedWorkOrder, 
        on_delete=models.CASCADE, 
        related_name='production_reports',
        verbose_name="已完工工單"
    )
    
    # 報工基本資訊
    report_date = models.DateField(verbose_name="報工日期")
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    operator = models.CharField(max_length=100, verbose_name="作業員")
    equipment = models.CharField(max_length=100, verbose_name="設備")
    
    # 數量資訊
    work_quantity = models.IntegerField(default=0, verbose_name="合格品數量")
    defect_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    
    # 時數資訊
    work_hours = models.FloatField(default=0.0, verbose_name="工作時數")
    overtime_hours = models.FloatField(default=0.0, verbose_name="加班時數")
    
    # 時間資訊
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="開始時間")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="結束時間")
    
    # 報工來源
    report_source = models.CharField(max_length=50, verbose_name="報工來源")
    report_type = models.CharField(max_length=20, verbose_name="報工類型")  # operator, smt, supervisor
    
    # 其他資訊
    remarks = models.TextField(null=True, blank=True, verbose_name="備註")
    abnormal_notes = models.TextField(null=True, blank=True, verbose_name="異常紀錄")
    
    # 審核資訊
    approval_status = models.CharField(max_length=20, default='approved', verbose_name="審核狀態")
    approved_by = models.CharField(max_length=100, null=True, blank=True, verbose_name="審核者")
    approved_at = models.DateTimeField(auto_now_add=True, verbose_name="審核時間")
    
    # 自動分配標記
    allocated_at = models.DateTimeField(null=True, blank=True, verbose_name="分配時間")
    allocation_method = models.CharField(max_length=50, null=True, blank=True, verbose_name="分配方式")
    
    class Meta:
        verbose_name = "已完工生產報工記錄"
        verbose_name_plural = "已完工生產報工記錄"
        db_table = 'workorder_completed_production_report'
        ordering = ['report_date', 'start_time']

    def __str__(self):
        return f"{self.completed_workorder.order_number} - {self.process_name} - {self.report_date}"


class AutoAllocationSettings(models.Model):
    """
    自動分配設定模型
    用於管理自動分配功能的執行設定
    """
    
    # 基本設定
    enabled = models.BooleanField(
        default=False,
        verbose_name="啟用自動執行",
        help_text="是否啟用自動分配功能"
    )
    
    interval_minutes = models.IntegerField(
        default=30,
        verbose_name="執行頻率（分鐘）",
        help_text="自動執行的間隔時間"
    )
    
    start_time = models.TimeField(
        default="08:00",
        verbose_name="開始時間",
        help_text="允許執行的開始時間"
    )
    
    end_time = models.TimeField(
        default="18:00",
        verbose_name="結束時間",
        help_text="允許執行的結束時間"
    )
    
    max_execution_time = models.IntegerField(
        default=30,
        verbose_name="最大執行時間（分鐘）",
        help_text="單次執行的最大時間限制"
    )
    
    notification_enabled = models.BooleanField(
        default=True,
        verbose_name="啟用通知",
        help_text="是否啟用執行結果通知"
    )
    
    # 執行狀態
    is_running = models.BooleanField(
        default=False,
        verbose_name="正在執行",
        help_text="當前是否正在執行"
    )
    
    last_execution = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="最後執行時間",
        help_text="最近一次執行的時間"
    )
    
    next_execution = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="下次執行時間",
        help_text="預定的下次執行時間"
    )
    
    # 統計資訊
    total_executions = models.IntegerField(
        default=0,
        verbose_name="總執行次數",
        help_text="累計執行次數"
    )
    
    success_count = models.IntegerField(
        default=0,
        verbose_name="成功次數",
        help_text="成功執行的次數"
    )
    
    failure_count = models.IntegerField(
        default=0,
        verbose_name="失敗次數",
        help_text="執行失敗的次數"
    )
    
    total_execution_time = models.DurationField(
        null=True,
        blank=True,
        verbose_name="總執行時間",
        help_text="累計執行時間"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "自動分配設定"
        verbose_name_plural = "自動分配設定"
        db_table = "workorder_auto_allocation_settings"
    
    def __str__(self):
        return f"自動分配設定 (啟用: {self.enabled}, 頻率: {self.interval_minutes}分鐘)"
    
    @property
    def avg_execution_time(self):
        """計算平均執行時間"""
        if self.total_executions > 0 and self.total_execution_time:
            total_seconds = self.total_execution_time.total_seconds()
            return total_seconds / self.total_executions
        return 0
    
    def get_avg_execution_time_display(self):
        """取得平均執行時間的顯示格式"""
        try:
            avg_seconds = self.avg_execution_time
            if avg_seconds < 60:
                return f"{avg_seconds:.1f}秒"
            elif avg_seconds < 3600:
                return f"{avg_seconds/60:.1f}分鐘"
            else:
                return f"{avg_seconds/3600:.1f}小時"
        except Exception:
            return "0秒"
    
    def is_within_execution_window(self):
        """檢查當前時間是否在執行時間範圍內"""
        from django.utils import timezone
        from datetime import time
        
        now = timezone.now().time()
        return self.start_time <= now <= self.end_time
    
    def should_execute(self):
        """判斷是否應該執行"""
        if not self.enabled:
            return False
        
        # 移除執行時間範圍檢查，允許全天候執行
        # if not self.is_within_execution_window():
        #     return False
        
        if self.is_running:
            return False
        
        if self.next_execution and timezone.now() < self.next_execution:
            return False
        
        return True


class AutoAllocationLog(models.Model):
    """
    自動分配執行記錄模型
    記錄每次自動分配的執行結果
    """
    
    # 執行資訊
    started_at = models.DateTimeField(
        verbose_name="開始時間",
        help_text="執行開始時間"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="完成時間",
        help_text="執行完成時間"
    )
    
    execution_time = models.DurationField(
        null=True,
        blank=True,
        verbose_name="執行時間",
        help_text="實際執行時間"
    )
    
    # 執行結果
    success = models.BooleanField(
        default=False,
        verbose_name="執行成功",
        help_text="是否執行成功"
    )
    
    total_workorders = models.IntegerField(
        default=0,
        verbose_name="處理工單數",
        help_text="本次處理的工單數量"
    )
    
    successful_allocations = models.IntegerField(
        default=0,
        verbose_name="成功分配數",
        help_text="成功分配的工單數量"
    )
    
    failed_allocations = models.IntegerField(
        default=0,
        verbose_name="失敗分配數",
        help_text="分配失敗的工單數量"
    )
    
    # 錯誤資訊
    error_message = models.TextField(
        blank=True,
        verbose_name="錯誤訊息",
        help_text="執行失敗時的錯誤訊息"
    )
    
    # 詳細結果
    result_details = models.JSONField(
        null=True,
        blank=True,
        verbose_name="詳細結果",
        help_text="執行的詳細結果資訊"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "自動分配執行記錄"
        verbose_name_plural = "自動分配執行記錄"
        db_table = "workorder_auto_allocation_log"
        ordering = ['-started_at']
    
    def __str__(self):
        status = "成功" if self.success else "失敗"
        return f"自動分配記錄 ({self.started_at.strftime('%Y-%m-%d %H:%M')}) - {status}"
    
    @property
    def execution_time_display(self):
        """取得執行時間的顯示格式"""
        if self.execution_time:
            total_seconds = self.execution_time.total_seconds()
            if total_seconds < 60:
                return f"{total_seconds:.1f}秒"
            elif total_seconds < 3600:
                return f"{total_seconds/60:.1f}分鐘"
            else:
                return f"{total_seconds/3600:.1f}小時"
        return "--"


class AutoManagementConfig(models.Model):
    """
    自動管理功能設定模型
    用於設定各種自動化功能的執行間隔和開關狀態
    """
    
    # 功能類型選擇
    FUNCTION_TYPE_CHOICES = [
        ('auto_completion_check', '完工判斷轉寫已完工'),
        ('auto_approval', '自動核准'),
        ('auto_notification', '自動通知'),
    ]
    
    function_type = models.CharField(
        max_length=50,
        choices=FUNCTION_TYPE_CHOICES,
        verbose_name="功能類型",
        help_text="選擇要設定的自動化功能類型"
    )
    
    is_enabled = models.BooleanField(
        default=True,
        verbose_name="是否啟用",
        help_text="是否啟用此自動化功能"
    )
    
    interval_minutes = models.IntegerField(
        default=30,
        verbose_name="執行間隔（分鐘）",
        help_text="設定自動化功能的執行間隔，以分鐘為單位"
    )
    
    last_execution = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="最後執行時間",
        help_text="記錄此功能最後執行的時間"
    )
    
    next_execution = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="下次執行時間",
        help_text="預估下次執行的時間"
    )
    
    execution_count = models.IntegerField(
        default=0,
        verbose_name="執行次數",
        help_text="記錄此功能已執行的次數"
    )
    
    success_count = models.IntegerField(
        default=0,
        verbose_name="成功次數",
        help_text="記錄此功能成功執行的次數"
    )
    
    error_count = models.IntegerField(
        default=0,
        verbose_name="錯誤次數",
        help_text="記錄此功能執行失敗的次數"
    )
    
    last_error_message = models.TextField(
        blank=True,
        verbose_name="最後錯誤訊息",
        help_text="記錄最後一次執行失敗的錯誤訊息"
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
        verbose_name = "自動管理功能設定"
        verbose_name_plural = "自動管理功能設定"
        db_table = "workorder_auto_management_config"
        unique_together = ['function_type']
        ordering = ['function_type']
    
    def __str__(self):
        return f"{self.get_function_type_display()} - {self.interval_minutes}分鐘"
    
    def save(self, *args, **kwargs):
        """儲存時自動計算下次執行時間"""
        if self.is_enabled and self.interval_minutes > 0:
            from django.utils import timezone
            from datetime import timedelta
            
            if self.last_execution:
                # 如果有最後執行時間，則下次執行時間 = 最後執行時間 + 間隔
                self.next_execution = self.last_execution + timedelta(minutes=self.interval_minutes)
            else:
                # 如果沒有最後執行時間，則下次執行時間 = 現在時間 + 間隔
                self.next_execution = timezone.now() + timedelta(minutes=self.interval_minutes)
        
        super().save(*args, **kwargs)
    
    def update_execution_time(self, success=True, error_message=""):
        """
        更新執行時間和統計資訊
        
        Args:
            success: 是否執行成功
            error_message: 錯誤訊息（如果執行失敗）
        """
        from django.utils import timezone
        
        self.last_execution = timezone.now()
        self.execution_count += 1
        
        if success:
            self.success_count += 1
            self.last_error_message = ""
        else:
            self.error_count += 1
            self.last_error_message = error_message
        
        self.save()
    
    @classmethod
    def get_config(cls, function_type):
        """
        獲取指定功能的設定
        
        Args:
            function_type: 功能類型
            
        Returns:
            AutoManagementConfig: 設定實例，如果不存在則建立預設設定
        """
        config, created = cls.objects.get_or_create(
            function_type=function_type,
            defaults={
                'is_enabled': True,
                'interval_minutes': 30,
            }
        )
        return config
    
    @classmethod
    def get_enabled_functions(cls):
        """
        獲取所有已啟用的功能設定
        
        Returns:
            QuerySet: 已啟用的功能設定列表
        """
        return cls.objects.filter(is_enabled=True)
    
    @classmethod
    def get_due_functions(cls):
        """
        獲取需要執行的功能（下次執行時間已到）
        
        Returns:
            QuerySet: 需要執行的功能設定列表
        """
        from django.utils import timezone
        return cls.objects.filter(
            is_enabled=True,
            next_execution__lte=timezone.now()
        )



