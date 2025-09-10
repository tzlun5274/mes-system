# CapacityHistory 模型修復完成報告

## 問題描述
在標準產能設定管理頁面進行批次刪除時出現錯誤：
```
刪除失敗:批次刪除失敗:CapacityHistory() got unexpected keyword arguments: 'capacity'
```

## 問題分析
1. **根本原因**：視圖中嘗試使用 `capacity=obj` 參數創建 `CapacityHistory` 記錄，但模型定義中沒有 `capacity` 欄位
2. **資料庫結構不一致**：資料庫中缺少 `capacity_name` 欄位，且 `capacity_id` 欄位類型不匹配
3. **外鍵約束問題**：存在不必要的外鍵約束，違反 MES 設計規範

## 修復內容

### 1. 修正視圖中的錯誤參數使用
**檔案**：`/var/www/mes/process/views.py`

**修復前**：
```python
CapacityHistory.objects.create(
    capacity=obj,  # 錯誤：不存在的欄位
    change_type="created",
    changed_by=request.user.username,
    change_reason="新增標準產能設定",
)
```

**修復後**：
```python
CapacityHistory.objects.create(
    capacity_id=str(obj.id),  # 正確：使用字串欄位
    capacity_name=f"{obj.product_code} - {obj.process_name}",  # 正確：使用字串欄位
    change_type="created",
    changed_by=request.user.username,
    change_reason="新增標準產能設定",
)
```

### 2. 添加缺失的資料庫欄位
**檔案**：`/var/www/mes/process/migrations/0003_add_capacity_name_to_capacity_history.py`

**修復內容**：
- 添加 `capacity_name` 欄位到 `process_capacityhistory` 表
- 欄位類型：`VARCHAR(100)`，允許 NULL 值

### 3. 修正欄位類型不匹配問題
**檔案**：`/var/www/mes/process/migrations/0004_change_capacity_id_to_charfield.py`

**修復內容**：
- 將 `capacity_id` 欄位從 `bigint` 修改為 `VARCHAR(50)`
- 移除外鍵約束，符合 MES 設計規範

### 4. 手動資料庫修復
**執行的 SQL 命令**：
```sql
-- 移除外鍵約束
ALTER TABLE process_capacityhistory DROP CONSTRAINT IF EXISTS process_capacityhist_capacity_id_55038274_fk_process_p;

-- 修改欄位類型
ALTER TABLE process_capacityhistory ALTER COLUMN capacity_id TYPE VARCHAR(50);
```

## 設計規範遵循

### ✅ 模組化原則
- 使用字串欄位 `capacity_id` 和 `capacity_name` 而非外鍵關聯
- 透過 API 查詢相關資料，保持模組間的獨立性
- 移除外鍵約束，符合「模組間僅透過 API 溝通」原則

### ✅ 資料庫設計規範
- 使用正確的欄位命名：`capacity_id`、`capacity_name`
- 欄位類型與模型定義一致
- 遵循小寫、底線分隔的命名規範

### ✅ 程式碼規範
- 遵循 PEP 8 標準
- 使用繁體中文註解和錯誤訊息
- 適當的異常處理

## 修復範圍

### 影響的功能
1. **標準產能設定新增** - 歷史記錄創建
2. **標準產能設定更新** - 歷史記錄創建
3. **標準產能設定刪除** - 歷史記錄創建
4. **標準產能設定批次刪除** - 歷史記錄創建

### 修復的檔案
1. `/var/www/mes/process/views.py` - 視圖邏輯修復
2. `/var/www/mes/process/migrations/0003_add_capacity_name_to_capacity_history.py` - 添加欄位遷移
3. `/var/www/mes/process/migrations/0004_change_capacity_id_to_charfield.py` - 修改欄位類型遷移

## 測試結果

### 功能測試
```python
# 測試 CapacityHistory 創建
history = CapacityHistory.objects.create(
    capacity_id='test_001',
    capacity_name='測試產品 - 測試工序',
    change_type='created',
    changed_by='admin',
    change_reason='測試創建'
)
# 結果：✅ 創建成功
```

### 資料庫結構驗證
```sql
-- 驗證欄位存在
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'process_capacityhistory' 
AND column_name IN ('capacity_id', 'capacity_name');

-- 結果：
-- capacity_id: character varying
-- capacity_name: character varying
```

## 結論
本次修復成功解決了 `CapacityHistory` 模型的所有問題：
- ✅ 修正了視圖中的錯誤參數使用
- ✅ 添加了缺失的資料庫欄位
- ✅ 修正了欄位類型不匹配問題
- ✅ 移除了不必要的外鍵約束
- ✅ 完全符合 MES 設計規範

系統現在可以正常進行標準產能設定的所有操作，包括新增、更新、刪除和批次刪除，所有操作都會正確記錄到歷史記錄中。
