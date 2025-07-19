# SMT補登報工 - 工序欄位變更說明

## 變更概述

將SMT補登報工表單中的「補登日期」欄位改為「工序」選擇欄位，讓使用者可以明確選擇要補登的工序。

## 主要變更

### 1. 表單欄位變更
- **移除**：補登日期 (supplement_date) 輸入欄位
- **新增**：工序 (process_name) 下拉選擇欄位
- **自動設置**：補登日期自動設為當前日期

### 2. 欄位順序調整
新的表單欄位順序：
1. **產品編號** (左側)
2. **工單編號** (右側)
3. **工序** (左側) ← 新增
4. **設備** (右側)
5. **實際工作日期** (左側)
6. **補登原因** (右側)
7. **完成數量** (左側)
8. **不良數量** (右側)
9. **動作類型** (左側)
10. **開始時間** (左側)
11. **結束時間** (右側)
12. **備註** (全寬)

### 3. 功能改進

#### 工序選擇
- 從ProcessName模型中取得所有包含"SMT"的工序
- 支援手動選擇特定工序
- 如果沒有選擇工序，會自動查找對應的SMT工序

#### 自動日期設置
- 補登日期自動設為當前日期
- 無需使用者手動輸入日期
- 確保資料的一致性和準確性

#### 驗證邏輯
- 移除補登日期與實際工作日期的比較驗證
- 保留開始時間與結束時間的邏輯驗證

## 技術實現

### 表單修改 (forms.py)
```python
class SupplementReportForm(forms.ModelForm):
    # 新增工序選擇欄位
    process_name = forms.ChoiceField(
        label="工序",
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
    )
    
    def __init__(self, *args, **kwargs):
        # 初始化工序選項
        from process.models import ProcessName
        process_names = ProcessName.objects.filter(name__icontains='SMT').order_by('name')
        process_choices = [(p.name, p.name) for p in process_names]
        self.fields['process_name'].choices = [('', '請選擇工序')] + process_choices
```

### 視圖修改 (views.py)
```python
def supplement_report_create(request):
    # 處理工序選擇
    process_name = form.cleaned_data.get('process_name')
    
    # 根據選擇的工序名稱查找對應的工序
    if process_name:
        process = workorder.processes.filter(process_name=process_name).first()
        if process:
            supplement.process = process
    
    # 自動設置補登日期
    from django.utils import timezone
    supplement.supplement_date = timezone.now().date()
```

### 模板修改 (form.html)
```html
<!-- 工序欄位 -->
<div class="col-md-6 mb-3">
    <label for="{{ form.process_name.id_for_label }}" class="form-label">
        工序 <span class="text-danger">*</span>
    </label>
    {{ form.process_name }}
    {% if form.process_name.errors %}
        <div class="text-danger small">
            {{ form.process_name.errors }}
        </div>
    {% endif %}
</div>
```

## 可用工序

根據資料庫中的ProcessName模型，目前可用的SMT工序包括：
- SMT_A面
- SMT_B面
- SMT

## 使用方式

### 1. 創建補登記錄
1. 選擇產品編號或工單編號
2. 選擇要補登的工序
3. 選擇設備
4. 填寫其他必要資訊
5. 提交表單

### 2. 編輯補登記錄
- 工序欄位會自動顯示當前記錄的工序
- 可以修改為其他工序

## 注意事項

1. **資料一致性**：補登日期自動設為當前日期，確保資料一致性
2. **工序驗證**：系統會驗證選擇的工序是否存在於對應的工單中
3. **向後相容**：現有的補登記錄仍然可以正常顯示和編輯
4. **錯誤處理**：如果找不到對應的工序，會顯示錯誤訊息

## 測試建議

1. **基本功能測試**：測試工序選擇和自動日期設置
2. **驗證測試**：測試選擇不存在的工序時的錯誤處理
3. **編輯測試**：測試編輯現有記錄時的工序顯示
4. **自動帶出測試**：測試產品編號和工單編號的自動帶出功能

## 檔案修改清單

### 修改檔案
- `workorder/forms.py` - 新增工序欄位，移除補登日期欄位
- `workorder/views.py` - 修改創建和編輯視圖的邏輯
- `workorder/templates/workorder/supplement_report/form.html` - 更新表單模板

### 新增檔案
- `workorder/README_工序欄位變更.md` - 本說明文件 