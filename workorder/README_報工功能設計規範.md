# MES 報工功能設計規範

## 📋 概述
本文件說明 MES 系統中報工功能的設計規範、共用表單位置、使用方式，以及各模組的設計原則。

## 🏗️ 模組層級關係
```
工單管理（主模組）
├── 報工管理（次模組）
    ├── SMT報工（SMT專用）
    │   ├── SMT現場報工
    │   └── SMT補登報工
    └── 作業員報工（一般作業員用）
        ├── 作業員現場報工
        ├── 作業員補登報工
        └── 作業員RD樣品補登報工
```

## 📍 共用表單位置與使用方式

### 共用表單資訊
- **名稱**：`ProductionReportBaseForm`
- **位置**：`workorder/forms.py` 第15行開始
- **用途**：所有報工（SMT、RD樣品、一般補登）都必須繼承這個表單

### 使用方式
```python
# 1. 直接繼承（無額外欄位）
class SMTSupplementReportForm(ProductionReportBaseForm):
    pass

# 2. 繼承並加專屬欄位
class RDSampleSupplementReportForm(ProductionReportBaseForm):
    rd_sample_code = forms.CharField(label="RD樣品編號")
    rd_project_name = forms.CharField(label="專案名稱")
```

## 🎯 設計原則

### 1. 統一性
- 所有報工表單都必須繼承 `ProductionReportBaseForm`
- 不可重複定義相同欄位
- 欄位名稱、型態、驗證規則要統一

### 2. 一致性
- 前端畫面風格統一
- 操作流程一致
- 錯誤處理方式相同

### 3. 擴展性
- 有特殊需求再於子類別加欄位
- 保持向後相容性
- 支援未來功能擴展

### 4. 模組化
- 每個報工類型都是獨立的子類別
- 不可共用表單類別
- 功能職責明確分離

## ⏰ 時間格式規範

### 標準格式
- **日期格式**：`YYYY-MM-DD`（例如：2025-01-15）
- **時間格式**：`HH:MM`（24小時制，例如：16:00、18:30）

### 禁止格式
- ❌ 上午、下午
- ❌ AM、PM
- ❌ 12小時制
- ❌ 其他現代化時間格式

### 原因
填報人員看不懂現代化格式，必須使用傳統的24小時制格式。

## 📝 表單設計規範

### 必備欄位
所有報工表單都必須包含以下欄位：
1. **工單號碼**：關聯到工單
2. **產品編號**：產品識別
3. **工序**：作業工序
4. **設備**：使用設備
5. **日期**：作業日期
6. **開始時間**：作業開始時間
7. **結束時間**：作業結束時間
8. **數量**：完成數量
9. **不良品**：不良品數量
10. **備註**：備註說明

### 特殊規範

#### SMT報工
- 工序和設備都只能跟SMT有關
- 使用SMT專用的工序和設備選項

#### 作業員報工
- 工序和設備可以是任何類型
- 支援所有類型的工序和設備

#### RD樣品補登
- 使用相同模型但不同模板
- 新增作業員補登報工與新增作業員RD樣品補登報工是兩個不同模板

## 🔧 開發指南

### 新增報工類型步驟
1. 繼承 `ProductionReportBaseForm`
2. 定義專屬欄位（如需要）
3. 建立對應的 View 和 Template
4. 更新 URL 路由
5. 測試功能

### 修改共用欄位步驟
1. 修改 `ProductionReportBaseForm`
2. 檢查所有繼承的表單是否正常
3. 更新相關的 View 和 Template
4. 測試所有報工功能

### 程式碼範例
```python
# workorder/forms.py
class ProductionReportBaseForm(forms.ModelForm):
    """
    【規範】報工共用表單
    - 任何報工表單都必須繼承這個類別
    - 共用欄位：工單號碼、產品編號、工序、設備、日期、開始/結束時間、數量、不良品、備註
    - 禁止在子類別重複定義這些欄位
    """
    # 共用欄位定義...

class SMTSupplementReportForm(ProductionReportBaseForm):
    """
    【規範】SMT補登報工表單
    - 繼承共用表單，無額外欄位
    - 工序和設備限制為SMT相關
    """
    pass

class RDSampleSupplementReportForm(ProductionReportBaseForm):
    """
    【規範】RD樣品補登報工表單
    - 繼承共用表單，加上RD專屬欄位
    - 使用相同模型但不同模板
    """
    rd_sample_code = forms.CharField(label="RD樣品編號")
    rd_project_name = forms.CharField(label="專案名稱")
```

## 📚 相關檔案
- `workorder/forms.py`：表單定義
- `workorder/views.py`：視圖邏輯
- `workorder/models.py`：資料模型
- `workorder/urls.py`：URL路由
- `workorder/templates/`：前端模板

## ⚠️ 注意事項
1. 嚴格遵守時間格式規範
2. 所有報工表單都必須繼承共用表單
3. 不可重複定義相同欄位
4. 保持模組間的獨立性
5. 定期檢查規範執行情況

---
*最後更新：2025年1月*
*維護者：MES開發團隊* 