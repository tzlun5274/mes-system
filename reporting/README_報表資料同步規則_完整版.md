# 報表資料來源同步規則 - 完整版

## 📋 專案概述

本文件詳細說明 MES 系統中報表資料來源同步的完整設計規則，包含核准後的補登報工和現場報工記錄同步到報表資料表的完整流程。

## 🏗️ 系統架構

### 資料流向圖
```
核准後的報工記錄 → 同步服務 → 報表資料表 → 報表展示
     ↓
工單完工 → 數量分擔 → 回寫報工記錄
```

### 核心組件
1. **同步服務** (`ReportDataSyncService`)
2. **管理命令** (`sync_report_data`, `allocate_workorder_quantity`)
3. **Celery 任務** (`auto_sync_report_data`)
4. **監控視圖** (`SyncStatusListView`, `SyncDashboardView`)
5. **設定管理** (`ReportSyncSettings`)

## 🔄 同步流程詳解

### 1. 工作時間報表同步

#### 資料來源
- `OperatorSupplementReport` (作業員補登報工)
- `SMTProductionReport` (SMT生產報工)
- `SupervisorProductionReport` (主管生產報工)

#### 同步條件
```python
# 只有已核准的報工記錄才會被同步
reports = OperatorSupplementReport.objects.filter(
    approval_status='approved',
    work_date__range=[date_from, date_to]
)
```

#### 重複檢查
```python
existing_record = WorkTimeReport.objects.filter(
    report_type='daily',
    report_date=report.work_date,
    worker_name=worker_name,
    workorder_number=workorder_number,
    process_name=process_name,
    start_time=start_time,
    end_time=end_time
).first()

if existing_record:
    skipped += 1
    continue
```

#### 計算邏輯
```python
# 工作時數計算
start_datetime = datetime.combine(report.work_date, report.start_time)
end_datetime = datetime.combine(report.work_date, report.end_time)
work_hours = (end_datetime - start_datetime).total_seconds() / 3600

# 良率計算
yield_rate = (completed_quantity / (completed_quantity + defect_quantity)) * 100

# 效率計算
efficiency_rate = completed_quantity / work_hours
```

### 2. 工單機種報表同步

#### 資料來源
- 同工作時間報表的資料來源
- 按工單和工序分組統計

#### 同步條件
```python
# 按工單和工序分組
workorder_groups = reports.values('workorder_number', 'product_id', 'process_name').annotate(
    total_completed=Sum('work_quantity'),
    total_defects=Sum('defect_quantity'),
    planned_qty=Max('planned_quantity')
)
```

#### 重複檢查
```python
existing_record = WorkOrderProductReport.objects.filter(
    workorder_number=workorder_number,
    product_code=product_code,
    process_name=process_name,
    report_date=report.work_date
).first()

if existing_record:
    skipped += 1
    continue
```

#### 計算邏輯
```python
# 完成率計算
completion_rate = (total_completed / planned_qty) * 100

# 良率計算
yield_rate = (total_completed / (total_completed + total_defects)) * 100
```

## 📊 工單數量分擔規則

### 分擔時機
1. 工單狀態變更為 `completed` 時
2. 手動執行數量分擔命令時
3. 自動定時檢查已完工工單

### 分擔邏輯
```python
def sync_workorder_allocation(self, workorder_id, force=False):
    # 1. 檢查工單狀態
    workorder = WorkOrder.objects.get(id=workorder_id)
    if not force and workorder.status != 'completed':
        return {'status': 'error', 'message': '工單尚未完工'}
    
    # 2. 取得工單工序明細
    processes = WorkOrderProcess.objects.filter(workorder=workorder)
    total_completed = sum([p.completed_quantity for p in processes])
    
    # 3. 取得相關報工記錄
    reports = OperatorSupplementReport.objects.filter(
        workorder=workorder,
        approval_status='approved'
    )
    
    # 4. 按工作時數比例分配
    total_hours = sum([report.work_hours for report in reports])
    
    for report in reports:
        allocation_ratio = report.work_hours / total_hours
        allocated_quantity = int(total_completed * allocation_ratio)
        
        # 5. 更新報工記錄
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
```python
def validate_report_data(self, report):
    """驗證報工記錄資料完整性"""
    required_fields = [
        'operator', 'workorder', 'product_id', 'process',
        'work_date', 'start_time', 'end_time', 'work_quantity'
    ]
    
    for field in required_fields:
        if not getattr(report, field, None):
            return False, f"缺少必要欄位: {field}"
    
    return True, "資料完整"
```

### 3. 事務處理
```python
@transaction.atomic
def sync_data(self, sync_type='all', date_from=None, date_to=None, user=None):
    """同步報表資料（事務處理）"""
    try:
        # 建立同步日誌
        sync_log = ReportDataSyncLog.objects.create(
            sync_type=sync_type,
            period_start=date_from,
            period_end=date_to,
            status='pending',
            started_at=timezone.now()
        )
        
        # 執行同步邏輯
        result = self._execute_sync(sync_type, date_from, date_to)
        
        # 更新同步日誌
        sync_log.status = 'success'
        sync_log.completed_at = timezone.now()
        sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
        sync_log.processed = result['processed']
        sync_log.created = result['created']
        sync_log.updated = result['updated']
        sync_log.details = json.dumps(result, ensure_ascii=False)
        sync_log.save()
        
        return result
        
    except Exception as e:
        # 記錄錯誤並回滾
        if 'sync_log' in locals():
            sync_log.status = 'error'
            sync_log.error_message = str(e)
            sync_log.save()
        
        raise
```

## 📈 同步監控

### 1. 同步日誌記錄
```python
class ReportDataSyncLog(models.Model):
    sync_type = models.CharField(max_length=20, verbose_name="同步類型")
    period_start = models.DateField(verbose_name="開始日期")
    period_end = models.DateField(verbose_name="結束日期")
    status = models.CharField(max_length=20, verbose_name="狀態")
    started_at = models.DateTimeField(verbose_name="開始時間")
    completed_at = models.DateTimeField(verbose_name="完成時間")
    duration_seconds = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="執行時間")
    processed = models.IntegerField(default=0, verbose_name="處理記錄數")
    created = models.IntegerField(default=0, verbose_name="新增記錄數")
    updated = models.IntegerField(default=0, verbose_name="更新記錄數")
    details = models.TextField(blank=True, verbose_name="詳細結果")
    error_message = models.TextField(blank=True, verbose_name="錯誤訊息")
```

### 2. 監控指標
- **同步成功率**：成功同步次數 / 總同步次數
- **平均執行時間**：所有同步的平均耗時
- **資料處理量**：每次同步處理的記錄數量
- **錯誤發生頻率**：同步失敗的頻率

### 3. 監控告警
```python
def check_sync_health(self):
    """檢查同步健康狀態"""
    # 檢查最近同步是否成功
    recent_syncs = ReportDataSyncLog.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    )
    
    success_rate = recent_syncs.filter(status='success').count() / recent_syncs.count()
    
    if success_rate < 0.8:  # 成功率低於80%
        # 發送告警
        self.send_alert(f"同步成功率過低: {success_rate:.2%}")
```

## 🚀 執行方式

### 1. 手動執行
```bash
# 執行全部同步
python manage.py sync_report_data --type all --date-from 2025-01-01 --date-to 2025-01-31

# 執行工作時間報表同步
python manage.py sync_report_data --type work_time --date-from 2025-01-01 --date-to 2025-01-31

# 執行工單機種報表同步
python manage.py sync_report_data --type work_order --date-from 2025-01-01 --date-to 2025-01-31

# 執行工單數量分擔
python manage.py allocate_workorder_quantity 123

# 強制執行（即使工單未完工）
python manage.py allocate_workorder_quantity 123 --force
```

### 2. 自動同步
```python
# Celery 任務
@shared_task
def auto_sync_report_data():
    """自動同步報表資料"""
    sync_service = ReportDataSyncService()
    
    # 讀取同步設定
    sync_settings = ReportSyncSettings.objects.filter(is_active=True)
    
    for setting in sync_settings:
        try:
            # 計算日期範圍
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=1)
            
            # 執行同步
            result = sync_service.sync_data(
                sync_type=setting.sync_type,
                date_from=start_date.strftime('%Y-%m-%d'),
                date_to=end_date.strftime('%Y-%m-%d'),
                user='system'
            )
            
            logger.info(f"自動同步完成: {result}")
            
        except Exception as e:
            logger.error(f"自動同步失敗: {str(e)}")
```

### 3. Web 介面執行
- 同步狀態列表：`/reporting/sync/`
- 同步儀表板：`/reporting/sync/dashboard/`
- 手動同步：`/reporting/sync/manual/`
- 同步設定：`/reporting/sync/settings/`

## 🔧 設定管理

### 1. 同步設定
```python
class ReportSyncSettings(models.Model):
    name = models.CharField(max_length=100, verbose_name="設定名稱")
    description = models.TextField(blank=True, verbose_name="設定描述")
    sync_type = models.CharField(max_length=20, verbose_name="同步類型")
    interval_minutes = models.IntegerField(verbose_name="執行間隔（分鐘）")
    is_active = models.BooleanField(default=True, verbose_name="是否啟用")
    created_by = models.CharField(max_length=100, verbose_name="建立者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_by = models.CharField(max_length=100, blank=True, verbose_name="更新者")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
```

### 2. 設定類型
- **工作時間報表**：同步作業員的工作時間、完成數量、效率等資料
- **工單機種報表**：同步工單的完成狀況、不良品數量、完成率等資料
- **全部同步**：同時執行工作時間報表和工單機種報表的同步

### 3. 執行間隔
- **5分鐘**：適用於高頻率資料更新
- **15分鐘**：適用於一般生產環境
- **30分鐘**：適用於低頻率資料更新
- **60分鐘**：適用於日報統計

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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
```

## 🛠️ 故障排除

### 常見問題
1. **同步失敗**
   - 檢查資料庫連線和權限
   - 檢查報工記錄的資料完整性
   - 查看同步日誌的錯誤訊息

2. **資料重複**
   - 檢查同步設定和重複檢查邏輯
   - 確認重複檢查的條件是否正確
   - 檢查是否有手動重複執行

3. **計算錯誤**
   - 檢查資料格式和計算邏輯
   - 驗證時間格式是否正確
   - 檢查除零錯誤

4. **效能問題**
   - 檢查資料庫索引
   - 優化查詢語句
   - 考慮分批處理大量資料

### 除錯方法
1. **查看同步日誌**
   ```bash
   # 查看最近的同步記錄
   python manage.py shell
   >>> from system.models import ReportDataSyncLog
   >>> ReportDataSyncLog.objects.order_by('-created_at')[:5]
   ```

2. **檢查錯誤訊息**
   ```bash
   # 查看錯誤的同步記錄
   >>> ReportDataSyncLog.objects.filter(status='error').order_by('-created_at')
   ```

3. **驗證資料完整性**
   ```bash
   # 檢查報工記錄
   >>> from workorder.models import OperatorSupplementReport
   >>> OperatorSupplementReport.objects.filter(approval_status='approved').count()
   ```

4. **測試同步功能**
   ```bash
   # 測試小範圍同步
   python manage.py sync_report_data --type work_time --date-from 2025-01-01 --date-to 2025-01-01
   ```

## 📝 最佳實踐

### 1. 同步頻率建議
- **工作時間報表**：每天同步一次
- **工單機種報表**：每天同步一次
- **數量分擔**：工單完工後立即執行

### 2. 效能優化
- 使用 `select_related()` 減少資料庫查詢
- 批量處理大量記錄
- 使用索引提升查詢效能
- 考慮使用資料庫視圖

### 3. 監控建議
- 定期檢查同步日誌
- 監控同步效能指標
- 設定同步失敗的警報機制
- 定期備份報表資料

### 4. 安全建議
- 只有超級用戶可以執行同步操作
- 記錄所有同步操作的詳細日誌
- 定期審查同步設定
- 設定資料庫備份策略

## 🔄 版本歷史

- **v1.0**：初始版本，基本同步功能
- **v1.1**：加入工單數量分擔功能
- **v1.2**：優化同步效能和錯誤處理
- **v1.3**：加入自動同步和監控功能
- **v1.4**：加入Web介面管理功能
- **v1.5**：完善同步防護機制

## 📞 技術支援

如有任何問題或建議，請聯繫：
- 系統管理員
- 技術支援團隊
- 開發團隊

---

**注意**：本文件會根據系統更新持續維護，請定期查看最新版本。 