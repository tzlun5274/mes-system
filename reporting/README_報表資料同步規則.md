# 報表資料來源同步規則

## 📋 概述

本文件說明 MES 系統中報表資料來源同步的設計規則，包含核准後的補登報工和現場報工記錄同步到報表資料表的完整流程。

## 🏗️ 同步架構

### 資料來源
- **補登報工記錄**：`OperatorSupplementReport`、`SMTProductionReport`、`SupervisorProductionReport`
- **現場報工記錄**：透過報工功能產生的即時記錄
- **核准狀態**：只有 `approval_status = 'approved'` 的記錄才會被同步

### 目標資料表
- **工作時間報表**：`WorkTimeReport` - 以工作時間為主
- **工單機種報表**：`WorkOrderProductReport` - 以工單和工序為主

## 🔄 同步流程

### 1. 工作時間報表同步 (`_sync_work_time_reports`)

#### 同步邏輯
- **資料來源**：已核准的報工記錄
- **主要維度**：作業員/設備 + 工單 + 工序 + 時間
- **統計重點**：工作時數、完成數量、效率、良率

#### 同步規則
```python
# 檢查重複記錄
existing_record = WorkTimeReport.objects.filter(
    report_type='daily',
    report_date=report.work_date,
    worker_name=worker_name,
    workorder_number=workorder_number,
    process_name=process_name,
    start_time=start_time,
    end_time=end_time
).first()

# 如果記錄已存在，跳過同步（避免重複）
if existing_record:
    skipped += 1
    continue
```

#### 計算邏輯
- **工作時數**：`(end_time - start_time).total_seconds() / 3600`
- **良率**：`(completed_quantity / (completed_quantity + defect_quantity)) * 100`
- **效率**：`completed_quantity / total_work_hours`

### 2. 工單機種報表同步 (`_sync_work_order_reports`)

#### 同步邏輯
- **資料來源**：已核准的報工記錄
- **主要維度**：工單 + 產品 + 工序
- **統計重點**：完成數量、不良數量、完成率、良率

#### 同步規則
```python
# 檢查重複記錄
existing_record = WorkOrderProductReport.objects.filter(
    workorder_number=workorder_number,
    product_code=product_code,
    process_name=process_name,
    report_date=report.work_date
).first()

# 如果記錄已存在，跳過同步（避免重複）
if existing_record:
    skipped += 1
    continue
```

#### 計算邏輯
- **完成率**：`(completed_quantity / planned_quantity) * 100`
- **良率**：`(completed_quantity / (completed_quantity + defect_quantity)) * 100`

## 📊 工單數量分擔規則

### 分擔時機
- 工單狀態變更為 `completed` 時
- 手動執行數量分擔命令時

### 分擔邏輯
```python
# 計算總工作時數
total_hours = sum([report.work_hours for report in reports])

# 按工作時數比例分配
for report in reports:
    allocation_ratio = report.work_hours / total_hours
    allocated_quantity = int(total_completed * allocation_ratio)
    
    # 更新報工記錄
    report.allocated_quantity = allocated_quantity
    report.allocation_notes = f"工單完工後按工作時數比例分配"
    report.save()
```

### 分擔規則
1. **按工作時數比例**：根據每個報工記錄的工作時數進行比例分配
2. **整數分配**：分配數量取整數，避免小數點問題
3. **記錄分擔說明**：在報工記錄中記錄分擔原因和計算方式
4. **防重複分擔**：已分擔的記錄不會重複分擔

## 🔒 同步防護機制

### 1. 重複檢查
- 同步前檢查目標資料表是否已存在相同記錄
- 檢查條件包含：日期、工單、作業員、工序、時間等關鍵欄位
- 避免重複同步造成資料重複

### 2. 資料完整性檢查
- 檢查必要欄位是否完整
- 驗證資料格式和範圍
- 記錄檢查失敗的記錄

### 3. 事務處理
- 使用資料庫事務確保同步的原子性
- 同步失敗時自動回滾
- 記錄詳細的錯誤訊息

## 📈 同步監控

### 1. 同步日誌
- 記錄每次同步的詳細資訊
- 包含處理數量、新增數量、更新數量、跳過數量
- 記錄同步執行時間和錯誤訊息

### 2. 同步狀態
- **成功**：同步正常完成
- **失敗**：同步過程中發生錯誤
- **等待中**：同步正在執行

### 3. 監控指標
- 同步成功率
- 平均執行時間
- 資料處理量
- 錯誤發生頻率

## 🚀 執行方式

### 1. 手動執行
```bash
# 執行全部同步
python manage.py sync_report_data --type all --date-from 2025-01-01 --date-to 2025-01-31

# 執行工作時間報表同步
python manage.py sync_report_data --type work_time --date-from 2025-01-01 --date-to 2025-01-31

# 執行工單機種報表同步
python manage.py sync_report_data --type work_order --date-from 2025-01-01 --date-to 2025-01-31
```

### 2. 工單數量分擔
```bash
# 執行工單數量分擔
python manage.py allocate_workorder_quantity 123

# 強制執行（即使工單未完工）
python manage.py allocate_workorder_quantity 123 --force
```

### 3. 自動同步
- 透過 Celery 任務定時執行
- 可設定執行間隔（5分鐘、15分鐘、30分鐘、60分鐘）
- 支援多種同步類型

## 🔧 設定管理

### 1. 同步設定
- **設定名稱**：易於識別的設定名稱
- **同步類型**：工作時間報表、工單機種報表、全部同步
- **執行間隔**：自動執行的時間間隔
- **啟用狀態**：是否啟用此設定

### 2. 設定管理功能
- 新增同步設定
- 編輯同步設定
- 啟用/停用設定
- 刪除同步設定

## 📊 報表資料結構

### WorkTimeReport（工作時間報表）
```python
class WorkTimeReport(models.Model):
    report_type = models.CharField(max_length=20, verbose_name="報表類型")
    report_date = models.DateField(verbose_name="報表日期")
    worker_name = models.CharField(max_length=100, verbose_name="作業員姓名")
    workorder_number = models.CharField(max_length=50, verbose_name="工單編號")
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    start_time = models.TimeField(verbose_name="開始時間")
    end_time = models.TimeField(verbose_name="結束時間")
    total_work_hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="總工作時數")
    completed_quantity = models.IntegerField(verbose_name="完成數量")
    defect_quantity = models.IntegerField(verbose_name="不良數量")
    yield_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="良率")
    efficiency_rate = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="效率")
```

### WorkOrderProductReport（工單機種報表）
```python
class WorkOrderProductReport(models.Model):
    workorder_number = models.CharField(max_length=50, verbose_name="工單編號")
    product_code = models.CharField(max_length=50, verbose_name="產品代號")
    product_name = models.CharField(max_length=100, verbose_name="產品名稱")
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    report_date = models.DateField(verbose_name="報表日期")
    planned_quantity = models.IntegerField(verbose_name="計劃數量")
    completed_quantity = models.IntegerField(verbose_name="完成數量")
    defect_quantity = models.IntegerField(verbose_name="不良數量")
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="完成率")
    yield_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="良率")
```

## 🛠️ 故障排除

### 常見問題
1. **同步失敗**：檢查資料庫連線和權限
2. **資料重複**：檢查同步設定和重複檢查邏輯
3. **計算錯誤**：檢查資料格式和計算邏輯
4. **效能問題**：檢查資料庫索引和查詢優化

### 除錯方法
1. 查看同步日誌
2. 檢查錯誤訊息
3. 驗證資料完整性
4. 測試同步功能

## 📝 注意事項

1. **資料一致性**：確保同步前後資料的一致性
2. **效能考量**：大量資料同步時注意效能影響
3. **備份策略**：同步前建議備份相關資料
4. **權限控制**：只有超級用戶可以執行同步操作
5. **監控告警**：設定同步失敗的告警機制

## 🔄 版本歷史

- **v1.0**：初始版本，基本同步功能
- **v1.1**：加入工單數量分擔功能
- **v1.2**：優化同步效能和錯誤處理
- **v1.3**：加入自動同步和監控功能 