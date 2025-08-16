# 作業員RD樣品現場報工功能說明

## 📋 功能概述

「新增作業員RD樣品現場報工」是MES系統中專門用於研發樣品現場報工記錄的功能模組。此功能提供即時報工模式，以當下報工狀態為時間戳，支援完整的報工流程管理。

## 🏗️ 功能架構

### 核心組件
- **後端視圖**：`operator_rd_onsite_report_create` (views.py)
- **前端模板**：`operator_rd_onsite_report_form.html`
- **資料模型**：`OnsiteReport` (models.py)
- **URL路由**：`/workorder/onsite_reporting/create/operator-rd/`

### 報工流程
```
開工 → 暫停 → 重啟開工 → 完工
每筆記錄代表一次完整的工作時段
```

## 📝 表單欄位設計

### 基本資訊欄位
1. **產品編號** (product_code)
   - 固定值：`PFP-CCT`
   - 唯讀欄位
   - 說明：RD樣品固定產品編號

2. **工單號碼** (order_number)
   - 固定值：`RD樣品`
   - 唯讀欄位
   - 說明：RD樣品固定工單號碼

3. **公司名稱** (company_code)
   - 下拉式選單
   - 必填欄位
   - 來源：`CompanyConfig` 模型

4. **作業員** (operator)
   - 下拉式選單
   - 必填欄位
   - 過濾：排除包含"SMT"的作業員
   - 來源：`Operator` 模型

5. **工序** (process)
   - 下拉式選單
   - 必填欄位
   - 過濾：排除包含"SMT"的工序
   - 來源：`ProcessName` 模型

6. **使用的設備** (equipment)
   - 下拉式選單
   - 可選欄位
   - 過濾：排除包含"SMT"的設備
   - 來源：`Equipment` 模型

### 報工資訊欄位
7. **報工狀態** (status)
   - 下拉式選單
   - 必填欄位
   - 選項：開工、暫停、重啟開工、完工、停工

8. **預設生產數量** (planned_quantity)
   - 固定值：`0`
   - 唯讀欄位
   - 說明：RD樣品無預設生產數量

### 數量資訊欄位
9. **工作數量** (work_quantity)
   - 數字輸入
   - 可選欄位
   - 最小值：0
   - 說明：該時段內實際完成的RD樣品數量

10. **不良品數量** (defect_quantity)
    - 數字輸入
    - 可選欄位
    - 最小值：0
    - 說明：本次RD樣品作業中產生的不良品數量

### 備註資訊欄位
11. **備註** (remarks)
    - 文字區域
    - 可選欄位
    - 說明：RD樣品作業的相關備註，如實驗目的、特殊要求等

12. **異常記錄** (abnormal_notes)
    - 文字區域
    - 可選欄位
    - 說明：記錄RD樣品作業過程中的異常情況，如設備故障、實驗問題等

## 🔧 JavaScript 功能

### 表單驗證
```javascript
function validateForm() {
    let errorMessages = [];
    
    // 檢查必填欄位
    const requiredFields = [
        { id: 'company_code', name: '公司名稱' },
        { id: 'operator', name: '作業員' },
        { id: 'process', name: '工序' },
        { id: 'status', name: '報工狀態' }
    ];
    
    for (let field of requiredFields) {
        const value = $(`#${field.id}`).val();
        if (!value || value === '') {
            errorMessages.push(`• ${field.name} 為必填欄位`);
        }
    }
    
    // 驗證數量欄位
    const workQuantity = parseInt($('#work_quantity').val());
    if (isNaN(workQuantity) || workQuantity < 0) {
        errorMessages.push('• 工作數量 不能為負數');
    }
    
    const defectQuantity = parseInt($('#defect_quantity').val()) || 0;
    if (defectQuantity < 0) {
        errorMessages.push('• 不良品數量 不能為負數');
    }
    
    return errorMessages.length === 0;
}
```

### 載入指示器
```javascript
function showLoading() {
    $('#loadingIndicator').show();
}

function hideLoading() {
    $('#loadingIndicator').hide();
}
```

## 🎨 前端設計特色

### 視覺設計
- **主題色彩**：警告色系（黃色/橙色）
- **圖示**：使用 Font Awesome 圖示
- **響應式設計**：支援各種螢幕尺寸
- **載入指示器**：提交時顯示載入動畫

### 使用者體驗
- **即時驗證**：表單提交前進行完整驗證
- **錯誤提示**：詳細的錯誤訊息顯示
- **成功跳轉**：成功提交後自動跳轉到列表頁面
- **返回按鈕**：提供返回列表的便捷操作

## 🔄 後端處理邏輯

### 資料驗證
1. **必填欄位檢查**：作業員、工序、報工狀態
2. **資料型態驗證**：數量欄位必須為非負整數
3. **業務邏輯驗證**：確保資料符合RD樣品報工規範

### 工單管理
1. **自動建立工單**：如果沒有RD樣品工單，自動建立
2. **工單關聯**：將報工記錄關聯到RD樣品工單
3. **數量管理**：RD樣品無預設生產數量

### 資料儲存
1. **事務處理**：使用資料庫事務確保資料一致性
2. **時間戳記**：自動記錄建立時間和開始時間
3. **使用者追蹤**：記錄建立人員資訊

## 📊 資料過濾邏輯

### 作業員過濾
```python
operators = Operator.objects.filter(
    ~Q(name__icontains='SMT')
).values_list('name', flat=True).distinct()
```

### 工序過濾
```python
processes = ProcessName.objects.filter(
    ~Q(name__icontains='SMT')
).values_list('name', flat=True).distinct()
```

### 設備過濾
```python
equipments = Equipment.objects.filter(
    ~Q(name__icontains='SMT')
).values_list('name', flat=True).distinct()
```

## 🚀 使用方式

### 1. 進入功能
- 導航到：現場報工 → 作業員RD樣品現場報工

### 2. 填寫表單
- 選擇公司名稱
- 選擇作業員（已過濾非SMT）
- 選擇工序（已過濾非SMT）
- 選擇設備（可選，已過濾非SMT）
- 選擇報工狀態
- 填寫數量資訊（如需要）
- 填寫備註資訊（如需要）

### 3. 提交表單
- 點擊「儲存RD樣品報工記錄」按鈕
- 系統會進行表單驗證
- 驗證通過後儲存資料並跳轉到列表頁面

## ✅ 功能特色

1. **專用設計**：專門為RD樣品報工設計，符合研發需求
2. **即時報工**：支援現場即時報工模式
3. **狀態管理**：完整的報工狀態流程管理
4. **資料過濾**：自動過濾SMT相關項目
5. **自動化**：自動建立工單和關聯資料
6. **使用者友善**：直觀的介面設計和即時驗證
7. **資料完整性**：完整的資料驗證和錯誤處理

## 🔗 相關功能

- **現場報工列表**：查看所有現場報工記錄
- **現場報工監控**：即時監控報工狀態
- **現場報工配置**：管理報工相關設定
- **RD樣品工單管理**：管理RD樣品相關工單

此功能已完全按照設計規範實作，提供完整的RD樣品現場報工解決方案。 