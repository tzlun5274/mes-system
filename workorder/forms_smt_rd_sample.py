"""
SMT RD樣品補登報工表單模組
專門處理SMT RD樣品補登報工的表單邏輯
"""

from django import forms
from workorder.workorder_reporting.models import SMTProductionReport


class SMTRDSampleSupplementReportForm(forms.ModelForm):
    """
    【規範】SMT RD樣品補登報工表單 (獨立版本)
    - 專門用於SMT RD樣品的報工記錄
    - 與主要forms.py完全分離
    - 共用SMTProductionReport資料表
    """
    
    # 產品編號欄位 - 手動輸入
    product_id = forms.CharField(
        max_length=100,
        label="RD產品編號",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "rd_product_id_input",
                "placeholder": "請輸入RD樣品的產品編號",
            }
        ),
        required=True,
        help_text="請輸入RD樣品的產品編號",
    )
    
    # 原始工單號碼欄位 - 唯讀
    original_workorder_number = forms.CharField(
        max_length=100,
        label="RD工單號碼",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "rd_workorder_number_input",
                "placeholder": "RD樣品",
                "readonly": "readonly",
            }
        ),
        required=False,
        help_text="RD樣品模式下的工單號碼固定為「RD樣品」",
    )
    
    # 工序欄位 - 下拉選單，只顯示SMT相關工序
    process = forms.ModelChoiceField(
        queryset=None,
        label="工序",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "rd_process_select",
                "placeholder": "請選擇SMT工序",
            }
        ),
        required=True,
        help_text="請選擇SMT相關的工序",
    )
    
    # 工序名稱欄位 - 隱藏，用於儲存
    operation = forms.CharField(
        max_length=100,
        label="工序名稱",
        widget=forms.HiddenInput(),
        required=False,
        help_text="工序名稱（自動從 process 欄位取得）",
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
    
    # 設備欄位 - 下拉選單
    equipment = forms.ModelChoiceField(
        queryset=None,
        label="使用的設備",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "id": "rd_equipment_select",
                "placeholder": "請選擇SMT設備",
            }
        ),
        required=True,
        help_text="請選擇SMT相關設備",
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
    
    # 開始時間欄位
    start_time = forms.TimeField(
        label="開始時間",
        widget=forms.TimeInput(
            attrs={
                "class": "form-control",
                "type": "time",
                "id": "rd_start_time_input",
                "placeholder": "請選擇開始時間",
            }
        ),
        required=True,
        help_text="請選擇或輸入實際開始時間 (24小時制)",
    )
    
    # 結束時間欄位
    end_time = forms.TimeField(
        label="結束時間",
        widget=forms.TimeInput(
            attrs={
                "class": "form-control",
                "type": "time",
                "id": "rd_end_time_input",
                "placeholder": "請選擇結束時間",
            }
        ),
        required=True,
        help_text="請選擇或輸入實際結束時間 (24小時制)",
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
        help_text="若此RD樣品製作已全部完成，請勾選",
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
    
    class Meta:
        model = SMTProductionReport
        fields = [
            "product_id",
            "original_workorder_number",
            "process",
            "operation",
            "planned_quantity",
            "equipment",
            "work_date",
            "start_time",
            "end_time",
            "work_quantity",
            "defect_quantity",
            "is_completed",
            "remarks",
            "abnormal_notes",
        ]
        labels = {
            "product_id": "RD產品編號",
            "original_workorder_number": "RD工單號碼",
            "process": "工序",
            "operation": "工序名稱",
            "planned_quantity": "工單預設生產數量",
            "equipment": "使用的設備",
            "work_date": "報工日期",
            "start_time": "開始時間",
            "end_time": "結束時間",
            "work_quantity": "工作數量",
            "defect_quantity": "不良品數量",
            "is_completed": "是否已完工",
            "remarks": "備註",
            "abnormal_notes": "異常記錄",
        }
        help_texts = {
            "product_id": "請輸入RD樣品的產品編號",
            "original_workorder_number": "RD樣品模式下的工單號碼固定為「RD樣品」",
            "process": "請選擇SMT相關的工序",
            "operation": "工序名稱（自動從 process 欄位取得）",
            "planned_quantity": "此為工單規劃的總生產數量，不可修改",
            "equipment": "請選擇SMT相關設備",
            "work_date": "請選擇報工日期",
            "start_time": "請選擇或輸入實際開始時間 (24小時制)",
            "end_time": "請選擇或輸入實際結束時間 (24小時制)",
            "work_quantity": "請輸入該時段內實際完成的合格產品數量",
            "defect_quantity": "請輸入本次生產中產生的不良品數量，若無則留空或填寫0",
            "is_completed": "若此RD樣品製作已全部完成，請勾選",
            "remarks": "請輸入任何需要補充的資訊，如設備標記、操作說明等",
            "abnormal_notes": "記錄生產過程中的異常情況，如設備故障、品質問題等",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 設定設備欄位的 queryset，只顯示 SMT 相關設備
        from equip.models import Equipment
        smt_equipment = Equipment.objects.filter(
            name__icontains='SMT'
        ).order_by('name')
        
        if 'equipment' in self.fields:
            self.fields['equipment'].queryset = smt_equipment
            self.fields['equipment'].empty_label = "請選擇設備"
        
        # 設定工序欄位的 queryset，只顯示 SMT 相關工序
        from process.models import ProcessName
        smt_processes = ProcessName.objects.filter(
            name__icontains='SMT'
        ).order_by('name')
        
        if 'process' in self.fields:
            self.fields['process'].queryset = smt_processes
            self.fields['process'].empty_label = "請選擇SMT工序"
        
        # 設定預設值
        if "product_id" in self.fields:
            self.fields["product_id"].initial = "PFP-CCT"
        
        if "original_workorder_number" in self.fields:
            self.fields["original_workorder_number"].initial = "RD樣品"
        
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
        cleaned_data['original_workorder_number'] = 'RD樣品'
        
        # 從選擇的工序自動設定工序名稱
        process = cleaned_data.get('process')
        if process:
            cleaned_data['operation'] = process.name
        
        # 驗證時間
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("結束時間必須晚於開始時間")
        
        return cleaned_data
    
    def save(self, commit=True):
        """儲存表單資料"""
        instance = super().save(commit=False)
        
        # 設定RD樣品報工相關欄位
        instance.original_workorder_number = 'RD樣品'
        instance.planned_quantity = 0  # RD樣品預設生產數量為0
        
        # 從選擇的工序設定工序名稱
        if self.cleaned_data.get('process'):
            instance.operation = self.cleaned_data['process'].name
        
        if commit:
            instance.save()
        
        return instance 