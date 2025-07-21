# 作業員報工功能設計說明

## 功能概述

作業員報工功能是MES系統中工單管理的次模組，專門為作業員提供現場報工和補登報工功能。與SMT報工不同，作業員報工不涉及SMT相關的設備和工序，主要針對一般生產線的作業員進行報工管理。

## 模組架構

```
作業員報工
├── 作業員現場報工
│   ├── 快速報工
│   ├── 工序開始/結束
│   ├── 進度報工
│   └── 作業員狀態監控
└── 作業員補登報工
    ├── 新增補登
    ├── 編輯補登
    ├── 審核管理
    ├── 批量匯入
    └── 資料匯出
```

## 主要功能

### 1. 作業員現場報工

#### 1.1 快速報工
- **功能描述**：提供簡化的報工介面，支援快速輸入基本報工資訊
- **主要欄位**：
  - 作業員選擇
  - 工單號選擇
  - 工序選擇
  - 報工數量
  - 開始/結束時間
  - 工時自動計算

#### 1.2 工序管理
- **開始工序**：記錄工序開始時間和狀態
- **結束工序**：記錄工序完成時間和產出數量
- **進度追蹤**：即時顯示工序進度和狀態

#### 1.3 作業員狀態監控
- **工作狀態**：顯示作業員當前工作狀態（工作中、閒置、休息、離線）
- **當前工單**：顯示作業員正在處理的工單資訊
- **今日統計**：顯示作業員今日報工統計

### 2. 作業員補登報工

#### 2.1 補登記錄管理
- **新增補登**：建立新的補登報工記錄
- **編輯補登**：修改現有的補登記錄（僅限草稿狀態）
- **刪除補登**：刪除補登記錄（僅限草稿狀態）

#### 2.2 審核流程
- **待審核**：新建立的補登記錄狀態
- **審核通過**：管理員審核通過的記錄
- **駁回**：管理員駁回的記錄，需重新提交
- **草稿**：未提交審核的記錄

#### 2.3 批量操作
- **批量匯入**：支援Excel/CSV檔案批量匯入補登記錄
- **資料匯出**：匯出補登記錄為Excel/CSV格式
- **範本下載**：提供標準的匯入範本

## 資料模型

### 1. 作業員報工記錄 (OperatorReport)
```python
class OperatorReport(models.Model):
    """作業員報工記錄"""
    operator = models.ForeignKey('system.Operator', on_delete=models.CASCADE, verbose_name="作業員")
    workorder = models.ForeignKey('WorkOrder', on_delete=models.CASCADE, verbose_name="工單")
    process = models.ForeignKey('process.Process', on_delete=models.CASCADE, verbose_name="工序")
    report_time = models.DateTimeField(verbose_name="報工時間")
    start_time = models.TimeField(verbose_name="開始時間")
    end_time = models.TimeField(verbose_name="結束時間")
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="工時")
    quantity = models.IntegerField(verbose_name="報工數量")
    good_quantity = models.IntegerField(null=True, blank=True, verbose_name="良品數量")
    defect_quantity = models.IntegerField(null=True, blank=True, verbose_name="不良品數量")
    yield_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="良率")
    notes = models.TextField(blank=True, verbose_name="報工備註")
    abnormal_notes = models.TextField(blank=True, verbose_name="異常記錄")
    status = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default='pending', verbose_name="狀態")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="建立人員")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
```

### 2. 作業員補登報工記錄 (OperatorSupplementReport)
```python
class OperatorSupplementReport(models.Model):
    """作業員補登報工記錄"""
    operator = models.ForeignKey('system.Operator', on_delete=models.CASCADE, verbose_name="作業員")
    workorder = models.ForeignKey('WorkOrder', on_delete=models.CASCADE, verbose_name="工單")
    process = models.ForeignKey('process.Process', on_delete=models.CASCADE, verbose_name="工序")
    report_time = models.DateTimeField(verbose_name="報工時間")
    start_time = models.TimeField(verbose_name="開始時間")
    end_time = models.TimeField(verbose_name="結束時間")
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="工時")
    quantity = models.IntegerField(verbose_name="報工數量")
    good_quantity = models.IntegerField(null=True, blank=True, verbose_name="良品數量")
    defect_quantity = models.IntegerField(null=True, blank=True, verbose_name="不良品數量")
    yield_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="良率")
    notes = models.TextField(blank=True, verbose_name="報工備註")
    abnormal_notes = models.TextField(blank=True, verbose_name="異常記錄")
    status = models.CharField(max_length=20, choices=SUPPLEMENT_STATUS_CHOICES, default='draft', verbose_name="狀態")
    rejection_reason = models.TextField(blank=True, verbose_name="駁回原因")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="建立人員")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="審核人員")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="審核時間")
```

## 頁面結構

### 1. 作業員報工首頁 (`/workorder/report/operator/`)
- 統計資訊卡片
- 現場報工功能卡片
- 補登報工功能卡片
- 作業員列表
- 最近報工記錄

### 2. 作業員現場報工 (`/workorder/report/operator/on_site/`)
- 快速報工表單
- 進行中工單列表
- 作業員狀態監控
- 最近報工記錄

### 3. 作業員補登報工 (`/workorder/report/operator/supplement/`)
- 補登記錄列表
- 搜尋篩選功能
- 批量操作按鈕
- 分頁顯示

### 4. 補登報工表單 (`/workorder/report/operator/supplement/form/`)
- 基本資訊區塊
- 報工時間區塊
- 報工數量區塊
- 備註資訊區塊
- 預覽功能

### 5. 補登報工詳情 (`/workorder/report/operator/supplement/detail/`)
- 報工記錄詳情
- 審核歷程
- 操作按鈕

## 審核流程

### 1. 補登記錄狀態
- **草稿 (draft)**：新建的記錄，可編輯和刪除
- **待審核 (pending)**：已提交的記錄，等待管理員審核
- **已審核 (approved)**：審核通過的記錄，正式生效
- **已駁回 (rejected)**：審核駁回的記錄，需重新提交

### 2. 審核操作
- **審核通過**：管理員確認記錄正確，正式生效
- **駁回**：管理員駁回記錄，需填寫駁回原因
- **重新提交**：作業員根據駁回原因修正後重新提交

## 時間格式規範

所有時間欄位統一使用以下格式：
- **日期格式**：`YYYY-MM-DD`（例如：2025-01-15）
- **時間格式**：`HH:MM`（例如：14:30）
- **日期時間格式**：`YYYY-MM-DD HH:MM`（例如：2025-01-15 14:30）

## 權限控制

### 1. 作業員權限
- 查看自己的報工記錄
- 建立和編輯補登記錄
- 提交補登記錄審核

### 2. 管理員權限
- 查看所有作業員的報工記錄
- 審核補登記錄
- 管理補登記錄（編輯、刪除）
- 匯入/匯出資料

### 3. 超級管理員權限
- 所有管理員權限
- 系統設定管理
- 資料清理和維護

## 技術特點

### 1. 前端技術
- 使用Bootstrap 5進行響應式設計
- 原生JavaScript實現互動功能
- AJAX技術實現非同步操作
- 表單驗證和錯誤處理

### 2. 後端技術
- Django 5.1.8框架
- PostgreSQL資料庫
- Celery異步任務處理
- RESTful API設計

### 3. 資料處理
- 自動計算工時和良率
- 資料驗證和完整性檢查
- 批量處理和匯入匯出
- 審核流程和狀態管理

## 與SMT報工的差異

### 1. 設備相關
- **SMT報工**：需要選擇SMT設備，監控設備狀態
- **作業員報工**：不需要設備選擇，專注於作業員操作

### 2. 工序範圍
- **SMT報工**：僅限SMT相關工序
- **作業員報工**：包含所有非SMT工序

### 3. 報工方式
- **SMT報工**：設備自動化程度高，數據較為精確
- **作業員報工**：人工操作為主，需要更多備註和異常記錄

### 4. 審核流程
- **SMT報工**：自動化程度高，審核相對簡單
- **作業員報工**：需要更詳細的審核流程和原因記錄

## 未來擴展

### 1. 功能擴展
- 作業員績效分析
- 工時統計報表
- 品質趨勢分析
- 異常預警系統

### 2. 技術升級
- 移動端APP支援
- 即時通訊功能
- 語音報工功能
- AI輔助審核

### 3. 整合功能
- 與薪資系統整合
- 與品質管理系統整合
- 與設備維護系統整合
- 與ERP系統深度整合 