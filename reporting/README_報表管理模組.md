# 報表管理模組

## 模組概述

報表管理模組是 MES 系統的核心組件之一，專門負責處理各種生產報表的生成、管理和分析。本模組提供完整的報表功能，包括數據收集、智能分配、報表生成和匯出等功能。

## 主要功能

### 1. 六種核心報表
- **工作時間報表** (Work Time Reports)
- **工單機種報表** (Work Order Product Reports)  
- **人員績效報表** (Personnel Performance Reports)
- **設備效率報表** (Equipment Efficiency Reports)
- **品質分析報表** (Quality Analysis Reports)
- **綜合分析報表** (Comprehensive Analysis Reports)

### 2. 智能數量分配
- 自動識別包裝人員（最後工序）
- 為不寫數量的作業員自動分配數量
- 處理多天多次的複雜情況
- 支援同一工序多名作業員的情況

### 3. 報表匯出功能
- 支援 Excel 和 CSV 格式匯出
- 自動郵件發送功能
- 報表排程管理

## 目錄結構

```
reporting/
├── __init__.py
├── admin.py              # 管理介面配置
├── apps.py               # 應用程式配置
├── models.py             # 資料模型
├── views.py              # 視圖邏輯
├── urls.py               # URL 路由
├── tasks.py              # 背景任務
├── utils.py              # 工具函數
├── tests.py              # 測試檔案
├── allocators/           # 分配器模組
│   ├── __init__.py
│   ├── base_allocator.py
│   └── hybrid_allocator.py
├── calculators/          # 計算器模組
│   ├── __init__.py
│   └── base_calculator.py
├── services/             # 服務層
│   ├── __init__.py
│   ├── base_service.py
│   ├── work_time_service.py
│   └── quantity_allocation_service.py
├── management/           # 管理命令
│   └── commands/
├── migrations/           # 資料庫遷移
├── static/               # 靜態檔案
│   └── reporting/
├── templates/            # 模板檔案
│   └── reporting/
└── README_報表管理模組.md
```

## 核心模型

### 1. 報表基礎模型
- `WorkTimeReport` - 工作時間報表
- `WorkOrderProductReport` - 工單機種報表
- `PersonnelPerformanceReport` - 人員績效報表
- `EquipmentEfficiencyReport` - 設備效率報表
- `QualityAnalysisReport` - 品質分析報表
- `ComprehensiveAnalysisReport` - 綜合分析報表

### 2. 操作記錄模型
- `ReportingOperationLog` - 報表操作日誌
- `ReportEmailSchedule` - 報表郵件排程
- `ReportEmailLog` - 報表郵件發送記錄

## 智能分配系統

### 分配策略
1. **時間比例分配** - 根據工作時間比例分配數量
2. **效率比例分配** - 根據作業員效率分配數量
3. **工序複雜度分配** - 根據工序複雜度調整分配
4. **作業員等級分配** - 根據作業員等級調整分配

### 分配流程
1. 識別包裝人員（最後工序）
2. 收集所有相關報工記錄
3. 計算分配權重
4. 執行智能分配
5. 更新報工記錄
6. 記錄分配日誌

## 使用方式

### 1. 訪問報表管理
```
URL: /reporting/
權限: 報表管理員或超級用戶
```

### 2. 數量分配功能
```
URL: /reporting/quantity-allocation/
功能: 智能分配作業員報工數量
```

### 3. 報表匯出
```
URL: /reporting/export/
格式: Excel, CSV
```

## 權限設定

### 用戶群組
- **報表管理員** - 完整報表管理權限
- **報表查看者** - 僅可查看報表
- **報表匯出者** - 可匯出報表

### 權限檢查
```python
def reporting_user_required(user):
    """檢查用戶是否有報表管理權限"""
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="報表管理員").exists()
    )
```

## 配置設定

### 1. 應用程式配置
```python
# settings.py
INSTALLED_APPS = [
    ...
    "reporting",  # 報表管理模組
    ...
]
```

### 2. URL 配置
```python
# urls.py
urlpatterns = [
    ...
    path("reporting/", include("reporting.urls")),  # 報表管理
    ...
]
```

## 開發規範

### 1. 命名規範
- 模組名稱：`reporting`
- 顯示名稱：`報表管理`
- URL 命名空間：`reporting_management`

### 2. 程式碼規範
- 所有註解使用繁體中文
- 函數和類別必須有 docstring
- 遵循 PEP 8 程式碼風格

### 3. 測試規範
- 每個功能必須有對應測試
- 測試覆蓋率目標 80% 以上

## 維護說明

### 1. 日誌記錄
- 所有操作都會記錄在 `ReportingOperationLog` 中
- 日誌檔案位置：`/var/log/mes/reporting.log`

### 2. 資料備份
- 定期備份報表資料
- 支援資料匯出和歸檔

### 3. 效能監控
- 監控報表生成時間
- 監控資料庫查詢效能

## 更新記錄

### v2.0.0 (2025-01-XX)
- 模組改名為「報表管理」
- 新增智能數量分配功能
- 完善六種核心報表
- 優化用戶介面

### v1.0.0 (2024-XX-XX)
- 初始版本發布
- 基本報表功能
- 郵件發送功能

---

> 本文件為報表管理模組的完整說明，請開發團隊遵循本規範進行開發和維護。 