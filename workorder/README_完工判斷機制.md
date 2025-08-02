# 工單完工判斷機制說明文件

## 概述

本機制實現了基於「出貨包裝」工序報工數量的自動完工判斷功能。當工單的出貨包裝報工數量達到工單目標數量時，系統會自動將工單標記為完工，並將資料從生產中工單轉移到已完工工單資料表。

## 核心功能

### 1. 完工判斷邏輯

- **判斷條件**：出貨包裝工序的報工數量 ≥ 工單目標數量
- **工序名稱**：`出貨包裝`（可配置）
- **報工記錄**：只統計已核准的出貨包裝報工記錄
- **數量計算**：統計良品數量（`work_quantity`）

### 2. 自動完工流程

1. **狀態更新**：將工單狀態從 `in_progress` 更新為 `completed`
2. **生產記錄更新**：更新生產記錄的結束時間和狀態
3. **工序狀態更新**：將所有工序狀態更新為 `completed`
4. **資料轉移**：將完整資料轉移到已完工工單資料表
5. **資料清理**：從生產中工單資料表移除已完工的資料

### 3. 資料轉移內容

- **工單基本資訊**：工單號、產品編號、數量等
- **統計資料**：總工時、加班時數、良品數量、不良品數量等
- **工序資料**：所有工序的執行狀況和統計
- **報工記錄**：所有已核准的報工記錄

## 使用方法

### 1. 自動觸發

當有新的出貨包裝報工記錄被核准時，系統會自動檢查該工單是否達到完工條件：

```python
# 信號處理器會自動觸發
@receiver(post_save, sender=OperatorSupplementReport)
def check_workorder_completion(sender, instance, created, **kwargs):
    if (instance.approval_status == 'approved' and 
        instance.process == WorkOrderCompletionService.PACKAGING_PROCESS_NAME):
        WorkOrderCompletionService.check_and_complete_workorder(instance.workorder.id)
```

### 2. 手動檢查

#### 使用管理命令

```bash
# 檢查所有生產中工單
python manage.py check_workorder_completion

# 乾跑模式（僅檢查不執行）
python manage.py check_workorder_completion --dry-run

# 檢查特定工單
python manage.py check_workorder_completion --workorder-id 123
```

#### 使用網頁介面

訪問 `/workorder/completion-check/` 頁面，可以：

- 查看所有生產中工單的完工進度
- 手動檢查特定工單的完工狀態
- 批量檢查所有生產中工單

### 3. 定時任務

系統會定期執行完工檢查任務：

```python
@shared_task
def auto_check_workorder_completion():
    # 自動檢查所有生產中工單
    production_workorders = WorkOrder.objects.filter(status='in_progress')
    for workorder in production_workorders:
        WorkOrderCompletionService.check_and_complete_workorder(workorder.id)
```

## 檔案結構

```
workorder/
├── services/
│   └── completion_service.py      # 完工服務核心邏輯
├── signals.py                     # 信號處理器
├── tasks.py                       # 定時任務
├── management/commands/
│   └── check_workorder_completion.py  # 管理命令
├── templates/workorder/
│   └── completion_check.html      # 完工檢查頁面
└── views_main.py                  # 完工檢查視圖
```

## 核心類別和方法

### WorkOrderCompletionService

主要的完工處理服務類別：

```python
class WorkOrderCompletionService:
    PACKAGING_PROCESS_NAME = "出貨包裝"
    
    @staticmethod
    def check_and_complete_workorder(workorder_id):
        """檢查工單是否達到完工條件並自動完工"""
        
    @staticmethod
    def _get_packaging_quantity(workorder):
        """獲取工單的出貨包裝報工數量"""
        
    @staticmethod
    def _complete_workorder(workorder):
        """執行工單完工流程"""
        
    @staticmethod
    def transfer_workorder_to_completed(workorder_id):
        """將完工的工單資料轉移到已完工工單模組"""
        
    @staticmethod
    def _cleanup_production_data(workorder):
        """清理生產中工單的資料"""
```

## 配置說明

### 1. 工序名稱配置

可以在 `WorkOrderCompletionService` 中修改出貨包裝工序的名稱：

```python
class WorkOrderCompletionService:
    PACKAGING_PROCESS_NAME = "出貨包裝"  # 可根據實際需求修改
```

### 2. 信號註冊

確保在 `workorder/apps.py` 中正確註冊信號：

```python
def ready(self):
    import workorder.signals
```

## 注意事項

### 1. 資料完整性

- 只有已核准的出貨包裝報工記錄才會被計入完工判斷
- 系統會自動處理資料轉移和清理，確保資料一致性
- 使用資料庫事務確保操作的原子性

### 2. 性能考量

- 大量工單時建議使用定時任務而非即時觸發
- 可以配置檢查間隔以平衡即時性和系統負載

### 3. 錯誤處理

- 所有操作都有完整的錯誤處理和日誌記錄
- 失敗的操作不會影響其他工單的處理

## 日誌記錄

系統會記錄所有完工相關的操作：

```
INFO: 工單 WO-2024-001 出貨包裝數量 100 達到目標數量 100，開始完工流程
INFO: 工單 WO-2024-001 狀態已更新為完工
INFO: 工單 WO-2024-001 成功轉移到已完工模組
INFO: 工單 WO-2024-001 的生產中資料已清理
```

## 故障排除

### 1. 工單未自動完工

檢查項目：
- 出貨包裝報工記錄是否已核准
- 工序名稱是否正確（預設為「出貨包裝」）
- 報工數量是否達到工單目標數量

### 2. 資料轉移失敗

檢查項目：
- 資料庫連線是否正常
- 相關資料表是否存在
- 權限是否足夠

### 3. 信號未觸發

檢查項目：
- 信號是否正確註冊
- 應用是否正確啟動
- 日誌中是否有錯誤訊息

## 未來擴展

1. **多工序完工判斷**：支援多個工序的完工判斷
2. **自定義完工條件**：允許配置不同的完工判斷規則
3. **完工通知**：完工時發送通知給相關人員
4. **完工統計報表**：提供完工統計和分析功能 