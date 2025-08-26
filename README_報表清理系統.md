# 報表清理系統

## 概述

報表清理系統是 MES 系統的一個重要組件，負責自動管理和清理報表檔案和執行日誌，確保系統效能和磁碟空間的有效利用。

## 功能特色

### 1. 自動清理功能
- **報表檔案清理**：自動刪除超過保留天數的報表檔案
- **執行日誌清理**：自動刪除超過保留天數的執行日誌
- **系統清理報告**：生成系統清理狀態報告

### 2. 前端管理介面
- **統計摘要**：顯示當前報表檔案數量、總大小、日誌數量
- **清理設定**：設定檔案和日誌的保留天數
- **手動清理**：提供手動執行清理操作的按鈕
- **清理歷史**：查看清理操作的歷史記錄

### 3. 後端自動化
- **Celery 任務**：使用 Celery Beat 進行定時自動清理
- **管理命令**：提供手動執行清理的 Django 管理命令
- **操作日誌**：記錄所有清理操作的詳細資訊

## 系統架構

### 檔案結構
```
reporting/
├── tasks.py                          # Celery 清理任務
├── management/
│   └── commands/
│       ├── setup_report_cleanup_tasks.py  # 設定自動清理任務
│       └── cleanup_reports.py             # 手動清理命令
system/
├── models.py                         # CleanupLog 模型
├── views.py                          # 前端 View
├── urls.py                           # URL 路由
└── templates/
    └── system/
        └── report_cleanup_settings.html   # 前端頁面
```

### 資料模型

#### CleanupLog 模型
```python
class CleanupLog(models.Model):
    """清理操作日誌"""
    action = models.CharField(max_length=100, verbose_name="操作類型")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name="執行狀態")
    execution_time = models.DateTimeField(auto_now_add=True, verbose_name="執行時間")
    details = models.TextField(blank=True, null=True, verbose_name="執行詳情")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="執行使用者")
```

## 設定說明

### 1. 系統設定
在 `mes_config/settings.py` 中設定：
```python
# 報表檔案保留天數
REPORT_FILE_RETENTION_DAYS = 7

# 執行日誌保留天數
REPORT_LOG_RETENTION_DAYS = 30
```

### 2. 自動清理任務設定
執行以下命令設定自動清理任務：
```bash
python3 manage.py setup_report_cleanup_tasks
```

### 3. 前端介面位置
- **主要路徑**：`/system/report_cleanup_settings/`
- **導航路徑**：系統管理 → 報表清理設定

## 使用方式

### 1. 前端操作
1. 登入系統管理模組
2. 點擊「報表清理設定」
3. 查看統計摘要
4. 設定保留天數
5. 手動執行清理操作

### 2. 手動清理命令
```bash
# 清理所有項目
python3 manage.py cleanup_reports --all

# 只清理檔案
python3 manage.py cleanup_reports --files

# 只清理日誌
python3 manage.py cleanup_reports --logs

# 只生成報告
python3 manage.py cleanup_reports --report

# 強制執行（跳過確認）
python3 manage.py cleanup_reports --all --force
```

### 3. 自動清理任務
系統會自動執行以下任務：
- **檔案清理**：每 24 小時執行一次
- **日誌清理**：每 7 天執行一次
- **清理報告**：每 7 天執行一次

## 安全考量

### 1. 權限控制
- 只有超級用戶可以訪問清理設定頁面
- 所有清理操作都會記錄操作日誌
- 手動清理操作需要確認

### 2. 資料保護
- 清理前會檢查檔案存在性
- 只清理指定目錄下的檔案
- 保留天數有最小和最大限制

### 3. 錯誤處理
- 所有清理操作都有錯誤處理機制
- 失敗的操作會記錄詳細錯誤資訊
- 系統不會因為清理失敗而停止運作

## 監控與維護

### 1. 日誌監控
- 查看 `CleanupLog` 模型中的操作記錄
- 監控清理任務的執行狀態
- 檢查清理報告的內容

### 2. 效能監控
- 監控報表目錄的檔案數量
- 監控磁碟空間使用情況
- 監控清理任務的執行時間

### 3. 定期維護
- 定期檢查清理任務是否正常執行
- 根據系統使用情況調整保留天數
- 定期檢查清理日誌的完整性

## 故障排除

### 1. 常見問題
- **清理任務未執行**：檢查 Celery Beat 是否正常運行
- **檔案未刪除**：檢查檔案權限和路徑設定
- **日誌記錄缺失**：檢查資料庫連線和模型設定

### 2. 除錯方法
- 查看 Django 日誌檔案
- 檢查 Celery 工作日誌
- 使用管理命令手動測試清理功能

### 3. 聯絡支援
如遇到無法解決的問題，請聯絡系統管理員或查看相關技術文件。

## 更新記錄

- **2025-08-26**：建立報表清理系統
  - 新增 CleanupLog 模型
  - 建立前端管理介面
  - 實作自動清理任務
  - 新增手動清理命令
