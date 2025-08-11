"""
填報作業管理子模組 - 表單定義
負責填報作業功能的表單，包括作業員填報、SMT填報等
"""

from django import forms
from django.utils import timezone
from datetime import date
from .models import FillWork
from workorder.forms import TimeField


class FillWorkForm(forms.ModelForm):
    """
    填報作業表單
    使用自定義的 TimeField 來符合填報功能設計規範
    """
    
    # 使用自定義的 TimeField
    start_time = TimeField(
        label="開始時間",
        help_text="請選擇或輸入開始時間 (HH:MM格式，24小時制)",
        required=True,
    )
    
    end_time = TimeField(
        label="結束時間", 
        help_text="請選擇或輸入結束時間 (HH:MM格式，24小時制)",
        required=True,
    )
    
    break_start_time = TimeField(
        label="休息開始時間",
        help_text="休息開始時間 (HH:MM格式，24小時制)",
        required=False,
    )
    
    break_end_time = TimeField(
        label="休息結束時間",
        help_text="休息結束時間 (HH:MM格式，24小時制)",
        required=False,
    )
    
    # 日期欄位使用 HTML5 date picker
    work_date = forms.DateField(
        label="填報日期",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "placeholder": "請選擇填報日期",
            }
        ),
        required=True,
        help_text="請選擇填報作業的日期",
    )
    
    # 重新定義需要下拉選單的欄位
    operator = forms.ChoiceField(
        choices=[],
        label="作業員",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': '請選擇作業員'
        }),
        required=True,
        help_text="請選擇作業員",
    )
    
    company_name = forms.ChoiceField(
        choices=[],
        label="公司名稱",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': '請選擇公司名稱'
        }),
        required=True,
        help_text="請選擇公司名稱",
    )
    
    product_id = forms.ChoiceField(
        choices=[],
        label="產品編號",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': '請選擇產品編號'
        }),
        required=True,
        help_text="請選擇產品編號",
    )
    
    workorder = forms.ChoiceField(
        choices=[],
        label="工單號碼",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': '請選擇工單號碼'
        }),
        required=False,
        help_text="請選擇工單號碼，將自動帶出公司名稱",
    )
    
    class Meta:
        model = FillWork
        fields = [
            'operator', 'company_name', 'workorder', 'product_id', 'planned_quantity',
            'process', 'operation', 'equipment', 'work_date', 'start_time', 'end_time',
            'has_break', 'break_start_time', 'break_end_time', 'break_hours',
            'work_quantity', 'defect_quantity', 'is_completed', 'remarks', 'abnormal_notes'
        ]
        widgets = {
            'planned_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': '工單預設生產數量'
            }),
            'process': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': '請選擇工序'
            }),
            'operation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '工序名稱'
            }),
            'equipment': forms.Select(attrs={
                'class': 'form-control',
                'placeholder': '請選擇使用的設備'
            }),
            'has_break': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'break_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'placeholder': '休息時數'
            }),
            'work_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入工作數量'
            }),
            'defect_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入不良品數量'
            }),
            'is_completed': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '請輸入備註'
            }),
            'abnormal_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': '請記錄異常情況'
            }),
        }
        labels = {
            'operator': '作業員',
            'company_name': '公司名稱',
            'workorder': '工單號碼',
            'product_id': '產品編號',
            'planned_quantity': '工單預設生產數量',
            'process': '工序',
            'operation': '工序名稱',
            'equipment': '使用的設備',
            'work_date': '填報日期',
            'start_time': '開始時間',
            'end_time': '結束時間',
            'has_break': '是否有休息時間',
            'break_start_time': '休息開始時間',
            'break_end_time': '休息結束時間',
            'break_hours': '休息時數',
            'work_quantity': '工作數量',
            'defect_quantity': '不良品數量',
            'is_completed': '是否已完工',
            'remarks': '備註',
            'abnormal_notes': '異常記錄',
        }
        help_texts = {
            'operator': '請輸入作業員姓名',
            'company_name': '請輸入公司名稱',
            'workorder': '請選擇工單號碼，或透過產品編號自動帶出',
            'product_id': '請選擇產品編號，將自動帶出相關工單',
            'planned_quantity': '此為工單規劃的總生產數量，不可修改',
            'process': '請選擇此次填報的工序',
            'operation': '工序名稱',
            'equipment': '請選擇使用的設備（可選）',
            'work_date': '請選擇填報作業的日期',
            'start_time': '請選擇或輸入開始時間 (HH:MM格式，24小時制)',
            'end_time': '請選擇或輸入結束時間 (HH:MM格式，24小時制)',
            'has_break': '是否有休息時間',
            'break_start_time': '休息開始時間 (HH:MM格式，24小時制)',
            'break_end_time': '休息結束時間 (HH:MM格式，24小時制)',
            'break_hours': '休息時數',
            'work_quantity': '請輸入工作數量（良品數量）',
            'defect_quantity': '請輸入不良品數量',
            'is_completed': '是否已完工',
            'remarks': '請輸入備註',
            'abnormal_notes': '請記錄異常情況',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定預設日期為今天（只在新增時）
        if not self.instance.pk:
            self.fields['work_date'].initial = date.today()
        
        # 載入工單選項
        workorder_choices = self.get_workorder_choices()
        self.fields['workorder'].choices = workorder_choices
        
        # 載入工序選項
        from process.models import ProcessName
        processes = ProcessName.objects.all().order_by('name')
        self.fields['process'].queryset = processes
        
        # 載入設備選項
        from equip.models import Equipment
        equipments = Equipment.objects.all().order_by('name')
        self.fields['equipment'].queryset = equipments
        
        # 載入產品編號選項（從工單中獲取）
        product_choices = self.get_product_choices()
        self.fields['product_id'].choices = product_choices
        
        # 載入公司名稱選項
        company_choices = self.get_company_choices()
        self.fields['company_name'].choices = company_choices
        
        # 載入作業員選項
        operator_choices = self.get_operator_choices()
        self.fields['operator'].choices = operator_choices

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # 驗證結束時間必須大於開始時間
        if start_time and end_time:
            try:
                # 將時間字串轉換為時間物件進行比較
                from datetime import datetime
                start_dt = datetime.strptime(start_time, '%H:%M').time()
                end_dt = datetime.strptime(end_time, '%H:%M').time()
                
                if end_dt <= start_dt:
                    raise forms.ValidationError('結束時間必須大於開始時間')
            except ValueError:
                raise forms.ValidationError('時間格式錯誤')
        
        return cleaned_data
    
    def get_product_choices(self):
        """獲取產品編號選項"""
        from workorder.models import WorkOrder
        
        # 從工單表中獲取所有產品編號
        products = WorkOrder.objects.values_list('product_code', flat=True).distinct().order_by('product_code')
        
        choices = [('', '請選擇產品編號')]  # 預設選項
        for product in products:
            if product:  # 確保產品編號不為空
                choices.append((product, product))
        return choices
    
    def get_company_choices(self):
        """獲取公司名稱選項"""
        # 從 ERP 整合模組獲取公司配置
        from erp_integration.models import CompanyConfig
        
        companies = CompanyConfig.objects.all().order_by('company_name')
        
        choices = [('', '請選擇公司名稱')]  # 預設選項
        for company in companies:
            choices.append((company.company_name, company.company_name))
        return choices
    
    def get_workorder_choices(self):
        """獲取工單選項（不包含公司代號）"""
        from workorder.models import WorkOrder
        
        workorders = WorkOrder.objects.all().order_by('-created_at')[:100]
        
        choices = [('', '請選擇工單號碼')]  # 預設選項
        for workorder in workorders:
            # 只顯示工單編號，不包含公司代號
            choices.append((workorder.id, workorder.order_number))
        return choices
    
    def get_operator_choices(self):
        """獲取作業員選項"""
        # 從製程模組獲取作業員
        from process.models import Operator
        
        operators = Operator.objects.all().order_by('name')
        
        choices = [('', '請選擇作業員')]  # 預設選項
        for operator in operators:
            choices.append((operator.name, operator.name))
        return choices 