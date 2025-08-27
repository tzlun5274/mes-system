# SMT設備報工資料匯出匯入功能說明

## 功能概述

本功能為MES系統新增了SMT設備報工資料的匯出匯入功能，完全參照作業員匯出匯入功能的設計，提供完整的資料處理能力。

## 功能特色

### 1. 完整的匯入功能
- **支援格式**：Excel (.xlsx) 和 CSV 格式
- **欄位驗證**：完整的資料驗證和錯誤處理
- **重複檢查**：自動檢查並跳過重複記錄
- **進度顯示**：即時顯示匯入進度
- **結果回饋**：詳細的成功/錯誤統計

### 2. 完整的匯出功能
- **Excel格式**：標準Excel檔案匯出
- **篩選條件**：支援日期範圍、設備等篩選
- **欄位完整**：包含所有必要欄位

### 3. 範本下載
- **標準範本**：提供標準的Excel匯入範本
- **範例資料**：包含實際範例資料
- **格式說明**：詳細的欄位格式說明

## 欄位格式規範

### 完整欄位清單（按照圖片格式順序）

| 欄位名稱 | 必填 | 資料類型 | 說明 | 範例 | 驗證規則 |
|---------|------|----------|------|------|----------|
| 設備名稱 | ✓ | 文字 | SMT設備的名稱，必須在系統中已存在 | SMT-001 | 不能為空，必須對應到系統中的設備 |
| 公司代號 | ✓ | 文字 | 公司代號，用於識別不同公司的工單 | 01 | 不能為空，必須對應到系統中的公司設定 |
| 報工日期 | ✓ | 日期 | 報工的日期 | 2025-01-15 | 格式：YYYY-MM-DD、YYYY/MM/DD、YYYY.MM.DD |
| 開始時間 | ✓ | 時間 | 報工開始時間 | 08:00 或 0800 | 支援 HH:MM:SS、HH:MM、HHMM、12小時制、Excel時間格式 |
| 結束時間 | ✓ | 時間 | 報工結束時間 | 12:00 或 1200 | 支援 HH:MM:SS、HH:MM、HHMM、12小時制、Excel時間格式 |
| 工單號 | ✓ | 文字 | 工單號碼 | WO-01-202501001 | 不能為空，必須對應到系統中的工單 |
| 產品編號 | ✓ | 文字 | 產品編號 | PROD-001 | 不能為空 |
| 工序名稱 | ✓ | 文字 | 工序名稱 | SMT | 不能為空，通常為SMT相關工序 |
| 空白佔位用 | ✗ | 文字 | 空白欄位，用於格式對齊 | | 可為空 |
| 報工數量 | ✓ | 整數 | 合格品數量 | 100 | 必須為非負整數 |
| 不良品數量 | ✗ | 整數 | 不良品數量（選填） | 2 | 可為空，如果填寫必須為非負整數 |
| 備註 | ✗ | 文字 | 備註說明（選填） | 正常生產 | 可為空，純文字描述 |
| 異常紀錄 | ✗ | 文字 | 異常情況記錄（選填） | 設備故障30分鐘 | 可為空，有內容才會列入異常紀錄 |

## 技術實作

### 1. 檔案結構
```
workorder/
├── views_import.py                    # 匯入匯出功能視圖
├── templates/workorder/import/
│   └── smt_report_import.html         # SMT匯入頁面模板
└── urls.py                           # URL路由配置
```

### 2. 主要功能函數

#### 匯入相關
- `smt_report_import_page()`: 匯入頁面顯示
- `smt_report_import_file()`: 檔案匯入處理
- `download_smt_import_template()`: 下載匯入範本
- `get_smt_import_field_guide()`: 取得欄位說明

#### 匯出相關
- `smt_report_export()`: 匯出SMT報工記錄

### 3. URL路由
```python
# SMT設備報工資料匯入功能
path("import/smt_report/", import_views.smt_report_import_page, name="smt_report_import_page"),
path("import/smt_report/file/", import_views.smt_report_import_file, name="smt_report_import_file"),
path("import/smt_report/template/", import_views.download_smt_import_template, name="download_smt_import_template"),
path("import/smt_report/field_guide/", import_views.get_smt_import_field_guide, name="get_smt_import_field_guide"),
path("import/smt_report/export/", import_views.smt_report_export, name="smt_report_export"),
```

## 使用方式

### 1. 訪問匯入頁面
- 路徑：`/workorder/import/smt_report/`
- 或從SMT補登報工頁面點擊「匯入資料」按鈕

### 2. 匯入資料
1. 點擊「下載匯入範本」取得標準範本
2. 按照範本格式填寫資料
3. 點擊「選擇檔案」或拖拽檔案到上傳區域
4. 系統自動處理並顯示結果

### 3. 匯出資料
1. 從SMT補登報工頁面點擊「匯出資料」按鈕
2. 或直接訪問：`/workorder/import/smt_report/export/`
3. 可選擇性添加篩選參數

## 資料驗證規則

### 1. 必填欄位驗證
- 設備名稱：必須在系統中存在
- 公司代號：必須對應到CompanyConfig
- 工單號：必須在指定公司下存在
- 報工數量：必須為非負整數

### 2. 時間格式支援
- 標準格式：HH:MM:SS、HH:MM
- 數字格式：HHMM
- 12小時制：支援AM/PM
- Excel格式：自動處理Excel時間格式

### 3. 日期格式支援
- YYYY-MM-DD（標準）
- YYYY/MM/DD
- YYYY.MM.DD

## 錯誤處理

### 1. 檔案格式錯誤
- 只支援 .xlsx 和 .csv 格式
- 自動檢測檔案類型

### 2. 欄位驗證錯誤
- 詳細的錯誤訊息
- 顯示具體的行號和錯誤原因
- 支援批次處理，單筆錯誤不影響其他記錄

### 3. 重複記錄處理
- 自動檢查重複記錄
- 跳過重複記錄並記錄統計

## 權限控制

### 1. 存取權限
- 需要登入
- 需要超級用戶權限或「報表使用者」群組權限

### 2. 功能權限
- 匯入功能：需要匯入權限
- 匯出功能：需要匯出權限
- 範本下載：公開存取

## 與作業員匯出匯入功能的差異

### 1. 欄位差異
- 作業員：作業員名稱
- SMT：設備名稱

### 2. 資料模型差異
- 作業員：OperatorSupplementReport
- SMT：SMTProductionReport

### 3. 工時計算差異
- 作業員：考慮休息時間
- SMT：中午不休息，16:30後算加班

## 注意事項

1. **資料完整性**：匯入前請確保所有必填欄位都有正確的資料
2. **格式一致性**：建議使用提供的範本格式
3. **重複檢查**：系統會自動檢查重複記錄
4. **權限要求**：需要適當的權限才能使用匯入功能
5. **資料備份**：建議在大量匯入前先備份資料庫

## 未來擴展

1. **批次匯入**：支援更大的檔案批次處理
2. **即時驗證**：前端即時欄位驗證
3. **進度追蹤**：更詳細的匯入進度追蹤
4. **錯誤匯出**：匯出錯誤記錄供修正
5. **API介面**：提供REST API介面 