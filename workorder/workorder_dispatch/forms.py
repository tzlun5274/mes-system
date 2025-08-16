"""
派工單管理子模組 - 表單定義
負責派工單的表單驗證和處理
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import WorkOrderDispatch, WorkOrderDispatchProcess
from workorder.models import WorkOrder


class WorkOrderDispatchForm(forms.ModelForm):
    """
    派工單表單
    用於新增和編輯派工單
    """
    
    # 額外欄位用於工單查詢
    work_order_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '輸入工單號碼查詢'
        }),
        label="工單查詢"
    )
    
    class Meta:
        model = WorkOrderDispatch
        fields = [
            'company_code', 'order_number', 'product_code', 'product_name',
            'planned_quantity', 'status', 'dispatch_date', 'planned_start_date',
            'planned_end_date', 'assigned_operator', 'assigned_equipment',
            'process_name', 'notes'
        ]
        widgets = {
            'company_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '輸入公司代號'
            }),
            'order_number': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': '輸入工單號碼'
            }),
            'product_code': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': '輸入產品編號'
            }),
            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '輸入產品名稱'
            }),
            'planned_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'required': True,
                'min': '1',
                'placeholder': '輸入計劃數量'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'dispatch_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'planned_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'planned_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'assigned_operator': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '輸入作業員姓名'
            }),
            'assigned_equipment': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '輸入設備編號'
            }),
            'process_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '輸入工序名稱'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '輸入備註'
            })
        }

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證日期邏輯
        planned_start_date = cleaned_data.get('planned_start_date')
        planned_end_date = cleaned_data.get('planned_end_date')
        
        if planned_start_date and planned_end_date:
            if planned_start_date > planned_end_date:
                raise ValidationError(_('計劃開始日期不能晚於計劃完成日期'))
        
        # 驗證工單號碼是否存在
        order_number = cleaned_data.get('order_number')
        if order_number:
            # 查詢所有匹配的工單
            # 使用公司代號和工單號碼組合查詢，確保唯一性
            work_orders = WorkOrder.objects.filter(order_number=order_number)
            # 注意：這裡需要從請求中獲取公司代號，暫時保持原有邏輯
            if work_orders.exists():
                # 如果有多個工單，使用第一個（保持原有行為）
                work_order = work_orders.first()
                # 自動填入產品資訊
                if not cleaned_data.get('product_code'):
                    cleaned_data['product_code'] = work_order.product_code
                if not cleaned_data.get('planned_quantity'):
                    cleaned_data['planned_quantity'] = work_order.quantity
            else:
                raise ValidationError(_('找不到指定的工單號碼'))
        
        return cleaned_data


class WorkOrderDispatchProcessForm(forms.ModelForm):
    """
    派工單工序表單
    用於新增和編輯派工單工序
    """
    
    class Meta:
        model = WorkOrderDispatchProcess
        fields = [
            'process_name', 'step_order', 'planned_quantity',
            'assigned_operator', 'assigned_equipment', 'dispatch_status'
        ]
        widgets = {
            'process_name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': '輸入工序名稱'
            }),
            'step_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'required': True,
                'min': '1',
                'placeholder': '輸入工序順序'
            }),
            'planned_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'required': True,
                'min': '1',
                'placeholder': '輸入計劃數量'
            }),
            'assigned_operator': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '輸入作業員姓名'
            }),
            'assigned_equipment': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '輸入設備編號'
            }),
            'dispatch_status': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證工序順序不能重複
        workorder_dispatch = cleaned_data.get('workorder_dispatch')
        step_order = cleaned_data.get('step_order')
        
        if workorder_dispatch and step_order:
            existing = WorkOrderDispatchProcess.objects.filter(
                workorder_dispatch=workorder_dispatch,
                step_order=step_order
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(_('此工序順序已存在'))
        
        return cleaned_data


class DispatchSearchForm(forms.Form):
    """
    派工單搜尋表單
    用於派工單列表的搜尋和篩選
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜尋工單號/產品/公司代號'
        }),
        label="搜尋"
    )
    
    status = forms.ChoiceField(
        choices=[('', '全部狀態')] + WorkOrderDispatch.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label="狀態"
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="開始日期"
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="結束日期"
    )
    
    company_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '公司代號'
        }),
        label="公司代號"
    )


class BulkDispatchForm(forms.Form):
    """
    批量派工表單
    用於批量建立派工單
    """
    work_order_numbers = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '每行輸入一個工單號碼'
        }),
        label="工單號碼列表"
    )
    
    assigned_operator = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '輸入作業員姓名'
        }),
        label="分配作業員"
    )
    
    assigned_equipment = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '輸入設備編號'
        }),
        label="分配設備"
    )
    
    process_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '輸入工序名稱'
        }),
        label="工序名稱"
    )
    
    dispatch_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="派工日期"
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '輸入備註'
        }),
        label="備註"
    )

    def clean_work_order_numbers(self):
        """驗證工單號碼列表"""
        work_order_numbers = self.cleaned_data['work_order_numbers']
        if not work_order_numbers.strip():
            raise ValidationError(_('請輸入工單號碼'))
        
        # 分割並清理工單號碼
        numbers = [no.strip() for no in work_order_numbers.split('\n') if no.strip()]
        if not numbers:
            raise ValidationError(_('請輸入有效的工單號碼'))
        
        # 驗證工單是否存在
        from workorder.models import WorkOrder
        invalid_numbers = []
        for number in numbers:
            if not WorkOrder.objects.filter(order_number=number).exists():
                invalid_numbers.append(number)
        
        if invalid_numbers:
            raise ValidationError(_(f'以下工單號碼不存在: {", ".join(invalid_numbers)}'))
        
        return numbers 