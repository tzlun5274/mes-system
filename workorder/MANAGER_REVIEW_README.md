# 管理者審核功能說明文件

## 功能概述

管理者審核功能是 MES 系統中專為管理者設計的報工記錄審核模組，結合了 SMT 補登報工和作業員補登報工的功能特點，支援跨工序、跨設備的報工記錄審核。

## 主要特色

### 1. 跨工序支援
- 支援所有工序的報工記錄（不限制 SMT 或非 SMT）
- 可選擇任意設備和作業員
- 靈活的工序配置

### 2. 智能完工判斷
- 手動勾選完工
- 自動依數量判斷完工
- 自動依工時判斷完工
- 管理者確認完工
- 系統自動判斷完工

### 3. 審核機制
- 三階段審核狀態：待審核、已審核、已駁回
- 權限控制：只有管理者或超級用戶可以審核
- 審核備註和駁回原因記錄

### 4. 批量操作
- 批量創建報工記錄
- 批量審核和駁回
- 資料匯出功能

## 資料模型

### ManagerProductionReport
```python
class ManagerProductionReport(models.Model):
    # 基本資訊
    manager = models.CharField(max_length=100, verbose_name="管理者")
    workorder = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, verbose_name="工單號碼")
    planned_quantity = models.IntegerField(verbose_name="工單預設生產數量")
    process = models.ForeignKey('process.ProcessName', on_delete=models.CASCADE, verbose_name="工序")
    equipment = models.ForeignKey('equip.Equipment', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="設備")
    operator = models.ForeignKey('process.Operator', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="作業員")
    
    # 時間資訊
    work_date = models.DateField(verbose_name="日期")
    start_time = models.TimeField(verbose_name="開始時間")
    end_time = models.TimeField(verbose_name="結束時間")
    
    # 數量資訊
    work_quantity = models.IntegerField(verbose_name="工作數量")
    defect_quantity = models.IntegerField(default=0, verbose_name="不良品數量")
    
    # 完工判斷
    is_completed = models.BooleanField(default=False, verbose_name="是否已完工")
    completion_method = models.CharField(max_length=20, choices=COMPLETION_METHOD_CHOICES, default='manual', verbose_name="完工判斷方式")
    auto_completed = models.BooleanField(default=False, verbose_name="自動完工狀態")
    completion_time = models.DateTimeField(blank=True, null=True, verbose_name="完工確認時間")
    
    # 累積資料
    cumulative_quantity = models.IntegerField(default=0, verbose_name="累積完成數量")
    cumulative_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="累積工時")
    
    # 審核狀態
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending', verbose_name="審核狀態")
    approved_by = models.CharField(max_length=100, blank=True, null=True, verbose_name="審核人員")
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="審核時間")
    approval_remarks = models.TextField(blank=True, verbose_name="審核備註")
    rejection_reason = models.TextField(blank=True, verbose_name="駁回原因")
    
    # 備註
    remarks = models.TextField(blank=True, verbose_name="備註")
    abnormal_notes = models.TextField(blank=True, verbose_name="異常記錄")
    
    # 系統欄位
    created_by = models.CharField(max_length=100, verbose_name="建立人員")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
```

## 功能頁面

### 1. 報工記錄列表 (`/workorder/report/manager/production/`)
- 顯示所有管理者審核記錄
- 支援搜尋、篩選和分頁
- 統計資訊顯示
- 快速操作按鈕（查看、編輯、刪除、審核）

### 2. 新增報工記錄 (`/workorder/report/manager/production/create/`)
- 完整的報工記錄表單
- 自動帶出工單資訊
- 時間選擇器
- 表單驗證

### 3. 編輯報工記錄 (`/workorder/report/manager/production/edit/<id>/`)
- 編輯現有報工記錄
- 權限控制
- 已審核記錄不可編輯

### 4. 報工記錄詳情 (`/workorder/report/manager/production/detail/<id>/`)
- 詳細的報工記錄資訊
- 統計資料顯示
- 完工狀態和審核狀態

### 5. 批量創建 (`/workorder/report/manager/production/batch/`)
- 批量創建報工記錄
- 日期範圍選擇
- 預覽功能
- 批量驗證

## API 端點

### 1. 批量創建 API
```
POST /workorder/api/manager/production/batch_create/
```

### 2. 取得工單資訊 API
```
GET /workorder/api/manager/production/workorders/
```

### 3. 取得報工詳細資訊 API
```
GET /workorder/api/manager/production/details/
```

### 4. 審核 API
```
POST /workorder/report/manager/production/approve/<id>/
POST /workorder/report/manager/production/reject/<id>/
```

### 5. 刪除 API
```
POST /workorder/report/manager/production/delete/<id>/
```

## 權限控制

### 1. 編輯權限
- 已審核的記錄不可編輯
- 只有建立者或超級用戶可以編輯

### 2. 刪除權限
- 已審核的記錄不可刪除
- 只有建立者或超級用戶可以刪除

### 3. 審核權限
- 只有超級用戶或管理者群組可以審核
- 已審核的記錄不可重複審核

## 自動化功能

### 1. 累積資料更新
- 自動計算累積完成數量
- 自動計算累積工時
- 更新時自動重新計算

### 2. 自動完工判斷
- 根據完工判斷方式自動判斷完工狀態
- 支援多種完工判斷邏輯
- 自動記錄完工時間

### 3. 資料驗證
- 時間格式驗證
- 數量驗證
- 日期範圍驗證

## 使用流程

### 1. 新增報工記錄
1. 進入新增頁面
2. 選擇管理者
3. 選擇產品編號（自動帶出工單）
4. 選擇工序、設備、作業員
5. 設定時間和數量
6. 選擇完工判斷方式
7. 填寫備註
8. 儲存記錄

### 2. 審核流程
1. 管理者提交報工記錄
2. 審核人員查看記錄
3. 進行審核或駁回
4. 填寫審核備註或駁回原因
5. 完成審核流程

### 3. 批量創建
1. 進入批量創建頁面
2. 設定基本資訊
3. 選擇日期範圍
4. 設定每日時間和數量
5. 預覽創建結果
6. 確認批量創建

## 技術特點

### 1. 前端技術
- Bootstrap 5 響應式設計
- Flatpickr 時間選擇器
- 原生 JavaScript 互動
- AJAX 非同步操作

### 2. 後端技術
- Django 5.1.8 框架
- PostgreSQL 資料庫
- 完整的 CRUD 操作
- RESTful API 設計

### 3. 資料驗證
- 前端 JavaScript 驗證
- 後端 Django 表單驗證
- 資料庫約束驗證

## 注意事項

1. **時間格式**：所有時間都使用 24 小時制，格式為 HH:MM
2. **日期格式**：使用 YYYY-MM-DD 格式
3. **權限控制**：嚴格遵循權限控制機制
4. **資料完整性**：確保資料的一致性和完整性
5. **效能優化**：大量資料時注意查詢效能

## 未來擴展

1. **報表功能**：新增管理者審核統計報表
2. **通知機制**：新增審核通知功能
3. **工作流程**：支援更複雜的審核工作流程
4. **行動裝置**：開發行動裝置版本
5. **整合功能**：與其他模組的深度整合 