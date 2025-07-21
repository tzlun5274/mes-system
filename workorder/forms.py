from django import forms
from .models import WorkOrder, CompanyOrder, WorkOrderProcess, SMTProductionReport
from process.models import Operator
from equip.models import Equipment
from .models import WorkOrderAssignment


# 工單管理表單，支援新增與編輯
class WorkOrderForm(forms.ModelForm):
    # 公司代號欄位（手動輸入或下拉）
    company_code = forms.CharField(
        max_length=10,
        label="公司代號",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    # 工單編號（手動輸入）
    order_number = forms.CharField(
        max_length=50,
        label="工單編號",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    # 產品編號（手動輸入）
    product_code = forms.CharField(
        max_length=100,
        label="產品編號",
        widget=forms.TextInput(attrs={"class": "form-control"}),
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
            "product_code": forms.TextInput(attrs={"class": "form-control"}),
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
            # 取得所有未轉換的公司製令單
            from .models import CompanyOrder

            company_orders = (
                CompanyOrder.objects.filter(is_converted=False)
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


class SMTSupplementReportForm(forms.ModelForm):
    """
    SMT補登報工表單
    用於創建和編輯SMT補登報工記錄
    """

    # 產品編號下拉選單（從工單自動帶出選項）
    product_code = forms.ChoiceField(
        choices=[],
        label="產品編號",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "product_code_select",
                "placeholder": "請選擇產品編號",
            }
        ),
        required=False,
        help_text="請選擇產品編號，或從工單自動帶出",
    )

    # 工單號碼下拉選單
    workorder = forms.ModelChoiceField(
        queryset=None,
        label="工單號碼",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "workorder_select",
                "placeholder": "請選擇工單號碼，或透過產品編號自動帶出",
            }
        ),
        required=True,
        help_text="請選擇工單號碼，或透過產品編號自動帶出",
    )

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

    # 工序下拉選單
    operation = forms.ChoiceField(
        choices=[],
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

    # 設備下拉選單
    equipment = forms.ModelChoiceField(
        queryset=None,
        label="設備",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "equipment_select",
                "placeholder": "請選擇本次報工使用的SMT設備",
            }
        ),
        required=True,
        help_text="請選擇本次報工使用的SMT設備",
    )

    # 日期選擇器
    work_date = forms.DateField(
        label="日期",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "id": "work_date_input",
                "placeholder": "請選擇實際報工日期",
            }
        ),
        required=True,
        help_text="請選擇實際報工日期",
    )

    # 開始時間（24小時制）
    start_time = forms.CharField(
        label="開始時間",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "text",
                "id": "start_time_input",
                "placeholder": "例如：16:00",
                "readonly": "readonly",
                "autocomplete": "off",
            }
        ),
        required=True,
        help_text="請輸入實際開始時間 (24小時制)，例如 16:00",
    )

    # 結束時間（24小時制）
    end_time = forms.CharField(
        label="結束時間",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "text",
                "id": "end_time_input",
                "placeholder": "例如：18:30",
                "readonly": "readonly",
                "autocomplete": "off",
            }
        ),
        required=True,
        help_text="請輸入實際結束時間 (24小時制)，例如 18:30",
    )

    # 工作數量
    work_quantity = forms.IntegerField(
        label="工作數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "id": "work_quantity_input",
                "placeholder": "請輸入本次實際完成的數量",
            }
        ),
        required=True,
        help_text="請輸入該時段內實際完成的合格產品數量",
    )

    # 不良品數量
    defect_quantity = forms.IntegerField(
        label="不良品數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "id": "defect_quantity_input",
                "placeholder": "請輸入本次產生的不良品數量 (可不填)",
            }
        ),
        required=False,
        initial=0,
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
    )

    # 完工勾選欄位
    is_completed = forms.BooleanField(
        label="是否已完工？",
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "id": "is_completed_checkbox"}
        ),
        required=False,
        help_text="若此工單在此工序上已全部完成，請勾選",
    )

    # 備註
    remarks = forms.CharField(
        label="備註",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "id": "remarks_input",
                "placeholder": "可填寫異常狀況、停機原因等",
            }
        ),
        required=False,
        help_text="請輸入任何需要補充的資訊，如異常、停機等",
    )

    # 核准狀態（僅顯示，不可編輯）
    approval_status = forms.CharField(
        label="核准狀態",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
                "id": "approval_status_input",
            }
        ),
        required=False,
        help_text="補登記錄的核准狀態",
    )

    class Meta:
        model = SMTProductionReport
        fields = [
            "product_id",
            "workorder",
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
            "approval_status",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # 設置產品編號選項
        self.fields["product_code"].choices = self.get_product_choices()

        # 設置工單選項
        self.fields["workorder"].queryset = self.get_workorder_queryset()

        # 設置工序選項
        self.fields["operation"].choices = self.get_operation_choices()

        # 設置設備選項（只顯示SMT設備）
        from equip.models import Equipment
        from django.db import models

        smt_equipment = Equipment.objects.filter(
            models.Q(name__icontains="SMT")
            | models.Q(name__icontains="貼片")
            | models.Q(name__icontains="Pick")
            | models.Q(name__icontains="Place")
        ).order_by("name")

        # 如果是編輯現有記錄，檢查核准狀態
        if self.instance and self.instance.pk:
            if self.instance.approval_status == "approved" and not (
                self.user and self.user.is_superuser
            ):
                # 已核准且非超級管理員，禁用所有欄位
                for field_name in self.fields:
                    if field_name != "approval_status":
                        self.fields[field_name].widget.attrs["readonly"] = "readonly"
                        self.fields[field_name].widget.attrs["disabled"] = "disabled"

                # 設置核准狀態顯示
                self.fields["approval_status"].initial = (
                    self.instance.get_approval_status_display()
                )
            else:
                # 未核准或超級管理員，設置核准狀態顯示
                self.fields["approval_status"].initial = (
                    self.instance.get_approval_status_display()
                )
        else:
            # 新增記錄，設置預設核准狀態
            self.fields["approval_status"].initial = "待核准"
        self.fields["equipment"].queryset = smt_equipment

        # 設置預設日期為今天
        from datetime import date

        if not self.instance.pk:  # 新增時才設置預設值
            self.fields["work_date"].initial = date.today()

    def get_product_choices(self):
        """取得產品編號選項"""
        choices = [("", "請選擇產品編號")]
        try:
            from .models import WorkOrder

            products = (
                WorkOrder.objects.values_list("product_code", "product_code")
                .distinct()
                .order_by("product_code")
            )
            for product_code, _ in products:
                choices.append((product_code, product_code))
        except Exception:
            pass
        return choices

    def get_workorder_queryset(self):
        """取得工單查詢集"""
        from .models import WorkOrder

        return WorkOrder.objects.filter(status__in=["pending", "in_progress"]).order_by(
            "-created_at"
        )

    def get_operation_choices(self):
        """取得工序選項 - 只顯示SMT相關工序"""
        choices = [("", "請選擇工序")]
        try:
            from process.models import ProcessName

            # 從資料庫中取得SMT相關工序
            smt_processes = ProcessName.objects.filter(name__icontains="SMT").order_by(
                "name"
            )

            for process in smt_processes:
                choices.append((process.name, process.name))
        except Exception as e:
            # 如果資料庫查詢失敗，使用預設的SMT工序
            smt_operations = [
                ("SMT", "SMT"),
                ("SMT_A面", "SMT_A面"),
                ("SMT_B面", "SMT_B面"),
            ]
            choices.extend(smt_operations)
        return choices

    def clean(self):
        """表單驗證（含防止重複填寫）"""
        cleaned_data = super().clean()
        from datetime import datetime, timedelta
        from workorder.models import SMTProductionReport

        # 取得欄位
        equipment = cleaned_data.get("equipment")
        work_date = cleaned_data.get("work_date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        work_quantity = cleaned_data.get("work_quantity")

        # 1. 時間格式轉換
        start_time_str = (
            start_time
            if isinstance(start_time, str)
            else (start_time.strftime("%H:%M") if start_time else None)
        )
        end_time_str = (
            end_time
            if isinstance(end_time, str)
            else (end_time.strftime("%H:%M") if end_time else None)
        )
        if start_time_str:
            try:
                start_time_obj = datetime.strptime(start_time_str, "%H:%M").time()
                cleaned_data["start_time"] = start_time_obj
            except ValueError:
                raise forms.ValidationError("開始時間格式錯誤，請用 16:00 這種格式！")
        else:
            start_time_obj = None
        if end_time_str:
            try:
                end_time_obj = datetime.strptime(end_time_str, "%H:%M").time()
                cleaned_data["end_time"] = end_time_obj
            except ValueError:
                raise forms.ValidationError("結束時間格式錯誤，請用 18:30 這種格式！")
        else:
            end_time_obj = None
        # 2. 結束時間必須大於開始時間
        if start_time_obj and end_time_obj:
            start_dt = datetime.combine(datetime.today(), start_time_obj)
            end_dt = datetime.combine(datetime.today(), end_time_obj)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            if end_dt <= start_dt:
                raise forms.ValidationError("結束時間一定要比開始時間晚喔！")
        # 3. 工作數量必須大於0
        if work_quantity is not None and work_quantity <= 0:
            raise forms.ValidationError("工作數量一定要大於0，不能是0或負數！")
        # 4. 不良品數量不能為負數
        defect_quantity = cleaned_data.get("defect_quantity", 0)
        if defect_quantity is not None and defect_quantity < 0:
            raise forms.ValidationError("不良品數量不能是負數喔！")
        # 5. 防止重複填寫（同設備、同日、時間重疊）
        if equipment and work_date and start_time_obj and end_time_obj:
            start_dt = datetime.combine(work_date, start_time_obj)
            end_dt = datetime.combine(work_date, end_time_obj)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            # 查詢重疊的報工
            overlap_qs = SMTProductionReport.objects.filter(
                equipment=equipment, work_date=work_date
            )
            if self.instance.pk:
                overlap_qs = overlap_qs.exclude(pk=self.instance.pk)
            for report in overlap_qs:
                report_start = datetime.combine(report.work_date, report.start_time)
                report_end = datetime.combine(report.work_date, report.end_time)
                if report_end <= report_start:
                    report_end += timedelta(days=1)
                # 有重疊
                if start_dt < report_end and end_dt > report_start:
                    raise forms.ValidationError(
                        f"這台設備在 {report.start_time.strftime('%H:%M')}~{report.end_time.strftime('%H:%M')} 已經有人填過了，請不要重複填寫！"
                    )
        # 6. 防止同設備、同日、同數量重複
        if equipment and work_date and work_quantity is not None:
            same_qty_qs = SMTProductionReport.objects.filter(
                equipment=equipment, work_date=work_date, work_quantity=work_quantity
            )
            if self.instance.pk:
                same_qty_qs = same_qty_qs.exclude(pk=self.instance.pk)
            if same_qty_qs.exists():
                raise forms.ValidationError(
                    "這台設備今天已經有一筆一樣數量的報工，請檢查是不是重複填寫！"
                )
        return cleaned_data

    def save(self, commit=True):
        """儲存表單"""
        instance = super().save(commit=False)

        # 設置建立人員
        if not instance.pk:  # 新增時才設置
            from django.contrib.auth.models import AnonymousUser

            if hasattr(self, "request") and hasattr(self.request, "user"):
                user = self.request.user
                if not isinstance(user, AnonymousUser):
                    instance.created_by = user.username
                else:
                    instance.created_by = "system"
            else:
                instance.created_by = "system"

        if commit:
            instance.save()
        return instance


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
            attrs={"class": "form-control", "min": "1", "id": "daily_quantity_input"}
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

        workorders = WorkOrder.objects.filter(
            status__in=["in_progress", "completed"]
        ).order_by("-created_at")[:100]
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

        # 驗證每日數量必須大於0
        daily_quantity = cleaned_data.get("daily_quantity")
        if daily_quantity and daily_quantity <= 0:
            raise forms.ValidationError({"daily_quantity": "每日數量必須大於0"})

        return cleaned_data


# ==================== 作業員補登報工表單 ====================


class OperatorSupplementReportForm(forms.ModelForm):
    """
    作業員補登報工表單
    用於創建和編輯作業員補登報工記錄
    """

    # 產品編號下拉選單（從工單自動帶出選項）
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
        required=False,
        help_text="請選擇產品編號，或從工單自動帶出",
    )

    # 工單號碼下拉選單
    workorder = forms.ModelChoiceField(
        queryset=None,
        label="工單號碼",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "workorder_select",
                "placeholder": "請選擇工單號碼，或透過產品編號自動帶出",
            }
        ),
        required=True,
        help_text="請選擇工單號碼，或透過產品編號自動帶出",
    )

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

    # 作業員下拉選單
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

    # 工序下拉選單（排除SMT相關工序）
    process = forms.ModelChoiceField(
        queryset=None,
        label="工序",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "process_select",
                "placeholder": "請選擇此次補登的工序（排除SMT相關工序）",
            }
        ),
        required=True,
        help_text="請選擇此次補登的工序（排除SMT相關工序）",
    )

    # 設備下拉選單（排除SMT相關設備）
    equipment = forms.ModelChoiceField(
        queryset=None,
        label="設備",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "equipment_select",
                "placeholder": "請選擇此次補登的設備（排除SMT相關設備）",
            }
        ),
        required=False,
        help_text="請選擇此次補登的設備（排除SMT相關設備）",
    )

    # 日期選擇器
    work_date = forms.DateField(
        label="日期",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "id": "work_date_input",
                "placeholder": "請選擇實際報工日期",
            }
        ),
        required=True,
        help_text="請選擇實際報工日期",
    )

    # 開始時間（24小時制）
    start_time = forms.CharField(
        label="開始時間",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "text",
                "id": "start_time_input",
                "placeholder": "例如：16:00",
                "readonly": "readonly",
                "autocomplete": "off",
            }
        ),
        required=True,
        help_text="請輸入實際開始時間 (24小時制)，例如 16:00",
    )

    # 結束時間（24小時制）
    end_time = forms.CharField(
        label="結束時間",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "text",
                "id": "end_time_input",
                "placeholder": "例如：18:30",
                "readonly": "readonly",
                "autocomplete": "off",
            }
        ),
        required=True,
        help_text="請輸入實際結束時間 (24小時制)，例如 18:30",
    )

    # 工作數量
    work_quantity = forms.IntegerField(
        label="工作數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "id": "work_quantity_input",
                "placeholder": "請輸入本次實際完成的數量",
            }
        ),
        required=True,
        help_text="請輸入該時段內實際完成的合格產品數量",
    )

    # 不良品數量
    defect_quantity = forms.IntegerField(
        label="不良品數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "id": "defect_quantity_input",
                "placeholder": "請輸入本次產生的不良品數量 (可不填)",
            }
        ),
        required=False,
        initial=0,
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
    )

    # 完工勾選欄位
    is_completed = forms.BooleanField(
        label="是否已完工？",
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "id": "is_completed_checkbox"}
        ),
        required=False,
        help_text="若此工單在此工序上已全部完成，請勾選",
    )
    
    # 完工判斷方式
    completion_method = forms.ChoiceField(
        choices=[
            ('manual', '手動勾選'),
            ('auto_quantity', '自動依數量判斷'),
            ('auto_time', '自動依工時判斷'),
            ('auto_operator', '作業員確認'),
            ('auto_system', '系統自動判斷'),
        ],
        label="完工判斷方式",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "completion_method_select",
            }
        ),
        required=False,
        initial='manual',
        help_text="選擇如何判斷此筆記錄是否代表工單完工",
    )

    # 備註
    remarks = forms.CharField(
        label="備註",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "id": "remarks_input",
                "placeholder": "可填寫異常狀況、停機原因等",
            }
        ),
        required=False,
        help_text="請輸入任何需要補充的資訊，如異常、停機等",
    )

    # 異常記錄
    abnormal_notes = forms.CharField(
        label="異常記錄",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": "3",
                "id": "abnormal_notes_input",
                "placeholder": "記錄生產過程中的異常情況",
            }
        ),
        required=False,
        help_text="記錄生產過程中的異常情況",
    )

    # 審核狀態（僅顯示，不可編輯）
    approval_status = forms.CharField(
        label="審核狀態",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
                "id": "approval_status_input",
            }
        ),
        required=False,
        help_text="此欄位由系統自動設定，不可手動修改",
    )

    class Meta:
        from .models import OperatorSupplementReport
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
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設置作業員查詢集
        from process.models import Operator
        self.fields["operator"].queryset = Operator.objects.all().order_by("name")
        
        # 設置工單查詢集
        from .models import WorkOrder
        self.fields["workorder"].queryset = WorkOrder.objects.filter(status__in=["pending", "in_progress"]).order_by("-created_at")
        
        # 設置工序查詢集（排除SMT相關工序）
        from process.models import ProcessName
        self.fields["process"].queryset = ProcessName.objects.exclude(
            name__icontains="SMT"
        ).exclude(
            name__icontains="貼片"
        ).exclude(
            name__icontains="印刷"
        ).exclude(
            name__icontains="迴焊"
        ).order_by("name")
        
        # 設置設備查詢集（排除SMT相關設備）
        from equip.models import Equipment
        self.fields["equipment"].queryset = Equipment.objects.exclude(
            name__icontains="SMT"
        ).exclude(
            name__icontains="貼片機"
        ).exclude(
            name__icontains="印刷機"
        ).exclude(
            name__icontains="迴焊爐"
        ).order_by("name")
        
        # 設置預設時間為當前時間
        from datetime import datetime

        current_time = datetime.now().time()
        self.fields["start_time"].initial = current_time.strftime("%H:%M")
        self.fields["end_time"].initial = current_time.strftime("%H:%M")
        
        # 設置產品編號選項
        self.fields["product_id"].choices = self.get_product_choices()

    def get_product_choices(self):
        """取得產品編號選項"""
        from .models import WorkOrder
        
        # 取得所有不重複的產品編號
        product_codes = WorkOrder.objects.values_list('product_code', flat=True).distinct().order_by('product_code')
        choices = [('', '請選擇產品編號')] + [(code, code) for code in product_codes if code]
        return choices

    def clean(self):
        cleaned_data = super().clean()
        
        # 驗證時間
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        
        if start_time and end_time:
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_time, "%H:%M")
                end_dt = datetime.strptime(end_time, "%H:%M")
                
                if start_dt >= end_dt:
                    raise forms.ValidationError("結束時間必須大於開始時間")
            except ValueError:
                raise forms.ValidationError("時間格式錯誤，請使用 HH:MM 格式")
        
        # 驗證數量
        work_quantity = cleaned_data.get("work_quantity")
        defect_quantity = cleaned_data.get("defect_quantity")
        
        if work_quantity is not None and work_quantity <= 0:
            raise forms.ValidationError("工作數量必須大於0")
        
        if defect_quantity is not None and defect_quantity < 0:
            raise forms.ValidationError("不良品數量不能為負數")
        
        return cleaned_data

    def save(self, commit=True):
        """儲存表單並執行自動完工檢查"""
        instance = super().save(commit=False)
        
        # 設定產品編號
        if self.cleaned_data.get("product_id"):
            instance.product_code = self.cleaned_data["product_id"]
        
        if commit:
            instance.save()
            
            # 執行自動完工檢查
            instance.check_auto_completion()
            
            # 如果選擇了自動判斷方式，更新完工狀態
            completion_method = self.cleaned_data.get('completion_method')
            if completion_method and completion_method != 'manual':
                if instance.auto_completed:
                    instance.is_completed = True
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

    start_time = forms.CharField(
        label="開始時間",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "text",
                "id": "batch_start_time_input",
                "placeholder": "例如：08:00",
                "readonly": "readonly",
                "autocomplete": "off",
            }
        ),
        required=True,
        help_text="請輸入每日的開始時間 (24小時制)",
    )

    end_time = forms.CharField(
        label="結束時間",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "type": "text",
                "id": "batch_end_time_input",
                "placeholder": "例如：17:00",
                "readonly": "readonly",
                "autocomplete": "off",
            }
        ),
        required=True,
        help_text="請輸入每日的結束時間 (24小時制)",
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

        workorders = WorkOrder.objects.filter(
            status__in=["in_progress", "completed"]
        ).order_by("-created_at")[:100]
        self.fields["workorder"].queryset = workorders

        # 設置工序選項（排除SMT相關工序）
        from process.models import ProcessName
        from django.db.models import Q

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
        self.fields["start_time"].initial = "08:00"
        self.fields["end_time"].initial = "17:00"

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

        # 驗證每日數量必須大於0
        daily_quantity = cleaned_data.get("daily_quantity")
        if daily_quantity and daily_quantity <= 0:
            raise forms.ValidationError({"daily_quantity": "每日數量必須大於0"})

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
