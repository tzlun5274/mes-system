# SMT設備作業員名稱優化說明

## 問題背景

在MES系統中，SMT設備同時也是作業員名稱，這是一個特殊的設計需求。原本的實作存在以下問題：

1. **資料庫欄位不一致**：模型定義 `operator` 為外鍵，但資料庫實際是字串欄位
2. **邏輯混亂**：SMT設備名稱被當作作業員名稱，但沒有統一的處理邏輯
3. **報表顯示問題**：在報表中無法清楚區分SMT設備和真實作業員

## 優化方案

### 1. 資料庫結構優化

#### 新增欄位
- `equipment_operator_name`: 專門用於儲存SMT設備的作業員名稱
- 保留 `operator` 欄位作為字串欄位，用於相容性

#### 欄位說明
```python
# 作業員欄位（SMT設備通常不需要作業員，但保留用於相容性）
operator = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    verbose_name="作業員",
    help_text="SMT設備報工時，此欄位會自動填入設備名稱作為作業員名稱",
)

# 新增：設備作業員名稱（用於報表顯示）
equipment_operator_name = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    verbose_name="設備作業員名稱",
    help_text="SMT設備的作業員名稱，通常與設備名稱相同",
)
```

### 2. 服務類別建立

建立 `SMTOperatorService` 服務類別，統一處理SMT設備作業員名稱的邏輯：

#### 主要功能
- `get_smt_equipment_operator_name()`: 根據設備名稱取得作業員名稱
- `get_smt_equipment_display_name()`: 取得設備的顯示名稱
- `is_smt_equipment()`: 判斷是否為SMT設備
- `create_smt_report_with_operator_name()`: 建立SMT報工記錄時自動設定作業員名稱
- `get_operator_display_name_for_report()`: 取得報工記錄的作業員顯示名稱

#### 命名規則
- **SMT設備名稱**: `SMT-A_LINE`, `SMT-B_LINE`, `SMT-P_LINE`
- **作業員名稱**: `SMT-A_LINE (SMT設備)`, `SMT-B_LINE (SMT設備)`, `SMT-P_LINE (SMT設備)`
- **顯示名稱**: 與作業員名稱相同，清楚標示為SMT設備

### 3. 自動化邏輯

#### 儲存時自動設定
```python
def save(self, *args, **kwargs):
    """儲存時自動設定設備作業員名稱"""
    # 如果有設備，自動設定設備作業員名稱
    if self.equipment and not self.equipment_operator_name:
        self.equipment_operator_name = self.equipment.name
    
    # 如果沒有作業員但有設備作業員名稱，設定作業員欄位
    if not self.operator and self.equipment_operator_name:
        self.operator = self.equipment_operator_name
    
    super().save(*args, **kwargs)
```

#### 顯示名稱邏輯
```python
def get_operator_display_name(self):
    """取得作業員顯示名稱"""
    if self.equipment_operator_name:
        # 如果設備作業員名稱已經包含(SMT設備)，就直接返回
        if '(SMT設備)' in self.equipment_operator_name:
            return self.equipment_operator_name
        else:
            return f"{self.equipment_operator_name} (SMT設備)"
    elif self.operator:
        # 如果作業員名稱已經包含(SMT設備)，就直接返回
        if '(SMT設備)' in self.operator:
            return self.operator
        else:
            return self.operator
    else:
        return "未指定"
```

### 4. 表單優化

#### SMT設備選擇
在SMT報工表單中，設備選項會顯示格式化的名稱：
- 原本: `SMT-A_LINE`
- 優化後: `SMT-A_LINE (SMT設備)`

#### 程式碼實作
```python
# 使用SMT作業員服務格式化設備顯示名稱
equipment_choices = []
for equipment in smt_equipment:
    display_name = SMTOperatorService.get_smt_equipment_display_name(equipment.name)
    equipment_choices.append((equipment.id, display_name))

self.fields["equipment"].choices = [("", "請選擇SMT設備")] + equipment_choices
```

### 5. 報表顯示優化

#### 報表詳情頁面
在報表詳情頁面中，SMT報工會同時顯示設備和作業員：
```html
{% if report_type == 'SMT報工' %}
    <p><strong>設備:</strong> {{ report.equipment.name|default:"-" }}</p>
    <p><strong>作業員:</strong> {{ report.get_operator_display_name|default:"-" }}</p>
    <p><strong>工序:</strong> {{ report.operation|default:"-" }}</p>
{% else %}
    <p><strong>作業員:</strong> {{ report.operator.name|default:"-" }}</p>
    <p><strong>工序:</strong> {{ report.process.name|default:"-" }}</p>
{% endif %}
```

### 6. 管理命令

建立 `update_smt_operator_names` 管理命令，用於更新現有的SMT報工記錄：

#### 使用方式
```bash
# 乾跑模式（只顯示會更新的記錄）
python3 manage.py update_smt_operator_names --dry-run

# 實際執行更新
python3 manage.py update_smt_operator_names
```

#### 功能
- 自動識別SMT報工記錄
- 更新作業員名稱格式
- 顯示統計資訊

## 優化效果

### 1. 資料一致性
- 統一SMT設備作業員名稱的格式
- 自動化設定邏輯，減少人為錯誤
- 清楚區分SMT設備和真實作業員

### 2. 使用者體驗
- 在表單中清楚顯示SMT設備
- 在報表中清楚標示SMT設備
- 保持向後相容性

### 3. 系統維護性
- 集中化的邏輯處理
- 統一的命名規則
- 易於擴展和修改

## 統計資訊

根據系統資料：
- **真實作業員**: 9 位
- **SMT設備**: 3 台
- **SMT報工記錄**: 1 筆（測試）
- **總作業員數**: 12 位

## 未來擴展

### 1. 更多設備類型
可以擴展支援其他類型的自動化設備：
- DIP設備
- 測試設備
- 包裝設備

### 2. 設備狀態追蹤
可以新增設備狀態的追蹤功能：
- 設備運行時間
- 設備效率統計
- 設備維護記錄

### 3. 報表功能增強
可以新增專門的設備報表：
- 設備產能報表
- 設備效率分析
- 設備維護計劃

## 結論

這次優化成功解決了SMT設備作業員名稱的問題，建立了統一、清晰的命名規則和處理邏輯。系統現在能夠：

1. **清楚區分**SMT設備和真實作業員
2. **自動化處理**SMT設備的作業員名稱
3. **保持相容性**與現有系統
4. **提供良好的使用者體驗**

這個優化為未來的系統擴展奠定了良好的基礎。 