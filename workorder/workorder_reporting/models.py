"""
報工管理子模組 - 模型定義
負責報工管理功能，包括SMT報工、作業員補登報工、主管報工等
"""

from django.db import models
from django.utils import timezone


class SMTProductionReport(models.Model):
    """
    SMT 生產報工記錄模型 (SMT Production Report Model)
    SMT 設備為自動化運作，不需要作業員
    """



    # 基本資訊
    # 公司代號欄位
    company_code = models.CharField(
        max_length=10,
        verbose_name="公司代號",
        help_text="公司代號，用於多公司架構",
        default="",
    )

    product_id = models.CharField(
        max_length=100,
        verbose_name="產品編號",
        help_text="請選擇產品編號，將自動帶出相關工單",
        default="",
    )

    workorder = models.ForeignKey(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        verbose_name="工單號碼",
        help_text="請選擇工單號碼，或透過產品編號自動帶出",
        null=True,
        blank=True,
    )

    # 舊資料匯入專用欄位
    original_workorder_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="原始工單號碼",
        help_text="用於儲存舊資料匯入時的工單號碼，當工單不存在於系統中時使用",
    )

    planned_quantity = models.IntegerField(
        verbose_name="工單預設生產數量",
        help_text="此為工單規劃的總生產數量，不可修改",
        default=0,
    )

    process = models.ForeignKey(
        "process.ProcessName",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="工序",
        help_text="請選擇此次補登的SMT工序",
    )

    operation = models.CharField(
        max_length=100,
        verbose_name="工序名稱",
        help_text="工序名稱（自動從 process 欄位取得）",
        default="",
    )

    equipment = models.ForeignKey(
        "equip.Equipment",
        on_delete=models.CASCADE,
        verbose_name="使用的設備",
        help_text="請選擇本次報工使用的SMT設備",
        null=True,
        blank=True,
    )

    # 時間資訊
    work_date = models.DateField(
        verbose_name="日期", help_text="請選擇實際報工日期", default=timezone.now
    )

    start_time = models.TimeField(
        verbose_name="開始時間",
        help_text="請輸入實際開始時間 (24小時制)，例如 16:00",
        default=timezone.now,
    )

    end_time = models.TimeField(
        verbose_name="結束時間",
        help_text="請輸入實際結束時間 (24小時制)，例如 18:30",
        default=timezone.now,
    )

    # SMT 工時計算欄位（SMT 中午不休息，16:30 以後算加班）
    work_hours_calculated = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="正常工時",
        help_text="16:30 之前的工時",
    )

    overtime_hours_calculated = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="加班工時",
        help_text="16:30 以後的工時",
    )

    # 數量資訊
    work_quantity = models.IntegerField(
        verbose_name="工作數量",
        help_text="請輸入該時段內實際完成的合格產品數量",
        default=0,
    )

    defect_quantity = models.IntegerField(
        default=0,
        verbose_name="不良品數量",
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
    )

    # 狀態資訊
    is_completed = models.BooleanField(
        default=False,
        verbose_name="是否已完工",
        help_text="若此工單在此工序上已全部完成，請勾選",
    )

    # 備註
    remarks = models.TextField(
        blank=True,
        verbose_name="備註",
        help_text="請輸入任何需要補充的資訊，如設備標記、操作說明等",
    )

    # 異常記錄
    abnormal_notes = models.TextField(
        blank=True,
        verbose_name="異常記錄",
        help_text="記錄生產過程中的異常情況，如設備故障、品質問題等",
    )

    # 報工類型欄位已移除，所有SMT報工都視為正常工作

    # 核准相關欄位
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "待核准"),
            ("approved", "已核准"),
            ("rejected", "已駁回"),
        ],
        default="pending",
        verbose_name="核准狀態",
        help_text="此補登記錄的核准狀態",
    )

    approved_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="核准人員",
        help_text="此補登記錄的核准人員",
    )

    approved_at = models.DateTimeField(
        blank=True, null=True, verbose_name="核准時間", help_text="此補登記錄的核准時間"
    )

    approval_remarks = models.TextField(
        blank=True, verbose_name="核准備註", help_text="核准時的備註說明"
    )

    rejection_reason = models.TextField(
        blank=True, verbose_name="駁回原因", help_text="駁回時的原因說明"
    )

    # 駁回相關欄位
    rejected_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="駁回人員",
        help_text="駁回此補登記錄的人員",
    )

    rejected_at = models.DateTimeField(
        blank=True, null=True, verbose_name="駁回時間", help_text="此補登記錄的駁回時間"
    )

    # 系統欄位
    created_by = models.CharField(
        max_length=100, verbose_name="建立人員", default="system"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "SMT生產報工記錄"
        verbose_name_plural = "SMT生產報工記錄"
        db_table = "workorder_smt_production_report"
        ordering = ["-work_date", "-start_time"]

    def __str__(self):
        return f"{self.workorder.order_number if self.workorder else '無工單'} - {self.work_date}"

    @property
    def workorder_number(self):
        """取得工單號碼"""
        if self.workorder:
            return self.workorder.order_number
        elif self.original_workorder_number:
            # 舊資料匯入的工單號碼
            return self.original_workorder_number
        elif self.product_id:
            # 如果有產品編號但沒有工單，可能是手動輸入的產品編號
            return f"產品編號：{self.product_id}"
        else:
            return ""

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


        # 已核准的記錄只有超級管理員可以編輯
        if self.approval_status == "approved":
            return user.is_superuser
        return True

    def can_delete(self, user):
        """
        檢查記錄是否可以刪除
        只有建立記錄的用戶和超級主管可以刪除待核准和已駁回的記錄
        已核准的記錄只有超級主管可以刪除
        """
        # 已核准的記錄只有超級主管可以刪除
        if self.approval_status == "approved":
            return user.is_superuser

        # 待核准和已駁回的記錄，只有建立者或超級主管可以刪除
        return user.is_superuser or self.created_by == user.username

    def can_approve(self, user):
        """檢查是否可以核准"""
        # 只有超級用戶或主管群組可以核准
        if user.is_superuser:
            return True

        # 檢查是否在主管群組中
        return user.groups.filter(name="主管").exists()

    def approve(self, user, remarks=""):
        """
        核准補登記錄
        """
        self.approval_status = "approved"
        self.approved_by = user.username
        self.approved_at = timezone.now()
        self.approval_remarks = remarks
        self.save()

    def reject(self, user, reason=""):
        """
        駁回補登記錄
        """
        self.approval_status = "rejected"
        self.rejected_by = user.username
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def calculate_work_hours(self):
        """計算 SMT 工作時數和加班時數（SMT 中午不休息，16:30 以後算加班）"""
        if self.start_time and self.end_time:
            from datetime import datetime, timedelta, time

            start_dt = datetime.combine(self.work_date, self.start_time)
            end_dt = datetime.combine(self.work_date, self.end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            # 計算總時數（SMT 不扣除休息時間）
            duration = end_dt - start_dt
            total_hours = round(duration.total_seconds() / 3600, 2)
            
            # 計算正常工時和加班時數
            # 加班時數：超過16:30以後的時間才算加班
            overtime_start_time = time(16, 30)  # 16:30開始算加班
            
            # 修正：正確計算加班時數
            if self.start_time >= overtime_start_time:
                # 開始時間在16:30之後，全部算加班
                self.overtime_hours_calculated = round(total_hours, 2)
                self.work_hours_calculated = 0.0
            elif self.end_time > overtime_start_time:
                # 開始時間在16:30之前，結束時間在16:30之後
                # 計算正常工時（從開始時間到16:30）
                normal_end_dt = datetime.combine(self.work_date, overtime_start_time)
                normal_duration = normal_end_dt - start_dt
                normal_hours = round(normal_duration.total_seconds() / 3600, 2)
                
                # 計算加班時數（從16:30到結束時間）
                overtime_start_dt = datetime.combine(self.work_date, overtime_start_time)
                overtime_duration = end_dt - overtime_start_dt
                overtime_hours = round(overtime_duration.total_seconds() / 3600, 2)
                
                self.work_hours_calculated = round(normal_hours, 2)
                self.overtime_hours_calculated = round(overtime_hours, 2)
            else:
                # 開始和結束時間都在16:30之前，全部算正常工時
                self.work_hours_calculated = round(total_hours, 2)
                self.overtime_hours_calculated = 0.0
            
            return {
                'total_hours': total_hours,
                'work_hours': self.work_hours_calculated,
                'overtime_hours': self.overtime_hours_calculated,
            }
        return {
            'total_hours': 0.0,
            'work_hours': 0.0,
            'overtime_hours': 0.0,
        }

    def save(self, *args, **kwargs):
        """儲存時自動計算工作時數和加班時數"""
        # 自動計算工作時數和加班時數
        self.calculate_work_hours()
        super().save(*args, **kwargs) 


class OperatorSupplementReport(models.Model):
    """
    作業員補登報工記錄模型 (Operator Supplement Report Model)
    專為作業員的歷史報工記錄管理而設計，支援離線數據輸入、歷史數據修正和批量數據處理
    """

    # 基本資訊
    operator = models.ForeignKey(
        "process.Operator",
        on_delete=models.CASCADE,
        verbose_name="作業員",
        help_text="請選擇進行補登報工的作業員",
    )

    # 公司代號欄位
    company_code = models.CharField(
        max_length=10,
        verbose_name="公司代號",
        help_text="公司代號，用於多公司架構",
        default="",
    )

    workorder = models.ForeignKey(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        verbose_name="工單號碼",
        help_text="請選擇要補登的工單號碼",
        null=True,
        blank=True,
    )

    # 舊資料匯入專用欄位
    original_workorder_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="原始工單號碼",
        help_text="用於儲存舊資料匯入時的工單號碼，當工單不存在於系統中時使用",
    )

    # 產品編號欄位（用於資料庫相容性）
    product_id = models.CharField(
        max_length=100,
        verbose_name="產品編號",
        help_text="產品編號（自動從工單取得）",
        default="",
    )

    # 工單預設生產數量（唯讀）
    planned_quantity = models.IntegerField(
        verbose_name="工單預設生產數量",
        help_text="此為工單規劃的總生產數量，不可修改",
        default=0,
    )

    process = models.ForeignKey(
        "process.ProcessName",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="工序",
        help_text="請選擇此次補登的工序（排除SMT相關工序）",
    )

    # 工序名稱欄位（用於資料庫相容性）
    operation = models.CharField(
        max_length=100,
        verbose_name="工序名稱",
        help_text="工序名稱（自動從 process 欄位取得）",
        default="",
    )

    # 設備資訊（可選）
    equipment = models.ForeignKey(
        "equip.Equipment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="使用的設備",
        help_text="請選擇此次補登使用的設備（排除SMT相關設備）",
    )

    # 時間資訊
    work_date = models.DateField(
        verbose_name="日期", help_text="請選擇實際報工日期", default=timezone.now
    )

    start_time = models.TimeField(
        verbose_name="開始時間",
        help_text="請輸入實際開始時間 (24小時制)，例如 16:00",
        default=timezone.now,
    )

    end_time = models.TimeField(
        verbose_name="結束時間",
        help_text="請輸入實際結束時間 (24小時制)，例如 18:30",
        default=timezone.now,
    )

    # 休息時間相關欄位
    has_break = models.BooleanField(
        default=False,
        verbose_name="是否有休息時間",
        help_text="系統自動判斷是否橫跨中午休息時間",
    )

    break_start_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="休息開始時間",
        help_text="中午休息開始時間（固定為12:00）",
    )

    break_end_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name="休息結束時間",
        help_text="中午休息結束時間（固定為13:00）",
    )

    break_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        verbose_name="休息時數",
        help_text="中午休息時數（固定為1小時）",
    )

    # 新增：工作時數和加班時數欄位
    work_hours_calculated = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="工作時數",
        help_text="扣除休息時間後的實際工作時數",
    )

    overtime_hours_calculated = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="加班時數",
        help_text="超過正常工時的部分",
    )

    # 數量資訊
    work_quantity = models.IntegerField(
        verbose_name="工作數量",
        help_text="請輸入該時段內實際完成的合格產品數量",
        default=0,
    )

    # 分配數量相關欄位
    allocated_quantity = models.IntegerField(
        default=0,
        verbose_name="分配數量",
        help_text="系統智能分配的數量"
    )
    
    quantity_source = models.CharField(
        max_length=20,
        choices=[
            ('original', '原始數量'),
            ('allocated', '智能分配'),
            ('packaging', '包裝工序'),
        ],
        default='original',
        verbose_name="數量來源",
        help_text="數量的來源類型"
    )
    
    allocation_notes = models.TextField(
        blank=True,
        verbose_name="分配說明",
        help_text="記錄分配計算過程和依據"
    )

    # 新增：自動分配檢查狀態欄位
    allocation_checked = models.BooleanField(
        default=False,
        verbose_name="已檢查自動分配",
        help_text="標記此記錄是否已經過自動分配檢查，避免重複檢查"
    )
    
    allocation_checked_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="分配檢查時間",
        help_text="記錄此記錄被自動分配檢查的時間"
    )
    
    allocation_check_result = models.CharField(
        max_length=20,
        choices=[
            ('not_checked', '未檢查'),
            ('allocated', '已分配'),
            ('excluded_packaging', '排除包裝'),
            ('no_allocation_needed', '無需分配'),
        ],
        default='not_checked',
        verbose_name="分配檢查結果",
        help_text="記錄自動分配檢查的結果"
    )

    defect_quantity = models.IntegerField(
        default=0,
        verbose_name="不良品數量",
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
    )

    # 狀態資訊
    is_completed = models.BooleanField(
        default=False,
        verbose_name="是否已完工",
        help_text="若此工單在此工序上已全部完成，請勾選",
    )

    # 完工判斷方式
    COMPLETION_METHOD_CHOICES = [
        ("manual", "手動勾選"),
        ("auto_quantity", "自動依數量判斷"),
        ("auto_time", "自動依工時判斷"),
        ("auto_operator", "作業員確認"),
        ("auto_system", "系統自動判斷"),
    ]

    completion_method = models.CharField(
        max_length=20,
        choices=COMPLETION_METHOD_CHOICES,
        default="manual",
        verbose_name="完工判斷方式",
        help_text="選擇如何判斷此筆記錄是否代表工單完工",
    )

    # 自動完工狀態（系統計算）
    auto_completed = models.BooleanField(
        default=False,
        verbose_name="自動完工狀態",
        help_text="系統根據累積數量或工時自動判斷的完工狀態",
    )

    # 完工確認時間
    completion_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="完工確認時間",
        help_text="系統記錄的完工確認時間",
    )

    # 累積完成數量（用於自動完工判斷）
    cumulative_quantity = models.IntegerField(
        default=0,
        verbose_name="累積完成數量",
        help_text="此工單在此工序上的累積完成數量",
    )

    # 累積工時（用於自動完工判斷）
    cumulative_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="累積工時",
        help_text="此工單在此工序上的累積工時",
    )

    # 核准狀態
    APPROVAL_STATUS_CHOICES = [
        ("pending", "待核准"),
        ("approved", "已核准"),
        ("rejected", "已駁回"),
    ]

    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default="pending",
        verbose_name="核准狀態",
        help_text="補登記錄的核准狀態，已核准的記錄不可修改",
    )

    approved_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="核准人員",
        help_text="核准此補登記錄的人員",
    )

    approved_at = models.DateTimeField(
        blank=True, null=True, verbose_name="核准時間", help_text="此補登記錄的核准時間"
    )

    approval_remarks = models.TextField(
        blank=True, verbose_name="核准備註", help_text="核准時的備註說明"
    )

    rejection_reason = models.TextField(
        blank=True, verbose_name="駁回原因", help_text="駁回時的原因說明"
    )

    # 駁回相關欄位
    rejected_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="駁回人員",
        help_text="駁回此補登記錄的人員",
    )

    rejected_at = models.DateTimeField(
        blank=True, null=True, verbose_name="駁回時間", help_text="此補登記錄的駁回時間"
    )

    # 備註
    remarks = models.TextField(
        blank=True,
        verbose_name="備註",
        help_text="請輸入任何需要補充的資訊，如設備標記、操作說明等",
    )

    # 異常記錄
    abnormal_notes = models.TextField(
        blank=True,
        verbose_name="異常記錄",
        help_text="記錄生產過程中的異常情況，如設備故障、品質問題等",
    )

    # 系統欄位
    created_by = models.CharField(
        max_length=100, verbose_name="建立人員", default="system"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "作業員補登報工記錄"
        verbose_name_plural = "作業員補登報工記錄"
        db_table = "workorder_operator_supplement_report"
        ordering = ["-work_date", "-start_time"]

    def __str__(self):
        return (
            f"{self.operator.name} - {self.workorder.order_number} - {self.work_date}"
        )

    @property
    def operator_name(self):
        """取得作業員名稱"""
        return self.operator.name if self.operator else ""

    @property
    def workorder_number(self):
        """取得工單號碼"""
        if self.workorder:
            return self.workorder.order_number
        elif self.original_workorder_number:
            # 舊資料匯入的工單號碼
            return self.original_workorder_number
        elif self.product_id:
            # 如果有產品編號但沒有工單，可能是手動輸入的產品編號
            return f"產品編號：{self.product_id}"
        else:
            return ""



    @property
    def process_name(self):
        """取得工序名稱"""
        return self.process.name if self.process else ""

    @property
    def equipment_name(self):
        """取得設備名稱"""
        return self.equipment.name if self.equipment else "未指定設備"

    @property
    def total_quantity(self):
        """取得總數量（工作數量 + 不良品數量）"""
        return self.work_quantity + self.defect_quantity

    @property
    def work_hours(self):
        """計算工作時數（扣除休息時間）"""
        if self.start_time and self.end_time:
            from datetime import datetime, timedelta, time

            start_dt = datetime.combine(self.work_date, self.start_time)
            end_dt = datetime.combine(self.work_date, self.end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            # 計算總時數
            duration = end_dt - start_dt
            total_hours = round(duration.total_seconds() / 3600, 2)
            
            # 檢查是否橫跨中午休息時間（12:00-13:00）
            lunch_start = time(12, 0)
            lunch_end = time(13, 0)
            
            # 判斷是否橫跨休息時間
            if (self.start_time < lunch_start and self.end_time > lunch_end):
                # 有橫跨休息時間，扣除1小時
                total_hours = max(0, total_hours - 1.0)
                self.has_break = True
                self.break_start_time = lunch_start
                self.break_end_time = lunch_end
                self.break_hours = 1.0
            else:
                # 沒有橫跨休息時間
                self.has_break = False
                self.break_start_time = None
                self.break_end_time = None
                self.break_hours = 0.0
            
            return round(total_hours, 2)
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
        if self.approval_status == "approved":
            return user.is_superuser
        return True

    def can_delete(self, user):
        """
        檢查記錄是否可以刪除
        只有建立記錄的用戶和超級主管可以刪除待核准和已駁回的記錄
        已核准的記錄只有超級主管可以刪除
        """
        # 調試信息
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Checking delete permission for user: {user.username}")
        logger.info(f"Record created_by: {self.created_by}, approval_status: {self.approval_status}")
        logger.info(f"User is_superuser: {user.is_superuser}")
        
        # 已核准的記錄只有超級主管可以刪除
        if self.approval_status == "approved":
            logger.info("Record is approved, only superuser can delete")
            return user.is_superuser

        # 待核准和已駁回的記錄，只有建立者或超級主管可以刪除
        # 如果 created_by 是 "system"，則允許所有用戶刪除
        if self.created_by == "system":
            logger.info("Record created by system, allowing delete")
            return True
            
        can_delete = user.is_superuser or self.created_by == user.username
        logger.info(f"Final can_delete result: {can_delete}")
        return can_delete

    def can_approve(self, user):
        """
        檢查記錄是否可以核准
        只有管理員和超級管理員可以核准
        """
        return user.is_staff or user.is_superuser

    def approve(self, user, remarks=""):
        """
        核准通過補登記錄
        """
        self.approval_status = "approved"
        self.approved_by = user.username
        self.approved_at = timezone.now()
        self.approval_remarks = remarks
        self.save()

    def reject(self, user, reason=""):
        """
        駁回補登記錄
        """
        self.approval_status = "rejected"
        self.rejected_by = user.username
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def submit_for_approval(self):
        """提交核准"""
        self.approval_status = "pending"
        self.save()

    def check_auto_completion(self):
        """檢查是否自動完工"""
        from django.utils import timezone

        # 取得此工單在此工序上的所有記錄
        all_reports = OperatorSupplementReport.objects.filter(
            workorder=self.workorder, process=self.process
        ).order_by("work_date", "start_time")

        # 計算累積數量
        total_quantity = sum(
            report.work_quantity for report in all_reports if report.work_quantity
        )

        # 計算累積工時
        total_hours = sum(report.work_hours for report in all_reports)

        # 更新累積數據
        self.cumulative_quantity = total_quantity
        self.cumulative_hours = total_hours

        # 自動完工判斷邏輯
        auto_completed = False
        completion_method = "manual"

        # 1. 依數量判斷：累積數量 >= 工單預設數量
        if total_quantity >= self.workorder.quantity:
            auto_completed = True
            completion_method = "auto_quantity"

        # 2. 依工時判斷：累積工時 >= 預估工時（假設每小時產出 50 件）
        estimated_hours = self.workorder.quantity / 50  # 可調整的預估標準
        if total_hours >= estimated_hours:
            auto_completed = True
            completion_method = "auto_time"

        # 3. 作業員確認：在備註中提及完工
        if "完工" in (self.remarks or "") or "完成" in (self.remarks or ""):
            auto_completed = True
            completion_method = "auto_operator"

        # 更新自動完工狀態
        self.auto_completed = auto_completed
        self.completion_method = completion_method

        # 如果自動完工，設定完工時間
        if auto_completed and not self.completion_time:
            self.completion_time = timezone.now()

        self.save()

        return auto_completed

    def calculate_work_hours(self):
        """計算工作時數和加班時數"""
        if self.start_time and self.end_time:
            from datetime import datetime, timedelta, time

            start_dt = datetime.combine(self.work_date, self.start_time)
            end_dt = datetime.combine(self.work_date, self.end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            # 計算總時數（從開始到結束的完整時數）
            duration = end_dt - start_dt
            total_hours = round(duration.total_seconds() / 3600, 2)
            
            # 檢查是否橫跨中午休息時間（12:00-13:00）
            lunch_start = time(12, 0)
            lunch_end = time(13, 0)
            
            # 判斷是否橫跨休息時間
            if (self.start_time < lunch_start and self.end_time > lunch_end):
                # 有橫跨休息時間，扣除1小時
                actual_work_hours = max(0, total_hours - 1.0)
                self.has_break = True
                self.break_start_time = lunch_start
                self.break_end_time = lunch_end
                self.break_hours = 1.0
            else:
                # 沒有橫跨休息時間
                actual_work_hours = total_hours
                self.has_break = False
                self.break_start_time = None
                self.break_end_time = None
                self.break_hours = 0.0
            
            # 計算正常工時和加班時數
            # 加班時數：超過17:30以後的時間才算加班
            overtime_start_time = time(17, 30)  # 17:30開始算加班
            
            # 修正：正確計算加班時數
            if self.start_time >= overtime_start_time:
                # 開始時間在17:30之後，全部算加班
                self.overtime_hours_calculated = round(actual_work_hours, 2)
                self.work_hours_calculated = 0.0
            elif self.end_time > overtime_start_time:
                # 開始時間在17:30之前，結束時間在17:30之後
                # 計算正常工時（從開始時間到17:30）
                normal_end_dt = datetime.combine(self.work_date, overtime_start_time)
                normal_duration = normal_end_dt - start_dt
                normal_hours = round(normal_duration.total_seconds() / 3600, 2)
                
                # 如果正常工時橫跨休息時間，需要扣除休息時間
                if self.has_break and self.start_time < lunch_start and overtime_start_time > lunch_end:
                    normal_hours = max(0, normal_hours - 1.0)
                
                # 計算加班時數（從17:30到結束時間）
                overtime_start_dt = datetime.combine(self.work_date, overtime_start_time)
                overtime_duration = end_dt - overtime_start_dt
                overtime_hours = round(overtime_duration.total_seconds() / 3600, 2)
                
                # 如果加班時間橫跨休息時間，需要扣除休息時間
                if self.has_break and overtime_start_time < lunch_start and self.end_time > lunch_end:
                    overtime_hours = max(0, overtime_hours - 1.0)
                
                self.work_hours_calculated = round(normal_hours, 2)
                self.overtime_hours_calculated = round(overtime_hours, 2)
            else:
                # 開始和結束時間都在17:30之前，全部算正常工時
                self.work_hours_calculated = round(actual_work_hours, 2)
                self.overtime_hours_calculated = 0.0
            
            return {
                'total_hours': total_hours,
                'actual_work_hours': actual_work_hours,
                'work_hours': self.work_hours_calculated,
                'overtime_hours': self.overtime_hours_calculated,
                'break_hours': float(self.break_hours)
            }
        return {
            'total_hours': 0.0,
            'actual_work_hours': 0.0,
            'work_hours': 0.0,
            'overtime_hours': 0.0,
            'break_hours': 0.0
        }

    def save(self, *args, **kwargs):
        """儲存時自動計算工作時數和加班時數，並自動取得產品編號"""
        # 自動從工單取得產品編號
        if self.workorder and hasattr(self.workorder, 'product_code') and self.workorder.product_code:
            self.product_id = self.workorder.product_code
        
        # 確保設備欄位正確保存
        if hasattr(self, 'equipment') and self.equipment:
            # 設備欄位存在且有值，確保正確保存
            pass
        
        # 自動計算工作時數和加班時數
        self.calculate_work_hours()
        super().save(*args, **kwargs)

    def get_completion_status_display(self):
        """取得完工狀態顯示文字"""
        if self.is_completed:
            return "手動完工"
        elif self.auto_completed:
            method_display = dict(self.COMPLETION_METHOD_CHOICES).get(
                self.completion_method, ""
            )
            return f"自動完工({method_display})"
        else:
            return "未完工"

    def get_completion_summary(self):
        """取得完工摘要資訊"""
        # 處理workorder為None的情況（RD樣品模式）
        if self.workorder is None:
            return {
                "is_completed": self.is_completed,
                "auto_completed": self.auto_completed,
                "completion_method": self.completion_method,
                "completion_time": self.completion_time,
                "cumulative_quantity": self.cumulative_quantity,
                "cumulative_hours": self.cumulative_hours,
                "planned_quantity": 0,  # RD樣品沒有預設數量
                "completion_rate": 0,  # RD樣品不計算完工率
            }
        
        return {
            "is_completed": self.is_completed,
            "auto_completed": self.auto_completed,
            "completion_method": self.completion_method,
            "completion_time": self.completion_time,
            "cumulative_quantity": self.cumulative_quantity,
            "cumulative_hours": self.cumulative_hours,
            "planned_quantity": self.workorder.quantity,
            "completion_rate": (
                (self.cumulative_quantity / self.workorder.quantity * 100)
                if self.workorder.quantity > 0
                else 0
            ),
        } 


# 移除主管報工模型，避免與主管審核功能混淆
# 主管應該專注於審核作業員和SMT的報工記錄，而不是自己報工

# 原本的 SupervisorProductionReport 模型已移除
# 主管職責：監督、審核、管理，不代為報工 