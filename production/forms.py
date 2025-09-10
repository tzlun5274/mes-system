# 產線管理表單
# 此檔案定義產線管理模組的表單類別，用於資料輸入驗證

from django import forms
from django.core.exceptions import ValidationError
from .models import ProductionLineType, ProductionLine, ProductionLineSchedule
import json


class ProductionLineTypeForm(forms.ModelForm):
    """
    產線類型表單
    """

    class Meta:
        model = ProductionLineType
        fields = ["type_code", "type_name", "description", "is_active"]
        widgets = {
            "type_code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：SMT、ASSY、TEST"}
            ),
            "type_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例如：SMT產線、組裝產線",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "請描述此產線類型的用途和特點",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_type_code(self):
        """驗證類型代號"""
        type_code = self.cleaned_data["type_code"]

        if not type_code:
            raise ValidationError("類型代號不能為空")

        # 檢查是否已存在相同的類型代號
        if (
            ProductionLineType.objects.filter(type_code=type_code)
            .exclude(pk=self.instance.pk if self.instance else None)
            .exists()
        ):
            raise ValidationError("此類型代號已存在")

        return type_code.upper()  # 轉為大寫


class ProductionLineForm(forms.ModelForm):
    """
    產線管理表單
    """

    # 工作日選擇欄位
    work_days_choices = [
        ("1", "週一"),
        ("2", "週二"),
        ("3", "週三"),
        ("4", "週四"),
        ("5", "週五"),
        ("6", "週六"),
        ("7", "週日"),
    ]

    work_days = forms.MultipleChoiceField(
        choices=work_days_choices,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="工作日設定",
        help_text="選擇此產線的工作日",
    )

    # 午休時間設定選項
    has_lunch_break = forms.BooleanField(
        required=False,
        initial=True,
        label="設定午休時間",
        help_text="勾選此選項以設定午休時間，不勾選則表示沒有午休時間",
    )

    class Meta:
        model = ProductionLine
        fields = [
            "line_code",
            "line_name",
            "line_type_id",
            "line_type_name",
            "description",
            "work_start_time",
            "work_end_time",
            "lunch_start_time",
            "lunch_end_time",
            "overtime_start_time",
            "overtime_end_time",
            "is_active",
        ]
        widgets = {
            "line_code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：LINE01、SMT01"}
            ),
            "line_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例如：SMT產線1、組裝產線1",
                }
            ),
            "line_type_id": forms.TextInput(attrs={"class": "form-control"}),
            "line_type_name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "請描述此產線的用途和特點",
                }
            ),
            "work_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "work_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "lunch_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "lunch_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "overtime_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "overtime_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 如果有實例，設定工作日的初始值
        if self.instance and self.instance.pk:
            try:
                work_days_list = self.instance.get_work_days_list()
                self.fields["work_days"].initial = work_days_list

                # 設定午休時間選項的初始值
                if self.instance.lunch_start_time and self.instance.lunch_end_time:
                    self.fields["has_lunch_break"].initial = True
                else:
                    self.fields["has_lunch_break"].initial = False
            except:
                self.fields["work_days"].initial = ["1", "2", "3", "4", "5"]
                self.fields["has_lunch_break"].initial = True
        else:
            # 預設選擇週一到週五
            self.fields["work_days"].initial = ["1", "2", "3", "4", "5"]
            self.fields["has_lunch_break"].initial = True

    def clean_line_code(self):
        """驗證產線代號"""
        line_code = self.cleaned_data["line_code"]

        if not line_code:
            raise ValidationError("產線代號不能為空")

        # 檢查是否已存在相同的產線代號
        if (
            ProductionLine.objects.filter(line_code=line_code)
            .exclude(pk=self.instance.pk if self.instance else None)
            .exists()
        ):
            raise ValidationError("此產線代號已存在")

        return line_code.upper()  # 轉為大寫

    def clean(self):
        """整體驗證"""
        cleaned_data = super().clean()

        # 驗證工作時間邏輯
        work_start = cleaned_data.get("work_start_time")
        work_end = cleaned_data.get("work_end_time")
        lunch_start = cleaned_data.get("lunch_start_time")
        lunch_end = cleaned_data.get("lunch_end_time")
        overtime_start = cleaned_data.get("overtime_start_time")
        overtime_end = cleaned_data.get("overtime_end_time")
        has_lunch_break = cleaned_data.get("has_lunch_break", True)

        if work_start and work_end:
            if work_start >= work_end:
                raise ValidationError("工作結束時間必須晚於工作開始時間")

        # 午休時間驗證
        if has_lunch_break:
            # 如果有設定午休時間，則必須填寫午休開始和結束時間
            if not lunch_start or not lunch_end:
                raise ValidationError("請填寫完整的午休時間（開始和結束時間）")

            if lunch_start >= lunch_end:
                raise ValidationError("午休結束時間必須晚於午休開始時間")

            # 驗證午休時間在工作時間內
            if work_start and work_end:
                if lunch_start < work_start or lunch_end > work_end:
                    raise ValidationError("午休時間必須在工作時間範圍內")
        else:
            # 如果沒有午休時間，清空午休時間欄位
            cleaned_data["lunch_start_time"] = None
            cleaned_data["lunch_end_time"] = None

        if overtime_start and overtime_end:
            if overtime_start >= overtime_end:
                raise ValidationError("加班結束時間必須晚於加班開始時間")

        # 驗證加班時間在工作時間之後
        if work_end and overtime_start:
            if overtime_start < work_end:
                raise ValidationError("加班開始時間必須晚於或等於工作結束時間")

        return cleaned_data

    def save(self, commit=True):
        """儲存表單資料"""
        instance = super().save(commit=False)

        # 處理工作日設定
        work_days = self.cleaned_data.get("work_days", [])
        if work_days:
            instance.set_work_days_list(work_days)

        # 處理午休時間設定
        has_lunch_break = self.cleaned_data.get("has_lunch_break", True)
        if not has_lunch_break:
            instance.lunch_start_time = None
            instance.lunch_end_time = None

        if commit:
            instance.save()
        return instance


class ProductionLineScheduleForm(forms.ModelForm):
    """
    產線排程表單
    """

    # 工作日選擇欄位
    work_days_choices = [
        ("1", "週一"),
        ("2", "週二"),
        ("3", "週三"),
        ("4", "週四"),
        ("5", "週五"),
        ("6", "週六"),
        ("7", "週日"),
    ]

    work_days = forms.MultipleChoiceField(
        choices=work_days_choices,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="工作日設定",
        help_text="選擇此排程的工作日",
    )

    # 午休時間設定選項
    has_lunch_break = forms.BooleanField(
        required=False,
        initial=True,
        label="設定午休時間",
        help_text="勾選此選項以設定午休時間，不勾選則表示沒有午休時間",
    )

    class Meta:
        model = ProductionLineSchedule
        fields = [
            "production_line_id",
            "production_line_name",
            "schedule_date",
            "work_start_time",
            "work_end_time",
            "lunch_start_time",
            "lunch_end_time",
            "overtime_start_time",
            "overtime_end_time",
            "is_holiday",
            "holiday_reason",
        ]
        widgets = {
            "production_line_id": forms.Select(attrs={"class": "form-select"}),
            "schedule_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "work_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "work_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "lunch_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "lunch_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "overtime_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "overtime_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "is_holiday": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "holiday_reason": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "請說明假日原因"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定產線選擇的選項
        from .models import ProductionLine
        production_lines = ProductionLine.objects.filter(is_active=True)
        choices = [(str(line.id), f"{line.line_name} ({line.line_code})") for line in production_lines]
        self.fields["production_line_id"].choices = [("", "請選擇產線")] + choices
        
        # 如果有實例，設定工作日的初始值
        if self.instance and self.instance.pk:
            try:
                work_days_list = json.loads(self.instance.work_days)
                self.fields["work_days"].initial = work_days_list
            except:
                self.fields["work_days"].initial = ["1", "2", "3", "4", "5"]
        else:
            # 預設選擇週一到週五
            self.fields["work_days"].initial = ["1", "2", "3", "4", "5"]

    def clean(self):
        """整體驗證"""
        cleaned_data = super().clean()
        
        # 根據選擇的產線ID設定產線名稱
        production_line_id = cleaned_data.get("production_line_id")
        if production_line_id:
            try:
                from .models import ProductionLine
                production_line = ProductionLine.objects.get(id=production_line_id)
                cleaned_data["production_line_name"] = production_line.line_name
            except ProductionLine.DoesNotExist:
                raise ValidationError("選擇的產線不存在")
        
        return cleaned_data

class ProductionLineForm(forms.ModelForm):
    """
    產線管理表單
    """

    # 工作日選擇欄位
    work_days_choices = [
        ("1", "週一"),
        ("2", "週二"),
        ("3", "週三"),
        ("4", "週四"),
        ("5", "週五"),
        ("6", "週六"),
        ("7", "週日"),
    ]

    work_days = forms.MultipleChoiceField(
        choices=work_days_choices,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="工作日設定",
        help_text="選擇此產線的工作日",
    )

    # 午休時間設定選項
    has_lunch_break = forms.BooleanField(
        required=False,
        initial=True,
        label="設定午休時間",
        help_text="勾選此選項以設定午休時間，不勾選則表示沒有午休時間",
    )

    class Meta:
        model = ProductionLine
        fields = [
            "line_code",
            "line_name",
            "line_type_id",
            "line_type_name",
            "description",
            "work_start_time",
            "work_end_time",
            "lunch_start_time",
            "lunch_end_time",
            "overtime_start_time",
            "overtime_end_time",
            "work_days",
            "is_active",
        ]
        widgets = {
            "line_code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：LINE001"}
            ),
            "line_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：第一產線"}
            ),
            "line_type_id": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：SMT"}
            ),
            "line_type_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "例如：SMT產線"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "產線描述"}
            ),
            "work_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "work_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "lunch_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "lunch_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "overtime_start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "overtime_end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 如果有實例，設定工作日的初始值
        if self.instance and self.instance.pk:
            try:
                work_days_list = json.loads(self.instance.work_days)
                self.fields["work_days"].initial = work_days_list

                # 設定午休時間選項的初始值
                if self.instance.lunch_start_time and self.instance.lunch_end_time:
                    self.fields["has_lunch_break"].initial = True
                else:
                    self.fields["has_lunch_break"].initial = False
            except:
                self.fields["work_days"].initial = ["1", "2", "3", "4", "5"]
                self.fields["has_lunch_break"].initial = True
        else:
            # 預設選擇週一到週五
            self.fields["work_days"].initial = ["1", "2", "3", "4", "5"]
            self.fields["has_lunch_break"].initial = True

    def clean(self):
        """整體驗證"""
        cleaned_data = super().clean()

        # 驗證工作時間邏輯
        work_start = cleaned_data.get("work_start_time")
        work_end = cleaned_data.get("work_end_time")
        lunch_start = cleaned_data.get("lunch_start_time")
        lunch_end = cleaned_data.get("lunch_end_time")
        overtime_start = cleaned_data.get("overtime_start_time")
        overtime_end = cleaned_data.get("overtime_end_time")
        has_lunch_break = cleaned_data.get("has_lunch_break", True)

        if work_start and work_end:
            if work_start >= work_end:
                raise ValidationError("工作結束時間必須晚於工作開始時間")

        # 午休時間驗證
        if has_lunch_break:
            # 如果有設定午休時間，則必須填寫午休開始和結束時間
            if not lunch_start or not lunch_end:
                raise ValidationError("請填寫完整的午休時間（開始和結束時間）")

            if lunch_start >= lunch_end:
                raise ValidationError("午休結束時間必須晚於午休開始時間")

            # 驗證午休時間在工作時間內
            if work_start and work_end:
                if lunch_start < work_start or lunch_end > work_end:
                    raise ValidationError("午休時間必須在工作時間範圍內")
        else:
            # 如果沒有午休時間，清空午休時間欄位
            cleaned_data["lunch_start_time"] = None
            cleaned_data["lunch_end_time"] = None

        if overtime_start and overtime_end:
            if overtime_start >= overtime_end:
                raise ValidationError("加班結束時間必須晚於加班開始時間")

        # 驗證加班時間在工作時間之後
        if work_end and overtime_start:
            if overtime_start < work_end:
                raise ValidationError("加班開始時間必須晚於或等於工作結束時間")

        return cleaned_data

    def save(self, commit=True):
        """儲存表單資料"""
        instance = super().save(commit=False)

        # 處理工作日設定
        work_days = self.cleaned_data.get("work_days", [])
        if work_days:
            instance.work_days = json.dumps(work_days)

        # 處理午休時間設定
        has_lunch_break = self.cleaned_data.get("has_lunch_break", True)
        if not has_lunch_break:
            instance.lunch_start_time = None
            instance.lunch_end_time = None

        if commit:
            instance.save()
        return instance
