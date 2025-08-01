# 主管功能模組 (Supervisor Management Module)

## 模組概述

主管功能模組是 MES 系統中專門為主管設計的功能集合，負責報工記錄的審核管理、統計分析、異常處理和資料維護等核心業務。

## 功能架構

### 1. 審核管理 (Approval Management)
- **待審核清單**: 顯示所有待審核的報工記錄
- **核准操作**: 處理報工記錄的核准
- **駁回操作**: 處理報工記錄的駁回
- **批量核准**: 支援批量核准多筆報工記錄

### 2. 統計分析 (Statistics Analysis)
- **今日統計**: 當日報工記錄統計
- **週統計**: 本週報工記錄統計
- **月統計**: 本月報工記錄統計
- **年統計**: 今年報工記錄統計
- **異常統計**: 異常記錄統計分析

### 3. 異常處理 (Abnormal Management)
- **異常清單**: 顯示所有異常報工記錄
- **異常詳情**: 查看異常記錄的詳細資訊
- **異常分類**: 按類型分類異常記錄

### 4. 資料維護 (Data Maintenance)
- **資料清理**: 清理舊的報工記錄
- **資料備份**: 建立資料庫備份
- **資料優化**: 優化資料庫效能
- **資料匯出**: 匯出報工記錄

## 目錄結構

```
workorder/supervisor/
├── __init__.py              # 模組初始化
├── apps.py                  # 應用配置
├── urls.py                  # URL路由配置
├── views.py                 # 視圖函數
├── services.py              # 業務邏輯服務層
├── README.md                # 說明文件
├── static/                  # 靜態檔案
│   └── supervisor/
└── templates/               # 模板檔案
    └── supervisor/
        ├── index.html       # 主管功能首頁
        ├── functions.html   # 主管功能選單
        ├── pending_approval_list.html  # 待審核清單
        ├── statistics.html  # 統計分析
        ├── abnormal.html    # 異常處理
        └── maintenance.html # 資料維護
```

## 模型關係

### 核心模型
- `OperatorSupplementReport`: 作業員補登報工記錄
- `SMTProductionReport`: SMT生產報工記錄
- `SupervisorProductionReport`: 主管生產報工記錄

### 審核狀態
- `pending`: 待審核
- `approved`: 已核准
- `rejected`: 已駁回

## 服務層架構

### SupervisorStatisticsService
負責統計數據的生成和計算

### SupervisorApprovalService
負責審核相關的業務邏輯

### SupervisorAbnormalService
負責異常處理的業務邏輯

## URL路由

| URL | 視圖函數 | 功能描述 |
|-----|----------|----------|
| `/supervisor/functions/` | `supervisor_functions` | 主管功能首頁 |
| `/supervisor/reports/` | `supervisor_report_index` | 主管報表首頁 |
| `/supervisor/pending_approval_list/` | `pending_approval_list` | 待審核清單 |
| `/supervisor/statistics/` | `report_statistics` | 統計分析 |
| `/supervisor/abnormal/` | `abnormal_management` | 異常處理 |
| `/supervisor/maintenance/` | `data_maintenance` | 資料維護 |

## 使用方式

### 1. 審核報工記錄
1. 進入主管功能首頁
2. 點擊「待審核清單」
3. 查看待審核的報工記錄
4. 選擇核准或駁回操作

### 2. 查看統計分析
1. 進入主管功能首頁
2. 點擊「統計分析」
3. 查看各項統計數據

### 3. 處理異常記錄
1. 進入主管功能首頁
2. 點擊「異常處理」
3. 查看異常記錄清單
4. 點擊詳情查看具體異常

### 4. 資料維護
1. 進入主管功能首頁
2. 點擊「資料維護」
3. 選擇維護操作
4. 執行維護任務

## 權限控制

- 只有主管角色的用戶可以訪問此模組
- 需要登入驗證
- 部分功能需要特定權限

## 開發規範

### 命名規範
- 類別名稱: PascalCase (如 `SupervisorStatisticsService`)
- 函數名稱: snake_case (如 `get_supervisor_statistics`)
- 變數名稱: snake_case (如 `recent_abnormal_records`)
- 檔案名稱: snake_case (如 `supervisor_views.py`)

### 註解規範
- 所有函數和類別都必須有繁體中文 docstring
- 重要邏輯需要行內註解
- 複雜業務邏輯需要詳細說明

### 程式碼組織
- 視圖層只負責 HTTP 請求和回應
- 業務邏輯放在服務層
- 資料存取放在模型層
- 保持各層的職責分離

## 測試

### 單元測試
- 測試服務層的業務邏輯
- 測試視圖層的請求和回應
- 測試模型層的資料操作

### 整合測試
- 測試完整的審核流程
- 測試統計分析功能
- 測試異常處理流程

## 部署注意事項

1. 確保資料庫遷移已執行
2. 檢查權限設定
3. 配置靜態檔案
4. 設定日誌記錄
5. 配置備份策略

## 維護指南

### 日常維護
- 定期檢查異常記錄
- 監控統計數據
- 清理舊資料
- 備份重要資料

### 故障排除
- 檢查日誌檔案
- 驗證資料庫連線
- 確認權限設定
- 檢查系統資源

## 版本歷史

- v1.0.0: 初始版本，包含基本審核功能
- v1.1.0: 新增統計分析功能
- v1.2.0: 新增異常處理功能
- v1.3.0: 新增資料維護功能
- v2.0.0: 重構為服務層架構，統一命名規範 