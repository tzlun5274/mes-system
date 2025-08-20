"""
已完工工單管理子模組 - 表單
負責處理已完工工單的資料輸入和驗證
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    CompletedWorkOrder, CompletedWorkOrderProcess, 
    CompletedProductionReport, AutoAllocationSettings
)


class CompletedWorkOrderForm(forms.ModelForm):
    """已完工工單表單"""
    
    class Meta:
        model = CompletedWorkOrder
        fields = [
            'company_code', 'order_number', 'product_code', 'product_name',
            'order_quantity', 'completed_quantity', 'defective_quantity',
            'start_date', 'completion_date', 'status', 'remarks'
        ]
        widgets = {
            'company_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入公司代號'
            }),
            'order_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入工單號碼'
            }),
            'product_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入產品編號'
            }),
            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入產品名稱'
            }),
            'order_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入訂單數量'
            }),
            'completed_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入完工數量'
            }),
            'defective_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入不良品數量'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': '請選擇開始日期'
            }),
            'completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': '請選擇完工日期'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '請輸入備註'
            })
        }
    
    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證數量邏輯
        order_quantity = cleaned_data.get('order_quantity')
        completed_quantity = cleaned_data.get('completed_quantity')
        defective_quantity = cleaned_data.get('defective_quantity')
        
        if order_quantity and completed_quantity:
            if completed_quantity > order_quantity:
                raise ValidationError('完工數量不能大於訂單數量')
        
        if completed_quantity and defective_quantity:
            if defective_quantity > completed_quantity:
                raise ValidationError('不良品數量不能大於完工數量')
        
        # 驗證日期邏輯
        start_date = cleaned_data.get('start_date')
        completion_date = cleaned_data.get('completion_date')
        
        if start_date and completion_date:
            if completion_date < start_date:
                raise ValidationError('完工日期不能早於開始日期')
        
        return cleaned_data


class CompletedWorkOrderProcessForm(forms.ModelForm):
    """已完工工單工序表單"""
    
    class Meta:
        model = CompletedWorkOrderProcess
        fields = [
            'process_name', 'process_sequence', 'planned_quantity',
            'completed_quantity', 'defective_quantity', 'start_time',
            'end_time', 'operator_name', 'equipment_name', 'remarks'
        ]
        widgets = {
            'process_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入工序名稱'
            }),
            'process_sequence': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': '請輸入工序順序'
            }),
            'planned_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入計劃數量'
            }),
            'completed_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入完工數量'
            }),
            'defective_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入不良品數量'
            }),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'placeholder': '請選擇開始時間'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'placeholder': '請選擇結束時間'
            }),
            'operator_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入作業員'
            }),
            'equipment_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入設備'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '請輸入備註'
            })
        }
    
    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證數量邏輯
        planned_quantity = cleaned_data.get('planned_quantity')
        completed_quantity = cleaned_data.get('completed_quantity')
        defective_quantity = cleaned_data.get('defective_quantity')
        
        if planned_quantity and completed_quantity:
            if completed_quantity > planned_quantity:
                raise ValidationError('完工數量不能大於計劃數量')
        
        if completed_quantity and defective_quantity:
            if defective_quantity > completed_quantity:
                raise ValidationError('不良品數量不能大於完工數量')
        
        # 驗證時間邏輯
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise ValidationError('結束時間必須晚於開始時間')
        
        return cleaned_data


class CompletedProductionReportForm(forms.ModelForm):
    """已完工生產報表表單"""
    
    class Meta:
        model = CompletedProductionReport
        fields = [
            'report_date', 'report_type', 'total_production',
            'good_quantity', 'defective_quantity', 'production_efficiency',
            'quality_rate', 'remarks'
        ]
        widgets = {
            'report_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': '請選擇報表日期'
            }),
            'report_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'total_production': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入總生產量'
            }),
            'good_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入良品數量'
            }),
            'defective_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入不良品數量'
            }),
            'production_efficiency': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01',
                'placeholder': '請輸入生產效率(%)'
            }),
            'quality_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01',
                'placeholder': '請輸入品質率(%)'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '請輸入備註'
            })
        }
    
    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證數量邏輯
        total_production = cleaned_data.get('total_production')
        good_quantity = cleaned_data.get('good_quantity')
        defective_quantity = cleaned_data.get('defective_quantity')
        
        if total_production and good_quantity and defective_quantity:
            if good_quantity + defective_quantity != total_production:
                raise ValidationError('良品數量 + 不良品數量 = 總生產量')
        
        # 驗證效率指標
        production_efficiency = cleaned_data.get('production_efficiency')
        quality_rate = cleaned_data.get('quality_rate')
        
        if production_efficiency is not None:
            if production_efficiency < 0 or production_efficiency > 100:
                raise ValidationError('生產效率必須在 0-100% 之間')
        
        if quality_rate is not None:
            if quality_rate < 0 or quality_rate > 100:
                raise ValidationError('品質率必須在 0-100% 之間')
        
        return cleaned_data


class AutoAllocationSettingsForm(forms.ModelForm):
    """自動分配設定表單"""
    
    class Meta:
        model = AutoAllocationSettings
        fields = [
            'setting_name', 'is_active', 'allocation_type',
            'priority_rules', 'check_interval', 'remarks'
        ]
        widgets = {
            'setting_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入設定名稱'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allocation_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'priority_rules': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '5',
                'placeholder': '請輸入優先級規則 (JSON 格式)'
            }),
            'check_interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '60',
                'placeholder': '請輸入檢查間隔(分鐘)'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '請輸入備註'
            })
        }
    
    def clean_priority_rules(self):
        """驗證優先級規則 JSON 格式"""
        import json
        
        priority_rules = self.cleaned_data.get('priority_rules')
        if priority_rules:
            try:
                # 嘗試解析 JSON
                json.loads(priority_rules)
            except json.JSONDecodeError:
                raise ValidationError('優先級規則必須是有效的 JSON 格式')
        
        return priority_rules
    
    def clean_check_interval(self):
        """驗證檢查間隔"""
        check_interval = self.cleaned_data.get('check_interval')
        if check_interval:
            if check_interval < 1 or check_interval > 60:
                raise ValidationError('檢查間隔必須在 1-60 分鐘之間')
        
        return check_interval


# 搜尋和篩選表單
class CompletedWorkOrderSearchForm(forms.Form):
    """已完工工單搜尋表單"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜尋公司代號、工單號碼、產品編號或產品名稱'
        })
    )
    
    company_code = forms.ChoiceField(
        required=False,
        choices=[('', '全部公司')],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', '全部狀態'),
            ('completed', '已完工'),
            ('archived', '已封存'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '開始日期'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '結束日期'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 動態載入公司代號選項
        from .models import CompletedWorkOrder
        company_choices = [('', '全部公司')]
        company_codes = CompletedWorkOrder.objects.values_list(
            'company_code', flat=True
        ).distinct().order_by('company_code')
        
        for company_code in company_codes:
            company_choices.append((company_code, company_code))
        
        self.fields['company_code'].choices = company_choices
    
    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError('結束日期不能早於開始日期')
        
        return cleaned_data


# 批次操作表單
class BatchTransferForm(forms.Form):
    """批次轉換表單"""
    
    workorder_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    transfer_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '3',
            'placeholder': '請輸入轉換原因（選填）'
        })
    )
    
    def clean_workorder_ids(self):
        """驗證工單 ID 列表"""
        workorder_ids = self.cleaned_data.get('workorder_ids')
        if not workorder_ids:
            raise ValidationError('請選擇要轉換的工單')
        
        try:
            # 解析工單 ID 列表
            ids = [int(id.strip()) for id in workorder_ids.split(',') if id.strip()]
            if not ids:
                raise ValidationError('請選擇要轉換的工單')
            return ids
        except ValueError:
            raise ValidationError('工單 ID 格式錯誤')


# 匯出表單
class ExportForm(forms.Form):
    """匯出表單"""
    
    EXPORT_FORMATS = [
        ('excel', 'Excel (.xlsx)'),
        ('csv', 'CSV (.csv)'),
    ]
    
    export_format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        initial='excel',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    include_processes = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    include_reports = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    ) 