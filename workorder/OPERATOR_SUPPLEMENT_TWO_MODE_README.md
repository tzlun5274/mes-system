# 作業員補登報工 - 兩種報工模式實現說明

## 功能概述

作業員補登報工功能已成功實現兩種報工模式：
1. **正式報工模式**：產品編號和工單號碼都是下拉選單，雙向帶出對方
2. **RD樣品報工模式**：工單號碼固定為"RD樣品"，產品編號手動輸入，工單預設生產數量為0

## 實現細節

### 1. 資料模型 (models.py)

`OperatorSupplementReport` 模型已包含以下欄位：

```python
# 報工類型
REPORT_TYPE_CHOICES = [
    ('normal', '正式工單'),
    ('rd_sample', 'RD樣品'),
]

report_type = models.CharField(
    max_length=20,
    choices=REPORT_TYPE_CHOICES,
    default='normal',
    verbose_name="報工類型",
    help_text="請選擇報工類型：正式工單或RD樣品"
)

# RD樣品專用欄位
rd_sample_code = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    verbose_name="RD樣品編號",
    help_text="請輸入RD樣品的專用編號"
)
```

### 2. 表單處理 (forms.py)

`OperatorSupplementReportForm` 表單已更新：

#### 新增報工類型選擇欄位
```python
report_type = forms.ChoiceField(
    choices=[
        ('normal', '正式報工'),
        ('rd_sample', 'RD樣品報工'),
    ],
    label="報工類型",
    required=True,
    initial='normal',
    help_text="請選擇報工類型：正式報工或RD樣品報工",
)
```

#### 表單驗證邏輯
- **正式報工模式**：必須選擇有效的工單號碼和產品編號
- **RD樣品報工模式**：工單號碼固定為"RD樣品"，必須輸入產品編號

#### 儲存邏輯
- **RD樣品報工模式**：`workorder=None`，`planned_quantity=0`，`rd_sample_code=product_id`
- **正式報工模式**：正常關聯工單，設定對應的生產數量

### 3. 視圖處理 (views.py)

#### 新增視圖 (`operator_supplement_report_create`)
- 支援兩種報工模式的資料處理
- 根據報工類型設定相關欄位
- 正確處理時間格式轉換

#### 編輯視圖 (`operator_supplement_report_edit`)
- 根據記錄類型設定初始值
- 支援兩種模式的編輯功能

### 4. 前端介面 (templates)

#### 報工類型選擇
- 在基本資訊區塊最上方增加報工類型選擇欄位
- 提供清晰的視覺區分

#### JavaScript 互動邏輯
```javascript
// 報工類型變化處理函數
function handleReportTypeChange() {
    const reportType = reportTypeSelect.value;
    
    if (reportType === 'rd_sample') {
        // RD樣品報工模式
        workorderSelect.value = 'rd_sample';
        productInput.readOnly = false;
        productInput.placeholder = '請輸入RD樣品編號';
        plannedQuantityInput.value = '0';
    } else {
        // 正式報工模式
        workorderSelect.value = '';
        productInput.readOnly = true;
        productInput.placeholder = '請選擇產品編號';
        plannedQuantityInput.value = '';
    }
}
```

## 使用流程

### 正式報工模式
1. 選擇「正式報工」類型
2. 產品編號欄位變為下拉選單（唯讀）
3. 選擇產品編號後，自動帶出相關工單
4. 選擇工單後，自動填入工單預設生產數量
5. 填寫其他必要資訊並提交

### RD樣品報工模式
1. 選擇「RD樣品報工」類型
2. 工單號碼自動設定為「RD樣品」（唯讀）
3. 產品編號欄位變為手動輸入
4. 工單預設生產數量自動設定為0
5. 填寫其他必要資訊並提交

## 技術特點

### 1. 智能欄位控制
- 根據報工類型動態調整欄位的可編輯性
- 自動設定相關欄位的預設值
- 提供清晰的視覺回饋

### 2. 資料驗證
- 根據報工類型進行不同的驗證規則
- 確保資料的完整性和一致性
- 提供友善的錯誤訊息

### 3. 使用者體驗
- 直觀的介面設計
- 即時的欄位狀態更新
- 清晰的說明文字

### 4. 資料完整性
- 正確的資料關聯
- 適當的預設值設定
- 完整的審核流程支援

## 資料庫結構

### 正式報工記錄
```sql
report_type = 'normal'
workorder_id = [實際工單ID]
rd_sample_code = NULL
planned_quantity = [工單實際數量]
```

### RD樣品報工記錄
```sql
report_type = 'rd_sample'
workorder_id = NULL
rd_sample_code = [手動輸入的產品編號]
planned_quantity = 0
```

## 相容性

- 完全向後相容現有的報工記錄
- 支援現有的審核流程
- 保持與其他模組的整合性

## 測試建議

1. **功能測試**
   - 測試兩種報工模式的切換
   - 驗證欄位的動態控制
   - 確認資料儲存的正確性

2. **驗證測試**
   - 測試必填欄位驗證
   - 驗證時間格式檢查
   - 確認數量驗證邏輯

3. **使用者介面測試**
   - 測試欄位狀態的即時更新
   - 驗證錯誤訊息的顯示
   - 確認表單提交的流程

## 未來擴展

1. **報工類型統計**
   - 新增報工類型的統計報表
   - 提供不同模式的效率分析

2. **RD樣品管理**
   - 擴展RD樣品的專案管理功能
   - 增加樣品追蹤功能

3. **審核流程優化**
   - 針對不同報工類型設定不同的審核規則
   - 提供更靈活的審核流程

---

**實現完成時間**：2025-07-22  
**版本**：v2.0  
**狀態**：已完成並測試通過 