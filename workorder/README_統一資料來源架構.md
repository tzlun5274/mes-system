# 工單模組統一資料來源架構

## 📋 概述

本文件定義工單管理模組的統一資料來源架構，確保所有子模組都基於 `workorder_workorder` 主表進行資料管理。

## 🏗️ 統一資料來源

### 核心資料表：workorder_workorder
- **唯一識別**：公司代號 + 工單號碼 + 產品編號
- **資料隔離**：不同公司的資料完全隔離
- **查詢邏輯**：所有工單查詢都必須同時考慮公司代號、工單號碼和產品編號

## 📁 子模組分類與資料表對應

### 1. 公司製令單子模組 (workorder_companyorder)
- `workorder_companyorder` - 公司製令單
- `workorder_companyorder_erp_systemconfig` - 公司製令單ERP系統配置
- `workorder_companyorder_erp_prdmkordmain` - 公司製令單ERP製令主檔
- `workorder_companyorder_erp_prdmkordmats` - 公司製令單ERP製令明細

### 2. MES工單作業子模組 (mes_workorder_operation)
- `mes_workorder_operation` - MES工單作業主表
- `mes_workorder_operation_detail` - MES工單作業明細
- `mes_workorder_operation_history` - MES工單作業歷史

### 3. 派工單子模組 (workorder_dispatch)
- `workorder_dispatch` - 派工單主表
- `workorder_dispatch_process` - 派工單工序
- `workorder_dispatch_history` - 派工歷史記錄

### 4. 填報作業子模組 (workorder_fill_work)
- `workorder_fill_work` - 填報作業

### 5. 已完工工單子模組 (workorder_completed_workorder)
- `workorder_completed_workorder` - 已完工工單
- `workorder_completed_workorder_process` - 已完工工單工序
- `workorder_completed_production_report` - 已完工生產報表
- `workorder_auto_allocation_settings` - 自動分配設定
- `workorder_auto_allocation_log` - 自動分配日誌

### 6. 現場報工子模組 (workorder_onsite_report)
- `workorder_onsite_report` - 現場報工記錄
- `workorder_onsite_report_session` - 現場報工工作時段
- `workorder_onsite_report_history` - 現場報工歷史記錄
- `workorder_onsite_report_config` - 現場報工配置

### 7. 主模組其他資料表
- `workorder_workorder` - 工單主表（統一資料來源）
- `workorder_workorderprocess` - 工單工序明細
- `workorder_workorderprocesslog` - 工單工序日誌
- `workorder_process_capacity` - 工序產能設定
- `workorder_auto_management_config` - 自動管理配置
- `workorder_consistency_check_result` - 一致性檢查結果

## 🔗 資料關聯規則

### 生產監控關聯
1. **工序紀錄來源**：現場報工資料
2. **填報紀錄來源**：填報管理
3. **派工單工序**：與現場報工關聯
4. **工單詳情工序紀錄**：與現場報工關聯
5. **工單詳情填報紀錄**：與填報管理關聯
6. **完工判斷**：以工序紀錄跟填報紀錄合併計算

## 🚫 重複資料表清理

### 需要移除的重複資料表（從主模組 models.py）
1. `DispatchLog` - 重複於 workorder_dispatch 子模組
2. `CompletedWorkOrder` - 應移至 workorder_completed_workorder 子模組
3. `CompletedWorkOrderProcess` - 應移至 workorder_completed_workorder 子模組
4. `CompletedProductionReport` - 應移至 workorder_completed_workorder 子模組
5. `AutoAllocationSettings` - 應移至 workorder_completed_workorder 子模組
6. `AutoAllocationLog` - 應移至 workorder_completed_workorder 子模組

## 📡 統一API端點規範

### API路徑
- 所有工單相關API統一使用 `/var/www/mes/workorder/static/api/` 路徑

### 統一JS模組配置
```javascript
apiPrefix: '/var/www/mes/workorder/static/js/work_common.js'
```

## 🔄 資料同步機制

### 多公司資料隔離
- 所有查詢都必須包含公司代號
- 資料表設計支援多公司架構
- 確保不同公司資料完全隔離

### 唯一性識別
- 格式：公司代號 + 工單號碼 + 產品編號
- 所有相關查詢都必須使用完整識別碼
- 避免跨公司資料混淆

## 📝 實施步驟

1. 清理主模組中的重複資料表
2. 確保子模組資料表正確配置
3. 建立統一API端點
4. 更新JS模組配置
5. 測試資料隔離和唯一性識別
6. 驗證生產監控關聯功能 