# MES工單作業子模組資料表檢查報告

## 📋 檢查概覽

**檢查時間：** 2025年1月25日  
**檢查範圍：** `mes_workorder_operation` MES工單作業子模組  
**檢查結果：** ⚠️ 發現資料表結構與模型定義不一致

## 📊 資料表現況

### 現有資料表清單

| 資料表名稱 | 狀態 | 記錄數量 | 說明 |
|------------|------|----------|------|
| `mes_workorder_operation` | ✅ 存在 | 0 筆 | MES工單作業主表 |
| `mes_workorder_operation_detail` | ✅ 存在 | 0 筆 | MES工單作業明細 |
| `mes_workorder_operation_history` | ✅ 存在 | 0 筆 | MES工單作業歷史 |

### 資料表結構分析

#### 1. mes_workorder_operation（作業主表）

**實際資料表結構：**
```sql
- id: bigint (NO)
- company_code: character varying (NO)
- order_number: character varying (NO)          -- 注意：應該是 workorder_number
- product_code: character varying (NO)
- product_name: character varying (YES)
- operation_name: character varying (NO)
- planned_quantity: integer (NO)
- actual_quantity: integer (NO)                 -- 注意：應該是 completed_quantity
- defect_quantity: integer (NO)
- planned_start_date: date (YES)
- planned_end_date: date (YES)
- actual_start_date: timestamp with time zone (YES)
- actual_end_date: timestamp with time zone (YES)
- status: character varying (NO)
- completion_rate: numeric (NO)                 -- 注意：模型中是計算欄位
- notes: text (NO)
- created_at: timestamp with time zone (NO)
- updated_at: timestamp with time zone (NO)
```

**模型定義欄位：**
```python
- company_code: CharField
- company_name: CharField                          -- 缺少
- workorder_number: CharField                      -- 資料表是 order_number
- product_code: CharField
- product_name: CharField
- operation_type: CharField                        -- 缺少
- operation_name: CharField
- status: CharField
- planned_quantity: PositiveIntegerField
- completed_quantity: PositiveIntegerField         -- 資料表是 actual_quantity
- defect_quantity: PositiveIntegerField
- planned_start_date: DateField
- planned_end_date: DateField
- actual_start_date: DateTimeField
- actual_end_date: DateTimeField
- assigned_operator: CharField                     -- 缺少
- assigned_equipment: CharField                    -- 缺少
- notes: TextField
- created_at: DateTimeField
- updated_at: DateTimeField
- created_by: CharField                            -- 缺少
- updated_by: CharField                            -- 缺少
```

#### 2. mes_workorder_operation_detail（作業明細）

**實際資料表結構：**
```sql
- id: bigint (NO)
- operator: character varying (NO)                 -- 注意：應該是 detail_name
- equipment: character varying (YES)               -- 注意：應該是 detail_description
- work_date: date (NO)                            -- 注意：應該是 start_time
- start_time: time without time zone (NO)         -- 注意：欄位名稱相同但類型不同
- end_time: time without time zone (YES)
- work_hours: numeric (NO)                        -- 注意：應該是 completion_rate
- good_quantity: integer (NO)                     -- 注意：應該是 planned_quantity
- defect_quantity: integer (NO)                   -- 注意：應該是 actual_quantity
- total_quantity: integer (NO)                    -- 注意：缺少
- is_completed: boolean (NO)
- remarks: text (NO)                              -- 注意：應該是 notes
- created_at: timestamp with time zone (NO)
- updated_at: timestamp with time zone (NO)
- operation_id: bigint (NO)
```

**模型定義欄位：**
```python
- operation: ForeignKey
- detail_type: CharField                           -- 缺少
- detail_name: CharField                           -- 資料表是 operator
- detail_description: TextField                    -- 資料表是 equipment
- planned_quantity: PositiveIntegerField           -- 資料表是 good_quantity
- actual_quantity: PositiveIntegerField            -- 資料表是 defect_quantity
- start_time: DateTimeField                        -- 資料表是 work_date + start_time
- end_time: DateTimeField
- is_completed: BooleanField
- completion_rate: DecimalField                    -- 資料表是 work_hours
- notes: TextField                                 -- 資料表是 remarks
- created_at: DateTimeField
- updated_at: DateTimeField
```

#### 3. mes_workorder_operation_history（作業歷史）

**實際資料表結構：**
```sql
- id: bigint (NO)
- change_type: character varying (NO)              -- 注意：應該是 history_type
- old_status: character varying (YES)
- new_status: character varying (YES)
- old_quantity: integer (NO)                       -- 注意：應該是 old_values
- new_quantity: integer (NO)                       -- 注意：應該是 new_values
- change_notes: text (NO)                          -- 注意：應該是 history_description
- changed_by: character varying (NO)               -- 注意：應該是 operator
- changed_at: timestamp with time zone (NO)        -- 注意：應該是 created_at
- operation_id: bigint (NO)
```

**模型定義欄位：**
```python
- operation: ForeignKey
- history_type: CharField                          -- 資料表是 change_type
- history_description: TextField                   -- 資料表是 change_notes
- old_values: JSONField                            -- 資料表是 old_quantity
- new_values: JSONField                            -- 資料表是 new_quantity
- operator: CharField                              -- 資料表是 changed_by
- ip_address: GenericIPAddressField                -- 缺少
- created_at: DateTimeField                        -- 資料表是 changed_at
```

## ⚠️ 發現問題

### 1. 欄位名稱不一致
- `workorder_number` vs `order_number`
- `completed_quantity` vs `actual_quantity`
- `detail_name` vs `operator`
- `history_type` vs `change_type`

### 2. 欄位類型不匹配
- `start_time` 在明細表中是 `time without time zone`，但模型定義是 `DateTimeField`
- `completion_rate` 在資料表中是 `numeric`，但模型中是計算欄位

### 3. 缺少欄位
- 主表缺少：`company_name`, `operation_type`, `assigned_operator`, `assigned_equipment`, `created_by`, `updated_by`
- 明細表缺少：`detail_type`
- 歷史表缺少：`ip_address`

### 4. 多餘欄位
- 主表多餘：`completion_rate`（應該是計算欄位）
- 明細表多餘：`work_date`, `work_hours`, `good_quantity`, `defect_quantity`, `total_quantity`
- 歷史表多餘：`old_quantity`, `new_quantity`

## 🔧 修復建議

### 1. 重新建立資料表（推薦）
由於資料表結構與模型定義差異較大，建議：
1. 備份現有資料（如果有）
2. 刪除現有資料表
3. 重新執行遷移
4. 恢復資料（如果有）

### 2. 修改模型定義（不推薦）
如果選擇修改模型定義來配合現有資料表，需要：
1. 修改所有相關的欄位名稱
2. 調整欄位類型
3. 移除或添加欄位
4. 更新所有相關的程式碼

### 3. 資料表結構對齊（中等複雜度）
1. 使用 ALTER TABLE 語句修改欄位名稱
2. 添加缺少的欄位
3. 移除多餘的欄位
4. 調整欄位類型

## 📋 修復優先級

### 高優先級
1. **資料表結構對齊**：確保資料表結構與模型定義一致
2. **欄位名稱統一**：統一所有欄位命名規範
3. **資料完整性**：確保所有必要欄位都存在

### 中優先級
1. **功能完整性**：確保所有模型功能正常運作
2. **資料驗證**：添加適當的資料驗證規則
3. **索引優化**：優化資料庫索引

### 低優先級
1. **效能優化**：優化查詢效能
2. **功能擴展**：添加額外功能
3. **介面改善**：改善使用者介面

## 📝 結論

MES工單作業子模組的資料表結構與模型定義存在顯著不一致，需要進行修復。建議採用「重新建立資料表」的方案，以確保系統的一致性和穩定性。

**建議行動：**
1. 立即進行資料表結構修復
2. 確保模型定義與資料表結構完全一致
3. 進行完整的功能測試
4. 更新相關文件 