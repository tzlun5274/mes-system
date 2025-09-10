# 工單模組 Process 欄位修復報告

## 問題描述
在訪問 `/workorder/active/` 頁面時，出現以下錯誤：
```
FieldError: Cannot resolve keyword 'process' into field
```

## 問題分析
1. **錯誤原因**：多個檔案中使用了 `process__name` 查詢，但 `FillWork` 模型沒有 `process` 外鍵關係
2. **影響範圍**：工單管理模組多個功能無法正常運作
3. **根本原因**：模型設計使用 `CharField` 而非 `ForeignKey`，但查詢時仍使用外鍵語法

## 處理方案
將所有 `process__name` 查詢改為 `process_name` 查詢，符合實際的模型欄位設計。

## 處理內容

### 修改檔案
1. `/var/www/mes/workorder/views_main.py`
2. `/var/www/mes/workorder/fill_work/views.py`
3. `/var/www/mes/workorder/workorder_dispatch/models.py`
4. `/var/www/mes/workorder/services/completion_service.py`
5. `/var/www/mes/workorder/onsite_reporting/signals.py`
6. `/var/www/mes/workorder/services/process_update_service.py`
7. `/var/www/mes/workorder/views_import.py`

### 修改內容
將所有 `process__name` 相關查詢改為 `process_name`：

**範例修改：**
```python
# 修改前
packaging_fillwork_reports = FillWork.objects.filter(
    approval_status='approved',
    process__name__exact='出貨包裝'
)

# 修改後
packaging_fillwork_reports = FillWork.objects.filter(
    approval_status='approved',
    process_name__exact='出貨包裝'
)
```

**處理的查詢類型：**
- `process__name__exact` → `process_name__exact`
- `process__name__icontains` → `process_name__icontains`
- `process__name` → `process_name`

## 處理結果
- ✅ 工單進行中頁面可以正常訪問
- ✅ 填報作業相關功能正常運作
- ✅ 派工單統計功能正常運作
- ✅ 現場報工功能正常運作
- ✅ 匯入功能正常運作

## 處理完成時間
2025-09-10 09:54

## 備註
此處理確保了模型設計與查詢語法的一致性，符合 MES 系統的模組化架構設計原則。
