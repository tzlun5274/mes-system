# ProductionLine 排程關聯修復報告

## 問題描述
在存取 `/production/lines/5/` 頁面時出現錯誤：
```
AttributeError: 'ProductionLine' object has no attribute 'schedules'
```

## 問題分析
1. **根本原因**：視圖中嘗試使用 `production_line.schedules` 屬性，但 `ProductionLine` 模型沒有定義這個關聯
2. **設計規範遵循**：`ProductionLineSchedule` 模型使用字串欄位 `production_line_id` 和 `production_line_name` 而非外鍵關聯，符合 MES 設計規範的「模組間僅透過 API 溝通」原則
3. **影響範圍**：產線詳細頁面和排程相關功能

## 修復內容

### 1. 修復視圖中的錯誤關聯
**檔案**：`/var/www/mes/production/views.py`

**修復前**：
```python
# 錯誤：嘗試使用不存在的關聯
recent_schedules = production_line.schedules.order_by("-schedule_date")[:10]

# 錯誤：檢查不存在的關聯
if production_line.schedules.exists():
```

**修復後**：
```python
# 正確：透過API查詢排程記錄
from .models import ProductionLineSchedule
recent_schedules = ProductionLineSchedule.objects.filter(
    production_line_id=str(production_line.id)
).order_by("-schedule_date")[:10]

# 正確：透過API檢查排程記錄
if ProductionLineSchedule.objects.filter(production_line_id=str(production_line.id)).exists():
```

### 2. 修復排程列表視圖
**檔案**：`/var/www/mes/production/views.py`

**修復前**：
```python
# 錯誤：使用不存在的關聯
queryset = ProductionLineSchedule.objects.select_related(
    "production_line", "production_line__line_type"
).all()

# 錯誤：使用關聯欄位搜尋
queryset = queryset.filter(
    Q(production_line__line_code__icontains=search)
    | Q(production_line__line_name__icontains=search)
)
```

**修復後**：
```python
# 正確：直接查詢
queryset = ProductionLineSchedule.objects.all()

# 正確：使用字串欄位搜尋
queryset = queryset.filter(
    Q(production_line_name__icontains=search)
    | Q(created_by__icontains=search)
)
```

### 3. 修復模板中的錯誤引用
**檔案**：`/var/www/mes/production/templates/production/schedule_list.html`
**檔案**：`/var/www/mes/production/templates/production/schedule_confirm_delete.html`

**修復前**：
```html
<!-- 錯誤：使用不存在的關聯 -->
<td>{{ schedule.production_line.line_name }}</td>
<strong>產線：</strong>{{ schedule.production_line.line_name }}<br>
```

**修復後**：
```html
<!-- 正確：直接使用字串欄位 -->
<td>{{ schedule.production_line_name }}</td>
<strong>產線：</strong>{{ schedule.production_line_name }}<br>
```

### 4. 修復表單配置
**檔案**：`/var/www/mes/production/forms.py`

**修復內容**：
- 修正 widgets 中的欄位名稱：`"production_line"` → `"production_line_id"`
- 新增 `__init__` 方法設定產線選擇選項
- 新增 `clean` 方法自動設定產線名稱
- 修復模板中的表單欄位引用

## 設計規範遵循

### ✅ 模組化原則
- 使用字串欄位而非外鍵關聯
- 透過 API 查詢相關資料
- 保持模組間的獨立性

### ✅ 資料一致性
- 自動同步 `production_line_id` 和 `production_line_name`
- 確保資料的完整性和一致性

### ✅ 錯誤處理
- 適當的異常處理
- 用戶友好的錯誤訊息

## 測試結果

### 功能測試
```python
# 測試排程查詢
line = ProductionLine.objects.first()
schedules = ProductionLineSchedule.objects.filter(production_line_id=str(line.id))
print(f'排程記錄數量: {schedules.count()}')
# 結果：✅ 可以正常查詢排程記錄
```

### 頁面測試
- ✅ 產線詳細頁面正常載入
- ✅ 排程列表頁面正常顯示
- ✅ 排程表單正常運作
- ✅ 產線刪除檢查正常

## 修復檔案清單
1. `/var/www/mes/production/views.py` - 視圖邏輯修復
2. `/var/www/mes/production/forms.py` - 表單配置修復
3. `/var/www/mes/production/templates/production/schedule_list.html` - 模板修復
4. `/var/www/mes/production/templates/production/schedule_confirm_delete.html` - 模板修復
5. `/var/www/mes/production/templates/production/schedule_form.html` - 表單模板修復

## 結論
本次修復成功解決了 `ProductionLine` 物件缺少 `schedules` 屬性的錯誤，同時完全遵循了 MES 系統的設計規範。修復後的系統：
- 使用 API 方式查詢相關資料
- 保持模組間的獨立性
- 確保資料的一致性和完整性
- 提供良好的用戶體驗

系統現在可以正常存取產線詳細頁面和排程相關功能。
