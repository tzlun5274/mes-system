# 派工單管理模組

## 概述

派工單管理模組是 MES 系統的核心組件之一，負責管理工單的派工流程。本模組提供完整的派工單生命週期管理，從建立、派工到完工的全程追蹤。

## 功能特色

### 1. 完整的 CRUD 操作
- **新增派工單**：支援手動建立和批量建立
- **編輯派工單**：修改派工資訊和狀態
- **查看詳情**：完整的派工單資訊展示
- **刪除派工單**：安全的刪除確認機制

### 2. 智能搜尋與篩選
- **多欄位搜尋**：工單號、產品編號、公司代號、作業員、工序名稱
- **狀態篩選**：待派工、已派工、生產中、已完工、已取消
- **日期範圍篩選**：按建立日期或派工日期篩選
- **公司代號篩選**：按公司別篩選

### 3. 批量操作
- **批量派工**：一次為多個工單建立派工單
- **批量匯出**：支援 CSV 格式匯出
- **批量狀態更新**：透過 AJAX 快速更新狀態

### 4. 歷史追蹤
- **操作歷史**：記錄所有派工單的操作記錄
- **狀態變更追蹤**：詳細記錄狀態變更歷史
- **審計日誌**：完整的操作人員和時間記錄

### 5. 資料驗證
- **工單存在性驗證**：確保派工單對應的工單存在
- **日期邏輯驗證**：計劃開始日期不能晚於完成日期
- **數量驗證**：計劃數量必須大於 0

## 資料模型

### WorkOrderDispatch（派工單主表）
```python
- id: 主鍵
- company_code: 公司代號
- order_number: 工單號碼（必填，索引）
- product_code: 產品編號（必填，索引）
- product_name: 產品名稱
- planned_quantity: 計劃數量（必填）
- status: 派工狀態（待派工/已派工/生產中/已完工/已取消）
- dispatch_date: 派工日期
- planned_start_date: 計劃開始日期
- planned_end_date: 計劃完成日期
- assigned_operator: 分配作業員
- assigned_equipment: 分配設備
- process_name: 工序名稱
- notes: 備註
- created_at: 建立時間
- updated_at: 更新時間
- created_by: 建立人員
```

### WorkOrderDispatchProcess（派工單工序明細）
```python
- id: 主鍵
- workorder_dispatch: 關聯派工單
- process_name: 工序名稱
- step_order: 工序順序
- planned_quantity: 計劃數量
- assigned_operator: 分配作業員
- assigned_equipment: 分配設備
- dispatch_status: 派工狀態
- created_at: 建立時間
- updated_at: 更新時間
```

### DispatchHistory（派工歷史記錄）
```python
- id: 主鍵
- workorder_dispatch: 關聯派工單
- action: 操作類型
- old_status: 原狀態
- new_status: 新狀態
- operator: 操作人員
- notes: 備註
- created_at: 操作時間
```

## 主要視圖

### 1. DispatchListView
- **功能**：派工單列表顯示
- **特色**：支援搜尋、篩選、分頁
- **URL**：`/workorder/dispatch/`

### 2. DispatchCreateView
- **功能**：新增派工單
- **特色**：工單查詢自動填入、表單驗證
- **URL**：`/workorder/dispatch/add/`

### 3. DispatchUpdateView
- **功能**：編輯派工單
- **特色**：狀態變更歷史記錄
- **URL**：`/workorder/dispatch/edit/<id>/`

### 4. DispatchDetailView
- **功能**：派工單詳情
- **特色**：完整資訊展示、相關工單連結
- **URL**：`/workorder/dispatch/detail/<id>/`

### 5. DispatchDeleteView
- **功能**：刪除派工單
- **特色**：安全確認機制
- **URL**：`/workorder/dispatch/delete/<id>/`

## API 端點

### 1. 工單資訊查詢
- **URL**：`/workorder/dispatch/api/work-order-info/`
- **方法**：GET
- **參數**：`order_number`
- **功能**：根據工單號碼查詢工單資訊

### 2. 狀態更新
- **URL**：`/workorder/dispatch/api/update-status/<id>/`
- **方法**：POST
- **參數**：`status`
- **功能**：更新派工單狀態

### 3. 批量派工
- **URL**：`/workorder/dispatch/bulk/`
- **方法**：POST
- **功能**：批量建立派工單

### 4. 資料匯出
- **URL**：`/workorder/dispatch/export/`
- **方法**：GET
- **功能**：匯出派工單資料為 CSV

## 表單

### 1. WorkOrderDispatchForm
- **用途**：新增和編輯派工單
- **特色**：完整的欄位驗證、工單查詢功能

### 2. BulkDispatchForm
- **用途**：批量派工
- **特色**：工單號碼列表驗證

### 3. DispatchSearchForm
- **用途**：搜尋和篩選
- **特色**：多條件組合搜尋

## 使用方式

### 1. 建立派工單
1. 進入派工單管理頁面
2. 點擊「新增派工單」
3. 輸入工單號碼或使用查詢功能
4. 填寫派工資訊
5. 儲存派工單

### 2. 批量派工
1. 點擊「批量派工」
2. 輸入工單號碼列表（每行一個）
3. 設定派工資訊
4. 系統自動驗證並建立派工單

### 3. 搜尋派工單
1. 使用搜尋欄位輸入關鍵字
2. 選擇狀態篩選
3. 設定日期範圍
4. 點擊查詢

### 4. 匯出資料
1. 設定搜尋條件
2. 點擊「匯出」按鈕
3. 下載 CSV 檔案

## 技術特色

### 1. 資料庫優化
- 建立適當的索引提升查詢效能
- 使用外鍵關聯確保資料完整性
- 支援軟刪除和歷史記錄

### 2. 前端互動
- AJAX 非同步操作
- 即時表單驗證
- 響應式設計

### 3. 安全性
- CSRF 保護
- 權限驗證
- 輸入驗證和清理

### 4. 可擴展性
- 模組化設計
- 清晰的 API 介面
- 完整的錯誤處理

## 注意事項

1. **工單關聯**：派工單必須對應到存在的工單
2. **狀態管理**：狀態變更會記錄歷史
3. **資料完整性**：刪除操作會影響相關記錄
4. **權限控制**：需要適當的用戶權限

## 未來擴展

1. **工作流程**：支援自定義派工流程
2. **通知系統**：狀態變更通知
3. **報表功能**：派工統計報表
4. **行動裝置**：支援行動裝置操作 