# MES 工單作業子模組

## 📋 概述

MES 工單作業子模組是 MES 系統的核心組件之一，專門負責管理 MES 工單的作業流程。本模組提供完整的作業生命週期管理，從作業建立、執行到完成的全程追蹤。

## 🏗️ 功能特色

### 1. 完整的作業管理
- **作業建立**：支援手動建立和自動建立作業
- **作業執行**：追蹤作業的執行狀態和進度
- **作業完成**：自動計算完成率和剩餘數量
- **作業歷史**：完整的作業變更歷史記錄

### 2. 多公司架構支援
- **公司隔離**：不同公司的作業資料完全隔離
- **唯一識別**：公司代號 + 工單號碼 + 產品編號 + 作業名稱
- **資料安全**：確保跨公司資料不會混淆

### 3. 智能狀態管理
- **自動狀態更新**：根據完成數量自動更新作業狀態
- **時間追蹤**：自動記錄開始時間和完成時間
- **完成率計算**：實時計算作業完成率

### 4. 詳細作業明細
- **明細管理**：支援多種明細類型（工序、物料、設備、品質等）
- **進度追蹤**：每個明細項目的完成情況
- **時長計算**：自動計算作業時長

### 5. 完整的歷史記錄
- **變更追蹤**：記錄所有作業變更的歷史
- **操作審計**：記錄操作者和操作時間
- **變更對比**：支援變更前後值的對比

## 📊 資料模型

### 1. MesWorkorderOperation（作業主表）
```python
- id: 主鍵
- company_code: 公司代號
- company_name: 公司名稱
- workorder_number: 工單號碼
- product_code: 產品編號
- product_name: 產品名稱
- operation_type: 作業類型（生產、檢驗、包裝、維護、其他）
- operation_name: 作業名稱
- status: 作業狀態（待作業、作業中、暫停、已完成、已取消）
- planned_quantity: 計劃數量
- completed_quantity: 完成數量
- defect_quantity: 不良品數量
- planned_start_date: 計劃開始日期
- planned_end_date: 計劃完成日期
- actual_start_date: 實際開始時間
- actual_end_date: 實際完成時間
- assigned_operator: 分配作業員
- assigned_equipment: 分配設備
- notes: 備註
- created_at: 建立時間
- updated_at: 更新時間
- created_by: 建立者
- updated_by: 更新者
```

### 2. MesWorkorderOperationDetail（作業明細）
```python
- id: 主鍵
- operation: 關聯作業主表
- detail_type: 明細類型（工序、物料、設備、品質、其他）
- detail_name: 明細名稱
- detail_description: 明細說明
- planned_quantity: 計劃數量
- actual_quantity: 實際數量
- start_time: 開始時間
- end_time: 結束時間
- is_completed: 是否完成
- completion_rate: 完成率
- notes: 備註
- created_at: 建立時間
- updated_at: 更新時間
```

### 3. MesWorkorderOperationHistory（作業歷史）
```python
- id: 主鍵
- operation: 關聯作業主表
- history_type: 歷史類型（建立、更新、開始、暫停、重啟、完成、取消、刪除）
- history_description: 歷史說明
- old_values: 變更前值（JSON格式）
- new_values: 變更後值（JSON格式）
- operator: 操作者
- ip_address: IP位址
- created_at: 建立時間
```

## 🔧 服務層功能

### 1. MesWorkorderOperationService
- `create_operation()`: 建立作業
- `get_operation_by_id()`: 根據ID取得作業
- `get_operations_by_workorder()`: 根據工單取得作業
- `search_operations()`: 搜尋作業
- `update_operation_status()`: 更新作業狀態
- `bulk_update_status()`: 批量更新狀態
- `get_operation_statistics()`: 取得統計資訊

### 2. MesWorkorderOperationDetailService
- `create_detail()`: 建立明細
- `update_detail_completion()`: 更新明細完成情況
- `get_operation_details()`: 取得作業明細

### 3. MesWorkorderOperationHistoryService
- `get_operation_history()`: 取得作業歷史
- `get_recent_activities()`: 取得最近活動

## 📝 使用範例

### 建立作業
```python
from workorder.mes_workorder_operation.services import MesWorkorderOperationService

# 建立新作業
operation = MesWorkorderOperationService.create_operation(
    company_code='01',
    workorder_number='WO-2025-001',
    product_code='PROD-001',
    operation_name='組裝作業',
    operation_type='production',
    planned_quantity=100,
    assigned_operator='張三',
    assigned_equipment='組裝線A'
)
```

### 更新作業狀態
```python
# 開始作業
operation = MesWorkorderOperationService.update_operation_status(
    operation_id=1,
    new_status='in_progress',
    operator='李四'
)

# 完成作業
operation = MesWorkorderOperationService.update_operation_status(
    operation_id=1,
    new_status='completed',
    operator='李四'
)
```

### 搜尋作業
```python
# 搜尋特定公司的作業
filters = {
    'company_code': '01',
    'status': 'in_progress',
    'date_from': '2025-01-01'
}
operations = MesWorkorderOperationService.search_operations(filters)
```

## 🔗 與其他模組的整合

### 1. 與工單管理模組整合
- 從工單管理模組取得工單資訊
- 自動建立對應的作業記錄
- 同步工單狀態和作業狀態

### 2. 與派工單模組整合
- 派工單完成後自動建立作業
- 作業進度影響派工單狀態
- 共享作業員和設備資訊

### 3. 與填報管理模組整合
- 填報記錄影響作業進度
- 作業完成率影響填報統計
- 共享完成數量資訊

## ⚙️ 配置說明

### 1. 作業類型配置
```python
OPERATION_TYPE_CHOICES = [
    ('production', '生產作業'),
    ('inspection', '檢驗作業'),
    ('packaging', '包裝作業'),
    ('maintenance', '維護作業'),
    ('other', '其他作業'),
]
```

### 2. 作業狀態配置
```python
STATUS_CHOICES = [
    ('pending', '待作業'),
    ('in_progress', '作業中'),
    ('paused', '暫停'),
    ('completed', '已完成'),
    ('cancelled', '已取消'),
]
```

### 3. 明細類型配置
```python
DETAIL_TYPE_CHOICES = [
    ('process', '工序'),
    ('material', '物料'),
    ('equipment', '設備'),
    ('quality', '品質'),
    ('other', '其他'),
]
```

## 📈 統計功能

### 1. 作業統計
- 總作業數量
- 各狀態作業數量
- 平均完成率
- 作業效率分析

### 2. 完成率分析
- 按公司統計完成率
- 按作業類型統計完成率
- 按時間段統計完成率
- 完成率趨勢分析

### 3. 效率分析
- 作業時長統計
- 作業員效率分析
- 設備利用率分析
- 瓶頸工序識別

## 🔒 安全與權限

### 1. 資料隔離
- 公司級別的資料隔離
- 用戶只能查看所屬公司的資料
- 跨公司資料訪問限制

### 2. 操作權限
- 作業建立權限
- 作業修改權限
- 作業刪除權限
- 歷史記錄查看權限

### 3. 審計追蹤
- 所有操作都有歷史記錄
- 操作者身份追蹤
- IP位址記錄
- 變更內容記錄

## 🚀 未來擴展

### 1. 計劃功能
- 作業排程功能
- 資源分配優化
- 預測性維護
- 智能作業建議

### 2. 整合功能
- 與 ERP 系統整合
- 與 WMS 系統整合
- 與 QMS 系統整合
- 與設備監控系統整合

### 3. 分析功能
- 大數據分析
- 機器學習預測
- 效能優化建議
- 異常檢測

## 📞 技術支援

如有任何問題或建議，請聯繫系統管理員或開發團隊。 