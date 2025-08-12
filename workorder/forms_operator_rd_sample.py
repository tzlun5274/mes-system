"""
作業員RD樣品補登報工表單模組
專門處理作業員RD樣品補登報工的表單邏輯
"""

from django import forms
from workorder.workorder_reporting.models import BackupOperatorSupplementReport as OperatorSupplementReport


class OperatorRDSampleSupplementReportForm(forms.ModelForm):
    """
    【規範】作業員RD樣品補登報工表單
    - 工單號碼統一固定為"RD樣品"
    - 產品編號需要自行輸入，沒有下拉選單
    - 共用OperatorSupplementReport資料表
    """
    
    # 產品編號欄位 - 手動輸入，沒有下拉選單
    product_id = forms.CharField(
        max_length=100,
        label="產品編號",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "rd_product_id_input",
                "placeholder": "請輸入產品編號",
            }
        ),
        required=True,
        help_text="請輸入產品編號（RD樣品需要自行輸入）",
    )
    
    # 工單號碼欄位 - 固定為"RD樣品"，唯讀
    workorder_number = forms.CharField(
        max_length=100,
        label="工單號碼",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "rd_workorder_number_input",
                "placeholder": "RD樣品",
                "readonly": "readonly",
                "value": "RD樣品",
            }
        ),
        required=False,
        initial="RD樣品",
        help_text="工單號碼統一固定為「RD樣品」",
    )
    
    # 作業員選擇
    operator = forms.ModelChoiceField(
        queryset=None,
        label="作業員",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "rd_operator_select",
                "placeholder": "請選擇進行補登報工的作業員",
            }
        ),
        required=True,
        help_text="請選擇進行補登報工的作業員",
    )
    
    # 工序欄位 - 下拉選單，排除SMT相關工序
    process = forms.ModelChoiceField(
        queryset=None,
        label="工序",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "rd_process_select",
                "placeholder": "請選擇工序",
            }
        ),
        required=True,
        help_text="請選擇工序（排除SMT相關工序）",
    )
    
    # 設備欄位 - 下拉選單，排除SMT相關設備
    equipment = forms.ModelChoiceField(
        queryset=None,
        label="使用的設備",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "rd_equipment_select",
                "placeholder": "請選擇設備",
            }
        ),
        required=False,
        help_text="請選擇使用的設備（排除SMT相關設備）",
    )
    
    # 工單預設生產數量欄位 - 唯讀
    planned_quantity = forms.IntegerField(
        label="工單預設生產數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "rd_planned_quantity_input",
                "readonly": "readonly",
                "placeholder": "0",
            }
        ),
        required=False,
        initial=0,
        help_text="此為工單規劃的總生產數量，不可修改",
    )
    
    # 日期欄位
    work_date = forms.DateField(
        label="報工日期",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "id": "rd_work_date_input",
                "placeholder": "請選擇報工日期",
            }
        ),
        required=True,
        help_text="請選擇報工日期",
    )
    
    # 開始時間欄位（24小時制）
    start_time = forms.CharField(
        max_length=5,
        label="開始時間",
        widget=forms.TextInput(
            attrs={
                "class": "form-control time-input",
                "type": "text",
                "id": "rd_start_time_input",
                "placeholder": "請選擇或輸入時間 (HH:MM)",
                "autocomplete": "off",
            }
        ),
        required=True,
        help_text="請選擇或輸入實際開始時間 (24小時制，格式：HH:MM)",
    )
    
    # 結束時間欄位（24小時制）
    end_time = forms.CharField(
        max_length=5,
        label="結束時間",
        widget=forms.TextInput(
            attrs={
                "class": "form-control time-input",
                "type": "text",
                "id": "rd_end_time_input",
                "placeholder": "請選擇或輸入時間 (HH:MM)",
                "autocomplete": "off",
            }
        ),
        required=True,
        help_text="請選擇或輸入實際結束時間 (24小時制，格式：HH:MM)",
    )
    
    # 工作數量欄位
    work_quantity = forms.IntegerField(
        label="工作數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "rd_work_quantity_input",
                "min": "0",
                "placeholder": "請輸入本次實際完成的數量",
            }
        ),
        required=True,
        help_text="請輸入該時段內實際完成的合格產品數量",
    )
    
    # 不良品數量欄位
    defect_quantity = forms.IntegerField(
        label="不良品數量",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "id": "rd_defect_quantity_input",
                "min": "0",
                "placeholder": "請輸入本次產生的不良品數量",
            }
        ),
        required=False,
        initial=0,
        help_text="請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
    )
    
    # 是否完工欄位
    is_completed = forms.BooleanField(
        label="是否已完工",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "rd_is_completed_input",
            }
        ),
        required=False,
        help_text="若此工單在此工序上已全部完成，請勾選",
    )
    
    # 完工判斷方式
    completion_method = forms.ChoiceField(
        choices=[
            ("manual", "手動勾選"),
            ("auto_quantity", "自動依數量判斷"),
            ("auto_time", "自動依工時判斷"),
            ("auto_operator", "作業員確認"),
            ("auto_system", "系統自動判斷"),
        ],
        label="完工判斷方式",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "rd_completion_method_select",
            }
        ),
        required=False,
        initial="manual",
        help_text="請選擇完工判斷方式",
    )
    
    # 備註欄位
    remarks = forms.CharField(
        label="備註",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "id": "rd_remarks_input",
                "rows": "3",
                "placeholder": "可填寫設備標記、操作說明等",
            }
        ),
        required=False,
        help_text="請輸入任何需要補充的資訊，如設備標記、操作說明等",
    )
    
    # 異常記錄欄位
    abnormal_notes = forms.CharField(
        label="異常記錄",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "id": "rd_abnormal_notes_input",
                "rows": "3",
                "placeholder": "記錄生產過程中的異常情況，如設備故障、品質問題等",
            }
        ),
        required=False,
        help_text="記錄生產過程中的異常情況，如設備故障、品質問題等",
    )
    
    # 核准狀態
    approval_status = forms.ChoiceField(
        choices=[
            ("pending", "待核准"),
            ("approved", "已核准"),
            ("rejected", "已駁回"),
        ],
        label="核准狀態",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "rd_approval_status_select",
            }
        ),
        required=False,
        initial="pending",
        help_text="請選擇核准狀態",
    )

    class Meta:
        model = OperatorSupplementReport
        fields = [
            "product_id",
            "workorder_number",
            "operator",
            "process",
            "equipment",
            "planned_quantity",
            "work_date",
            "start_time",
            "end_time",
            "work_quantity",
            "defect_quantity",
            "is_completed",
            "completion_method",
            "remarks",
            "abnormal_notes",
            "approval_status",
        ]
        labels = {
            "product_id": "產品編號",
            "workorder_number": "工單號碼",
            "operator": "作業員",
            "process": "工序",
            "equipment": "使用的設備",
            "planned_quantity": "工單預設生產數量",
            "work_date": "報工日期",
            "start_time": "開始時間",
            "end_time": "結束時間",
            "work_quantity": "工作數量",
            "defect_quantity": "不良品數量",
            "is_completed": "是否已完工",
            "completion_method": "完工判斷方式",
            "remarks": "備註",
            "abnormal_notes": "異常記錄",
            "approval_status": "核准狀態",
        }
        help_texts = {
            "product_id": "請輸入產品編號（RD樣品需要自行輸入）",
            "workorder_number": "工單號碼統一固定為「RD樣品」",
            "operator": "請選擇進行補登報工的作業員",
            "process": "請選擇工序（排除SMT相關工序）",
            "equipment": "請選擇使用的設備（排除SMT相關設備）",
            "planned_quantity": "此為工單規劃的總生產數量，不可修改",
            "work_date": "請選擇報工日期",
            "start_time": "請選擇或輸入實際開始時間 (24小時制，格式：HH:MM)",
            "end_time": "請選擇或輸入實際結束時間 (24小時制，格式：HH:MM)",
            "work_quantity": "請輸入該時段內實際完成的合格產品數量",
            "defect_quantity": "請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
            "is_completed": "若此工單在此工序上已全部完成，請勾選",
            "completion_method": "請選擇完工判斷方式",
            "remarks": "請輸入任何需要補充的資訊，如設備標記、操作說明等",
            "abnormal_notes": "記錄生產過程中的異常情況，如設備故障、品質問題等",
            "approval_status": "請選擇核准狀態",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定作業員欄位的 queryset，排除SMT相關作業員
        from process.models import Operator
        operators = Operator.objects.exclude(
            name__icontains='SMT'
        ).order_by('name')
        
        if 'operator' in self.fields:
            self.fields['operator'].queryset = operators
            self.fields['operator'].empty_label = "請選擇作業員"
        
        # 設定工序欄位的 queryset，排除SMT相關工序
        from process.models import ProcessName
        processes = ProcessName.objects.exclude(
            name__icontains='SMT'
        ).order_by('name')
        
        if 'process' in self.fields:
            self.fields['process'].queryset = processes
            self.fields['process'].empty_label = "請選擇工序"
        
        # 設定設備欄位的 queryset，排除SMT相關設備
        from equip.models import Equipment
        equipments = Equipment.objects.exclude(
            name__icontains='SMT'
        ).order_by('name')
        
        if 'equipment' in self.fields:
            self.fields['equipment'].queryset = equipments
            self.fields['equipment'].empty_label = "請選擇設備"
        
        # 設定預設值
        if "product_id" in self.fields:
            self.fields["product_id"].initial = ""
        
        if "workorder_number" in self.fields:
            self.fields["workorder_number"].initial = "RD樣品"
        
        if "planned_quantity" in self.fields:
            self.fields["planned_quantity"].initial = 0
        
        # 設定預設日期為今天（只在新增時）
        if not self.instance.pk:
            from datetime import date
            self.fields["work_date"].initial = date.today()
    
    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        
        # RD樣品模式下，設定預設值
        cleaned_data['workorder_number'] = 'RD樣品'
        
        # 驗證時間
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("結束時間必須晚於開始時間")
        
        return cleaned_data
    
    def clean_start_time(self):
        """驗證開始時間格式"""
        start_time = self.cleaned_data.get("start_time")
        if start_time:
            # 驗證時間格式 (HH:MM)
            import re

            if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", start_time):
                raise forms.ValidationError(
                    "開始時間格式不正確，請使用 24 小時制格式，例如：16:00"
                )
        return start_time

    def clean_end_time(self):
        """驗證結束時間格式"""
        end_time = self.cleaned_data.get("end_time")
        if end_time:
            # 驗證時間格式 (HH:MM)
            import re

            if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", end_time):
                raise forms.ValidationError(
                    "結束時間格式不正確，請使用 24 小時制格式，例如：18:30"
                )
        return end_time

    def clean(self):
        """表單驗證"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        # 驗證時間邏輯
        if start_time and end_time:
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_time, "%H:%M")
                end_dt = datetime.strptime(end_time, "%H:%M")
                
                if end_dt <= start_dt:
                    raise forms.ValidationError("結束時間必須晚於開始時間")
                    
            except ValueError:
                raise forms.ValidationError("時間格式錯誤")

        return cleaned_data

    def save(self, commit=True):
        """儲存表單資料"""
        instance = super().save(commit=False)
        
        # 設定RD樣品報工相關欄位
        instance.workorder_number = 'RD樣品'
        instance.planned_quantity = 0  # RD樣品預設生產數量為0
        
        if commit:
            instance.save()
        
        return instance 