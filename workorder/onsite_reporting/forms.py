"""
現場報工子模組 - 表單定義
負責現場報工的表單處理和驗證
"""

from django import forms
from django.forms import ModelForm
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, time
from decimal import Decimal

from .models import OnsiteReport, OnsiteReportConfig


class OnsiteReportForm(ModelForm):
    """現場報工基本表單"""

    # 產品編號 - 下拉式選單
    product_id = forms.CharField(
        label="產品編號",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇產品編號'}),
        required=True,
        help_text="請選擇產品編號",
    )

    # 工作狀態 - 下拉選單
    status = forms.ChoiceField(
        choices=OnsiteReport.STATUS_CHOICES,
        label="報工狀態",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text="請選擇此次報工的狀態",
    )

    # 公司名稱欄位 - 下拉式選單
    company_code = forms.ChoiceField(
        choices=[],
        label="公司名稱",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇公司名稱'}),
        required=True,
        help_text="請選擇公司名稱",
    )

    # 作業員欄位 - 下拉式選單
    operator = forms.ChoiceField(
        choices=[],
        label="作業員",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇作業員'}),
        required=True,
        help_text="請選擇作業員",
    )

    # 使用的設備欄位 - 下拉式選單
    equipment = forms.ChoiceField(
        choices=[],
        label="使用的設備",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇使用的設備'}),
        required=False,
        help_text="請選擇使用的設備",
    )

    class Meta:
        model = OnsiteReport
        fields = [
            'report_type', 'work_date', 'product_id', 'workorder', 'company_code', 'operator',
            'process', 'equipment', 'planned_quantity', 'work_quantity', 'defect_quantity', 'status',
            'remarks', 'abnormal_notes'
        ]
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'work_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'workorder': forms.TextInput(attrs={'class': 'form-control'}),
            'process': forms.TextInput(attrs={'class': 'form-control'}),
            'planned_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'readonly': True}),
            'work_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'defect_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'abnormal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 動態載入選項
        self.load_dynamic_choices()

    def load_dynamic_choices(self):
        """動態載入表單選項"""
        try:
            from erp_integration.models import CompanyConfig
            from process.models import Operator
            from equip.models import Equipment
            from workorder.models import WorkOrder

            # 載入公司選項
            companies = CompanyConfig.objects.filter(is_active=True).order_by('company_name')
            self.fields['company_code'].choices = [('', '請選擇公司名稱')] + [
                (company.company_name, company.company_name) for company in companies
            ]

            # 載入作業員選項
            operators = Operator.objects.filter(is_active=True).order_by('name')
            self.fields['operator'].choices = [('', '請選擇作業員')] + [
                (operator.name, operator.name) for operator in operators
            ]

            # 載入設備選項
            equipments = Equipment.objects.filter(is_active=True).order_by('name')
            self.fields['equipment'].choices = [('', '請選擇設備')] + [
                (equipment.name, equipment.name) for equipment in equipments
            ]

        except Exception as e:
            # 如果載入失敗，設定空選項
            self.fields['company_code'].choices = [('', '載入失敗')]
            self.fields['operator'].choices = [('', '載入失敗')]
            self.fields['equipment'].choices = [('', '載入失敗')]


class OperatorOnsiteReportForm(OnsiteReportForm):
    """作業員現場報工表單"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 設定報工類型為作業員
        self.fields['report_type'].initial = 'operator'
        self.fields['report_type'].widget = forms.HiddenInput()
        # 設定預設狀態為開工
        self.fields['status'].initial = 'started'


class SMTOnsiteReportForm(OnsiteReportForm):
    """SMT設備現場報工表單"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 設定報工類型為SMT
        self.fields['report_type'].initial = 'smt'
        self.fields['report_type'].widget = forms.HiddenInput()
        # SMT設備為必填
        self.fields['equipment'].required = True
        # 設定預設狀態為開工
        self.fields['status'].initial = 'started'


class OnsiteReportUpdateForm(ModelForm):
    """現場報工更新表單"""

    class Meta:
        model = OnsiteReport
        fields = [
            'status', 'work_quantity', 'defect_quantity', 'remarks'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'work_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'defect_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        work_quantity = cleaned_data.get('work_quantity', 0)
        defect_quantity = cleaned_data.get('defect_quantity', 0)

        # 檢查數量合理性
        if work_quantity < 0:
            raise forms.ValidationError("工作數量不能為負數")

        if defect_quantity < 0:
            raise forms.ValidationError("不良品數量不能為負數")

        if defect_quantity > work_quantity:
            raise forms.ValidationError("不良品數量不能超過工作數量")

        return cleaned_data


class OnsiteReportConfigForm(ModelForm):
    """現場報工配置表單"""

    class Meta:
        model = OnsiteReportConfig
        fields = [
            'config_type', 'config_key', 'config_value', 'config_description', 'is_active'
        ]
        widgets = {
            'config_type': forms.Select(attrs={'class': 'form-select'}),
            'config_key': forms.TextInput(attrs={'class': 'form-control'}),
            'config_value': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'config_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_config_key(self):
        config_key = self.cleaned_data['config_key']
        config_type = self.cleaned_data.get('config_type')

        # 檢查配置鍵的唯一性
        if OnsiteReportConfig.objects.filter(
            config_type=config_type,
            config_key=config_key
        ).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("此配置鍵已存在")

        return config_key


class OnsiteReportSearchForm(forms.Form):
    """現場報工搜尋表單"""

    # 搜尋條件
    search = forms.CharField(
        label="搜尋關鍵字",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜尋作業員、工單號碼、產品編號...'
        })
    )

    # 報工類型篩選
    report_type = forms.ChoiceField(
        label="報工類型",
        required=False,
        choices=[('', '全部')] + OnsiteReport.REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # 狀態篩選
    status = forms.ChoiceField(
        label="報工狀態",
        required=False,
        choices=[('', '全部')] + OnsiteReport.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # 公司篩選
    company_name = forms.ChoiceField(
        label="公司名稱",
        required=False,
        choices=[('', '全部')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # 日期範圍篩選
    date_from = forms.DateField(
        label="開始日期",
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '開始日期'
        })
    )

    date_to = forms.DateField(
        label="結束日期",
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '結束日期'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 動態載入公司選項
        try:
            from erp_integration.models import CompanyConfig
            companies = CompanyConfig.objects.filter(is_active=True).order_by('company_name')
            self.fields['company_name'].choices = [('', '全部')] + [
                (company.company_name, company.company_name) for company in companies
            ]
        except Exception:
            pass 