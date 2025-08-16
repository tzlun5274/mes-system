# 作業員、工序、設備統一管理模組使用說明

## 概述

`OperatorProcessEquipmentController` 是一個統一的JavaScript模組，用於處理所有填報表單中的作業員、工序、設備選擇功能。這個模組可以自動根據表單類型（作業員或SMT）來過濾相應的選項，並提供設備自動填入作業員的功能。

## 功能特性

### 1. 自動過濾功能
- **SMT表單**：只顯示包含"SMT"的工序和設備
- **作業員表單**：排除包含"SMT"的工序和設備

### 2. 設備自動填入功能
- **SMT表單**：選擇設備時自動填入作業員欄位為設備名稱
- **作業員表單**：不啟用此功能

### 3. 統一的API介面
- 使用相同的API端點載入資料
- 支援自定義API前綴

## 使用方法

### 基本用法

```javascript
// 初始化統一的作業員、工序、設備控制器
window.operatorProcessEquipmentController = new OperatorProcessEquipmentController({
    formType: 'smt',                    // 表單類型：'smt' 或 'operator'
    enableEquipmentAutoFill: true,      // 是否啟用設備自動填入作業員功能
    apiPrefix: '/workorder/onsite_reporting/api',  // API端點前綴
    operatorId: 'operator',             // 作業員下拉選單的ID
    processId: 'process',               // 工序下拉選單的ID
    equipmentId: 'equipment'            // 設備下拉選單的ID
});
```

### SMT表單配置

```javascript
// SMT補登填報表單
window.operatorProcessEquipmentController = new OperatorProcessEquipmentController({
    formType: 'smt',
    enableEquipmentAutoFill: true,
    apiPrefix: '/workorder/onsite_reporting/api',
    operatorId: 'operator',
    processId: 'process',
    equipmentId: 'equipment'
});

// SMT現場報工表單
window.operatorProcessEquipmentController = new OperatorProcessEquipmentController({
    formType: 'smt',
    enableEquipmentAutoFill: true,
    apiPrefix: '/workorder/onsite_reporting/api',
    operatorId: 'operator',
    processId: 'process',
    equipmentId: 'equipment'
});
```

### 作業員表單配置

```javascript
// 作業員補登填報表單
window.operatorProcessEquipmentController = new OperatorProcessEquipmentController({
    formType: 'operator',
    enableEquipmentAutoFill: false,
    apiPrefix: '/workorder/onsite_reporting/api',
    operatorId: 'operator',
    processId: 'process',
    equipmentId: 'equipment'
});

// 作業員現場報工表單
window.operatorProcessEquipmentController = new OperatorProcessEquipmentController({
    formType: 'operator',
    enableEquipmentAutoFill: false,
    apiPrefix: '/workorder/onsite_reporting/api',
    operatorId: 'operator',
    processId: 'process',
    equipmentId: 'equipment'
});
```

## 配置選項

### formType
- **類型**：`string`
- **預設值**：`'operator'`
- **說明**：表單類型，決定過濾邏輯
  - `'smt'`：只顯示包含"SMT"的工序和設備
  - `'operator'`：排除包含"SMT"的工序和設備

### enableEquipmentAutoFill
- **類型**：`boolean`
- **預設值**：`false`
- **說明**：是否啟用設備自動填入作業員功能
  - `true`：選擇設備時自動填入作業員欄位
  - `false`：不啟用自動填入功能

### apiPrefix
- **類型**：`string`
- **預設值**：`'/workorder/onsite_reporting/api'`
- **說明**：API端點前綴，用於載入作業員、工序、設備資料

### operatorId
- **類型**：`string`
- **預設值**：`'operator'`
- **說明**：作業員下拉選單的DOM元素ID

### processId
- **類型**：`string`
- **預設值**：`'process'`
- **說明**：工序下拉選單的DOM元素ID

### equipmentId
- **類型**：`string`
- **預設值**：`'equipment'`
- **說明**：設備下拉選單的DOM元素ID

## 方法

### loadInitialData()
載入初始資料，包括作業員、工序、設備選項。

### loadOperators()
載入作業員選項。

### loadProcesses()
根據表單類型載入並過濾工序選項。

### loadEquipment()
根據表單類型載入並過濾設備選項。

### handleEquipmentChange()
處理設備變更事件（SMT專用）。

### resetAllOptions()
重置所有選項到初始狀態。

### getSelectedValues()
取得當前選中的值。

```javascript
const values = controller.getSelectedValues();
console.log(values);
// 輸出：{ operator: '作業員A', process: 'SMT貼片', equipment: 'SMT-01' }
```

### setValues(values)
設定選項的值。

```javascript
controller.setValues({
    operator: '作業員A',
    process: 'SMT貼片',
    equipment: 'SMT-01'
});
```

## 全域函數

### resetOperatorProcessEquipmentForm()
重置作業員、工序、設備表單。

```javascript
// 按F5時重置表單
window.resetOperatorProcessEquipmentForm = function() {
    if (window.operatorProcessEquipmentController) {
        window.operatorProcessEquipmentController.resetAllOptions();
    }
};
```

## 注意事項

1. **HTML結構**：確保表單中有對應ID的下拉選單元素
2. **API端點**：確保API端點能正常回應作業員、工序、設備資料
3. **全域變數**：控制器實例會儲存在 `window.operatorProcessEquipmentController` 中
4. **相容性**：與現有的 `FillWorkController` 完全相容

## 範例

### 完整的表單初始化

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // 初始化統一的填報控制器（處理產品編號、工單號碼、公司名稱）
    new FillWorkController();
    
    // 初始化統一的作業員、工序、設備控制器
    window.operatorProcessEquipmentController = new OperatorProcessEquipmentController({
        formType: 'smt',
        enableEquipmentAutoFill: true,
        apiPrefix: '/workorder/onsite_reporting/api',
        operatorId: 'operator',
        processId: 'process',
        equipmentId: 'equipment'
    });
    
    console.log('表單初始化完成');
});
```

這個統一的JS模組可以大大簡化填報表單的開發和維護工作，確保所有表單都有一致的行為和功能。 