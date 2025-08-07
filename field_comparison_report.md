# 作業員報工與SMT報工資料表欄位對比報告

## 📊 欄位對比總覽

### 共同欄位（完全一致）
| 欄位名稱 | 欄位類型 | 說明 |
|---------|---------|------|
| id | BigAutoField | 主鍵ID |
| company_code | CharField | 公司代號 |
| product_id | CharField | 產品編號 |
| workorder | ForeignKey | 工單號碼 |
| original_workorder_number | CharField | 原始工單號碼 |
| planned_quantity | IntegerField | 工單預設生產數量 |
| process | ForeignKey | 工序 |
| operation | CharField | 工序名稱 |
| equipment | ForeignKey | 使用的設備 |
| work_date | DateField | 日期 |
| start_time | TimeField | 開始時間 |
| end_time | TimeField | 結束時間 |
| work_hours_calculated | DecimalField | 工作時數 |
| overtime_hours_calculated | DecimalField | 加班時數 |
| work_quantity | IntegerField | 工作數量 |
| defect_quantity | IntegerField | 不良品數量 |
| is_completed | BooleanField | 是否已完工 |
| has_break | BooleanField | 是否有休息時間 |
| break_start_time | TimeField | 休息開始時間 |
| break_end_time | TimeField | 休息結束時間 |
| break_hours | DecimalField | 休息時數 |
| approval_status | CharField | 核准狀態 |
| approved_by | CharField | 核准人員 |
| approved_at | DateTimeField | 核准時間 |
| approval_remarks | TextField | 核准備註 |
| rejection_reason | TextField | 駁回原因 |
| rejected_by | CharField | 駁回人員 |
| rejected_at | DateTimeField | 駁回時間 |
| created_by | CharField | 建立人員 |
| created_at | DateTimeField | 建立時間 |
| updated_at | DateTimeField | 更新時間 |

### 作業員報工特有欄位
| 欄位名稱 | 欄位類型 | 說明 |
|---------|---------|------|
| operator | ForeignKey | 作業員（外鍵關聯） |
| allocated_quantity | IntegerField | 分配數量 |
| quantity_source | CharField | 數量來源 |
| allocation_notes | TextField | 分配說明 |
| allocation_checked | BooleanField | 已檢查自動分配 |
| allocation_checked_at | DateTimeField | 分配檢查時間 |
| allocation_check_result | CharField | 分配檢查結果 |
| completion_method | CharField | 完工判斷方式 |
| auto_completed | BooleanField | 自動完工狀態 |
| completion_time | DateTimeField | 完工確認時間 |
| cumulative_quantity | IntegerField | 累積完成數量 |
| cumulative_hours | DecimalField | 累積工時 |
| remarks | TextField | 備註 |
| abnormal_notes | TextField | 異常記錄 |

### SMT報工特有欄位
| 欄位名稱 | 欄位類型 | 說明 |
|---------|---------|------|
| operator | CharField | 作業員（字串欄位） |
| equipment_operator_name | CharField | 設備作業員名稱 |

## ⚠️ 不一致的欄位

### 1. operator 欄位類型不一致
- **作業員報工**: `operator` 為 `ForeignKey` 關聯到 `process.Operator`
- **SMT報工**: `operator` 為 `CharField` 字串欄位

### 2. 作業員報工缺少的欄位
- **SMT報工有**: `equipment_operator_name` (設備作業員名稱)
- **作業員報工沒有**: 此欄位

### 3. SMT報工缺少的欄位
作業員報工有許多智能分配和完工管理相關欄位，SMT報工都沒有：
- `allocated_quantity` (分配數量)
- `quantity_source` (數量來源)
- `allocation_notes` (分配說明)
- `allocation_checked` (已檢查自動分配)
- `allocation_checked_at` (分配檢查時間)
- `allocation_check_result` (分配檢查結果)
- `completion_method` (完工判斷方式)
- `auto_completed` (自動完工狀態)
- `completion_time` (完工確認時間)
- `cumulative_quantity` (累積完成數量)
- `cumulative_hours` (累積工時)
- `remarks` (備註)
- `abnormal_notes` (異常記錄)

## 🔧 建議修正方案

### 方案一：統一 operator 欄位類型
將 SMT報工的 `operator` 欄位改為 `ForeignKey`，與作業員報工保持一致：

```python
# 在 SMTProductionReport 中
operator = models.ForeignKey(
    "process.Operator",
    on_delete=models.CASCADE,
    verbose_name="作業員",
    help_text="SMT設備的作業員",
    null=True,
    blank=True,
)
```

### 方案二：為 SMT報工添加缺失欄位
為 SMTProductionReport 添加作業員報工中的智能分配和完工管理欄位：

```python
# 添加智能分配相關欄位
allocated_quantity = models.IntegerField(
    default=0,
    verbose_name="分配數量",
    help_text="系統智能分配的數量"
)

quantity_source = models.CharField(
    max_length=20,
    choices=[
        ('original', '原始數量'),
        ('allocated', '智能分配'),
    ],
    default='original',
    verbose_name="數量來源",
    help_text="數量的來源類型"
)

# 添加完工管理相關欄位
completion_method = models.CharField(
    max_length=20,
    choices=[
        ("manual", "手動勾選"),
        ("auto_quantity", "自動依數量判斷"),
        ("auto_time", "自動依工時判斷"),
        ("auto_system", "系統自動判斷"),
    ],
    default="manual",
    verbose_name="完工判斷方式",
    help_text="選擇如何判斷此筆記錄是否代表工單完工",
)

auto_completed = models.BooleanField(
    default=False,
    verbose_name="自動完工狀態",
    help_text="系統根據累積數量或工時自動判斷的完工狀態",
)

# 添加其他必要欄位...
```

### 方案三：保持現狀但統一命名規範
如果兩個模型的功能確實不同，建議：
1. 統一欄位命名規範
2. 確保共同欄位的資料類型和約束一致
3. 為不同功能保留專用欄位

## 📋 結論

目前兩個模型的欄位存在以下主要問題：
1. **operator 欄位類型不一致** - 影響資料一致性和查詢效率
2. **SMT報工缺少智能分配功能** - 可能影響報表統計的準確性
3. **欄位命名和功能定位不夠統一** - 影響系統維護和擴展

建議採用**方案二**，為 SMT報工添加必要的智能分配和完工管理欄位，同時統一 operator 欄位類型，這樣可以確保兩個模型在功能上的一致性，便於後續的報表統計和資料分析。 