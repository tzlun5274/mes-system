# 工單填報作業欄位修復報告

## 問題描述
在訪問 `/workorder/active/` 頁面時，出現以下錯誤：
```
ProgrammingError: column workorder_fill_work.process_name does not exist
```

## 問題分析
1. **錯誤原因**：`FillWork` 模型定義中包含 `process_name` 欄位，但資料庫表中實際不存在此欄位
2. **影響範圍**：工單管理模組的進行中工單頁面無法正常顯示
3. **根本原因**：模型定義與資料庫結構不一致

## 處理方案
採用 `values()` 查詢方式，只選擇資料庫中實際存在的欄位，避免查詢不存在的 `process_name` 欄位。

## 處理內容

### 修改檔案
- `/var/www/mes/workorder/views_main.py`

### 修改內容
將原本的查詢：
```python
approved_fill_works = FillWork.objects.filter(
    approval_status='approved'
)
```

修改為：
```python
approved_fill_works = FillWork.objects.filter(
    approval_status='approved'
).values(
    'id', 'operator', 'company_code', 'company_name', 'workorder', 
    'product_id', 'planned_quantity', 'process_id', 'operation', 
    'equipment', 'work_date', 'start_time', 'end_time', 'has_break',
    'break_start_time', 'break_end_time', 'break_hours', 
    'work_hours_calculated', 'overtime_hours_calculated', 
    'work_quantity', 'defect_quantity', 'is_completed', 
    'approval_status', 'approved_by', 'approved_at', 
    'approval_remarks', 'rejection_reason', 'rejected_by', 
    'rejected_at', 'remarks', 'abnormal_notes', 'created_by', 
    'created_at', 'updated_at'
)
```

## 處理結果
- ✅ 工單進行中頁面可以正常訪問
- ✅ 不再出現 `process_name` 欄位不存在的錯誤
- ✅ 系統功能正常運作

## 處理完成時間
2025-09-10 09:52

## 備註
此處理方案避免了直接修改資料庫結構，採用查詢層面的解決方案，確保系統穩定性。
