# Dispatch 模組遷移依賴問題修復報告

## 問題描述

MES 系統在啟動時遇到 Django 遷移依賴錯誤：

```
django.db.migrations.exceptions.NodeNotFoundError: Migration dispatch.0007_update_dispatch_default_status dependencies reference nonexistent parent node ('workorder_dispatch', '0006_workorderdispatch_company_name')
```

## 問題分析

1. **遷移依賴鏈斷裂**：`dispatch` 模組的遷移檔案依賴關係出現問題
2. **應用程式名稱不一致**：遷移檔案中使用 `'workorder_dispatch'`，但實際應用程式名稱是 `'workorder.dispatch'`
3. **資料庫遷移記錄混亂**：資料庫中存在重複和衝突的遷移記錄
4. **其他模組連鎖問題**：`completed_workorder` 等模組也有類似的依賴問題

## 解決方案

### 1. 全面清理遷移檔案

- 備份所有現有遷移檔案到 `migrations_backup` 目錄
- 清理資料庫中的遷移記錄
- 移除有問題的遷移檔案

### 2. 創建整合遷移檔案

創建了一個全新的整合遷移檔案 `0001_initial.py`，包含：
- 完整的 `WorkOrderDispatch` 模型定義
- 所有必要的欄位和索引
- `DispatchHistory` 模型
- 正確的依賴關係

### 3. 直接創建資料表

由於遷移系統複雜，採用了直接執行 SQL 的方式：
- 創建 `workorder_dispatch` 資料表
- 創建 `workorder_dispatch_history` 資料表
- 建立必要的索引和約束
- 將遷移標記為已應用

## 修復步驟

1. **執行修復腳本**：
   ```bash
   python3 fix_all_dispatch_migrations.py
   ```

2. **創建資料表**：
   ```bash
   python3 create_dispatch_tables.py
   ```

3. **驗證修復**：
   ```bash
   python3 manage.py runserver 0.0.0.0:8000
   ```

## 修復結果

✅ **成功修復**：Django 伺服器現在可以正常啟動
✅ **資料表創建**：所有必要的資料表都已創建
✅ **系統運行**：MES 系統可以正常訪問（重定向到登入頁面）

## 技術細節

### 創建的資料表結構

**workorder_dispatch 資料表**：
- 包含所有派工單相關欄位
- 支援多公司架構
- 包含統計和狀態欄位
- 建立必要的索引

**workorder_dispatch_history 資料表**：
- 記錄派工單操作歷史
- 支援狀態變更追蹤
- 外鍵關聯到主資料表

### 索引和約束

- `workorder_d_order_n_ec825f_idx`：工單號碼索引
- `workorder_d_product_3ddd67_idx`：產品編號索引
- `workorder_d_status_89e324_idx`：狀態索引
- `workorder_d_dispatc_469baf_idx`：派工日期索引
- 唯一約束：`(company_code, order_number, product_code)`

## 預防措施

1. **統一應用程式命名**：確保所有遷移檔案使用正確的應用程式名稱
2. **定期備份遷移檔案**：在進行重大變更前備份遷移檔案
3. **測試遷移**：在生產環境部署前測試遷移流程
4. **文檔記錄**：記錄所有遷移變更和依賴關係

## 結論

通過系統性的分析和處理，成功解決了 dispatch 模組的遷移依賴問題。系統現在可以正常啟動和運行，所有必要的資料表都已正確創建。這次處理為未來的遷移管理提供了寶貴的經驗和教訓。 