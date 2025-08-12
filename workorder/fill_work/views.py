"""
填報作業管理子模組 - 視圖定義
負責填報作業的網頁視圖和表單處理
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse_lazy
from django.forms import ModelForm
from django import forms
from datetime import datetime, time
from decimal import Decimal
from mes_config.date_utils import get_today_string, convert_date_for_html_input, normalize_date_string
from mes_config.custom_fields import smart_time_field
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

from .models import FillWork
from workorder.workorder_dispatch.models import WorkOrderDispatch
from erp_integration.models import CompanyConfig
from process.models import ProcessName, Operator
from equip.models import Equipment


# ==================== 表單類別定義 ====================

class OperatorBackfillForm(ModelForm):
    """作業員補登填報表單"""
    
    # 產品編號 - 下拉式選單（選項由前端載入；後端不做 choices 驗證）
    product_id = forms.CharField(
        label="產品編號",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇產品編號'}),
        required=True,
        help_text="請選擇產品編號",
    )
    
    # 下拉式日期（最近 30 天）
    work_date = forms.ChoiceField(
        choices=[],
        label="填報日期",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text="請選擇日期（預設今天）"
    )
    
    # 公司名稱欄位 - 下拉式選單
    company_name = forms.ChoiceField(
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
        model = FillWork
        fields = [
            'product_id', 'workorder', 'company_name', 'operator', 'process', 'equipment',
            'planned_quantity', 'work_quantity', 'defect_quantity', 'is_completed',
            'work_date', 'start_time', 'end_time', 'remarks', 'abnormal_notes'
        ]
        widgets = {
            # product_id 由上方 ChoiceField 控制
            'workorder': forms.TextInput(attrs={'class': 'form-control'}),
            'planned_quantity': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'work_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'defect_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'process': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM',
                'pattern': r'\d{2}:\d{2}',
                'maxlength': '5',
                'title': '請輸入24小時制時間格式，例如：08:30、17:30'
            }),
            'end_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM',
                'pattern': r'\d{2}:\d{2}',
                'maxlength': '5',
                'title': '請輸入24小時制時間格式，例如：08:30、17:30'
            }),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'abnormal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 過濾工序，排除SMT相關
        self.fields['process'].queryset = ProcessName.objects.exclude(name__icontains='SMT')
        
        # 設定 planned_quantity 可留空
        self.fields['planned_quantity'].required = False
        
        # 載入選項
        self.fields['company_name'].choices = self.get_company_choices()
        self.fields['operator'].choices = self.get_operator_choices()
        self.fields['equipment'].choices = self.get_equipment_choices()
        
        # 設定預設值與日期選項
        if not self.instance.pk:
            from datetime import timedelta, date
            today = date.today()
            options = []
            for i in range(0, 30):
                d = today - timedelta(days=i)
                s = d.strftime('%Y-%m-%d')
                options.append((s, s))
            self.fields['work_date'].choices = options
            self.fields['work_date'].initial = today.strftime('%Y-%m-%d')
    
    def get_company_choices(self):
        choices = [("", "請選擇公司名稱")]
        try:
            from erp_integration.models import CompanyConfig
            companies = CompanyConfig.objects.all().order_by('company_name')
            for company in companies:
                choices.append((company.company_name, company.company_name))
        except ImportError:
            pass
        return choices
    
    def get_operator_choices(self):
        choices = [("", "請選擇作業員")]
        try:
            from process.models import Operator
            operators = Operator.objects.all().order_by('name')
            for operator in operators:
                choices.append((operator.name, operator.name))
        except ImportError:
            pass
        return choices
    
    def get_equipment_choices(self):
        choices = [("", "請選擇使用的設備")]
        try:
            from equip.models import Equipment
            equipments = Equipment.objects.exclude(name__icontains='SMT').order_by('name')
            for equipment in equipments:
                choices.append((equipment.name, equipment.name))
        except ImportError:
            pass
        return choices
    
    def clean_start_time(self):
        """驗證開始時間格式"""
        start_time = self.cleaned_data.get('start_time')
        if start_time:
            try:
                # 驗證 HH:MM 格式
                from datetime import datetime, time as time_cls
                if isinstance(start_time, time_cls):
                    return start_time
                time_obj = datetime.strptime(str(start_time), "%H:%M").time()
                return time_obj
            except (ValueError, TypeError):
                raise forms.ValidationError("請輸入正確的時間格式：HH:MM（24小時制）")
        return start_time
    
    def clean_end_time(self):
        """驗證結束時間格式"""
        end_time = self.cleaned_data.get('end_time')
        if not end_time:
            return end_time
        from datetime import datetime, time as time_cls
        if isinstance(end_time, time_cls):
            return end_time
        try:
            return datetime.strptime(str(end_time), "%H:%M").time()
        except (ValueError, TypeError):
            raise forms.ValidationError("請輸入正確的時間格式：HH:MM（24小時制）")


class OperatorRDBackfillForm(ModelForm):
    """作業員RD樣品補登填報表單 - 使用智慧日期欄位，支援任何格式輸入"""
    
    # 下拉式日期（最近 30 天）
    work_date = forms.ChoiceField(
        choices=[],
        label="填報日期",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text="請選擇日期（預設今天）"
    )
    
    # 公司名稱欄位 - 下拉式選單
    company_name = forms.ChoiceField(
        choices=[],
        label="公司名稱",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': '請選擇公司名稱'
        }),
        required=True,
        help_text="請選擇公司名稱",
    )
    
    # 作業員欄位 - 下拉式選單
    operator = forms.ChoiceField(
        choices=[],
        label="作業員",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': '請選擇作業員'
        }),
        required=True,
        help_text="請選擇作業員",
    )
    
    # 使用的設備欄位 - 下拉式選單
    equipment = forms.ChoiceField(
        choices=[],
        label="使用的設備",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': '請選擇使用的設備'
        }),
        required=False,
        help_text="請選擇使用的設備",
    )
    
    class Meta:
        model = FillWork
        fields = [
            'product_id', 'workorder', 'company_name', 'operator', 'process', 'equipment',
            'planned_quantity', 'work_quantity', 'defect_quantity', 'is_completed',
            'work_date', 'start_time', 'end_time', 'remarks', 'abnormal_notes'
        ]
        widgets = {
            'product_id': forms.TextInput(attrs={'class': 'form-control'}),
            'workorder': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'planned_quantity': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'work_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'defect_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'process': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM',
                'pattern': r'\d{2}:\d{2}',
                'maxlength': '5',
                'title': '請輸入24小時制時間格式，例如：08:30、17:30'
            }),
            'end_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM',
                'pattern': r'\d{2}:\d{2}',
                'maxlength': '5',
                'title': '請輸入24小時制時間格式，例如：08:30、17:30'
            }),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'abnormal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 過濾工序，排除SMT相關
        self.fields['process'].queryset = ProcessName.objects.exclude(name__icontains='SMT')
        
        # 設定planned_quantity為非必填
        self.fields['planned_quantity'].required = False
        
        # 載入選項
        self.fields['company_name'].choices = self.get_company_choices()
        self.fields['operator'].choices = self.get_operator_choices()
        self.fields['equipment'].choices = self.get_equipment_choices()
        
        # 設定預設值
        if not self.instance.pk:  # 新增時
            # 構建最近 30 天的日期選項（含今天，往前 29 天）
            from datetime import timedelta, date
            today = date.today()
            options = []
            for i in range(0, 30):
                d = today - timedelta(days=i)
                s = d.strftime('%Y-%m-%d')
                options.append((s, s))
            self.fields['work_date'].choices = options
            self.fields['work_date'].initial = today.strftime('%Y-%m-%d')
            self.fields['product_id'].initial = 'PFP-CCT'
            self.fields['workorder'].initial = 'RD樣品'
            self.fields['planned_quantity'].initial = 0
            # 不設定時間初始值，讓前端JavaScript處理
    
    def get_company_choices(self):
        """獲取公司選項"""
        choices = [("", "請選擇公司名稱")]
        
        try:
            from erp_integration.models import CompanyConfig
            companies = CompanyConfig.objects.all().order_by('company_name')
            for company in companies:
                choices.append((company.company_name, company.company_name))
        except ImportError:
            pass
        
        return choices
    
    def get_operator_choices(self):
        """獲取作業員選項"""
        choices = [("", "請選擇作業員")]
        
        try:
            from process.models import Operator
            operators = Operator.objects.all().order_by('name')
            for operator in operators:
                choices.append((operator.name, operator.name))
        except ImportError:
            pass
        
        return choices
    
    def get_equipment_choices(self):
        """獲取設備選項（排除SMT相關設備）"""
        choices = [("", "請選擇使用的設備")]
        
        try:
            from equip.models import Equipment
            equipments = Equipment.objects.exclude(name__icontains='SMT').order_by('name')
            for equipment in equipments:
                choices.append((equipment.name, equipment.name))
        except ImportError:
            pass
        
        return choices
    
    def clean_start_time(self):
        """驗證開始時間格式"""
        start_time = self.cleaned_data.get('start_time')
        if not start_time:
            return start_time
        from datetime import datetime, time as time_cls
        if isinstance(start_time, time_cls):
            return start_time
        try:
            return datetime.strptime(str(start_time), "%H:%M").time()
        except (ValueError, TypeError):
            raise forms.ValidationError("請輸入正確的時間格式：HH:MM（24小時制）")
    
    def clean_end_time(self):
        """驗證結束時間格式"""
        end_time = self.cleaned_data.get('end_time')
        if end_time:
            try:
                # 驗證 HH:MM 格式
                from datetime import datetime, time as time_cls
                if isinstance(end_time, time_cls):
                    return end_time
                time_obj = datetime.strptime(str(end_time), "%H:%M").time()
                return time_obj
            except (ValueError, TypeError):
                raise forms.ValidationError("請輸入正確的時間格式：HH:MM（24小時制）")
        return end_time
     



class SMTBackfillForm(ModelForm):
    """SMT補登填報表單"""

    # 下拉式日期（最近 30 天）
    work_date = forms.ChoiceField(
        choices=[],
        label="填報日期",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text="請選擇日期（預設今天）"
    )

    # 公司名稱、作業員、設備（僅顯示SMT相關設備）
    company_name = forms.ChoiceField(
        choices=[], label="公司名稱",
        widget=forms.Select(attrs={'class': 'form-select'}), required=True
    )
    operator = forms.CharField(label="作業員", required=False)
    equipment = forms.ChoiceField(
        choices=[], label="使用的設備",
        widget=forms.Select(attrs={'class': 'form-select'}), required=True
    )
    
    class Meta:
        model = FillWork
        fields = [
            'product_id', 'workorder', 'company_name', 'operator', 'process', 'equipment',
            'planned_quantity', 'work_quantity', 'defect_quantity', 'is_completed',
            'work_date', 'start_time', 'end_time', 'remarks', 'abnormal_notes'
        ]
        widgets = {
            'product_id': forms.TextInput(attrs={'class': 'form-control'}),
            'workorder': forms.TextInput(attrs={'class': 'form-control'}),
            'planned_quantity': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'work_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'defect_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'process': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM',
                'pattern': r'\d{2}:\d{2}',
                'maxlength': '5',
                'title': '請輸入24小時制時間格式，例如：08:30、17:30'
            }),
            'end_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM',
                'pattern': r'\d{2}:\d{2}',
                'maxlength': '5',
                'title': '請輸入24小時制時間格式，例如：08:30、17:30'
            }),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'abnormal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 過濾工序，只顯示SMT相關
        self.fields['process'].queryset = ProcessName.objects.filter(name__icontains='SMT')
        # planned_quantity 非必填
        self.fields['planned_quantity'].required = False
        # 載入選項
        self.fields['company_name'].choices = self.get_company_choices()
        self.fields['equipment'].choices = self.get_equipment_choices()
        
        # 最近30天日期選項
        from datetime import timedelta, date
        today = date.today()
        options = []
        for i in range(0, 30):
            d = today - timedelta(days=i)
            s = d.strftime('%Y-%m-%d')
            options.append((s, s))
        self.fields['work_date'].choices = options
        if not self.instance.pk:
            self.fields['work_date'].initial = today.strftime('%Y-%m-%d')

    def get_company_choices(self):
        choices = [("", "請選擇公司名稱")]
        try:
            companies = CompanyConfig.objects.all().order_by('company_name')
            for c in companies:
                choices.append((c.company_name, c.company_name))
        except Exception:
            pass
        return choices

    def get_operator_choices(self):
        choices = [("", "請選擇作業員")]
        try:
            operators = Operator.objects.all().order_by('name')
            for o in operators:
                choices.append((o.name, o.name))
        except Exception:
            pass
        return choices

    def get_equipment_choices(self):
        choices = [("", "請選擇使用的設備")]
        try:
            equipments = Equipment.objects.filter(name__icontains='SMT').order_by('name')
            for e in equipments:
                choices.append((e.name, e.name))
        except Exception:
            pass
        return choices

    def clean_start_time(self):
        """驗證開始時間格式"""
        start_time = self.cleaned_data.get('start_time')
        if not start_time:
            return start_time
        from datetime import datetime, time as time_cls
        if isinstance(start_time, time_cls):
            return start_time
        try:
            return datetime.strptime(str(start_time), "%H:%M").time()
        except (ValueError, TypeError):
            raise forms.ValidationError("請輸入正確的時間格式：HH:MM（24小時制）")
    
    def clean_end_time(self):
        """驗證結束時間格式"""
        end_time = self.cleaned_data.get('end_time')
        if not end_time:
            return end_time
        from datetime import datetime, time as time_cls
        if isinstance(end_time, time_cls):
            return end_time
        try:
            return datetime.strptime(str(end_time), "%H:%M").time()
        except (ValueError, TypeError):
            raise forms.ValidationError("請輸入正確的時間格式：HH:MM（24小時制）")


class SMTRDBackfillForm(ModelForm):
    """SMT_RD樣品補登填報表單"""

    # 下拉式日期（最近 30 天）
    work_date = forms.ChoiceField(
        choices=[],
        label="填報日期",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text="請選擇日期（預設今天）"
    )

    # 公司名稱、作業員、設備（僅顯示SMT相關設備）
    company_name = forms.ChoiceField(
        choices=[], label="公司名稱",
        widget=forms.Select(attrs={'class': 'form-select'}), required=True
    )
    operator = forms.CharField(label="作業員", required=False)
    equipment = forms.ChoiceField(
        choices=[], label="使用的設備",
        widget=forms.Select(attrs={'class': 'form-select'}), required=True
    )
    
    class Meta:
        model = FillWork
        fields = [
            'product_id', 'workorder', 'company_name', 'operator', 'process', 'equipment',
            'planned_quantity', 'work_quantity', 'defect_quantity', 'is_completed',
            'work_date', 'start_time', 'end_time', 'remarks', 'abnormal_notes'
        ]
        widgets = {
            'product_id': forms.TextInput(attrs={'class': 'form-control'}),
            'workorder': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'planned_quantity': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'work_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'defect_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'process': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM',
                'pattern': r'\d{2}:\d{2}',
                'maxlength': '5',
                'title': '請輸入24小時制時間格式，例如：08:30、17:30'
            }),
            'end_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HH:MM',
                'pattern': r'\d{2}:\d{2}',
                'maxlength': '5',
                'title': '請輸入24小時制時間格式，例如：08:30、17:30'
            }),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'abnormal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 過濾工序，只顯示SMT相關
        self.fields['process'].queryset = ProcessName.objects.filter(name__icontains='SMT')
        
        # planned_quantity 非必填
        self.fields['planned_quantity'].required = False
        # 載入選項
        self.fields['company_name'].choices = self.get_company_choices()
        self.fields['operator'].choices = self.get_operator_choices()
        self.fields['equipment'].choices = self.get_equipment_choices()

        # 設定預設值
        if not self.instance.pk:  # 新增時
            from datetime import date, timedelta
            today = date.today()
            # 最近30天日期選項
            options = []
            for i in range(0, 30):
                d = today - timedelta(days=i)
                s = d.strftime('%Y-%m-%d')
                options.append((s, s))
            self.fields['work_date'].choices = options
            self.fields['work_date'].initial = today.strftime('%Y-%m-%d')
            self.fields['product_id'].initial = 'PFP-CCT'
            self.fields['workorder'].initial = 'RD樣品'
            self.fields['planned_quantity'].initial = 0
            # 不設定時間初始值，讓前端JavaScript處理

    def get_company_choices(self):
        choices = [("", "請選擇公司名稱")]
        try:
            companies = CompanyConfig.objects.all().order_by('company_name')
            for c in companies:
                choices.append((c.company_name, c.company_name))
        except Exception:
            pass
        return choices

    def get_operator_choices(self):
        choices = [("", "請選擇作業員")]
        try:
            operators = Operator.objects.all().order_by('name')
            for o in operators:
                choices.append((o.name, o.name))
        except Exception:
            pass
        return choices

    def get_equipment_choices(self):
        choices = [("", "請選擇使用的設備")]
        try:
            equipments = Equipment.objects.filter(name__icontains='SMT').order_by('name')
            for e in equipments:
                choices.append((e.name, e.name))
        except Exception:
            pass
        return choices
    
    def clean_start_time(self):
        """驗證開始時間格式"""
        start_time = self.cleaned_data.get('start_time')
        if not start_time:
            return start_time
        from datetime import datetime, time as time_cls
        if isinstance(start_time, time_cls):
            return start_time
        try:
            return datetime.strptime(str(start_time), "%H:%M").time()
        except (ValueError, TypeError):
            raise forms.ValidationError("請輸入正確的時間格式：HH:MM（24小時制）")
    
    def clean_end_time(self):
        """驗證結束時間格式"""
        end_time = self.cleaned_data.get('end_time')
        if not end_time:
            return end_time
        from datetime import datetime, time as time_cls
        if isinstance(end_time, time_cls):
            return end_time
        try:
            return datetime.strptime(str(end_time), "%H:%M").time()
        except (ValueError, TypeError):
            raise forms.ValidationError("請輸入正確的時間格式：HH:MM（24小時制）")


# ==================== 視圖類別定義 ====================

class FillWorkIndexView(LoginRequiredMixin, ListView):
    """填報管理首頁"""
    model = FillWork
    template_name = 'workorder/fill_work/index.html'
    context_object_name = 'fill_works'
    paginate_by = 20
    
    def get_queryset(self):
        return FillWork.objects.all().order_by('-created_at')


class OperatorIndexView(LoginRequiredMixin, ListView):
    """作業員填報首頁"""
    model = FillWork
    template_name = 'workorder/fill_work/operator_index.html'
    context_object_name = 'fill_works'
    paginate_by = 20
    
    def get_queryset(self):
        return FillWork.objects.exclude(
            Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """提供統計數據與最近記錄，供首頁儀表板顯示"""
        context = super().get_context_data(**kwargs)
        base_qs = FillWork.objects.exclude(
            Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
        )
        context['operator_pending_count'] = base_qs.filter(approval_status='pending').count()
        context['operator_approved_count'] = base_qs.filter(approval_status='approved').count()
        context['operator_rejected_count'] = base_qs.filter(approval_status='rejected').count()
        context['operator_total_count'] = base_qs.count()
        context['recent_operator_records'] = base_qs.order_by('-created_at')[:10]
        return context


class OperatorBackfillCreateView(LoginRequiredMixin, CreateView):
    """新增作業員補登填報"""
    model = FillWork
    template_name = 'workorder/fill_work/operator_backfill_form.html'
    form_class = OperatorBackfillForm
    success_url = reverse_lazy('workorder:fill_work:operator_index')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hours_range'] = [f"{h:02d}" for h in range(0, 24)]
        context['minutes_range'] = [f"{m:02d}" for m in range(0, 60)]
        return context
    
    def form_valid(self, form):
        try:
            # 設定休息時間（作業員填報：12:00-13:00）
            form.instance.has_break = True
            form.instance.break_start_time = time(12, 0)
            form.instance.break_end_time = time(13, 0)
            
            # 設定建立者
            form.instance.created_by = self.request.user.username
            
            response = super().form_valid(form)
            messages.success(self.request, '作業員補登填報新增成功！')
            return response
        except Exception as e:
            messages.error(self.request, f'儲存失敗：{str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # 彙整詳細欄位錯誤
        if form.errors:
            details = []
            for field, errs in form.errors.items():
                for err in errs:
                    details.append(f"{field}: {err}")
            if details:
                messages.error(self.request, "資料有誤：" + "；".join(details))
        else:
            messages.error(self.request, '請檢查表單資料，有必填欄位未填寫或格式不正確')
        return self.render_to_response(self.get_context_data(form=form))


class OperatorRDBackfillCreateView(LoginRequiredMixin, CreateView):
    """新增作業員RD樣品補登填報"""
    model = FillWork
    template_name = 'workorder/fill_work/operator_rd_backfill_form.html'
    form_class = OperatorRDBackfillForm
    success_url = reverse_lazy('workorder:fill_work:operator_index')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 後端提供正確的時間選單：00-23 與 00-59
        context['hours_range'] = [f"{h:02d}" for h in range(0, 24)]
        context['minutes_range'] = [f"{m:02d}" for m in range(0, 60)]
        return context
    
    def form_valid(self, form):
        try:
            # 設定休息時間（作業員RD填報：12:00-13:00）
            form.instance.has_break = True
            form.instance.break_start_time = time(12, 0)
            form.instance.break_end_time = time(13, 0)
            
            # 設定建立者
            form.instance.created_by = self.request.user.username
            
            # 儲存表單
            response = super().form_valid(form)
            
            # 成功訊息
            messages.success(self.request, '作業員RD樣品補登填報新增成功！')
            
            return response
            
        except Exception as e:
            # 錯誤訊息
            messages.error(self.request, f'儲存失敗：{str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        # 顯示錯誤訊息
        messages.error(self.request, '請檢查表單資料，有必填欄位未填寫或格式不正確')
        
        # 返回表單頁面，讓使用者繼續編輯
        return self.render_to_response(self.get_context_data(form=form))


class SMTIndexView(LoginRequiredMixin, ListView):
    """SMT填報首頁
    提供 SMT 相關的統計數字與最近填報記錄，供首頁儀表板顯示。
    """
    model = FillWork
    template_name = 'workorder/fill_work/smt_index.html'
    context_object_name = 'fill_works'
    paginate_by = 20
    
    def get_queryset(self):
        return FillWork.objects.filter(
            Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """組裝 SMT 首頁需要的統計資訊與最近記錄清單。
        - smt_pending_count / smt_approved_count / smt_rejected_count / smt_total_count
        - recent_smt_records：最近 10 筆 SMT 填報
        """
        context = super().get_context_data(**kwargs)
        base_qs = FillWork.objects.filter(
            Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
        )
        context['smt_pending_count'] = base_qs.filter(approval_status='pending').count()
        context['smt_approved_count'] = base_qs.filter(approval_status='approved').count()
        context['smt_rejected_count'] = base_qs.filter(approval_status='rejected').count()
        context['smt_total_count'] = base_qs.count()
        context['recent_smt_records'] = base_qs.order_by('-created_at')[:10]
        return context


class SMTBackfillCreateView(LoginRequiredMixin, CreateView):
    """新增SMT補登填報"""
    model = FillWork
    template_name = 'workorder/fill_work/smt_backfill_form.html'
    form_class = SMTBackfillForm
    success_url = reverse_lazy('workorder:fill_work:smt_index')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hours_range'] = [f"{h:02d}" for h in range(0, 24)]
        context['minutes_range'] = [f"{m:02d}" for m in range(0, 60)]
        return context

    def form_valid(self, form):
        try:
            # 設定無休息時間（SMT填報：12:00-12:00）
            form.instance.has_break = True
            form.instance.break_start_time = time(12, 0)
            form.instance.break_end_time = time(12, 0)
            
            # 設定建立者
            form.instance.created_by = self.request.user.username
            
            response = super().form_valid(form)
            messages.success(self.request, 'SMT補登填報新增成功！')
            return response
        except Exception as e:
            messages.error(self.request, f'儲存失敗：{str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        # 彙整詳細欄位錯誤
        if form.errors:
            details = []
            for field, errs in form.errors.items():
                for err in errs:
                    details.append(f"{field}: {err}")
            if details:
                messages.error(self.request, "資料有誤：" + "；".join(details))
        else:
            messages.error(self.request, '請檢查表單資料，有必填欄位未填寫或格式不正確')
        return self.render_to_response(self.get_context_data(form=form))


class SMTRDBackfillCreateView(LoginRequiredMixin, CreateView):
    """新增SMT_RD樣品補登填報"""
    model = FillWork
    template_name = 'workorder/fill_work/smt_rd_backfill_form.html'
    form_class = SMTRDBackfillForm
    success_url = reverse_lazy('workorder:fill_work:smt_index')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hours_range'] = [f"{h:02d}" for h in range(0, 24)]
        context['minutes_range'] = [f"{m:02d}" for m in range(0, 60)]
        return context
    
    def form_valid(self, form):
        try:
            # 設定無休息時間（SMT RD填報：12:00-12:00）
            form.instance.has_break = True
            form.instance.break_start_time = time(12, 0)
            form.instance.break_end_time = time(12, 0)
            
            # 設定建立者
            form.instance.created_by = self.request.user.username
            
            response = super().form_valid(form)
            messages.success(self.request, 'SMT_RD樣品補登填報新增成功！')
            return response
        except Exception as e:
            messages.error(self.request, f'儲存失敗：{str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        if form.errors:
            details = []
            for field, errs in form.errors.items():
                for err in errs:
                    details.append(f"{field}: {err}")
            if details:
                messages.error(self.request, "資料有誤：" + "；".join(details))
        else:
            messages.error(self.request, '請檢查表單資料，有必填欄位未填寫或格式不正確')
        return self.render_to_response(self.get_context_data(form=form))


class SMTBackfillUpdateView(LoginRequiredMixin, UpdateView):
    """編輯 SMT 補登/SMT_RD樣品 補登填報（僅允許未審核）"""
    model = FillWork
    # 預設使用 SMT 補登模板，RD 會在 get_template_names 動態切換
    template_name = 'workorder/fill_work/smt_backfill_form.html'
    success_url = reverse_lazy('workorder:fill_work:smt_index')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.approval_status != 'pending':
            messages.error(request, '此筆記錄已審核，無法修改')
            return redirect('workorder:fill_work:smt_index')
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        obj = self.get_object()
        # 依工單號碼是否為 RD樣品 決定使用的表單
        if str(obj.workorder).strip() == 'RD樣品':
            return SMTRDBackfillForm
        return SMTBackfillForm

    def get_template_names(self):
        obj = self.get_object()
        if str(obj.workorder).strip() == 'RD樣品':
            return ['workorder/fill_work/smt_rd_backfill_form.html']
        return ['workorder/fill_work/smt_backfill_form.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hours_range'] = [f"{h:02d}" for h in range(0, 24)]
        context['minutes_range'] = [f"{m:02d}" for m in range(0, 60)]
        return context

    def form_valid(self, form):
        try:
            form.instance.created_by = self.request.user.username or form.instance.created_by
            response = super().form_valid(form)
            # 依 RD 與否顯示不同成功訊息
            if str(self.object.workorder).strip() == 'RD樣品':
                messages.success(self.request, 'SMT_RD樣品補登填報修改成功！')
            else:
                messages.success(self.request, 'SMT補登填報修改成功！')
            return response
        except Exception as e:
            messages.error(self.request, f'儲存失敗：{str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        if form.errors:
            details = []
            for field, errs in form.errors.items():
                for err in errs:
                    details.append(f"{field}: {err}")
            if details:
                messages.error(self.request, "資料有誤：" + "；".join(details))
        else:
            messages.error(self.request, '請檢查表單資料，有必填欄位未填寫或格式不正確')
        return self.render_to_response(self.get_context_data(form=form))


class OperatorBackfillUpdateView(LoginRequiredMixin, UpdateView):
    """編輯作業員補登填報（僅允許未審核）"""
    model = FillWork
    template_name = 'workorder/fill_work/operator_backfill_form.html'
    form_class = OperatorBackfillForm
    success_url = reverse_lazy('workorder:fill_work:operator_index')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.approval_status != 'pending':
            messages.error(request, '此筆記錄已審核，無法修改')
            return redirect('workorder:fill_work:operator_index')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hours_range'] = [f"{h:02d}" for h in range(0, 24)]
        context['minutes_range'] = [f"{m:02d}" for m in range(0, 60)]
        return context

    def form_valid(self, form):
        try:
            form.instance.created_by = self.request.user.username or form.instance.created_by
            response = super().form_valid(form)
            messages.success(self.request, '作業員補登填報修改成功！')
            return response
        except Exception as e:
            messages.error(self.request, f'儲存失敗：{str(e)}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        if form.errors:
            details = []
            for field, errs in form.errors.items():
                for err in errs:
                    details.append(f"{field}: {err}")
            if details:
                messages.error(self.request, "資料有誤：" + "；".join(details))
        else:
            messages.error(self.request, '請檢查表單資料，有必填欄位未填寫或格式不正確')
        return self.render_to_response(self.get_context_data(form=form))


class FillWorkListView(LoginRequiredMixin, ListView):
    """填報記錄列表視圖"""
    model = FillWork
    template_name = 'workorder/fill_work/fill_work_list.html'
    context_object_name = 'fill_works'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = FillWork.objects.all()
        
        # 根據類型過濾
        fill_type = self.request.GET.get('type')
        if fill_type == 'operator':
            queryset = queryset.exclude(
                Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
            )
        elif fill_type == 'smt':
            queryset = queryset.filter(
                Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
            )
        
        # 根據狀態過濾
        status = self.request.GET.get('status')
        if status == 'pending':
            queryset = queryset.filter(approval_status='pending')
        elif status == 'approved':
            queryset = queryset.filter(approval_status='approved')
        elif status == 'rejected':
            queryset = queryset.filter(approval_status='rejected')
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fill_type'] = self.request.GET.get('type', '')
        context['status'] = self.request.GET.get('status', '')
        return context


class SupervisorApprovalIndexView(LoginRequiredMixin, ListView):
    """主管審核首頁"""
    model = FillWork
    template_name = 'workorder/fill_work/supervisor_approval_index.html'
    context_object_name = 'fill_works'
    paginate_by = 20
    
    def get_queryset(self):
        return FillWork.objects.all().order_by('-created_at')


class FillWorkDetailView(LoginRequiredMixin, DetailView):
    """填報記錄詳情視圖"""
    model = FillWork
    template_name = 'workorder/fill_work/fill_work_detail.html'
    context_object_name = 'fill_work'


class FillWorkDeleteView(LoginRequiredMixin, DeleteView):
    """刪除填報記錄（僅允許待核准）
    注意：直接在 GET 就執行刪除（前端已彈出確認），避免需要 confirm template。
    """
    model = FillWork
    success_url = reverse_lazy('workorder:fill_work:fill_work_list')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.approval_status != 'pending':
            messages.error(request, '此筆記錄非待核准狀態，無法刪除')
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """直接執行刪除，不呈現確認頁面。"""
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        response = super().post(request, *args, **kwargs)
        messages.success(request, f'已刪除填報記錄（ID: {obj_id}）')
        return response


def approve_fill_work(request, pk: int):
    """核准填報記錄"""
    from django.shortcuts import redirect
    try:
        record = FillWork.objects.get(pk=pk)
        record.approval_status = 'approved'
        record.save(update_fields=['approval_status', 'updated_at'])
        messages.success(request, '已核准該筆填報記錄')
    except FillWork.DoesNotExist:
        messages.error(request, '記錄不存在')
    return redirect('workorder:fill_work:fill_work_list')


def reject_fill_work(request, pk: int):
    """駁回填報記錄"""
    from django.shortcuts import redirect
    try:
        record = FillWork.objects.get(pk=pk)
        record.approval_status = 'rejected'
        record.save(update_fields=['approval_status', 'updated_at'])
        messages.info(request, '已駁回該筆填報記錄')
    except FillWork.DoesNotExist:
        messages.error(request, '記錄不存在')
    return redirect('workorder:fill_work:fill_work_list')


def delete_fill_work(request, pk: int):
    """刪除填報記錄（僅允許待核准），不使用確認模板，直接刪除後導回列表。"""
    try:
        obj = get_object_or_404(FillWork, pk=pk)
        if obj.approval_status != 'pending':
            messages.error(request, '此筆記錄非待核准狀態，無法刪除')
            return redirect('workorder:fill_work:fill_work_list')
        obj_id = obj.id
        obj.delete()
        messages.success(request, f'已刪除填報記錄（ID: {obj_id}）')
    except Exception as exc:
        messages.error(request, f'刪除失敗：{exc}')
    return redirect('workorder:fill_work:fill_work_list')


# ==================== API 視圖 ====================

def get_workorder_data(request):
    """獲取工單資料的API"""
    product_id = request.GET.get('product_id')
    workorder_id = request.GET.get('workorder_id')
    
    if product_id:
        # 根據產品編號獲取工單資料
        try:
            workorder = WorkOrderDispatch.objects.filter(
                product_code=product_id
            ).first()
            
            if workorder:
                # 獲取公司名稱
                company_name = workorder.company_code
                try:
                    company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                    if company_config:
                        company_name = company_config.company_name
                except:
                    pass
                
                return JsonResponse({
                    'workorder': workorder.order_number,
                    'company_name': company_name,
                    'planned_quantity': workorder.planned_quantity
                })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif workorder_id:
        # 根據工單號碼獲取工單資料
        try:
            workorder = WorkOrderDispatch.objects.filter(
                order_number=workorder_id
            ).first()
            
            if workorder:
                # 獲取公司名稱
                company_name = workorder.company_code
                try:
                    company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                    if company_config:
                        company_name = company_config.company_name
                except:
                    pass
                
                return JsonResponse({
                    'product_id': workorder.product_code,
                    'company_name': company_name,
                    'planned_quantity': workorder.planned_quantity
                })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': '未找到相關資料'}, status=404)


def get_workorder_list(request):
    """獲取工單清單的API"""
    try:
        # 獲取所有匹配的工單
        workorders = WorkOrderDispatch.objects.all().order_by('-created_at')[:10]  # 限制10筆
        
        if workorders.exists():
            workorder_list = []
            for workorder in workorders:
                # 獲取公司名稱
                company_name = workorder.company_code
                try:
                    company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                    if company_config:
                        company_name = company_config.company_name
                except:
                    pass
                
                workorder_list.append({
                    'id': workorder.id,
                    'workorder': workorder.order_number,
                    'product_id': workorder.product_code,
                    'company_name': company_name,
                    'planned_quantity': workorder.planned_quantity
                })
            
            return JsonResponse({'workorders': workorder_list})
        else:
            return JsonResponse({'workorders': []})
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def get_product_list(request):
    """獲取產品清單的API"""
    try:
        # 獲取所有產品編號
        products = WorkOrderDispatch.objects.values_list('product_code', flat=True).distinct()
        product_list = list(products)
        
        return JsonResponse({'products': product_list})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def get_workorder_by_product(request):
    """根據產品編號獲取工單清單的API"""
    try:
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'error': '缺少產品編號參數'}, status=400)
        
        # 根據產品編號獲取工單資料
        workorders = WorkOrderDispatch.objects.filter(product_code=product_id).order_by('-created_at')
        
        workorder_list = []
        for workorder in workorders:
            # 獲取公司名稱
            company_name = workorder.company_code
            try:
                company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                if company_config:
                    company_name = company_config.company_name
            except:
                pass
            
            workorder_list.append({
                'id': workorder.id,
                'workorder': workorder.order_number,
                'product_id': workorder.product_code,
                'company_name': company_name,
                'planned_quantity': workorder.planned_quantity,
                'display_name': f"{workorder.order_number} - {workorder.product_code}"
            })
        
        return JsonResponse({'workorders': workorder_list})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def get_workorder_info(request):
    """根據工單號碼獲取工單詳細資訊的API"""
    try:
        workorder_id = request.GET.get('workorder_id')
        if not workorder_id:
            return JsonResponse({'error': '缺少工單號碼參數'}, status=400)
        
        # 根據工單號碼獲取工單資料
        workorder = WorkOrderDispatch.objects.filter(order_number=workorder_id).first()
        
        if workorder:
            # 獲取公司名稱
            company_name = workorder.company_code
            try:
                company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                if company_config:
                    company_name = company_config.company_name
            except:
                pass
            
            return JsonResponse({
                'workorder': workorder.order_number,
                'product_id': workorder.product_code,
                'company_name': company_name,
                'planned_quantity': workorder.planned_quantity
            })
        else:
            return JsonResponse({'error': '未找到工單資料'}, status=404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def get_products_by_company(request):
    """根據公司名稱獲取產品清單的API"""
    try:
        company_name = request.GET.get('company_name')
        if not company_name:
            return JsonResponse({'error': '缺少公司名稱參數'}, status=400)
        
        # 根據公司名稱找到 company_code，再查產品
        company_cfg = CompanyConfig.objects.filter(company_name=company_name).first()
        code = company_cfg.company_code if company_cfg else company_name
        products = WorkOrderDispatch.objects.filter(company_code=code).values_list('product_code', flat=True).distinct()
        product_list = list(products)
        
        return JsonResponse({'products': product_list})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# 取得全部派工單號碼
def get_all_workorder_numbers(request):
    """回傳所有派工單號碼（不過濾狀態）。"""
    try:
        numbers_qs = (
            WorkOrderDispatch.objects
            .exclude(order_number__isnull=True)
            .exclude(order_number__exact='')
            .values_list('order_number', flat=True)
            .distinct()
            .order_by('order_number')
        )
        return JsonResponse({'workorders': list(numbers_qs)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)