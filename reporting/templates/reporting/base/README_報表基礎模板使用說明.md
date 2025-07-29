# 報表基礎模板使用說明

## 概述

本文件說明 MES 系統報表模組的基礎模板架構和使用方式。根據報表系統設計架構規範，我們提供了多種基礎模板來滿足不同類型的報表需求。

## 模板架構

### 1. 基礎模板層級

```
reporting/templates/reporting/base/
├── report_base_v2.html          # 主要基礎模板（最新版本）
├── table_report_template.html   # 表格型報表模板
├── chart_report_template.html   # 圖表型報表模板
├── dashboard_report_template.html # 儀表板型報表模板
├── export_template.html         # 匯出專用模板
└── README_報表基礎模板使用說明.md # 本說明文件
```

### 2. 模板繼承關係

```
base.html (全域基礎模板)
    └── report_base_v2.html (報表基礎模板)
        ├── table_report_template.html
        ├── chart_report_template.html
        ├── dashboard_report_template.html
        └── export_template.html
```

## 各模板詳細說明

### 1. report_base_v2.html - 主要基礎模板

**用途**: 所有報表模板的基礎，提供通用的報表功能

**主要功能**:
- 統一的報表標題和導航
- 查詢條件區域
- 統計摘要區域
- 報表內容區域
- 匯出功能
- 載入遮罩
- 響應式設計

**可覆寫區塊**:
- `{% block query_form %}` - 查詢表單
- `{% block statistics %}` - 統計摘要
- `{% block report_content %}` - 報表內容
- `{% block extra_css %}` - 額外樣式
- `{% block extra_js %}` - 額外 JavaScript

**使用範例**:
```html
{% extends 'reporting/base/report_base_v2.html' %}

{% block report_content %}
<!-- 自訂報表內容 -->
{% endblock %}
```

### 2. table_report_template.html - 表格型報表模板

**用途**: 專門用於顯示數據表格的報表

**特色功能**:
- DataTables 整合（排序、搜尋、分頁）
- 多種數據類型支援（日期、數字、百分比、狀態）
- 表格摘要統計
- 匯出按鈕（複製、CSV、Excel、列印）

**必要變數**:
```python
context = {
    'table_columns': [
        {'field': 'date', 'label': '日期', 'type': 'date'},
        {'field': 'quantity', 'label': '數量', 'type': 'number'},
        {'field': 'status', 'label': '狀態', 'type': 'status'},
    ],
    'table_data': [...],  # 表格數據
    'table_summary': [    # 可選：表格摘要
        {'icon': 'users', 'color': 'primary', 'label': '總人數', 'value': '100'},
    ]
}
```

**使用範例**:
```html
{% extends 'reporting/base/table_report_template.html' %}

{% block query_form %}
<!-- 自訂查詢表單 -->
{% endblock %}
```

### 3. chart_report_template.html - 圖表型報表模板

**用途**: 專門用於顯示各種圖表的報表

**支援圖表類型**:
- 折線圖 (line)
- 長條圖 (bar)
- 圓餅圖 (pie)
- 環形圖 (doughnut)

**特色功能**:
- 主要圖表和次要圖表支援
- 圖表互動功能
- 圖表數據表格
- 圖表分析摘要

**必要變數**:
```python
context = {
    'main_chart': {
        'type': 'line',
        'title': '生產趨勢',
        'data': {...},  # Chart.js 格式數據
        'height': 400
    },
    'secondary_charts': [
        {
            'type': 'bar',
            'title': '設備效率',
            'data': {...},
            'height': 300
        }
    ],
    'chart_data_table': {  # 可選
        'columns': ['日期', '產量', '效率'],
        'data': [...]
    },
    'chart_analysis': [    # 可選
        {'icon': 'trending-up', 'color': 'success', 'label': '平均效率', 'value': '85%'}
    ]
}
```

### 4. dashboard_report_template.html - 儀表板型報表模板

**用途**: 綜合顯示多個指標和圖表的儀表板

**特色功能**:
- 多個統計指標卡片
- 進度指標條
- 多個圖表區域
- 數據表格區域
- 警報和通知
- 快速操作按鈕
- 自動更新功能

**必要變數**:
```python
context = {
    'dashboard_metrics': [
        {
            'icon': 'users',
            'value': '150',
            'label': '總作業員數',
            'trend': '+5%',
            'trend_direction': 'up',
            'trend_color': 'success'
        }
    ],
    'progress_indicators': [
        {
            'label': '生產進度',
            'value': 75,
            'color': 'success',
            'description': '已完成 75% 的生產目標'
        }
    ],
    'main_charts': [...],
    'secondary_charts': [...],
    'data_tables': [...],
    'alerts': [...],
    'quick_actions': [...]
}
```

### 5. export_template.html - 匯出專用模板

**用途**: 專門處理報表匯出功能

**特色功能**:
- 多種報表類型選擇
- 多種日期範圍選擇
- 多種匯出格式支援
- 報表預覽功能
- 排程匯出功能
- 匯出歷史記錄

**支援格式**:
- Excel (.xlsx)
- CSV (.csv)
- PDF (.pdf) - 開發中

## 使用指南

### 1. 選擇合適的模板

根據報表需求選擇合適的基礎模板：

- **純數據展示**: 使用 `table_report_template.html`
- **圖表分析**: 使用 `chart_report_template.html`
- **綜合儀表板**: 使用 `dashboard_report_template.html`
- **匯出功能**: 使用 `export_template.html`
- **自訂需求**: 直接繼承 `report_base_v2.html`

### 2. 準備數據格式

確保傳遞給模板的數據符合對應格式要求：

```python
def your_report_view(request):
    # 準備數據
    context = {
        'report_title': '生產報表',
        'report_description': '顯示生產相關統計數據',
        'table_columns': [...],
        'table_data': [...],
        # 其他必要數據
    }
    
    return render(request, 'reporting/your_report.html', context)
```

### 3. 自訂樣式和功能

可以透過覆寫區塊來自訂樣式和功能：

```html
{% extends 'reporting/base/table_report_template.html' %}

{% block extra_css %}
{{ block.super }}
<style>
/* 自訂樣式 */
.custom-style {
    background-color: #f8f9fa;
}
</style>
{% endblock %}

{% block extra_js %}
{{ block.super }}
<script>
// 自訂 JavaScript 功能
function customFunction() {
    // 自訂邏輯
}
</script>
{% endblock %}
```

### 4. 響應式設計

所有模板都支援響應式設計，在不同螢幕尺寸下自動調整：

- **桌面版**: 完整功能顯示
- **平板版**: 適度調整佈局
- **手機版**: 簡化介面，重點功能優先

## 最佳實踐

### 1. 數據驗證

在傳遞數據給模板前進行驗證：

```python
def validate_report_data(data):
    """驗證報表數據格式"""
    if not isinstance(data, dict):
        raise ValueError("數據必須是字典格式")
    
    required_fields = ['title', 'data']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"缺少必要欄位: {field}")
    
    return True
```

### 2. 錯誤處理

在模板中加入錯誤處理：

```html
{% if table_data %}
    <!-- 正常顯示數據 -->
{% else %}
    <div class="alert alert-warning">
        <i class="fas fa-exclamation-triangle me-2"></i>
        暫無數據可顯示
    </div>
{% endif %}
```

### 3. 效能優化

- 使用分頁顯示大量數據
- 實作數據快取機制
- 延遲載入非關鍵功能

### 4. 使用者體驗

- 提供載入提示
- 友善的錯誤訊息
- 直觀的操作流程
- 快速響應的介面

## 擴展開發

### 1. 新增模板類型

如需新增特定類型的報表模板，請：

1. 繼承 `report_base_v2.html`
2. 實作必要的區塊
3. 更新本說明文件
4. 提供使用範例

### 2. 新增功能

如需新增功能，請：

1. 遵循現有的程式碼風格
2. 確保向後相容性
3. 更新相關文件
4. 進行充分測試

## 技術支援

如有問題或建議，請：

1. 查看本說明文件
2. 檢查範例程式碼
3. 參考報表系統設計架構規範
4. 聯繫開發團隊

---

**版本**: 2.0  
**更新日期**: 2025-07-28  
**維護者**: MES 開發團隊 