"""
統一補登報工表單
提供統一補登報工的新增、編輯、核准等功能表單
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import UnifiedWorkReport, UnifiedWorkReportLog
from workorder.models import WorkOrder
from process.models import ProcessName
import logging

logger = logging.getLogger(__name__)


class UnifiedWorkReportForm(forms.ModelForm):
    """
    統一補登報工表單
    用於新增和編輯統一補登報工記錄
    """
    
    # 自定義欄位，用於更好的用戶體驗
    workorder_search = forms.CharField(
        max_length=50,
        required=False,
        label="工單搜尋",
        help_text="輸入工單號碼進行搜尋",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入工單號碼'
        })
    )
    
    process_search = forms.CharField(
        max_length=100,
        required=False,
        label="工序搜尋",
        help_text="輸入工序名稱進行搜尋",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入工序名稱'
        })
    )
    
    class Meta:
        model = UnifiedWorkReport
        fields = [
            'operator', 'company_code', 'workorder', 'original_workorder_number',
            'product_id', 'planned_quantity', 'process', 'operation', 'equipment',
            'work_date', 'start_time', 'end_time', 'has_break', 'break_start_time',
            'break_end_time', 'work_quantity', 'defect_quantity', 'is_completed',
            'remarks', 'abnormal_notes'
        ]
        widgets = {
            'operator': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入作業員姓名'
            }),
            'company_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如：01、02、03'
            }),
            'workorder': forms.Select(attrs={
                'class': 'form-control'
            }),
            'original_workorder_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入原始工單號碼'
            }),
            'product_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入產品編號'
            }),
            'planned_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'process': forms.Select(attrs={
                'class': 'form-control'
            }),
            'operation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入工序名稱'
            }),
            'equipment': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入設備名稱或編號'
            }),
            'work_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': '請選擇日期'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control time-input',
                'type': 'time',
                'placeholder': 'HH:MM',
                'pattern': '[0-9]{2}:[0-9]{2}'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control time-input',
                'type': 'time',
                'placeholder': 'HH:MM',
                'pattern': '[0-9]{2}:[0-9]{2}'
            }),
            'has_break': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'break_start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'break_end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'work_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'defect_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
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
                'placeholder': '請輸入異常記錄'
            }),
        }
        labels = {
            'operator': '作業員',
            'company_code': '公司代號',
            'workorder': '工單號碼',
            'original_workorder_number': '原始工單號碼',
            'product_id': '產品編號',
            'planned_quantity': '工單預設生產數量',
            'process': '工序',
            'operation': '工序名稱',
            'equipment': '使用的設備',
            'work_date': '日期',
            'start_time': '開始時間',
            'end_time': '結束時間',
            'has_break': '是否有休息時間',
            'break_start_time': '休息開始時間',
            'break_end_time': '休息結束時間',
            'work_quantity': '工作數量',
            'defect_quantity': '不良品數量',
            'is_completed': '是否已完工',
            'remarks': '備註',
            'abnormal_notes': '異常記錄',
        }
        help_texts = {
            'operator': '請輸入作業員的姓名',
            'company_code': '請輸入公司代號，例如：01、02、03',
            'workorder': '請選擇關聯的工單',
            'original_workorder_number': '請輸入原始工單號碼',
            'product_id': '請輸入產品編號',
            'planned_quantity': '請輸入工單預設的生產數量',
            'process': '請選擇工序',
            'operation': '請輸入工序名稱',
            'equipment': '請輸入使用的設備名稱或編號',
            'work_date': '請選擇工作日期',
            'start_time': '請選擇工作開始時間',
            'end_time': '請選擇工作結束時間',
            'has_break': '勾選此項表示有休息時間',
            'break_start_time': '請選擇休息開始時間',
            'break_end_time': '請選擇休息結束時間',
            'work_quantity': '請輸入工作數量（良品）',
            'defect_quantity': '請輸入不良品數量',
            'is_completed': '勾選此項表示已完工',
            'remarks': '請輸入一般備註',
            'abnormal_notes': '請輸入異常記錄',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定工單選項
        self.fields['workorder'].queryset = WorkOrder.objects.all().order_by('-created_at')
        self.fields['workorder'].empty_label = "請選擇工單"
        
        # 設定工序選項
        self.fields['process'].queryset = ProcessName.objects.all().order_by('name')
        self.fields['process'].empty_label = "請選擇工序"
        
        # 設定預設值
        if not self.instance.pk:  # 新增時
            self.fields['work_date'].initial = timezone.now().date()
            self.fields['company_code'].initial = '01'  # 預設公司代號
    
    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證時間邏輯
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        work_date = cleaned_data.get('work_date')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError("結束時間必須晚於開始時間")
        
        # 驗證休息時間邏輯
        has_break = cleaned_data.get('has_break')
        break_start_time = cleaned_data.get('break_start_time')
        break_end_time = cleaned_data.get('break_end_time')
        
        if has_break:
            if not break_start_time or not break_end_time:
                raise ValidationError("勾選有休息時間時，必須填寫休息開始和結束時間")
            
            if break_start_time >= break_end_time:
                raise ValidationError("休息結束時間必須晚於休息開始時間")
            
            # 驗證休息時間是否在工作時間內
            if start_time and end_time:
                if break_start_time < start_time or break_end_time > end_time:
                    raise ValidationError("休息時間必須在工作時間範圍內")
        
        # 驗證數量邏輯
        work_quantity = cleaned_data.get('work_quantity', 0)
        defect_quantity = cleaned_data.get('defect_quantity', 0)
        
        if work_quantity < 0:
            raise ValidationError("工作數量不能為負數")
        
        if defect_quantity < 0:
            raise ValidationError("不良品數量不能為負數")
        
        # 驗證日期不能是未來日期
        if work_date and work_date > timezone.now().date():
            raise ValidationError("工作日期不能是未來日期")
        
        return cleaned_data
    
    def save(self, commit=True):
        """儲存時設定建立人員"""
        instance = super().save(commit=False)
        
        if not instance.pk:  # 新增時
            # 這裡需要從 request 中獲取當前用戶
            # 暫時設為 'system'，實際使用時需要從 request 中獲取
            instance.created_by = 'system'
        
        if commit:
            instance.save()
        return instance


class UnifiedWorkReportApprovalForm(forms.ModelForm):
    """
    統一補登報工核准表單
    用於核准或駁回統一補登報工記錄
    """
    
    approval_action = forms.ChoiceField(
        choices=[
            ('approve', '核准'),
            ('reject', '駁回'),
        ],
        label="核准動作",
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    approval_remarks = forms.CharField(
        max_length=500,
        required=False,
        label="核准備註",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '3',
            'placeholder': '請輸入核准備註'
        })
    )
    
    rejection_reason = forms.CharField(
        max_length=500,
        required=False,
        label="駁回原因",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '3',
            'placeholder': '請輸入駁回原因'
        })
    )
    
    class Meta:
        model = UnifiedWorkReport
        fields = []  # 不需要任何模型欄位
    
    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        approval_action = cleaned_data.get('approval_action')
        approval_remarks = cleaned_data.get('approval_remarks')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if approval_action == 'reject' and not rejection_reason:
            raise ValidationError("駁回時必須填寫駁回原因")
        
        return cleaned_data


class UnifiedWorkReportSearchForm(forms.Form):
    """
    統一補登報工搜尋表單
    用於搜尋和篩選統一補登報工記錄
    """
    
    # 基本搜尋條件
    operator = forms.CharField(
        max_length=100,
        required=False,
        label="作業員",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入作業員姓名'
        })
    )
    
    company_code = forms.CharField(
        max_length=10,
        required=False,
        label="公司代號",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入公司代號'
        })
    )
    
    workorder_number = forms.CharField(
        max_length=50,
        required=False,
        label="工單號碼",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入工單號碼'
        })
    )
    
    product_id = forms.CharField(
        max_length=100,
        required=False,
        label="產品編號",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入產品編號'
        })
    )
    
    # 日期範圍搜尋
    date_from = forms.DateField(
        required=False,
        label="開始日期",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        label="結束日期",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    # 核准狀態搜尋
    approval_status = forms.ChoiceField(
        choices=[
            ('', '全部'),
            ('pending', '待核准'),
            ('approved', '已核准'),
            ('rejected', '已駁回'),
            ('cancelled', '已取消'),
        ],
        required=False,
        label="核准狀態",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    # 工序搜尋
    process = forms.ModelChoiceField(
        queryset=ProcessName.objects.all().order_by('name'),
        required=False,
        label="工序",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    # 完工狀態搜尋
    is_completed = forms.ChoiceField(
        choices=[
            ('', '全部'),
            ('True', '已完工'),
            ('False', '未完工'),
        ],
        required=False,
        label="完工狀態",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("開始日期不能晚於結束日期")
        
        return cleaned_data


class UnifiedWorkReportImportForm(forms.Form):
    """
    統一補登報工匯入表單
    用於從 Excel 或 CSV 檔案匯入統一補登報工資料
    """
    
    file = forms.FileField(
        label="選擇檔案",
        help_text="支援 Excel (.xlsx, .xls) 和 CSV 檔案格式",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls,.csv'
        })
    )
    
    company_code = forms.CharField(
        max_length=10,
        label="公司代號",
        help_text="匯入資料的公司代號",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例如：01、02、03'
        })
    )
    
    created_by = forms.CharField(
        max_length=100,
        label="建立人員",
        help_text="匯入資料的建立人員",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入建立人員姓名'
        })
    )
    
    skip_duplicates = forms.BooleanField(
        required=False,
        initial=True,
        label="跳過重複資料",
        help_text="勾選此項將跳過重複的報工記錄",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_file(self):
        """驗證檔案格式"""
        file = self.cleaned_data.get('file')
        if file:
            # 檢查檔案大小（限制為 10MB）
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("檔案大小不能超過 10MB")
            
            # 檢查檔案格式
            allowed_extensions = ['.xlsx', '.xls', '.csv']
            file_extension = file.name.lower()
            
            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                raise ValidationError("只支援 Excel (.xlsx, .xls) 和 CSV 檔案格式")
        
        return file 


class UnifiedWorkReportSimpleForm(forms.ModelForm):
    """
    簡化統一補登報工表單
    只包含基本必要的欄位，用於快速報工
    """
    
    # 自定義工單號碼欄位（文字輸入）
    workorder_number = forms.CharField(
        max_length=50,
        label="工單號碼",
        help_text="請輸入工單號碼",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入工單號碼'
        })
    )
    
    class Meta:
        model = UnifiedWorkReport
        fields = [
            'company_code', 'product_id', 'operator', 'process', 'equipment',
            'planned_quantity', 'work_quantity', 'defect_quantity',
            'work_date', 'start_time', 'end_time', 'is_completed',
            'remarks', 'abnormal_notes'
        ]
        widgets = {
            'company_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '例如：01、02、03'
            }),
            'product_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入產品編號'
            }),
            'operator': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入作業員姓名'
            }),
            'process': forms.Select(attrs={
                'class': 'form-control'
            }),
            'equipment': forms.Select(attrs={
                'class': 'form-control'
            }),
            'planned_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '請輸入預設生產數量',
                'style': 'appearance: textfield; -moz-appearance: textfield; -webkit-appearance: textfield;'
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
            'work_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': '請選擇日期'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control time-input',
                'type': 'time',
                'placeholder': 'HH:MM',
                'pattern': '[0-9]{2}:[0-9]{2}'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control time-input',
                'type': 'time',
                'placeholder': 'HH:MM',
                'pattern': '[0-9]{2}:[0-9]{2}'
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
                'placeholder': '請輸入異常記錄'
            }),
        }
        labels = {
            'company_code': '公司代號',
            'product_id': '產品編號',
            'operator': '作業員',
            'process': '工序',
            'equipment': '使用的設備',
            'planned_quantity': '工單預設生產數量',
            'work_quantity': '工作數量',
            'defect_quantity': '不良品數量',
            'work_date': '報工日期',
            'start_time': '開始時間',
            'end_time': '結束時間',
            'is_completed': '是否已完工',
            'remarks': '備註',
            'abnormal_notes': '異常記錄',
        }
        help_texts = {
            'company_code': '請輸入公司代號，例如：01、02、03',
            'product_id': '請輸入產品編號',
            'operator': '請輸入作業員姓名',
            'process': '請選擇工序',
            'equipment': '請輸入使用的設備名稱或編號',
            'planned_quantity': '請輸入工單預設的生產數量',
            'work_quantity': '請輸入實際完成的工作數量（良品）',
            'defect_quantity': '請輸入不良品數量',
            'work_date': '請選擇報工日期',
            'start_time': '請輸入工作開始時間（24小時制）',
            'end_time': '請輸入工作結束時間（24小時制）',
            'is_completed': '勾選此項表示已完工',
            'remarks': '請輸入一般備註',
            'abnormal_notes': '請輸入異常記錄',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定工序的查詢集
        self.fields['process'].queryset = ProcessName.objects.all().order_by('name')
        self.fields['process'].empty_label = "請選擇工序"
        
        # 設定設備的查詢集
        from equip.models import Equipment
        self.fields['equipment'].queryset = Equipment.objects.all().order_by('name')
        self.fields['equipment'].empty_label = "請選擇設備"
        
        # 如果是新增模式，設定預設值
        if not self.instance.pk:
            # 設定報工日期預設為今天
            from datetime import date
            self.fields['work_date'].initial = date.today()
            
            # 設定數量預設值
            self.fields['work_quantity'].initial = 0
            self.fields['defect_quantity'].initial = 0
            self.fields['is_completed'].initial = False
        else:
            # 編輯模式，設定工單號碼的初始值
            if self.instance.workorder:
                self.fields['workorder_number'].initial = self.instance.workorder.order_number
            elif self.instance.original_workorder_number:
                self.fields['workorder_number'].initial = self.instance.original_workorder_number
            
            # 設定設備的初始值
            if self.instance.equipment:
                self.fields['equipment'].initial = self.instance.equipment

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # 驗證時間邏輯
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        work_date = cleaned_data.get('work_date')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError("結束時間必須晚於開始時間")
        
        # 驗證數量邏輯
        work_quantity = cleaned_data.get('work_quantity', 0)
        defect_quantity = cleaned_data.get('defect_quantity', 0)
        
        if work_quantity < 0:
            raise ValidationError("工作數量不能為負數")
        
        if defect_quantity < 0:
            raise ValidationError("不良品數量不能為負數")
        
        # 驗證日期不能是未來日期
        if work_date and work_date > timezone.now().date():
            raise ValidationError("工作日期不能是未來日期")
        
        return cleaned_data

    def save(self, commit=True):
        """儲存時設定必要欄位"""
        instance = super().save(commit=False)
        
        # 處理工單號碼
        workorder_number = self.cleaned_data.get('workorder_number', '').strip()
        if workorder_number:
            try:
                workorder = WorkOrder.objects.get(order_number=workorder_number)
                instance.workorder = workorder
                instance.original_workorder_number = workorder.order_number
                instance.product_id = workorder.product_code
                instance.planned_quantity = workorder.quantity
            except WorkOrder.DoesNotExist:
                # 如果找不到工單，只設定原始工單號碼
                instance.original_workorder_number = workorder_number
                instance.workorder = None
        
        if not instance.pk:  # 新增時
            # 設定預設值
            instance.company_code = '01'  # 預設公司代號
            
            # 從工序獲取相關資訊
            if instance.process:
                instance.operation = instance.process.name
            
            # 從設備獲取相關資訊
            if instance.equipment:
                # 如果設備有型號，可以設定到 operation 欄位
                if instance.equipment.model:
                    instance.operation = f"{instance.process.name} - {instance.equipment.model}"
        
        if commit:
            instance.save()
        return instance 