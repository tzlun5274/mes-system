# SMT 現場報工資料清除功能說明

## 功能概述

本功能提供兩個管理命令，用於清除 SMT 現場報工即時模式的資料：

1. **clear_smt_data** - 清除 SMT 報工記錄
2. **reset_smt_system** - 重置整個 SMT 系統（包括設備狀態）

## 使用方式

### 1. 清除 SMT 報工記錄 (clear_smt_data)

#### 基本語法
```bash
python3 manage.py clear_smt_data [選項]
```

#### 選項說明
- `--all` - 清除所有 SMT 報工記錄（不限制日期）
- `--days N` - 清除最近 N 天的資料（預設：7天）
- `--confirm` - 確認清除操作（避免誤刪）
- `--dry-run` - 預覽要清除的資料，但不實際刪除

#### 使用範例

**預覽最近 7 天的資料**
```bash
python3 manage.py clear_smt_data --dry-run
```

**預覽最近 3 天的資料**
```bash
python3 manage.py clear_smt_data --days 3 --dry-run
```

**清除最近 7 天的資料**
```bash
python3 manage.py clear_smt_data --confirm
```

**清除所有資料**
```bash
python3 manage.py clear_smt_data --all --confirm
```

### 2. 重置 SMT 系統 (reset_smt_system)

#### 基本語法
```bash
python3 manage.py reset_smt_system [選項]
```

#### 選項說明
- `--confirm` - 確認重置操作（避免誤操作）
- `--dry-run` - 預覽重置操作，但不實際執行
- `--reset-equipment` - 同時重置設備狀態為閒置

#### 使用範例

**預覽重置操作**
```bash
python3 manage.py reset_smt_system --dry-run --reset-equipment
```

**執行完整重置（清除報工記錄 + 重置設備狀態）**
```bash
python3 manage.py reset_smt_system --confirm --reset-equipment
```

**只清除報工記錄，不重置設備狀態**
```bash
python3 manage.py reset_smt_system --confirm
```

## 功能特色

### 安全性設計
- **預覽模式**：使用 `--dry-run` 可先預覽要清除的資料
- **確認機制**：必須使用 `--confirm` 參數才能執行實際操作
- **詳細統計**：顯示清除前後的詳細統計資訊

### 資料統計
- 按設備分組統計報工記錄
- 顯示總產出數量
- 顯示最新報工時間
- 清除後狀態驗證

### 設備狀態管理
- 可選擇是否重置設備狀態
- 顯示設備狀態圖示（🟢運轉中、🟡閒置、🔴維修）
- 顯示今日報工記錄數量

## 操作流程

### 標準清除流程
1. **預覽資料**：使用 `--dry-run` 查看要清除的資料
2. **確認操作**：檢查統計資訊是否正確
3. **執行清除**：使用 `--confirm` 執行實際清除
4. **驗證結果**：檢查清除後的狀態

### 完整重置流程
1. **預覽重置**：使用 `--dry-run --reset-equipment` 預覽
2. **確認重置**：檢查設備狀態和報工記錄
3. **執行重置**：使用 `--confirm --reset-equipment` 執行
4. **後續操作**：重新開始 SMT 現場報工

## 注意事項

### ⚠️ 重要警告
- **不可逆操作**：清除的資料無法復原
- **影響範圍**：會影響 SMT 現場報工的統計資料
- **設備狀態**：重置設備狀態會影響即時監控

### 🔒 安全建議
- 執行前務必使用 `--dry-run` 預覽
- 確認統計資訊正確後再執行
- 建議在非生產時間執行
- 執行前備份重要資料

### 📊 資料影響
- **統計資料**：今日報工數、本班產出等統計會歸零
- **設備狀態**：設備狀態會重置為閒置
- **報工記錄**：所有相關報工記錄會被刪除

## 常見使用場景

### 1. 測試環境清理
```bash
# 清除所有測試資料
python3 manage.py reset_smt_system --confirm --reset-equipment
```

### 2. 每日資料清理
```bash
# 清除昨天的資料
python3 manage.py clear_smt_data --days 1 --confirm
```

### 3. 系統重置
```bash
# 完整系統重置
python3 manage.py reset_smt_system --confirm --reset-equipment
```

### 4. 資料維護
```bash
# 清除舊資料但保留設備狀態
python3 manage.py clear_smt_data --days 30 --confirm
```

## 錯誤處理

### 常見錯誤
1. **權限不足**：確保有管理員權限
2. **資料庫連線**：檢查資料庫連線狀態
3. **模型錯誤**：確認相關模型已正確載入

### 故障排除
- 檢查 Django 設定檔
- 確認資料庫連線正常
- 查看系統日誌檔案

## 技術細節

### 資料模型
- `SMTProductionReport` - SMT 報工記錄
- `Equipment` - 設備資訊

### 日誌記錄
- 所有操作都會記錄到系統日誌
- 包含操作時間、操作人員、影響範圍

### 效能考量
- 大量資料清除時建議分批處理
- 建議在低峰期執行清除操作 