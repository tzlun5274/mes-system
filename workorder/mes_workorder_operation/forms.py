"""
MES 工單作業子模組 - 表單定義
"""

from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from .models import MesWorkorderOperation, MesWorkorderOperationDetail, MesWorkorderOperationHistory


class MesWorkorderOperationForm(forms.ModelForm):
    """
    MES 工單作業主表表單
    """
    
    class Meta:
        model = MesWorkorderOperation
        fields = [
            'company_code',
            'company_name',
            'workorder_number',
            'product_code',
            'product_name',
            'operation_type',
            'operation_name',
            'status',
            'planned_quantity',
            'completed_quantity',
            'defect_quantity',
            'planned_start_date',
            'planned_end_date',
            'actual_start_date',
            'actual_end_date',
            'assigned_operator',
            'assigned_equipment',
            'notes'
        ]
        widgets = {
            'company_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如：01、02、03'
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '公司名稱'
            }),
            'workorder_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '工單號碼'
            }),
            'product_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '產品編號'
            }),
            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '產品名稱'
            }),
            'operation_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'operation_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '作業名稱'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'planned_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '計劃數量'
            }),
            'completed_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '完成數量'
            }),
            'defect_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '不良品數量'
            }),
            'planned_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'planned_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'actual_start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'actual_end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'assigned_operator': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '分配作業員'
            }),
            'assigned_equipment': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '分配設備'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '作業備註'
            })
        }
        labels = {
            'company_code': _('公司代號'),
            'company_name': _('公司名稱'),
            'workorder_number': _('工單號碼'),
            'product_code': _('產品編號'),
            'product_name': _('產品名稱'),
            'operation_type': _('作業類型'),
            'operation_name': _('作業名稱'),
            'status': _('作業狀態'),
            'planned_quantity': _('計劃數量'),
            'completed_quantity': _('完成數量'),
            'defect_quantity': _('不良品數量'),
            'planned_start_date': _('計劃開始日期'),
            'planned_end_date': _('計劃完成日期'),
            'actual_start_date': _('實際開始時間'),
            'actual_end_date': _('實際完成時間'),
            'assigned_operator': _('分配作業員'),
            'assigned_equipment': _('分配設備'),
            'notes': _('備註')
        }
        help_texts = {
            'company_code': _('公司代號，例如：01、02、03'),
            'workorder_number': _('工單號碼'),
            'product_code': _('產品編號'),
            'operation_name': _('作業名稱'),
            'planned_quantity': _('計劃作業數量'),
            'completed_quantity': _('已完成作業數量'),
            'defect_quantity': _('不良品數量'),
            'notes': _('作業備註')
        }

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證數量邏輯
        planned_quantity = cleaned_data.get('planned_quantity', 0)
        completed_quantity = cleaned_data.get('completed_quantity', 0)
        defect_quantity = cleaned_data.get('defect_quantity', 0)
        
        if completed_quantity > planned_quantity:
            raise forms.ValidationError(_('完成數量不能大於計劃數量'))
        
        if completed_quantity + defect_quantity > planned_quantity:
            raise forms.ValidationError(_('完成數量與不良品數量總和不能大於計劃數量'))
        
        # 驗證日期邏輯
        planned_start_date = cleaned_data.get('planned_start_date')
        planned_end_date = cleaned_data.get('planned_end_date')
        actual_start_date = cleaned_data.get('actual_start_date')
        actual_end_date = cleaned_data.get('actual_end_date')
        
        if planned_start_date and planned_end_date and planned_start_date > planned_end_date:
            raise forms.ValidationError(_('計劃開始日期不能晚於計劃完成日期'))
        
        if actual_start_date and actual_end_date and actual_start_date > actual_end_date:
            raise forms.ValidationError(_('實際開始時間不能晚於實際完成時間'))
        
        return cleaned_data


class MesWorkorderOperationDetailForm(forms.ModelForm):
    """
    MES 工單作業明細表單
    """
    
    class Meta:
        model = MesWorkorderOperationDetail
        fields = [
            'operation',
            'detail_type',
            'detail_name',
            'detail_description',
            'planned_quantity',
            'actual_quantity',
            'start_time',
            'end_time',
            'is_completed',
            'notes'
        ]
        widgets = {
            'operation': forms.Select(attrs={
                'class': 'form-select'
            }),
            'detail_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'detail_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '明細名稱'
            }),
            'detail_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '明細說明'
            }),
            'planned_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '計劃數量'
            }),
            'actual_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '實際數量'
            }),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_completed': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '明細備註'
            })
        }
        labels = {
            'operation': _('作業主表'),
            'detail_type': _('明細類型'),
            'detail_name': _('明細名稱'),
            'detail_description': _('明細說明'),
            'planned_quantity': _('計劃數量'),
            'actual_quantity': _('實際數量'),
            'start_time': _('開始時間'),
            'end_time': _('結束時間'),
            'is_completed': _('是否完成'),
            'notes': _('備註')
        }
        help_texts = {
            'detail_name': _('明細名稱'),
            'detail_description': _('明細說明'),
            'planned_quantity': _('計劃數量'),
            'actual_quantity': _('實際數量'),
            'notes': _('明細備註')
        }

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證數量邏輯
        planned_quantity = cleaned_data.get('planned_quantity', 0)
        actual_quantity = cleaned_data.get('actual_quantity', 0)
        
        if actual_quantity > planned_quantity:
            raise forms.ValidationError(_('實際數量不能大於計劃數量'))
        
        # 驗證時間邏輯
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time > end_time:
            raise forms.ValidationError(_('開始時間不能晚於結束時間'))
        
        return cleaned_data


class MesWorkorderOperationSearchForm(forms.Form):
    """
    MES 工單作業搜尋表單
    """
    
    # 搜尋條件
    company_code = forms.CharField(
        required=False,
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '公司代號'
        }),
        label=_('公司代號')
    )
    
    workorder_number = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '工單號碼'
        }),
        label=_('工單號碼')
    )
    
    product_code = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '產品編號'
        }),
        label=_('產品編號')
    )
    
    operation_type = forms.ChoiceField(
        required=False,
        choices=[('', '全部類型')] + MesWorkorderOperation.OPERATION_TYPE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('作業類型')
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', '全部狀態')] + MesWorkorderOperation.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('作業狀態')
    )
    
    assigned_operator = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '分配作業員'
        }),
        label=_('分配作業員')
    )
    
    # 日期範圍
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('開始日期')
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('結束日期')
    )
    
    # 完成率範圍
    completion_rate_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=100,
        decimal_places=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '最小完成率',
            'step': '0.1'
        }),
        label=_('最小完成率 (%)')
    )
    
    completion_rate_max = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=100,
        decimal_places=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '最大完成率',
            'step': '0.1'
        }),
        label=_('最大完成率 (%)')
    )

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證日期範圍
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(_('開始日期不能晚於結束日期'))
        
        # 驗證完成率範圍
        completion_rate_min = cleaned_data.get('completion_rate_min')
        completion_rate_max = cleaned_data.get('completion_rate_max')
        
        if completion_rate_min and completion_rate_max and completion_rate_min > completion_rate_max:
            raise forms.ValidationError(_('最小完成率不能大於最大完成率'))
        
        return cleaned_data


class MesWorkorderOperationBulkActionForm(forms.Form):
    """
    MES 工單作業批量操作表單
    """
    
    ACTION_CHOICES = [
        ('start', '開始作業'),
        ('pause', '暫停作業'),
        ('resume', '重啟作業'),
        ('complete', '完成作業'),
        ('cancel', '取消作業'),
        ('delete', '刪除作業'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('批量操作')
    )
    
    operation_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('確認執行此操作')
    )

    def clean_operation_ids(self):
        """驗證作業ID列表"""
        operation_ids = self.cleaned_data.get('operation_ids')
        if not operation_ids:
            raise forms.ValidationError(_('請選擇要操作的作業'))
        
        try:
            ids = [int(id.strip()) for id in operation_ids.split(',') if id.strip()]
            if not ids:
                raise forms.ValidationError(_('請選擇要操作的作業'))
            return ids
        except ValueError:
            raise forms.ValidationError(_('作業ID格式錯誤')) 