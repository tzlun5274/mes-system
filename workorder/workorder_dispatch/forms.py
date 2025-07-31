"""
派工單管理子模組 - 表單定義
負責派工單的表單驗證和處理
"""

from django import forms
from .models import WorkOrderDispatch
from workorder.models import WorkOrder


class WorkOrderDispatchForm(forms.ModelForm):
    """
    派工單表單
    用於新增和編輯派工單
    """
    
    class Meta:
        model = WorkOrderDispatch
        fields = ['work_order', 'operator', 'process', 'planned_quantity', 'status', 'notes']
        widgets = {
            'work_order': forms.Select(
                attrs={
                    'class': 'form-control',
                    'required': True,
                    'placeholder': '選擇工單'
                }
            ),
            'operator': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '輸入作業員姓名'
                }
            ),
            'process': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'required': True,
                    'placeholder': '輸入工序名稱'
                }
            ),
            'planned_quantity': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'required': True,
                    'min': '1',
                    'placeholder': '輸入計劃數量'
                }
            ),
            'status': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': '選擇狀態'
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': '3',
                    'placeholder': '輸入備註（可選）'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定工單選項
        self.fields['work_order'].queryset = WorkOrder.objects.filter(
            status__in=['pending', 'in_progress']
        ).order_by('-created_at')
        
        # 設定狀態選項（新增時不顯示狀態欄位）
        if not self.instance.pk:
            self.fields['status'].widget = forms.HiddenInput()
        
        # 添加 Bootstrap 樣式
        for field_name, field in self.fields.items():
            if field_name != 'status' or self.instance.pk:
                field.widget.attrs.update({'class': 'form-control'})

    def clean_planned_quantity(self):
        """驗證計劃數量"""
        planned_quantity = self.cleaned_data.get('planned_quantity')
        
        if planned_quantity is not None and planned_quantity <= 0:
            raise forms.ValidationError('計劃數量必須大於0')
        
        return planned_quantity

    def clean_work_order(self):
        """驗證工單"""
        work_order = self.cleaned_data.get('work_order')
        
        if work_order and work_order.status == 'completed':
            raise forms.ValidationError('無法為已完成的工單建立派工單')
        
        return work_order

    def clean(self):
        """整體表單驗證"""
        cleaned_data = super().clean()
        work_order = cleaned_data.get('work_order')
        process = cleaned_data.get('process')
        
        # 檢查是否已存在相同的工單和工序組合
        if work_order and process:
            existing_dispatch = WorkOrderDispatch.objects.filter(
                work_order=work_order,
                process=process
            )
            
            if self.instance.pk:
                existing_dispatch = existing_dispatch.exclude(pk=self.instance.pk)
            
            if existing_dispatch.exists():
                raise forms.ValidationError(
                    f'工單 {work_order.order_number} 的 {process} 工序已有派工單'
                )
        
        return cleaned_data


class WorkOrderDispatchSearchForm(forms.Form):
    """
    派工單搜尋表單
    用於篩選和搜尋派工單
    """
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '搜尋工單號、作業員或工序...'
            }
        )
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', '所有狀態'),
            ('pending', '待處理'),
            ('dispatched', '已派工'),
            ('in_production', '生產中'),
            ('completed', '已完成'),
            ('cancelled', '已取消'),
        ],
        widget=forms.Select(
            attrs={
                'class': 'form-control'
            }
        )
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': '開始日期'
            }
        )
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': '結束日期'
            }
        )
    )

    def clean(self):
        """驗證日期範圍"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('開始日期不能晚於結束日期')
        
        return cleaned_data


class BulkDispatchForm(forms.Form):
    """
    批量派工表單
    用於一次為多個工單建立派工單
    """
    
    work_orders = forms.ModelMultipleChoiceField(
        queryset=WorkOrder.objects.filter(status__in=['pending', 'in_progress']),
        widget=forms.CheckboxSelectMultiple(
            attrs={
                'class': 'form-check-input'
            }
        ),
        label='選擇工單'
    )
    
    operator = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '輸入作業員姓名'
            }
        ),
        label='作業員'
    )
    
    process = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '輸入工序名稱'
            }
        ),
        label='工序'
    )
    
    planned_quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'placeholder': '輸入計劃數量'
            }
        ),
        label='計劃數量'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '輸入備註（可選）'
            }
        ),
        label='備註'
    )

    def clean_work_orders(self):
        """驗證工單選擇"""
        work_orders = self.cleaned_data.get('work_orders')
        
        if not work_orders:
            raise forms.ValidationError('請至少選擇一個工單')
        
        return work_orders

    def clean_operator(self):
        """驗證作業員"""
        operator = self.cleaned_data.get('operator')
        
        if not operator.strip():
            raise forms.ValidationError('作業員姓名不能為空')
        
        return operator.strip()

    def clean_process(self):
        """驗證工序"""
        process = self.cleaned_data.get('process')
        
        if not process.strip():
            raise forms.ValidationError('工序名稱不能為空')
        
        return process.strip() 