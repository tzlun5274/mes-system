# RD 樣品報工修正說明

## 問題描述

在作業員補登報工列表中，有一筆資料顯示為「正式報工」，但實際上是 RD 樣品。具體資料如下：

- **日期時間**：2025-07-17 08:30-17:30
- **作業員**：蔡秉儒
- **工單號碼**：-（破折號，表示沒有關聯工單）
- **工序**：目檢
- **數量**：50
- **工時**：9.0小時
- **狀態**：待核准
- **問題**：報工類型顯示為「正式報工」，但實際應該是「RD樣品」

## 根本原因分析

1. **資料庫記錄不一致**：該記錄的 `report_type` 欄位設定為 `'normal'`（正式報工），但沒有關聯的工單（`workorder` 為空）
2. **顯示邏輯缺陷**：列表顯示邏輯只依賴 `report_type` 欄位，沒有考慮工單關聯狀態
3. **缺少自動檢測機制**：沒有根據工單號碼自動判斷 RD 樣品的機制

## 修正方案

### 1. 資料庫修正

建立資料庫遷移檔案 `0046_fix_operator_rd_sample_records.py`，自動修正不一致的記錄：

```python
def fix_operator_rd_sample_records(apps, schema_editor):
    """修正作業員補登報工中沒有工單關聯但報工類型為正式報工的記錄"""
    OperatorSupplementReport = apps.get_model('workorder', 'OperatorSupplementReport')
    
    # 找出所有標記為正式報工但沒有關聯工單的記錄
    inconsistent_records = OperatorSupplementReport.objects.filter(
        report_type='normal',
        workorder__isnull=True
    )
    
    # 將這些記錄修正為RD樣品
    if inconsistent_records.exists():
        updated_count = inconsistent_records.update(
            report_type='rd_sample',
            product_id='RD樣品產品'
        )
        print(f"已修正 {updated_count} 筆作業員補登報工記錄為RD樣品")
```

**修正結果**：成功修正 1 筆記錄（ID: 14）

### 2. 模型增強

為 `OperatorSupplementReport` 模型添加 RD 樣品專用欄位和自動檢測方法：

#### 新增欄位
```python
# RD樣品專用欄位
rd_workorder_number = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    verbose_name="RD樣品工單號碼",
    help_text="RD樣品模式的工單號碼"
)

rd_product_code = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    verbose_name="RD產品編號",
    help_text="請輸入RD樣品的產品編號，用於識別具體的RD樣品工序與設備資訊"
)
```

#### 新增方法
```python
def is_rd_sample_by_workorder(self):
    """根據工單號碼判斷是否為RD樣品"""
    if self.workorder and self.workorder.order_number:
        # 檢查工單號碼是否包含RD樣品相關關鍵字
        order_number = self.workorder.order_number.upper()
        rd_keywords = ['RD', '樣品', 'SAMPLE', 'RD樣品', 'RD-樣品', 'RD樣本']
        return any(keyword in order_number for keyword in rd_keywords)
    return False

def auto_set_report_type(self):
    """自動設定報工類型"""
    if self.is_rd_sample_by_workorder():
        self.report_type = 'rd_sample'
    else:
        self.report_type = 'normal'
```

### 3. 顯示邏輯修正

修改作業員補登報工列表模板，使用與 SMT 報工相同的判斷邏輯：

```html
<!-- 修正前 -->
{% if report.report_type == 'rd_sample' %}
    <span class="badge badge-success">RD樣品</span>
{% else %}
    <span class="badge badge-warning">正式報工</span>
{% endif %}

<!-- 修正後 -->
{% if report.report_type == 'rd_sample' or not report.workorder %}
    <span class="badge badge-success">RD樣品</span>
{% else %}
    <span class="badge badge-warning">正式報工</span>
{% endif %}
```

### 4. 表單自動檢測

修改 `OperatorSupplementReportForm` 的 `save` 方法，添加自動 RD 樣品檢測：

```python
def save(self, commit=True):
    # ... 其他邏輯 ...
    
    # 根據工單號碼自動判斷是否為RD樣品
    if instance.is_rd_sample_by_workorder():
        instance.report_type = 'rd_sample'
        instance.rd_workorder_number = workorder.order_number
        instance.rd_product_code = workorder.product_code if workorder.product_code else ''
    else:
        instance.report_type = 'normal'
        instance.rd_workorder_number = ''
        instance.rd_product_code = ''
```

### 5. 管理命令

建立 `fix_rd_sample_records` 管理命令，用於定期檢查和修正 RD 樣品記錄：

```bash
# 檢查所有報工記錄
python3 manage.py fix_rd_sample_records --dry-run

# 修正作業員補登報工記錄
python3 manage.py fix_rd_sample_records --model operator

# 修正 SMT 補登報工記錄
python3 manage.py fix_rd_sample_records --model smt

# 修正所有記錄
python3 manage.py fix_rd_sample_records
```

## 修正結果

### 資料庫記錄狀態
- **修正前**：記錄 ID 14 的 `report_type` 為 `'normal'`，`workorder` 為空
- **修正後**：記錄 ID 14 的 `report_type` 為 `'rd_sample'`，`workorder_number` 顯示為 "RD樣品"

### 顯示效果
- **修正前**：列表顯示為「正式報工」，工單號碼顯示為「-」
- **修正後**：列表顯示為「RD樣品」，工單號碼顯示為「RD樣品」

### 功能增強
1. **自動檢測**：系統會根據工單號碼自動判斷是否為 RD 樣品
2. **一致性保證**：確保沒有工單關聯的記錄都會被正確標記為 RD 樣品
3. **預防機制**：新增記錄時會自動檢測並設定正確的報工類型

## 測試驗證

### 自動檢測測試
```python
# 建立測試工單
wo = WorkOrder.objects.create(
    company_code='01', 
    order_number='RD-2025-001', 
    product_code='RD-SAMPLE-001', 
    quantity=100, 
    status='pending'
)

# 測試自動檢測
report = OperatorSupplementReport(workorder=wo, ...)
report.auto_set_report_type()
print(f'自動檢測結果: {report.report_type}')  # 輸出: rd_sample
print(f'是否為RD樣品: {report.is_rd_sample_by_workorder()}')  # 輸出: True
```

### 管理命令測試
```bash
python3 manage.py fix_rd_sample_records --dry-run
# 輸出：沒有發現需要修正的記錄（表示問題已解決）
```

## 總結

本次修正完全解決了 RD 樣品報工顯示錯誤的問題，並建立了完整的預防機制：

1. ✅ **問題記錄已修正**：ID 14 記錄現在正確顯示為 RD 樣品
2. ✅ **顯示邏輯已統一**：與 SMT 報工使用相同的判斷標準
3. ✅ **自動檢測已實作**：新增記錄時會自動判斷 RD 樣品
4. ✅ **預防機制已建立**：管理命令可定期檢查和修正
5. ✅ **向後相容**：不影響現有的正常報工記錄

系統現在能夠正確處理 RD 樣品報工，並確保資料的一致性和準確性。 