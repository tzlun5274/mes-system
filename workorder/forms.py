from django import forms
from django.db.models import Q
from django.utils import timezone
from .models import (
    WorkOrder,
    CompanyOrder,
    WorkOrderProcess,
    WorkOrderAssignment,
    WorkOrderProduction,
    WorkOrderProductionDetail,
    AutoManagementConfig,
)
from .workorder_reporting.models import SMTProductionReport, OperatorSupplementReport
from process.models import Operator
from equip.models import Equipment
from datetime import datetime, date, timedelta
from django.contrib.auth.models import User


class TimeInputWidget(forms.Widget):
    """
    自定義時間輸入元件
    支援下拉式選單和手動輸入兩種方式
    """

    template_name = "workorder/widgets/time_input.html"

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        # 設定預設屬性
        default_attrs = {
            "class": "form-control time-input",
            "type": "text",
            "placeholder": "請選擇或輸入時間 (HH:MM)",
            "autocomplete": "off",
        }
        default_attrs.update(attrs)
        super().__init__(default_attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        # 生成時間選項（每30分鐘一個選項）
        time_options = []
        for hour in range(24):
            for minute in [0, 30]:
                time_str = f"{hour:02d}:{minute:02d}"
                time_options.append(time_str)

        context["time_options"] = time_options
        return context


class TimeField(forms.CharField):
    """
    自定義時間欄位
    支援下拉式選單和手動輸入兩種方式
    """

    widget = TimeInputWidget

    def __init__(self, *args, **kwargs):
        # 設定預設屬性
        kwargs.setdefault("max_length", 5)
        kwargs.setdefault("help_text", "請選擇或輸入時間 (24小時制，格式：HH:MM)")
        super().__init__(*args, **kwargs)

    def clean(self, value):
        """驗證時間格式"""
        value = super().clean(value)
        if not value:
            return value

        # 驗證時間格式 (HH:MM)
        try:
            if ":" not in value:
                raise ValueError("時間格式錯誤")

            hour_str, minute_str = value.split(":")
            hour = int(hour_str)
            minute = int(minute_str)

            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("時間範圍錯誤")

            # 格式化為標準格式
            return f"{hour:02d}:{minute:02d}"

        except (ValueError, TypeError):
            raise forms.ValidationError(
                "請輸入正確的時間格式 (HH:MM)，例如：08:30 或 16:45"
            )


class ProductionReportBaseForm(forms.ModelForm):
    """
    【規範】報工共用表單
    - 任何報工表單都必須繼承這個類別
    - 共用欄位：工單號碼、產品編號、工序、設備、日期、開始/結束時間、數量、不良品、備註
    - 禁止在子類別重複定義這些欄位
    """

    # 工單號碼欄位
    workorder = forms.ModelChoiceField(
        queryset=None,
        label="工單號碼",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "placeholder": "請選擇工單號碼",
            }
        ),
        required=True,
        help_text="請選擇工單號碼",
    )

    # 產品編號欄位
    product_id = forms.ChoiceField(
        choices=[],
        label="產品編號",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "product_id_select",
                "placeholder": "請選擇產品編號",
            }
        ),
        required=True,
        help_text="請選擇產品編號，將自動帶出相關工單號碼",
    )

    # 工序欄位
    process = forms.ModelChoiceField(
        queryset=None,
        label="工序",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "placeholder": "請選擇工序名稱",
            }
        ),
        required=True,
        help_text="請選擇工序名稱",
    )

    # 設備欄位
    equipment = forms.ModelChoiceField(
        queryset=None,
        label="使用的設備",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "placeholder": "請選擇使用的設備",
            }
        ),
        required=False,
        help_text="請選擇使用的設備（可選）",
    )

    # 日期欄位
    work_date = forms.DateField(
        label="報工日期",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "placeholder": "請選擇報工日期",
            }
        ),
        required=True,
        help_text="請選擇報工日期",
    )

    # 開始時間欄位（24小時制）
    start_time = TimeField(
        label="開始時間",
        help_text="請選擇或輸入實際開始時間 (24小時制)，例如 16:00",
    )

    # 結束時間欄位（24小時制）
    end_time = TimeField(
        label="結束時間",
        help_text="請選擇或輸入實際結束時間 (24小時制)，例如 18:30",
    )

    # 工作數量欄位
    work_quantity = forms.IntegerField(
        label="工作數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "placeholder": "請輸入本次實際完成的數量",
            }
        ),
        required=True,
        help_text="請輸入該時段內實際完成的合格產品數量",
    )

    # 不良品數量欄位
    defect_quantity = forms.IntegerField(
        label="不良品數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "placeholder": "請輸入本次產生的不良品數量",
            }
        ),
        required=False,
        initial=0,
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
    )

    # 備註欄位
    remarks = forms.CharField(
        label="備註",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "placeholder": "可填寫設備標記、操作說明等",
            }
        ),
        required=False,
        help_text="請輸入任何需要補充的資訊，如設備標記、操作說明等",
    )

    # 異常記錄欄位
    abnormal_notes = forms.CharField(
        label="異常記錄",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "placeholder": "記錄生產過程中的異常情況，如設備故障、品質問題等",
            }
        ),
        required=False,
        help_text="記錄生產過程中的異常情況，如設備故障、品質問題等",
    )

    # 是否完工欄位
    is_completed = forms.BooleanField(
        label="是否已完工？",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        required=False,
        help_text="若此工單在此工序上已全部完成，請勾選",
    )

    class Meta:
        abstract = True

    def clean_start_time(self):
        """驗證開始時間格式"""
        start_time = self.cleaned_data.get("start_time")
        if start_time:
            # 驗證時間格式 (HH:MM)
            import re

            if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", start_time):
                raise forms.ValidationError(
                    "開始時間格式不正確，請使用 24 小時制格式，例如：16:00"
                )
        return start_time

    def clean_end_time(self):
        """驗證結束時間格式"""
        end_time = self.cleaned_data.get("end_time")
        if end_time:
            # 驗證時間格式 (HH:MM)
            import re

            if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", end_time):
                raise forms.ValidationError(
                    "結束時間格式不正確，請使用 24 小時制格式，例如：18:30"
                )
        return end_time

    def clean(self):
        """整體驗證"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time:
            # 驗證結束時間是否晚於開始時間
            try:
                start_dt = datetime.strptime(start_time, "%H:%M").time()
                end_dt = datetime.strptime(end_time, "%H:%M").time()
                if end_dt <= start_dt:
                    raise forms.ValidationError("結束時間必須晚於開始時間")
            except ValueError:
                pass

        return cleaned_data


# 工單管理表單，支援新增與編輯
class WorkOrderForm(forms.ModelForm):
    # 公司代號欄位（手動輸入或下拉）
    company_code = forms.CharField(
        max_length=10,
        label="公司代號",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    # 工單編號（自動生成或手動輸入）
    order_number = forms.CharField(
        max_length=50,
        label="工單編號",
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}),
        required=True,
        help_text="工單號碼將自動生成，格式：WO-{公司代號}-{年月}{序號}",
    )
    # 產品編號（下拉選單）
    product_code = forms.ChoiceField(
        choices=[],
        label="產品編號",
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
    )
    # 數量（手動輸入）
    quantity = forms.IntegerField(
        label="數量",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=True,
        min_value=1,
    )
    # 狀態（下拉選單）
    status = forms.ChoiceField(
        label="狀態",
        choices=[
            ("pending", "待生產"),
            ("in_progress", "生產中"),
            ("completed", "已完工"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
    )

    class Meta:
        model = WorkOrder
        fields = ["company_code", "order_number", "product_code", "quantity", "status"]
        labels = {
            "company_code": "公司代號",
            "order_number": "工單編號",
            "product_code": "產品編號",
            "quantity": "數量",
            "status": "狀態",
        }
        widgets = {
            "company_code": forms.TextInput(attrs={"class": "form-control"}),
            "order_number": forms.TextInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 動態載入產品編號選項
        self.fields["product_code"].choices = self.get_product_choices()

    def get_product_choices(self):
        """取得產品編號選項，從公司製令單中取得"""
        choices = [("", "請選擇產品編號")]
        try:
            # 取得所有公司製令單的產品編號（包括已轉換和未轉換的）
            from .models import CompanyOrder

            company_orders = (
                CompanyOrder.objects.all()
                .values_list("product_id", "product_id")
                .distinct()
                .order_by("product_id")
            )

            for product_id, _ in company_orders:
                choices.append((product_id, product_id))
        except Exception as e:
            # 如果發生錯誤，至少提供空選項
            pass

        return choices


# ==================== SMT 補登報工表單 ====================


class SMTSupplementReportForm(ProductionReportBaseForm):
    """
    【規範】SMT補登報工表單
    - 繼承共用表單，工序和設備限制為SMT相關
    """

    # 工單預設生產數量（唯讀）
    planned_quantity = forms.IntegerField(
        label="工單預設生產數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "planned_quantity_input",
                "readonly": "readonly",
                "placeholder": "此為工單規劃的總生產數量，不可修改",
            }
        ),
        required=False,
        help_text="此為工單規劃的總生產數量，不可修改",
    )

    class Meta:
        model = SMTProductionReport
        fields = [
            "workorder",
            "product_id",
            "planned_quantity",
            "operation",
            "equipment",
            "work_date",
            "start_time",
            "end_time",
            "work_quantity",
            "defect_quantity",
            "is_completed",
            "remarks",
            "abnormal_notes",
        ]
        labels = {
            "workorder": "工單號碼",
            "product_id": "產品編號",
            "planned_quantity": "工單預設生產數量",
            "operation": "工序",
            "equipment": "使用的設備",
            "work_date": "報工日期",
            "start_time": "開始時間",
            "end_time": "結束時間",
            "work_quantity": "工作數量",
            "defect_quantity": "不良品數量",
            "is_completed": "是否已完工",
            "remarks": "備註",
            "abnormal_notes": "異常記錄",
        }
        help_texts = {
            "workorder": "請選擇工單號碼",
            "product_id": "請輸入產品編號",
            "planned_quantity": "此為工單規劃的總生產數量，不可修改",
            "rd_product_code": "請輸入RD樣品的產品編號，用於識別具體的RD樣品工序與設備資訊",
            "operation": "請選擇SMT相關工序",
            "equipment": "請選擇SMT相關設備",
            "work_date": "請選擇報工日期",
            "start_time": "請輸入實際開始時間 (24小時制)，例如 16:00",
            "end_time": "請輸入實際結束時間 (24小時制)，例如 18:30",
            "work_quantity": "請輸入該時段內實際完成的合格產品數量",
            "defect_quantity": "請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
            "is_completed": "若此工單在此工序上已全部完成，請勾選",
            "remarks": "請輸入任何需要補充的資訊，如設備標記、操作說明等",
            "abnormal_notes": "記錄生產過程中的異常情況，如設備故障、品質問題等",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 設定設備查詢集 - 根據設備名稱過濾SMT設備
        from equip.models import Equipment
        from workorder.services.smt_operator_service import SMTOperatorService

        smt_equipment = Equipment.objects.filter(
            name__icontains="SMT"
        ).order_by("name")
        
        # 設定 equipment 的 queryset，而不是 choices
        self.fields["equipment"].queryset = smt_equipment

        # 設定工單查詢集（直接從工單表取得）
        from .models import WorkOrder

        workorders = (
            WorkOrder.objects.exclude(order_number__icontains="RD樣品")
            .exclude(order_number__icontains="RD-樣品")
            .exclude(order_number__icontains="RD樣本")
            .exclude(status="completed")
            .order_by("-created_at")
        )
        self.fields["workorder"].queryset = workorders

        # 載入產品編號選項
        product_choices = self.get_product_choices()
        self.fields["product_id"].choices = product_choices

        # 設定預設日期為今天（只在新增時）
        if not self.instance.pk:
            from datetime import date

            self.fields["work_date"].initial = date.today()

        # 移除基礎表單中的 process 欄位，因為 SMT 表單使用 operation 欄位
        if "process" in self.fields:
            del self.fields["process"]

        # 為 SMT 表單添加工序欄位（使用 CharField 但提供選項）
        from process.models import ProcessName

        processes = ProcessName.objects.filter(name__icontains="SMT").order_by("name")
        process_choices = [("", "請選擇此次補登的SMT工序")] + [
            (p.name, p.name) for p in processes
        ]
        self.fields["operation"] = forms.ChoiceField(
            choices=process_choices,
            label="工序",
            widget=forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "operation_select",
                    "placeholder": "請選擇此次補登的SMT工序",
                }
            ),
            required=True,
            help_text="請選擇此次補登的SMT工序",
        )

    def get_product_choices(self):
        """獲取產品編號選項（直接從工單表取得）"""
        from .models import WorkOrder

        # 直接從工單表中獲取所有產品編號
        products = (
            WorkOrder.objects.exclude(order_number__icontains="RD樣品")
            .exclude(order_number__icontains="RD-樣品")
            .exclude(order_number__icontains="RD樣本")
            .exclude(status="completed")
            .values_list("product_code", flat=True)
            .distinct()
            .order_by("product_code")
        )

        choices = [("", "請選擇產品編號")]  # 預設選項
        for product in products:
            if product:  # 確保產品編號不為空
                choices.append((product, product))
        return choices


class SMTSupplementBatchForm(forms.Form):
    """
    SMT補登報工批量創建表單
    用於批量創建SMT補登報工記錄
    """

    equipment = forms.ModelChoiceField(
        queryset=None,
        label="設備",
        widget=forms.Select(
            attrs={"class": "form-control", "id": "batch_equipment_select"}
        ),
        required=True,
        help_text="請選擇SMT設備",
    )

    workorder = forms.ModelChoiceField(
        queryset=None,
        label="工單",
        widget=forms.Select(
            attrs={"class": "form-control", "id": "batch_workorder_select"}
        ),
        required=True,
        help_text="請選擇要補登的工單",
    )

    start_date = forms.DateField(
        label="開始日期",
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "id": "start_date_input"}
        ),
        required=True,
        help_text="請選擇批量補登的開始日期",
    )

    end_date = forms.DateField(
        label="結束日期",
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "id": "end_date_input"}
        ),
        required=True,
        help_text="請選擇批量補登的結束日期",
    )

    daily_quantity = forms.IntegerField(
        label="每日數量",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "0", "id": "daily_quantity_input"}
        ),
        required=True,
        help_text="請輸入每日的報工數量",
    )

    notes = forms.CharField(
        label="備註說明",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "id": "batch_notes_input",
                "placeholder": "請輸入批量補登的說明...",
            }
        ),
        required=False,
        help_text="請輸入批量補登的說明",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 設置設備選項
        from equip.models import Equipment
        from django.db import models

        smt_equipment = Equipment.objects.filter(
            models.Q(name__icontains="SMT")
            | models.Q(name__icontains="貼片")
            | models.Q(name__icontains="Pick")
            | models.Q(name__icontains="Place")
        ).order_by("name")
        self.fields["equipment"].queryset = smt_equipment

        # 設置工單選項
        from .models import WorkOrder

        workorders = (
            WorkOrder.objects.filter(status__in=["pending", "in_progress", "paused"])
            .exclude(status="completed")  # 排除已完工的工單
            .order_by("-created_at")[:100]
        )
        self.fields["workorder"].queryset = workorders

        # 設置預設日期為今天
        from datetime import date

        today = date.today()
        self.fields["start_date"].initial = today
        self.fields["end_date"].initial = today

    def clean(self):
        cleaned_data = super().clean()

        # 驗證結束日期不能早於開始日期
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError({"end_date": "結束日期不能早於開始日期"})

        # 驗證日期範圍不能超過30天
        if start_date and end_date:
            from datetime import timedelta

            date_range = (end_date - start_date).days
            if date_range > 30:
                raise forms.ValidationError(
                    {"end_date": "批量補登的日期範圍不能超過30天"}
                )

        # 驗證每日數量不能為負數
        daily_quantity = cleaned_data.get("daily_quantity")
        if daily_quantity and daily_quantity < 0:
            raise forms.ValidationError({"daily_quantity": "每日數量不能為負數"})

        return cleaned_data


# ==================== 作業員補登報工表單 ====================


class OperatorSupplementReportForm(ProductionReportBaseForm):
    """
    【規範】作業員補登報工表單
    - 繼承共用表單，專門用於作業員補登報工
    - 工序和設備排除SMT相關
    """

    # 作業員選擇（繼承自父類別，但需要自定義查詢集）
    operator = forms.ModelChoiceField(
        queryset=None,
        label="作業員",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "operator_select",
                "placeholder": "請選擇進行補登報工的作業員",
            }
        ),
        required=True,
        help_text="請選擇進行補登報工的作業員",
    )

    class Meta:
        model = OperatorSupplementReport
        fields = [
            "operator",
            "workorder",
            "product_id",
            "process",
            "equipment",
            "work_date",
            "start_time",
            "end_time",
            "work_quantity",
            "defect_quantity",
            "is_completed",
            "completion_method",
            "remarks",
            "abnormal_notes",
            "approval_status",
        ]
        labels = {
            "operator": "作業員",
            "workorder": "工單號碼",
            "product_id": "產品編號",
            "process": "工序",
            "equipment": "使用的設備",
            "work_date": "報工日期",
            "start_time": "開始時間",
            "end_time": "結束時間",
            "work_quantity": "工作數量",
            "defect_quantity": "不良品數量",
            "is_completed": "是否已完工",
            "completion_method": "完工判斷方式",
            "remarks": "備註",
            "abnormal_notes": "異常記錄",
            "approval_status": "核准狀態",
        }
        help_texts = {
            "operator": "請選擇進行補登報工的作業員",
            "workorder": "請選擇工單號碼，或透過產品編號自動帶出",
            "product_id": "請選擇產品編號，將自動帶出相關工單號碼",
            "process": "請選擇此次補登的工序（排除SMT相關工序）",
            "equipment": "請選擇此次補登使用的設備（排除SMT相關設備）",
            "work_date": "請選擇報工日期",
            "start_time": "請輸入實際開始時間 (24小時制)，例如 16:00",
            "end_time": "請輸入實際結束時間 (24小時制)，例如 18:30",
            "work_quantity": "請輸入該時段內實際完成的合格產品數量",
            "defect_quantity": "請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
            "is_completed": "若此工單在此工序上已全部完成，請勾選",
            "completion_method": "請選擇完工判斷方式",
            "remarks": "請輸入備註說明（可選）",
            "abnormal_notes": "記錄生產過程中的異常情況，如設備故障、品質問題等",
            "approval_status": "請選擇核准狀態",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 載入作業員選項（排除SMT相關作業員）
        from process.models import Operator

        operators = (
            Operator.objects.all().exclude(name__icontains="SMT").order_by("name")
        )
        self.fields["operator"].queryset = operators

        # 載入工序選項（排除SMT相關工序）
        from process.models import ProcessName

        processes = (
            ProcessName.objects.all().exclude(name__icontains="SMT").order_by("name")
        )
        self.fields["process"].queryset = processes

        # 載入設備選項（排除SMT相關設備）
        from equip.models import Equipment

        equipments = (
            Equipment.objects.all().exclude(name__icontains="SMT").order_by("name")
        )
        self.fields["equipment"].queryset = equipments

        # 設定工單查詢集（直接從工單表取得，排除RD樣品相關工單）
        from .models import WorkOrder

        workorders = (
            WorkOrder.objects.exclude(status="completed")
            .exclude(order_number__icontains="RD樣品")
            .exclude(order_number__icontains="RD-樣品")
            .exclude(order_number__icontains="RD樣本")
            .order_by("-created_at")
        )
        self.fields["workorder"].queryset = workorders

        # 載入產品編號選項
        product_choices = self.get_product_choices()
        self.fields["product_id"].choices = product_choices

        # 設定預設日期為今天（只在新增時）
        if not self.instance.pk:
            from datetime import date

            self.fields["work_date"].initial = date.today()

    def get_product_choices(self):
        """獲取產品編號選項（直接從工單表取得，排除RD樣品相關產品）"""
        from .models import WorkOrder

        # 直接從工單表中獲取所有產品編號，排除RD樣品相關工單
        products = (
            WorkOrder.objects.exclude(status="completed")
            .exclude(order_number__icontains="RD樣品")
            .exclude(order_number__icontains="RD-樣品")
            .exclude(order_number__icontains="RD樣本")
            .values_list("product_code", flat=True)
            .distinct()
            .order_by("product_code")
        )

        choices = [("", "請選擇產品編號")]  # 預設選項
        for product in products:
            if product:  # 確保產品編號不為空
                choices.append((product, product))
        return choices

    # 工單預設生產數量（唯讀）
    planned_quantity = forms.IntegerField(
        label="工單預設生產數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "planned_quantity_input",
                "readonly": "readonly",
                "placeholder": "此為工單規劃的總生產數量，不可修改",
            }
        ),
        required=False,
        help_text="此為工單規劃的總生產數量，不可修改",
    )

    # 核准狀態
    APPROVAL_STATUS_CHOICES = [
        ("pending", "待核准"),
        ("approved", "已核准"),
        ("rejected", "已駁回"),
    ]

    approval_status = forms.ChoiceField(
        choices=APPROVAL_STATUS_CHOICES,
        label="核准狀態",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "approval_status_select",
                "placeholder": "請選擇核准狀態",
            }
        ),
        required=True,
        initial="pending",
        help_text="請選擇核准狀態",
    )

    # 休息時間相關欄位已完全移除，系統自動計算

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # 確保所有 ModelChoiceField 都有有效的 queryset
        from .models import WorkOrder
        from equip.models import Equipment
        from django.contrib.auth.models import User
        from process.models import Operator, ProcessName

        try:
            # 設置產品編號選項（從工單中取得所有產品編號）
            self.fields["product_id"].choices = self.get_product_choices()

            # 設置工單號碼選項（比照SMT報工，顯示所有未完工的工單）
            self.fields["workorder"].queryset = self.get_workorder_queryset()

            # 設置作業員選項
            operators = Operator.objects.all().order_by("name")
            self.fields["operator"].queryset = operators

            # 設置工序選項（排除SMT相關工序）
            from django.db import models

            non_smt_processes = ProcessName.objects.exclude(
                models.Q(name__icontains="SMT")
                | models.Q(name__icontains="貼片")
                | models.Q(name__icontains="Pick")
                | models.Q(name__icontains="Place")
            ).order_by("name")

            self.fields["process"].queryset = non_smt_processes

            # 設置設備選項（排除SMT相關設備）
            non_smt_equipment = Equipment.objects.exclude(
                models.Q(name__icontains="SMT")
                | models.Q(name__icontains="貼片")
                | models.Q(name__icontains="Pick")
                | models.Q(name__icontains="Place")
            ).order_by("name")

            self.fields["equipment"].queryset = non_smt_equipment

        except Exception as e:
            print(f"作業員補登報工表單初始化失敗: {e}")
            # 如果任何查詢失敗，設置空的查詢集
            self.fields["workorder"].queryset = WorkOrder.objects.none()
            self.fields["operator"].queryset = Operator.objects.none()
            # 重新導入 ProcessName 以避免 UnboundLocalError
            from process.models import ProcessName

            self.fields["process"].queryset = ProcessName.objects.none()
            self.fields["equipment"].queryset = Equipment.objects.none()

        # 如果是編輯現有記錄，設定初始值
        if self.instance and self.instance.pk:
            # 編輯模式：設定初始值
            if self.instance.workorder:
                self.fields["product_id"].initial = self.instance.workorder.product_code
                self.fields["workorder"].initial = self.instance.workorder
                self.fields["planned_quantity"].initial = (
                    self.instance.workorder.quantity
                )

                # 設定時間欄位的初始值
                if self.instance.start_time:
                    self.fields["start_time"].initial = (
                        self.instance.start_time.strftime("%H:%M")
                    )
                if self.instance.end_time:
                    self.fields["end_time"].initial = self.instance.end_time.strftime(
                        "%H:%M"
                    )

        # 如果是編輯現有記錄，檢查核准狀態
        if self.instance and self.instance.pk:
            # 只有當記錄已核准且非超級管理員時，才禁用欄位
            if self.instance.approval_status == "approved" and not (
                self.user and self.user.is_superuser
            ):
                # 已核准且非超級管理員，禁用所有欄位
                for field_name in self.fields:
                    self.fields[field_name].widget.attrs["readonly"] = "readonly"
                    self.fields[field_name].widget.attrs["disabled"] = "disabled"

        # 為產品編號欄位添加變更事件處理
        self.fields["product_id"].widget.attrs.update(
            {
                "onchange": "updateWorkorderOptions(this.value);",
                "data-url": "/workorder/api/get-workorders-by-product/",
            }
        )

    def get_product_choices(self):
        """取得產品編號選項列表（從工單取得）"""
        choices = [("", "請選擇產品編號")]
        try:
            from .models import WorkOrder

            # 從工單中取得所有產品編號
            product_codes = (
                WorkOrder.objects.filter(
                    status__in=["pending", "in_progress"]  # 只選擇待處理或進行中的工單
                )
                .values_list("product_code", flat=True)
                .distinct()
                .order_by("product_code")
            )

            for product_code in product_codes:
                if product_code:  # 確保產品編號不為空
                    choices.append((product_code, product_code))

        except Exception as e:
            print(f"取得產品編號選項失敗: {e}")
        return choices

    def get_workorder_choices(self):
        """取得工單選項列表（比照SMT報工）"""
        choices = [("", "請選擇工單號碼")]
        try:
            workorders = self.get_workorder_queryset()
            for workorder in workorders:
                # 格式化公司代號，確保是兩位數格式（例如：2 -> 02）
                formatted_company_code = workorder.company_code
                if formatted_company_code and formatted_company_code.isdigit():
                    formatted_company_code = formatted_company_code.zfill(2)

                choices.append(
                    (
                        workorder.id,
                        f"{formatted_company_code} - {workorder.order_number}",
                    )
                )
        except Exception as e:
            print(f"取得工單選項失敗: {e}")
        return choices

    def get_workorder_queryset(self, product_code=None):
        """取得工單查詢集（從工單表取得）"""
        from .models import WorkOrder

        try:
            # 直接從工單表取得資料
            queryset = (
                WorkOrder.objects.filter(
                    status__in=["pending", "in_progress"]  # 只選擇待處理或進行中的工單
                )
                .exclude(order_number__icontains="RD樣品")
                .exclude(order_number__icontains="RD-樣品")
                .exclude(order_number__icontains="RD樣本")
                .exclude(status="completed")
            )

            if product_code:
                queryset = queryset.filter(product_code=product_code)

            return queryset
        except Exception as e:
            print(f"從工單取得工單查詢集失敗: {e}")
            return WorkOrder.objects.none()

    def get_operation_choices(self):
        """取得工序選項"""
        from process.models import ProcessName
        from django.db import models

        # 只顯示SMT相關工序
        smt_processes = ProcessName.objects.filter(
            models.Q(name__icontains="SMT")
            | models.Q(name__icontains="貼片")
            | models.Q(name__icontains="Pick")
            | models.Q(name__icontains="Place")
        ).order_by("name")

        choices = [("", "請選擇工序")]
        for process in smt_processes:
            choices.append((process.name, process.name))

        return choices

    class Meta:
        model = OperatorSupplementReport
        fields = [
            "operator",
            "process",
            "equipment",
            "work_date",
            "start_time",
            "end_time",
            "work_quantity",
            "defect_quantity",
            "is_completed",
            "completion_method",
            "remarks",
            "abnormal_notes",
            "approval_status",
            # 休息時間相關欄位已移除，系統自動計算
        ]

        labels = {
            "operator": "作業員",
            "process": "工序",
            "equipment": "使用的設備",
            "work_date": "日期",
            "start_time": "開始時間",
            "end_time": "結束時間",
            "work_quantity": "工作數量",
            "defect_quantity": "不良品數量",
            "is_completed": "是否已完工",
            "completion_method": "完工判斷方式",
            "remarks": "備註",
            "abnormal_notes": "異常記錄",
            "approval_status": "核准狀態",
        }

        help_texts = {
            "operator": "請選擇進行補登報工的作業員",
            "process": "請選擇此次補登的工序（排除SMT相關工序）",
            "equipment": "請選擇此次補登使用的設備（排除SMT相關設備）",
            "work_date": "請選擇實際報工日期",
            "start_time": "請輸入實際開始時間 (24小時制)，例如 16:00",
            "end_time": "請輸入實際結束時間 (24小時制)，例如 18:30",
            "work_quantity": "請輸入該時段內實際完成的合格產品數量（可為0）",
            "defect_quantity": "請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
            "is_completed": "若此工單在此工序上已全部完成，請勾選",
            "completion_method": "請選擇完工判斷方式",
            "remarks": "請輸入備註說明（可選）",
            "abnormal_notes": "記錄生產過程中的異常情況，如設備故障、品質問題等",
            "approval_status": "請選擇核准狀態",
        }

    def save(self, commit=True):
        """
        儲存表單，處理時間欄位的轉換和工單關聯
        """
        from datetime import datetime

        # 先取得實例但不儲存
        instance = super().save(commit=False)

        # 處理時間欄位轉換
        if self.cleaned_data.get("start_time"):
            try:
                # 將字串時間轉換為 TimeField
                start_time_str = self.cleaned_data["start_time"]
                if ":" in start_time_str:
                    hour, minute = map(int, start_time_str.split(":"))
                    from datetime import time

                    instance.start_time = time(hour, minute)
            except (ValueError, TypeError) as e:
                print(f"開始時間轉換失敗: {e}")

        if self.cleaned_data.get("end_time"):
            try:
                # 將字串時間轉換為 TimeField
                end_time_str = self.cleaned_data["end_time"]
                if ":" in end_time_str:
                    hour, minute = map(int, end_time_str.split(":"))
                    from datetime import time

                    instance.end_time = time(hour, minute)
            except (ValueError, TypeError) as e:
                print(f"結束時間轉換失敗: {e}")

        # 處理工單關聯
        if self.cleaned_data.get("workorder"):
            instance.workorder = self.cleaned_data["workorder"]
            # 如果有工單，設定相關欄位
            if instance.workorder:
                instance.rd_workorder_number = instance.workorder.order_number
                instance.product_id = instance.workorder.product_code

        # 處理產品編號（如果沒有工單但有產品編號）
        if not instance.workorder and self.cleaned_data.get("product_id"):
            instance.product_id = self.cleaned_data["product_id"]

        # 設定建立者
        if hasattr(self, "request") and self.request.user.is_authenticated:
            instance.created_by = self.request.user.username

        # 設定核准狀態為待核准
        instance.approval_status = "pending"

        if commit:
            instance.save()

        return instance


class OperatorSupplementBatchForm(forms.Form):
    """
    作業員補登報工批量創建表單
    用於批量創建作業員補登報工記錄
    """

    operator = forms.ModelChoiceField(
        queryset=None,
        label="作業員",
        widget=forms.Select(
            attrs={"class": "form-control", "id": "batch_operator_select"}
        ),
        required=True,
        help_text="請選擇作業員",
    )

    workorder = forms.ModelChoiceField(
        queryset=None,
        label="工單",
        widget=forms.Select(
            attrs={"class": "form-control", "id": "batch_workorder_select"}
        ),
        required=True,
        help_text="請選擇要補登的工單",
    )

    process = forms.ModelChoiceField(
        queryset=None,
        label="工序",
        widget=forms.Select(
            attrs={"class": "form-control", "id": "batch_process_select"}
        ),
        required=True,
        help_text="請選擇工序（排除SMT相關工序）",
    )

    start_date = forms.DateField(
        label="開始日期",
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "id": "start_date_input"}
        ),
        required=True,
        help_text="請選擇批量補登的開始日期",
    )

    end_date = forms.DateField(
        label="結束日期",
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "id": "end_date_input"}
        ),
        required=True,
        help_text="請選擇批量補登的結束日期",
    )

    daily_quantity = forms.IntegerField(
        label="每日數量",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "1", "id": "daily_quantity_input"}
        ),
        required=True,
        help_text="請輸入每日的報工數量",
    )

    start_time = TimeField(
        label="開始時間",
        help_text="請選擇或輸入每日的開始時間 (24小時制)",
    )

    end_time = TimeField(
        label="結束時間",
        help_text="請選擇或輸入每日的結束時間 (24小時制)",
    )

    notes = forms.CharField(
        label="備註說明",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "id": "batch_notes_input",
                "placeholder": "請輸入批量補登的說明...",
            }
        ),
        required=False,
        help_text="請輸入批量補登的說明",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 設置作業員選項
        from process.models import Operator

        operators = Operator.objects.all().order_by("name")
        self.fields["operator"].queryset = operators

        # 設置工單選項
        from .models import WorkOrder

        workorders = (
            WorkOrder.objects.filter(status__in=["pending", "in_progress", "paused"])
            .exclude(status="completed")  # 排除已完工的工單
            .order_by("-created_at")[:100]
        )
        self.fields["workorder"].queryset = workorders

        # 設置工序選項（排除SMT相關工序）
        from process.models import ProcessName

        processes = ProcessName.objects.filter(
            ~Q(name__icontains="SMT")  # 排除SMT相關工序
        ).order_by("name")
        self.fields["process"].queryset = processes

        # 設置預設日期為今天
        from datetime import date

        today = date.today()
        self.fields["start_date"].initial = today
        self.fields["end_date"].initial = today

        # 設置預設時間
        self.fields["start_time"].initial = "08:30"
        self.fields["end_time"].initial = "17:30"

    def clean(self):
        cleaned_data = super().clean()

        # 驗證結束日期不能早於開始日期
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError({"end_date": "結束日期不能早於開始日期"})

        # 驗證日期範圍不能超過30天
        if start_date and end_date:
            from datetime import timedelta

            date_range = (end_date - start_date).days
            if date_range > 30:
                raise forms.ValidationError(
                    {"end_date": "批量補登的日期範圍不能超過30天"}
                )

        # 驗證每日數量不能為負數
        daily_quantity = cleaned_data.get("daily_quantity")
        if daily_quantity and daily_quantity < 0:
            raise forms.ValidationError({"daily_quantity": "每日數量不能為負數"})

        # 驗證時間格式
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time:
            try:
                from datetime import datetime

                start_dt = datetime.strptime(start_time, "%H:%M").time()
                end_dt = datetime.strptime(end_time, "%H:%M").time()

                if end_dt <= start_dt:
                    raise forms.ValidationError(
                        {"end_time": "結束時間必須晚於開始時間"}
                    )

            except ValueError:
                raise forms.ValidationError(
                    {"start_time": "時間格式錯誤，請使用 HH:MM 格式"}
                )

        return cleaned_data


class RDSampleSupplementReportForm(ProductionReportBaseForm):
    """
    【規範】RD樣品補登報工表單
    - 繼承共用表單，專門用於RD樣品的報工記錄
    - 工序和設備排除SMT相關
    """

    # 作業員選擇
    operator = forms.ModelChoiceField(
        queryset=None,
        label="作業員",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "operator_select",
                "placeholder": "請選擇進行作業員RD樣品補登報工的作業員",
            }
        ),
        required=True,
        help_text="請選擇進行作業員RD樣品補登報工的作業員",
    )

    # 完工判斷方式
    completion_method = forms.ChoiceField(
        choices=[
            ("manual", "手動勾選"),
            ("auto_quantity", "自動依數量判斷"),
            ("auto_time", "自動依工時判斷"),
            ("auto_operator", "作業員確認"),
            ("auto_system", "系統自動判斷"),
        ],
        label="完工判斷方式",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "completion_method_select",
            }
        ),
        required=False,
        initial="manual",
        help_text="請選擇完工判斷方式",
    )

    # 核准狀態
    approval_status = forms.ChoiceField(
        choices=[
            ("pending", "待核准"),
            ("approved", "已核准"),
            ("rejected", "已駁回"),
        ],
        label="審核狀態",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "approval_status_select",
            }
        ),
        required=False,
        initial="pending",
        help_text="請選擇審核狀態",
    )

    class Meta:
        model = OperatorSupplementReport
        fields = [
            "operator",
            "workorder",
            "product_id",
            "process",
            "equipment",
            "work_date",
            "start_time",
            "end_time",
            "work_quantity",
            "defect_quantity",
            "is_completed",
            "completion_method",
            "remarks",
            "abnormal_notes",
            "approval_status",
        ]
        labels = {
            "operator": "作業員",
            "workorder": "工單號碼",
            "product_id": "產品編號",
            "process": "工序",
            "equipment": "使用的設備",
            "work_date": "報工日期",
            "start_time": "開始時間",
            "end_time": "結束時間",
            "work_quantity": "完成數量",
            "defect_quantity": "不良品數量",
            "is_completed": "是否已完工",
            "completion_method": "完工判斷方式",
            "remarks": "備註",
            "abnormal_notes": "異常記錄",
            "approval_status": "審核狀態",
        }
        help_texts = {
            "operator": "請選擇進行作業員RD樣品補登報工的作業員",
            "workorder": "請選擇工單號碼（RD樣品固定為RD樣品）",
            "product_id": "請輸入RD樣品的產品編號",
            "process": "請選擇此次RD樣品報工的工序（排除SMT相關工序）",
            "equipment": "請選擇此次RD樣品報工使用的設備（排除SMT相關設備）",
            "work_date": "請選擇實際RD樣品報工日期",
            "start_time": "請輸入實際開始時間 (24小時制)，例如 16:00",
            "end_time": "請輸入實際結束時間 (24小時制)，例如 18:30",
            "work_quantity": "請輸入該時段內實際完成的樣品數量",
            "defect_quantity": "請輸入本次製作中產生的不良品數量，若無則留空或填寫0",
            "is_completed": "若此RD樣品製作已全部完成，請勾選",
            "completion_method": "請選擇完工判斷方式",
            "remarks": "請輸入備註說明（可選）",
            "abnormal_notes": "記錄生產過程中的異常情況，如設備故障、品質問題等",
            "approval_status": "請選擇審核狀態",
        }

    # 時間資訊
    work_date = forms.DateField(
        label="日期",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "id": "work_date_input",
            }
        ),
        required=True,
        help_text="請選擇實際RD樣品報工日期",
    )

    start_time = TimeField(
        label="開始時間",
        help_text="請選擇或輸入實際開始時間 (24小時制)，例如 16:00",
    )

    end_time = TimeField(
        label="結束時間",
        help_text="請選擇或輸入實際結束時間 (24小時制)，例如 18:30",
    )

    # 數量資訊
    work_quantity = forms.IntegerField(
        label="完成數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "work_quantity_input",
                "min": "0",
                "placeholder": "請輸入該時段內實際完成的樣品數量",
            }
        ),
        required=True,
        help_text="請輸入該時段內實際完成的樣品數量",
    )

    defect_quantity = forms.IntegerField(
        label="不良品數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "defect_quantity_input",
                "min": "0",
                "placeholder": "請輸入本次製作中產生的不良品數量",
            }
        ),
        required=False,
        initial=0,
        help_text="請輸入本次製作中產生的不良品數量，若無則留空或填寫0",
    )

    # 狀態資訊
    is_completed = forms.BooleanField(
        label="是否已完工",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "is_completed_input",
            }
        ),
        required=False,
        help_text="若此RD樣品製作已全部完成，請勾選",
    )

    # 完工判斷方式
    completion_method = forms.ChoiceField(
        choices=[
            ("manual", "手動勾選"),
            ("auto_quantity", "自動依數量判斷"),
            ("auto_time", "自動依工時判斷"),
            ("auto_operator", "作業員確認"),
            ("auto_system", "系統自動判斷"),
        ],
        label="完工判斷方式",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "completion_method_select",
            }
        ),
        required=False,
        initial="manual",
        help_text="請選擇完工判斷方式",
    )

    # 備註資訊
    remarks = forms.CharField(
        label="備註",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "id": "remarks_input",
                "rows": "3",
                "placeholder": "請輸入備註說明（可選）",
            }
        ),
        required=False,
        help_text="請輸入備註說明（可選）",
    )

    # 核准狀態
    approval_status = forms.ChoiceField(
        choices=[
            ("draft", "草稿"),
            ("pending", "待審核"),
            ("approved", "已審核"),
            ("rejected", "已駁回"),
        ],
        label="審核狀態",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "approval_status_select",
            }
        ),
        required=False,
        initial="draft",
        help_text="請選擇審核狀態",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 載入作業員選項（排除SMT相關作業員）
        from process.models import Operator

        operators = (
            Operator.objects.all().exclude(name__icontains="SMT").order_by("name")
        )
        self.fields["operator"].queryset = operators

        # 載入工序選項（排除SMT相關工序）
        from process.models import ProcessName

        processes = (
            ProcessName.objects.all().exclude(name__icontains="SMT").order_by("name")
        )
        self.fields["process"].queryset = processes

        # 載入設備選項（排除SMT相關設備）
        from equip.models import Equipment

        equipments = (
            Equipment.objects.all().exclude(name__icontains="SMT").order_by("name")
        )
        self.fields["equipment"].queryset = equipments

        # 設定預設日期為今天（只在新增時）
        if not self.instance.pk:
            from datetime import date

            self.fields["work_date"].initial = date.today()

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()

        # RD樣品模式下，設定預設值
        cleaned_data["workorder"] = None
        cleaned_data["original_workorder_number"] = (
            "RD樣品"  # 修正：將RD樣品寫入原始工單號碼欄位
        )
        cleaned_data["product_id"] = cleaned_data.get("product_id", "PFP-CCT")
        cleaned_data["operation"] = "SMT_RD樣品"  # 自動設定工序名稱

        return cleaned_data

    def save(self, commit=True):
        """儲存表單資料"""
        instance = super().save(commit=False)

        # 設定RD樣品報工相關欄位

        instance.workorder = None  # RD樣品沒有對應的工單
        instance.planned_quantity = 0  # RD樣品預設生產數量為0

        if commit:
            instance.save()

        return instance

    class Meta:
        model = OperatorSupplementReport
        fields = [
            "operator",
            "process",
            "equipment",
            "work_date",
            "start_time",
            "end_time",
            "work_quantity",
            "defect_quantity",
            "is_completed",
            "completion_method",
            "remarks",
            "approval_status",
        ]

        labels = {
            "operator": "作業員",
            "process": "工序",
            "equipment": "使用的設備",
            "work_date": "日期",
            "start_time": "開始時間",
            "end_time": "結束時間",
            "work_quantity": "完成數量",
            "defect_quantity": "不良品數量",
            "is_completed": "是否已完工",
            "completion_method": "完工判斷方式",
            "remarks": "備註",
            "approval_status": "審核狀態",
        }

        help_texts = {
            "operator": "請選擇進行RD樣品報工的作業員",
            "process": "請選擇此次RD樣品報工的工序（排除SMT相關工序）",
            "equipment": "請選擇此次RD樣品報工的設備（排除SMT相關設備）",
            "work_date": "請選擇實際RD樣品報工日期",
            "start_time": "請輸入實際開始時間 (24小時制)，例如 16:00",
            "end_time": "請輸入實際結束時間 (24小時制)，例如 18:30",
            "work_quantity": "請輸入該時段內實際完成的樣品數量",
            "defect_quantity": "請輸入本次製作中產生的不良品數量，若無則留空或填寫0",
            "is_completed": "若此RD樣品製作已全部完成，請勾選",
            "completion_method": "請選擇完工判斷方式",
            "remarks": "請輸入備註說明（可選）",
            "approval_status": "請選擇審核狀態",
        }


# ==================== SMT補登報工表單 ====================

# 已刪除違反設計規範的 SMTProductionReportForm
# 現在使用符合規範的 SMTSupplementReportForm，它繼承自 ProductionReportBaseForm


# ==================== 作業員現場報工表單 ====================


class OperatorOnSiteReportForm(forms.ModelForm):
    """
    作業員現場報工表單
    用於作業員現場報工記錄
    """

    # 作業員選擇
    operator = forms.ModelChoiceField(
        queryset=None,
        label="作業員",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "operator_select",
                "placeholder": "請選擇作業員",
            }
        ),
        required=True,
        help_text="請選擇作業員",
    )

    # 工單選擇
    workorder = forms.ModelChoiceField(
        queryset=None,
        label="工單號碼",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "workorder_select",
                "placeholder": "請選擇工單號碼",
            }
        ),
        required=True,
        help_text="請選擇工單號碼",
    )

    # 工序選擇
    process = forms.ModelChoiceField(
        queryset=None,
        label="工序",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "process_select",
                "placeholder": "請選擇工序",
            }
        ),
        required=True,
        help_text="請選擇工序",
    )

    # 設備選擇
    equipment = forms.ModelChoiceField(
        queryset=None,
        label="設備",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "equipment_select",
                "placeholder": "請選擇設備",
            }
        ),
        required=False,
        help_text="請選擇設備（可選）",
    )

    # 數量
    quantity = forms.IntegerField(
        label="完成數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "id": "quantity_input",
                "placeholder": "請輸入完成數量",
            }
        ),
        required=True,
        help_text="請輸入完成數量",
    )

    # 備註
    notes = forms.CharField(
        label="備註",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "id": "notes_input",
                "placeholder": "請輸入備註",
            }
        ),
        required=False,
        help_text="請輸入備註",
    )

    class Meta:
        model = OperatorSupplementReport
        fields = [
            "operator",
            "workorder",
            "process",
            "equipment",
            "quantity",
            "notes",
        ]
        labels = {
            "operator": "作業員",
            "workorder": "工單號碼",
            "process": "工序",
            "equipment": "使用的設備",
            "quantity": "完成數量",
            "notes": "備註",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 設定作業員查詢集
        from process.models import Operator

        self.fields["operator"].queryset = Operator.objects.all().order_by("name")

        # 設定工單查詢集
        self.fields["workorder"].queryset = WorkOrder.objects.filter(
            status__in=["pending", "in_progress"]
        ).order_by("-created_at")

        # 設定工序查詢集
        from process.models import ProcessName

        self.fields["process"].queryset = ProcessName.objects.exclude(
            name__icontains="SMT"
        ).order_by("name")

        # 設定設備查詢集 - 排除SMT相關設備
        from equip.models import Equipment

        self.fields["equipment"].queryset = Equipment.objects.exclude(
            name__icontains="SMT"
        ).order_by("name")


class AutoManagementConfigForm(forms.ModelForm):
    """
    自動管理功能設定表單
    """
    
    class Meta:
        model = AutoManagementConfig
        fields = ['function_type', 'is_enabled', 'interval_minutes']
        widgets = {
            'function_type': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': '請選擇功能類型'
                }
            ),
            'is_enabled': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'interval_minutes': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '請輸入執行間隔（分鐘）',
                    'min': '1',
                    'max': '1440',  # 最多24小時
                }
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定欄位標籤
        self.fields['function_type'].label = '功能類型'
        self.fields['is_enabled'].label = '是否啟用'
        self.fields['interval_minutes'].label = '執行間隔（分鐘）'
        
        # 設定說明文字
        self.fields['function_type'].help_text = '選擇要設定的自動化功能類型'
        self.fields['is_enabled'].help_text = '是否啟用此自動化功能'
        self.fields['interval_minutes'].help_text = '設定自動化功能的執行間隔，以分鐘為單位（1-1440分鐘）'
    
    def clean_interval_minutes(self):
        """驗證執行間隔"""
        interval_minutes = self.cleaned_data.get('interval_minutes')
        
        if interval_minutes is not None:
            if interval_minutes < 1:
                raise forms.ValidationError('執行間隔不能少於1分鐘')
            elif interval_minutes > 1440:
                raise forms.ValidationError('執行間隔不能超過1440分鐘（24小時）')
        
        return interval_minutes
