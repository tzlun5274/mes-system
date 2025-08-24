# 已完工工單報表功能說明

## 功能概述

已完工工單報表是MES系統中的重要報表功能，提供已完工工單的統計分析、趨勢圖表和公司分布等資訊。

## 主要功能

### 1. 統計摘要
- 完工工單數量統計
- 完成數量統計
- 平均完工率
- 平均不良率
- 總工作時數
- 平均時產出

### 2. 圖表視覺化
- **完工工單趨勢圖**：顯示最近30天的完工工單數量和完成數量趨勢
- **公司完工分布圖**：顯示各公司的完工工單分布情況

### 3. 快速操作
- **報表列表**：查看所有已完工工單報表
- **匯出報表**：匯出已完工工單報表
- **同步資料**：手動同步已完工工單資料

## 技術架構

### 資料模型
- `CompletedWorkOrderReportData`：已完工工單報表資料模型
- `CompletedWorkOrder`：已完工工單模型

### 服務類別
- `CompletedWorkOrderReportService`：提供報表資料查詢和統計功能

### 主要方法
- `get_completed_workorder_summary()`：取得統計摘要
- `get_completed_workorder_trend()`：取得趨勢資料
- `get_company_completion_distribution()`：取得公司分布資料
- `sync_completed_workorder_data()`：同步已完工工單資料

## 自動化機制

### 1. 自動生成報表資料
當工單完工時，系統會自動：
1. 執行完工流程
2. 轉移工單到已完工模組
3. 自動生成報表資料

### 2. 手動同步
- 透過網頁介面的「同步資料」按鈕
- 使用管理命令：`python manage.py sync_completed_workorder_reports`

## 使用方式

### 1. 查看報表
訪問：`/reporting/completed-workorder/`

### 2. 查看報表列表
訪問：`/reporting/completed-workorder/list/`

### 3. 手動同步資料
- 在報表頁面點擊「立即同步」按鈕
- 或使用管理命令

### 4. 匯出報表
在報表列表頁面可以匯出Excel格式的報表

## 資料來源

報表資料來源於：
1. 已完工工單（`CompletedWorkOrder`）
2. 已完工生產報工記錄（`CompletedProductionReport`）
3. 已完工工單工序記錄（`CompletedWorkOrderProcess`）

## 注意事項

1. **資料同步**：報表資料需要從已完工工單資料同步生成
2. **自動化**：新的已完工工單會自動生成報表資料
3. **手動同步**：如果發現資料不一致，可以手動執行同步
4. **公司分離**：報表資料會按公司代號進行分離

## 故障排除

### 問題：報表顯示無資料
**解決方案**：
1. 檢查是否有已完工工單
2. 執行同步：`python manage.py sync_completed_workorder_reports`
3. 檢查報表資料表是否有資料

### 問題：圖表無法顯示
**解決方案**：
1. 檢查瀏覽器控制台是否有JavaScript錯誤
2. 確認Chart.js函式庫已正確載入
3. 檢查API端點是否正常回應

### 問題：同步失敗
**解決方案**：
1. 檢查日誌檔案中的錯誤訊息
2. 確認資料庫連線正常
3. 檢查已完工工單資料是否完整

## 相關檔案

- `reporting/models.py`：資料模型定義
- `reporting/services.py`：服務類別
- `reporting/views.py`：視圖函數
- `reporting/templates/reporting/completed_workorder_report.html`：報表模板
- `reporting/management/commands/sync_completed_workorder_reports.py`：同步命令
