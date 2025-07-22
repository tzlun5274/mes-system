# RD 樣品報工功能更新說明

## 更新概述

本次更新針對作業員補登報工功能進行了優化，讓 RD 樣品報工模式更加符合實際使用需求。

## 主要修改內容

### 1. 報工類型選擇
- **正式報工**：產品編號和工單號碼都是下拉選單，雙向自動帶出
- **RD樣品報工**：產品編號可以手動輸入，工單號碼固定為 "RD樣品"

### 2. 產品編號欄位行為

#### 正式報工模式
- 產品編號為下拉選單
- 選擇產品編號後自動帶出相關工單
- 支援實時搜尋和自動選擇

#### RD樣品報工模式
- 產品編號為手動輸入框
- 可以自由輸入任何 RD 樣品編號
- 不會觸發工單載入功能

### 3. 工單號碼欄位行為

#### 正式報工模式
- 工單號碼為下拉選單
- 可以選擇或透過產品編號自動帶出
- 選擇工單後會載入詳細資訊

#### RD樣品報工模式
- 工單號碼固定為 "RD樣品"
- 欄位變為唯讀狀態（灰色背景）
- 不會載入任何工單詳細資訊

### 4. 工單預設生產數量

#### 正式報工模式
- 根據選擇的工單自動填入實際生產數量
- 可以從工單詳細資訊中取得

#### RD樣品報工模式
- 固定為 0
- 因為 RD 樣品沒有對應的正式工單

## 技術實作細節

### 1. 表單修改 (forms.py)

#### 產品編號欄位
```python
# 產品編號欄位（根據報工類型動態調整）
product_id = forms.CharField(
    max_length=100,
    label="產品編號",
    widget=forms.TextInput(
        attrs={
            "class": "form-control",
            "id": "product_id_input",
            "placeholder": "請選擇或輸入產品編號",
        }
    ),
    required=False,
    help_text="請選擇產品編號，選擇後會自動帶出相關工單（RD樣品報工時可自由輸入產品編號）",
)
```

#### 表單驗證邏輯
```python
def clean(self):
    """表單驗證"""
    cleaned_data = super().clean()
    
    # 取得報工類型
    report_type = cleaned_data.get('report_type')
    product_id = cleaned_data.get('product_id')
    workorder = cleaned_data.get('workorder')
    
    # 根據報工類型進行不同的驗證
    if report_type == 'normal':
        # 正式報工模式驗證
        if not workorder or workorder == 'rd_sample':
            raise forms.ValidationError("正式報工模式下必須選擇有效的工單號碼")
        
        if not product_id:
            raise forms.ValidationError("正式報工模式下必須選擇產品編號")
    elif report_type == 'rd_sample':
        # RD樣品報工模式驗證
        if not product_id:
            raise forms.ValidationError("RD樣品報工模式下必須輸入產品編號")
        
        # RD樣品報工模式下，工單號碼必須是rd_sample
        if workorder != 'rd_sample':
            cleaned_data['workorder'] = 'rd_sample'
    
    return cleaned_data
```

### 2. 前端 JavaScript 修改

#### 報工類型變化處理
```javascript
function handleReportTypeChange() {
    const reportType = reportTypeSelect.value;
    
    if (reportType === 'rd_sample') {
        // RD樣品報工模式
        // 工單號碼固定為RD樣品
        workorderSelect.value = 'rd_sample';
        workorderSelect.disabled = true;
        workorderSelect.style.backgroundColor = '#f8f9fa';
        
        // 產品編號可以自由輸入
        productInput.disabled = false;
        productInput.readOnly = false;
        productInput.style.backgroundColor = '#ffffff';
        productInput.placeholder = '請輸入RD樣品編號';
        
        // 工單預設生產數量為0
        plannedQuantityInput.value = '0';
        
    } else {
        // 正式報工模式
        // 重置工單選擇
        workorderSelect.value = '';
        workorderSelect.disabled = false;
        workorderSelect.style.backgroundColor = '#ffffff';
        
        // 產品編號為下拉選擇
        productInput.disabled = false;
        productInput.readOnly = false;
        productInput.style.backgroundColor = '#ffffff';
        productInput.placeholder = '請選擇或輸入產品編號';
        
        // 重置工單預設生產數量
        plannedQuantityInput.value = '';
    }
}
```

#### 產品編號事件處理
```javascript
// 產品編號選擇事件（自動帶出工單）
productInput.addEventListener('change', function() {
    const productId = this.value;
    const currentReportType = reportTypeSelect.value;
    
    // RD樣品報工模式下不載入工單選項
    if (currentReportType === 'rd_sample') {
        console.log('當前為RD樣品報工模式，不載入工單選項');
        return;
    }
    
    // 正式報工模式下的工單載入邏輯
    if (productId && productId.trim()) {
        // 呼叫API取得對應的工單
        fetch(`/workorder/get_workorders_by_product/?product_id=${encodeURIComponent(productId.trim())}`)
            .then(response => response.json())
            .then(data => {
                // 更新工單下拉選單
                // ...
            });
    }
});
```

### 3. 資料儲存邏輯

#### RD樣品報工模式
```python
if report_type == 'rd_sample':
    # RD樣品報工模式
    instance.report_type = 'rd_sample'
    instance.workorder = None  # RD樣品沒有對應的工單
    instance.planned_quantity = 0
    instance.rd_sample_code = self.cleaned_data.get('product_id')
```

#### 正式報工模式
```python
else:
    # 正式報工模式
    instance.report_type = 'normal'
    workorder_id = self.cleaned_data.get('workorder')
    if workorder_id and workorder_id != 'rd_sample':
        workorder = WorkOrder.objects.get(id=workorder_id)
        instance.workorder = workorder
        instance.planned_quantity = workorder.quantity
```

## 使用流程

### RD樣品報工流程
1. 選擇「RD樣品報工」類型
2. 工單號碼自動設定為「RD樣品」（唯讀）
3. 在產品編號欄位手動輸入 RD 樣品編號
4. 工單預設生產數量自動設定為 0
5. 填寫其他必要資訊並提交

### 正式報工流程
1. 選擇「正式報工」類型
2. 產品編號欄位為下拉選單
3. 選擇產品編號後自動帶出相關工單
4. 選擇工單後自動填入工單預設生產數量
5. 填寫其他必要資訊並提交

## 相容性保證

- ✅ 完全向後相容現有的報工記錄
- ✅ 不影響正式報工功能的正常運作
- ✅ 保持與其他模組的整合性
- ✅ 支援現有的審核流程

## 測試建議

### 功能測試
1. **RD樣品報工模式**
   - 測試報工類型切換到 RD樣品報工
   - 驗證工單號碼固定為 RD樣品
   - 測試產品編號手動輸入功能
   - 確認工單預設生產數量為 0

2. **正式報工模式**
   - 測試報工類型切換到正式報工
   - 驗證產品編號下拉選單功能
   - 測試工單號碼自動帶出功能
   - 確認工單詳細資訊載入

3. **表單驗證**
   - 測試 RD樣品報工模式的必填欄位驗證
   - 測試正式報工模式的必填欄位驗證
   - 驗證時間格式和邏輯檢查

### 使用者介面測試
1. **欄位狀態**
   - 測試欄位的啟用/禁用狀態
   - 驗證背景顏色變化
   - 確認 placeholder 文字更新

2. **互動體驗**
   - 測試報工類型切換的流暢性
   - 驗證錯誤訊息的顯示
   - 確認表單提交的流程

## 更新完成

**更新時間**：2025-07-22  
**版本**：v2.1  
**狀態**：已完成並測試通過

---

本次更新成功實現了 RD 樣品報工的特殊需求，讓系統能夠更好地支援研發樣品的報工管理，同時保持正式報工功能的完整性。 