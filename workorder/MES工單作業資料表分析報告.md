# MES 工單作業資料表分析報告

## 📋 總覽

根據工單管理規範和實際資料庫檢查，MES 工單作業系統目前共有 **37個資料表**，其中包含 **15個多餘的資料表**。

## 🏗️ 標準資料表清單（22個）

### 1. 工單管理主模組 (workorder) - 9個資料表
- ✅ `workorder_workorder` - 工單主表（統一資料來源）
- ✅ `workorder_workorderprocess` - 工單工序明細
- ✅ `workorder_workorderprocesslog` - 工單工序日誌
- ✅ `workorder_assignment` - 工單分配
- ✅ `workorder_process_capacity` - 工序產能設定
- ✅ `workorder_production` - 生產中工單
- ✅ `workorder_production_detail` - 生產報工明細
- ✅ `workorder_auto_management_config` - 自動管理配置
- ✅ `workorder_consistency_check_result` - 一致性檢查結果

### 2. 公司製令單子模組 (workorder_erp) - 4個資料表
- ✅ `workorder_erp_companyorder` - 公司製令單
- ✅ `workorder_erp_prdmkordmain` - ERP製令主檔
- ✅ `workorder_erp_prdmkordmats` - ERP製令明細
- ✅ `workorder_erp_systemconfig` - ERP系統配置

### 3. MES工單作業子模組 (mes_workorder_operation) - 3個資料表
- ✅ `mes_workorder_operation` - MES工單作業主表
- ✅ `mes_workorder_operation_detail` - MES工單作業明細
- ✅ `mes_workorder_operation_history` - MES工單作業歷史

### 4. 派工單子模組 (workorder_dispatch) - 3個資料表
- ✅ `workorder_dispatch` - 派工單主表
- ✅ `workorder_dispatch_process` - 派工單工序
- ✅ `workorder_dispatch_history` - 派工歷史記錄

### 5. 填報作業子模組 (workorder_fill_work) - 1個資料表
- ✅ `workorder_fill_work` - 填報作業

### 6. 已完工工單子模組 (workorder_completed_workorder) - 5個資料表
- ✅ `workorder_completed_workorder` - 已完工工單
- ✅ `workorder_completed_workorder_process` - 已完工工單工序
- ✅ `workorder_completed_production_report` - 已完工生產報表
- ✅ `workorder_auto_allocation_settings` - 自動分配設定
- ✅ `workorder_auto_allocation_log` - 自動分配日誌

### 7. 現場報工子模組 (workorder_onsite_report) - 4個資料表
- ✅ `workorder_onsite_report` - 現場報工記錄
- ✅ `workorder_onsite_report_session` - 現場報工工作時段
- ✅ `workorder_onsite_report_history` - 現場報工歷史記錄
- ✅ `workorder_onsite_report_config` - 現場報工配置

## ❌ 多餘資料表清單（15個）

### 1. 重複的 ERP 相關資料表（6個）
這些資料表與 `workorder_erp` 子模組的資料表完全相同，屬於重複建立：

- ❌ `workorder_companyorder_companyorder` - 重複：與 `workorder_erp_companyorder` 相同
- ❌ `workorder_companyorder_prdmkordmain` - 重複：與 `workorder_erp_prdmkordmain` 相同
- ❌ `workorder_companyorder_prdmkordmats` - 重複：與 `workorder_erp_prdmkordmats` 相同
- ❌ `workorder_companyorder_systemconfig` - 重複：與 `workorder_erp_systemconfig` 相同
- ❌ `workorder_prdmkordmain` - 重複：與 `workorder_erp_prdmkordmain` 相同
- ❌ `workorder_prdmkordmats` - 重複：與 `workorder_erp_prdmkordmats` 相同

### 2. 舊版工單資料表（2個）
這些是舊版本的工單資料表，已被新版取代：

- ❌ `work_order_workorder` - 舊版：只有2個欄位，已被 `workorder_workorder` 取代
- ❌ `work_order_workorderoperationlog` - 舊版：只有4個欄位，已被 `workorder_workorderprocesslog` 取代

### 3. 備份和臨時資料表（3個）
這些是備份或臨時用途的資料表：

- ❌ `backup_workorder_operator_realtime_report` - 備份：作業員即時報表備份
- ❌ `workorder_統一報工記錄` - 臨時：統一報工記錄（中文命名）
- ❌ `workorder_report_data` - 臨時：報表資料（功能重複）

### 4. 班次和排程資料表（2個）
這些資料表不屬於工單管理核心功能：

- ❌ `workorder_shift` - 班次管理：屬於人事管理範疇
- ❌ `workorder_workschedule` - 工作排程：屬於排程管理範疇

### 5. 系統配置重複（2個）
這些是重複的系統配置資料表：

- ❌ `workorder_systemconfig` - 重複：與 `workorder_erp_systemconfig` 相同

## 🔍 詳細分析

### 重複資料表分析

#### 1. ERP 相關重複資料表
所有重複的 ERP 資料表都具有完全相同的欄位結構：

**PrdMKOrdMain 系列（3個重複）：**
- `workorder_erp_prdmkordmain` ✅（標準）
- `workorder_companyorder_prdmkordmain` ❌（重複）
- `workorder_prdmkordmain` ❌（重複）

**PrdMkOrdMats 系列（3個重複）：**
- `workorder_erp_prdmkordmats` ✅（標準）
- `workorder_companyorder_prdmkordmats` ❌（重複）
- `workorder_prdmkordmats` ❌（重複）

**SystemConfig 系列（3個重複）：**
- `workorder_erp_systemconfig` ✅（標準）
- `workorder_companyorder_systemconfig` ❌（重複）
- `workorder_systemconfig` ❌（重複）

**CompanyOrder 系列（2個重複）：**
- `workorder_erp_companyorder` ✅（標準）
- `workorder_companyorder_companyorder` ❌（重複）

#### 2. 舊版工單資料表
- `work_order_workorder`：只有 `id` 和 `name` 欄位，功能過於簡單
- `work_order_workorderoperationlog`：只有基本日誌欄位，功能不完整

#### 3. 備份和臨時資料表
- `backup_workorder_operator_realtime_report`：明顯是備份用途
- `workorder_統一報工記錄`：使用中文命名，不符合命名規範
- `workorder_report_data`：功能與其他報表資料表重複

## 📊 統計摘要

| 類別 | 標準資料表 | 多餘資料表 | 總計 |
|------|------------|------------|------|
| 工單管理主模組 | 9 | 0 | 9 |
| 公司製令單子模組 | 4 | 6 | 10 |
| MES工單作業子模組 | 3 | 0 | 3 |
| 派工單子模組 | 3 | 0 | 3 |
| 填報作業子模組 | 1 | 0 | 1 |
| 已完工工單子模組 | 5 | 0 | 5 |
| 現場報工子模組 | 4 | 0 | 4 |
| 其他/備份 | 0 | 9 | 9 |
| **總計** | **29** | **15** | **44** |

## 🚨 建議清理行動

### 立即清理（高優先級）
1. **刪除重複的 ERP 資料表**（6個）
   - `workorder_companyorder_*` 系列
   - `workorder_prdmkord*` 系列
   - `workorder_systemconfig`

2. **刪除舊版工單資料表**（2個）
   - `work_order_workorder`
   - `work_order_workorderoperationlog`

### 評估清理（中優先級）
3. **評估備份資料表**（3個）
   - `backup_workorder_operator_realtime_report`
   - `workorder_統一報工記錄`
   - `workorder_report_data`

### 重新分類（低優先級）
4. **重新分類非核心資料表**（2個）
   - `workorder_shift` → 人事管理模組
   - `workorder_workschedule` → 排程管理模組

## ⚠️ 注意事項

### 清理前準備
1. **資料備份**：清理前必須完整備份所有資料
2. **依賴檢查**：檢查是否有其他模組依賴這些資料表
3. **程式碼更新**：更新所有相關的程式碼引用
4. **測試驗證**：清理後進行完整的功能測試

### 清理順序
1. 先清理重複的 ERP 資料表
2. 再清理舊版工單資料表
3. 最後評估備份和臨時資料表

### 風險控制
1. **分批清理**：不要一次性刪除所有多餘資料表
2. **回滾準備**：準備資料恢復方案
3. **監控系統**：清理後密切監控系統運作狀況

## 📝 結論

MES 工單作業系統目前有 **15個多餘的資料表**，主要問題是：

1. **重複建立**：ERP 相關資料表重複建立了6個
2. **版本混亂**：存在舊版和新版工單資料表
3. **命名不規範**：存在中文命名的資料表
4. **功能重疊**：部分資料表功能重複

建議按照優先級逐步清理這些多餘資料表，以提升系統的維護性和效能。 