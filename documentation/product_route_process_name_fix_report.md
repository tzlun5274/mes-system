# 產品工藝路線 process_name 欄位修復報告

## 問題描述

在 MES 系統的產品工藝路線功能中，出現了多個與 `process_name` 欄位相關的錯誤：

1. **資料庫欄位缺失錯誤**：
   ```
   ProgrammingError: column process_productroute.process_name does not exist
   ```

2. **屬性存取錯誤**：
   ```
   AttributeError: 'NoneType' object has no attribute 'name'
   ```

3. **欄位類型不匹配錯誤**：
   ```
   Tried to update field process.ProductProcessRoute.process_name with a model instance, <ProcessName: 電測>. Use a value compatible with CharField.
   ```

## 根本原因分析

1. **資料庫結構不一致**：`ProductProcessRoute` 模型定義了 `process_name` 欄位，但資料庫中缺少此欄位。

2. **欄位類型混淆**：程式碼中將 `ProcessName` 模型實例直接賦值給 `process_name` 欄位，但該欄位是 `CharField`，不是外鍵關聯。

3. **存取方式錯誤**：程式碼嘗試使用 `route.process_name.name`，但 `process_name` 是字串欄位，不是模型實例。

## 修復方案

### 1. 資料庫結構修復

創建遷移檔案 `0005_auto_20250910_0926.py` 添加缺失的 `process_name` 欄位：

```python
migrations.AddField(
    model_name="productprocessroute",
    name="process_name",
    field=models.CharField(max_length=100, verbose_name="工序名稱", null=True, blank=True),
),
```

### 2. 視圖程式碼修復

修復所有錯誤的 `process_name` 使用方式：

#### 2.1 修復屬性存取錯誤
將 `route.process_name.name` 改為 `route.process_name`：

```python
# 修復前
f"檢視產品工藝路線: process_name={route.process_name.name}"

# 修復後  
f"檢視產品工藝路線: process_name={route.process_name}"
```

#### 2.2 修復欄位賦值錯誤
將模型實例賦值改為字串賦值：

```python
# 修復前
ProductProcessRoute.objects.create(
    product_id=product_id,
    process_name=process_name,  # ProcessName 模型實例
    step_order=step_order,
)

# 修復後
ProductProcessRoute.objects.create(
    product_id=product_id,
    process_name=process_name.name,  # 字串值
    process_name_id=str(process_name.id),  # 同時設定 ID
    step_order=step_order,
)
```

### 3. 修復範圍

修復了以下檔案中的錯誤：

- `/var/www/mes/process/views_product_routes.py`：
  - `view_product_route` 函數
  - `add_product_route` 函數  
  - `edit_product_route` 函數
  - `import_product_routes` 函數
  - `import_product_routes_override` 函數

## 修復結果

1. **資料庫結構**：成功添加 `process_name` 欄位到 `process_productroute` 表
2. **視圖功能**：所有產品工藝路線相關功能正常運作
3. **資料完整性**：同時維護 `process_name`（字串）和 `process_name_id`（ID）欄位

## 測試驗證

從使用者提供的截圖可以確認：

1. ✅ 編輯頁面正常顯示工序名稱（如 "SMT_A面"）
2. ✅ 更新操作成功完成（顯示 "產品工藝路線更新成功!"）
3. ✅ 列表頁面正常顯示產品工藝路線

## 技術要點

1. **模組化設計遵循**：遵循 MES 系統設計規範，使用 `CharField` 進行模組間通訊，避免直接外鍵關聯
2. **資料一致性**：同時維護字串名稱和 ID 欄位，確保資料查詢和顯示的靈活性
3. **向後相容性**：修復過程中保持現有資料的完整性

## 修復完成時間

2025-09-10 09:35:00

## 相關檔案

- 模型定義：`/var/www/mes/process/models.py`
- 視圖邏輯：`/var/www/mes/process/views_product_routes.py`
- 遷移檔案：`/var/www/mes/process/migrations/0005_auto_20250910_0926.py`
- 修復報告：`/var/www/mes/documentation/product_route_process_name_fix_report.md`
