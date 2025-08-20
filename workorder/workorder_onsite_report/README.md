# 現場報工管理模組

## 模組概述

現場報工管理模組是 MES 系統的核心組件之一，專門負責處理現場即時報工功能。本模組支援作業員手動報工和 SMT 設備自動報工兩種模式，提供即時狀態追蹤、進度監控、異常處理等功能。

## 功能特色

### 🏭 雙模式報工支援
- **作業員現場報工**：支援作業員手動輸入報工資料
- **SMT設備報工**：支援自動化設備的無人化報工

### 📊 即時監控功能
- 即時狀態追蹤（已開始、進行中、暫停、完成、異常）
- 進度百分比計算
- 工作時數統計
- 異常狀況記錄

### 🔄 狀態管理
- 支援報工狀態變更（開始、暫停、恢復、完成）
- 自動記錄狀態變更歷史
- 異常狀況處理機制

### 📈 統計分析
- 今日報工統計
- 報工類型分析
- 活躍報工監控
- 異常報工追蹤

## 資料模型

### OnsiteReport（現場報工記錄）
主要資料模型，記錄所有現場報工資訊：

```python
class OnsiteReport(models.Model):
    # 基本資訊
    report_type = models.CharField(choices=REPORT_TYPE_CHOICES)  # 報工類型
    operator = models.CharField(max_length=100)  # 作業員
    company_code = models.CharField(max_length=10)  # 公司代號
    company_name = models.CharField(max_length=100)  # 公司名稱
    
    # 工單資訊
    workorder = models.CharField(max_length=100)  # 工單號碼
    product_id = models.CharField(max_length=100)  # 產品編號
    planned_quantity = models.IntegerField()  # 預設生產數量
    
    # 製程資訊
    process = models.CharField(max_length=100)  # 工序
    operation = models.CharField(max_length=100)  # 工序名稱
    equipment = models.CharField(max_length=100)  # 使用的設備
    
    # 時間資訊
    work_date = models.DateField()  # 工作日期
    start_time = models.TimeField()  # 開始時間
    end_time = models.TimeField()  # 結束時間
    
    # 狀態資訊
    status = models.CharField(choices=STATUS_CHOICES)  # 報工狀態
    current_quantity = models.IntegerField()  # 當前數量
    defect_quantity = models.IntegerField()  # 不良品數量
    
    # 監控資訊
    last_update_time = models.DateTimeField()  # 最後更新時間
    is_active = models.BooleanField()  # 是否活躍
    
    # 異常記錄
    abnormal_notes = models.TextField()  # 異常記錄
    abnormal_start_time = models.DateTimeField()  # 異常開始時間
    abnormal_end_time = models.DateTimeField()  # 異常結束時間
```

### OnsiteReportHistory（歷史記錄）
記錄所有狀態變更歷史：

```python
class OnsiteReportHistory(models.Model):
    onsite_report = models.ForeignKey(OnsiteReport)  # 關聯報工記錄
    change_type = models.CharField(choices=CHANGE_TYPE_CHOICES)  # 變更類型
    old_status = models.CharField()  # 原狀態
    new_status = models.CharField()  # 新狀態
    old_quantity = models.IntegerField()  # 原數量
    new_quantity = models.IntegerField()  # 新數量
    change_notes = models.TextField()  # 變更說明
    changed_by = models.CharField()  # 變更人員
    changed_at = models.DateTimeField()  # 變更時間
```

### OnsiteReportConfig（系統配置）
管理系統配置參數：

```python
class OnsiteReportConfig(models.Model):
    config_type = models.CharField(choices=CONFIG_TYPE_CHOICES)  # 配置類型
    config_key = models.CharField(max_length=100)  # 配置鍵
    config_value = models.TextField()  # 配置值
    config_description = models.TextField()  # 配置說明
    is_active = models.BooleanField()  # 是否啟用
```

## 主要功能

### 1. 現場報工首頁
- **路徑**：`/workorder/onsite_reporting/`
- **功能**：顯示統計資料、功能入口、最近活躍報工、異常報工

### 2. 作業員現場報工
- **路徑**：`/workorder/onsite_reporting/create/operator/`
- **功能**：新增作業員報工記錄

### 3. SMT設備現場報工
- **路徑**：`/workorder/onsite_reporting/create/smt/`
- **功能**：新增SMT設備報工記錄

### 4. 報工記錄列表
- **路徑**：`/workorder/onsite_reporting/list/`
- **功能**：查看所有報工記錄，支援搜尋和篩選

### 5. 即時監控
- **路徑**：`/workorder/onsite_reporting/monitoring/`
- **功能**：即時監控活躍報工和異常狀況

### 6. 系統配置
- **路徑**：`/workorder/onsite_reporting/config/`
- **功能**：管理系統配置參數

## API 介面

### 更新報工狀態
- **路徑**：`/workorder/onsite_reporting/api/update-status/<pk>/`
- **方法**：POST
- **功能**：更新報工狀態和數量

### 完成報工
- **路徑**：`/workorder/onsite_reporting/api/complete/<pk>/`
- **方法**：POST
- **功能**：完成報工記錄

### 暫停報工
- **路徑**：`/workorder/onsite_reporting/api/pause/<pk>/`
- **方法**：POST
- **功能**：暫停報工記錄

### 恢復報工
- **路徑**：`/workorder/onsite_reporting/api/resume/<pk>/`
- **方法**：POST
- **功能**：恢復報工記錄

## 使用方式

### 1. 作業員報工流程
1. 進入現場報工首頁
2. 點擊「新增作業員報工」
3. 填寫報工資訊（作業員、工單、產品等）
4. 提交建立報工記錄
5. 在監控頁面查看即時狀態
6. 根據需要更新數量或狀態

### 2. SMT設備報工流程
1. 進入現場報工首頁
2. 點擊「新增SMT設備報工」
3. 填寫設備報工資訊
4. 提交建立報工記錄
5. 設備可透過API自動更新狀態

### 3. 監控管理
1. 在首頁查看統計資料
2. 進入監控頁面查看活躍報工
3. 處理異常狀況
4. 查看歷史記錄

## 技術特點

### 多公司架構支援
- 支援多公司資料隔離
- 透過 CompanyConfig 模型查找公司資訊

### 即時更新機制
- 自動刷新頁面（30秒間隔）
- API 介面支援即時狀態更新
- WebSocket 支援（可擴展）

### 歷史記錄追蹤
- 完整記錄所有狀態變更
- 支援變更原因說明
- 提供審計追蹤功能

### 異常處理機制
- 異常狀況記錄
- 異常時間追蹤
- 異常處理流程

## 配置說明

### 系統配置參數
- `auto_refresh_interval`：自動刷新間隔（秒）
- `overtime_start_time`：加班起算時間
- `break_time_deduction`：休息時間扣除

### 權限控制
- 超級用戶：完整管理權限
- 一般用戶：查看和基本操作權限
- 作業員：僅限自己的報工記錄

## 開發規範

### 程式碼結構
```
workorder/onsite_reporting/
├── __init__.py
├── apps.py
├── models.py
├── forms.py
├── views.py
├── urls.py
├── admin.py
├── templates/
│   └── workorder/onsite_reporting/
│       ├── index.html
│       ├── onsite_report_list.html
│       ├── operator_onsite_report_form.html
│       └── smt_onsite_report_form.html
└── static/
    └── workorder/onsite_reporting/
```

### 命名規範
- 模型：OnsiteReport, OnsiteReportHistory, OnsiteReportConfig
- 視圖：OnsiteReportIndexView, OnsiteReportListView
- URL：onsite_report_index, onsite_report_list
- 模板：index.html, onsite_report_list.html

## 測試

### 執行測試
```bash
python3 test_onsite_reporting.py
```

### 測試內容
- 模型功能測試
- 表單驗證測試
- URL配置測試
- API介面測試

## 部署說明

### 1. 資料庫遷移
```bash
python3 manage.py makemigrations onsite_reporting
python3 manage.py migrate onsite_reporting
```

### 2. 設定配置
在 `mes_config/settings.py` 中加入：
```python
INSTALLED_APPS = [
    # ... 其他應用程式
    "workorder.onsite_reporting",
]
```

### 3. URL配置
在 `workorder/urls.py` 中加入：
```python
urlpatterns = [
    # ... 其他URL
    path("onsite_reporting/", include('workorder.onsite_reporting.urls')),
]
```

## 維護說明

### 日常維護
- 定期檢查異常報工記錄
- 清理過期的歷史記錄
- 監控系統效能

### 故障排除
- 檢查資料庫連線
- 驗證權限設定
- 查看錯誤日誌

## 版本資訊

- **版本**：1.0.0
- **建立日期**：2024-08-15
- **開發者**：MES系統開發團隊
- **相容性**：Django 5.1.8+, Python 3.10+

## 聯絡資訊

如有問題或建議，請聯絡系統管理員或開發團隊。 