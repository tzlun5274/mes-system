# 報表同步間隔設定功能說明

## 功能概述

本次更新為 SMT 生產報表和作業員生產報表頁面新增了「同步間隔（小時）」設定功能，讓使用者可以自訂報表數據的自動同步頻率。

## 新增功能

### 1. 同步間隔設定模型 (ReportSyncSettings)

- **位置**: `reporting/models.py`
- **功能**: 儲存每種報表類型的同步間隔設定
- **欄位**:
  - `report_type`: 報表類型 (smt/operator)
  - `sync_interval_hours`: 同步間隔（小時）
  - `is_active`: 是否啟用自動同步
  - `created_at/updated_at`: 創建/更新時間

### 2. 網頁介面更新

#### SMT 生產報表頁面
- **位置**: `reporting/templates/reporting/smt_production_report.html`
- **新增功能**:
  - 同步間隔輸入框（1-168小時）
  - 儲存設定按鈕
  - 自動載入現有設定

#### 作業員生產報表頁面
- **位置**: `reporting/templates/reporting/operator_performance.html`
- **新增功能**:
  - 同步間隔輸入框（1-168小時）
  - 儲存設定按鈕
  - 自動載入現有設定

### 3. API 端點

#### 更新同步間隔
- **URL**: `/reporting/api/update_sync_interval/`
- **方法**: POST
- **參數**:
  - `report_type`: 報表類型 (smt/operator)
  - `sync_interval_hours`: 同步間隔（小時）

#### 取得同步設定
- **URL**: `/reporting/api/get_sync_settings/`
- **方法**: GET
- **回傳**: 所有報表類型的同步設定

### 4. 管理介面

- **位置**: `reporting/admin.py`
- **功能**: 在 Django 管理介面中管理同步設定
- **限制**: 每種報表類型只能有一個設定

## 使用方式

### 1. 設定同步間隔

1. 進入 SMT 生產報表或作業員生產報表頁面
2. 在右側的「同步間隔設定」卡片中輸入小時數
3. 點擊「儲存設定」按鈕
4. 系統會顯示設定成功訊息

### 2. 設定範圍

- **最小值**: 1 小時
- **最大值**: 168 小時（7天）
- **預設值**: 24 小時

### 3. 驗證規則

- 同步間隔必須是有效的數字
- 範圍必須在 1-168 小時之間
- 報表類型必須是 'smt' 或 'operator'

## 技術實作

### 1. 資料庫遷移

```bash
python3 manage.py makemigrations reporting
python3 manage.py migrate reporting
```

### 2. 模型方法

```python
# 取得指定報表類型的同步間隔
interval = ReportSyncSettings.get_sync_interval('smt')
```

### 3. JavaScript 功能

- `loadSyncSettings()`: 載入現有設定
- `updateSMTInterval()`: 更新 SMT 同步間隔
- `updateOperatorInterval()`: 更新作業員同步間隔

## 安全性

- 所有 API 端點都需要登入驗證
- 需要「報表使用者」群組權限或超級用戶權限
- 使用 CSRF 保護
- 輸入驗證和錯誤處理

## 記錄功能

- 所有設定變更都會記錄在 `ReportingOperationLog` 中
- 記錄包含使用者、操作內容和時間戳

## 相容性

- 向後相容：現有的報表功能不受影響
- 預設值：如果沒有設定，使用 24 小時作為預設間隔
- 資料庫：自動創建必要的資料表和欄位

## 測試

功能已通過以下測試：
- 模型創建和更新
- API 端點功能
- 網頁介面互動
- 資料驗證
- 錯誤處理

## 未來擴展

- 可考慮添加更細緻的時間單位（分鐘）
- 可考慮添加排程功能（特定時間同步）
- 可考慮添加同步歷史記錄
- 可考慮添加批量設定功能 