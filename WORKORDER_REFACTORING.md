# Workorder 模組重構說明

## 🎯 重構目標

移除 `workorder` 模組中的重複功能，讓各模組職責更加明確：

- **`equip` 模組**：專責設備管理
- **`process` 模組**：專責工序和作業員管理  
- **`workorder` 模組**：專責工單管理

## ✅ 已移除的重複功能

### 1. 重複的 API 函數

**移除的函數：**
- `get_operators_and_equipments()` - 同時取得作業員和設備資料
- `get_operators_only()` - 取得作業員資料
- `get_equipments_only()` - 取得設備資料

**替代方案：**
- 作業員 API：移至 `process` 模組 (`/process/api/operators_only/`)
- 設備 API：移至 `equip` 模組 (`/equip/api/equipments/`)
- 綜合 API：移至 `equip` 模組 (`/equip/api/operators-and-equipments/`)

### 2. 重複的 URL 路由

**移除的路由：**
```python
path('get_operators_and_equipments/', views.get_operators_and_equipments, name='get_operators_and_equipments'),
path('get_operators_only/', views.get_operators_only, name='get_operators_only'),
path('get_equipments_only/', views.get_equipments_only, name='get_equipments_only'),
```

**新增的路由：**
```python
# equip/urls.py
path('api/equipments/', views.api_equipments, name='api_equipments'),
path('api/operators-and-equipments/', views.api_operators_and_equipments, name='api_operators_and_equipments'),

# process/urls.py  
path('api/operators_only/', views.api_operators_only, name='api_operators_only'),
```

## 🔄 前端調用更新

如果前端有使用這些 API，需要更新調用路徑：

**舊路徑：**
```javascript
// 取得作業員資料
fetch('/workorder/get_operators_only/')

// 取得設備資料  
fetch('/workorder/get_equipments_only/')

// 取得作業員和設備資料
fetch('/workorder/get_operators_and_equipments/')
```

**新路徑：**
```javascript
// 取得作業員資料
fetch('/process/api/operators_only/')

// 取得設備資料
fetch('/equip/api/equipments/')

// 取得作業員和設備資料
fetch('/equip/api/operators-and-equipments/')
```

## 📋 保留的功能

以下功能保留在 `workorder` 模組中，因為它們是工單管理的核心功能：

1. **工單管理**：`WorkOrder` 模型的 CRUD 操作
2. **工單工序管理**：`WorkOrderProcess` 模型的相關功能
3. **派工記錄**：`DispatchLog` 模型
4. **作業員和設備分配**：在工單工序中分配作業員和設備（這是工單管理的核心功能）
5. **報表功能**：生產報表、作業員報表等
6. **SMT 相關功能**：SMT 報工、補登等

## 🎯 重構效果

1. **職責明確**：各模組功能更加專注
2. **減少重複**：消除了 API 功能的重複實作
3. **易於維護**：相關功能集中在對應的模組中
4. **提高一致性**：統一的資料來源和 API 設計

## ⚠️ 注意事項

1. 前端需要更新 API 調用路徑
2. 如果有其他模組調用這些 API，也需要更新
3. 建議進行完整的測試，確保功能正常

## 📝 後續建議

1. 考慮建立統一的服務層來處理跨模組的業務邏輯
2. 進一步優化各模組的職責分工
3. 建立完整的 API 文檔
4. 添加單元測試確保重構後的功能正常 