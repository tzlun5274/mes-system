# 📊 MES 報表基礎模板使用說明

## 📋 概述

本文件說明如何使用 MES 系統的報表基礎模板來創建標準化的報表頁面。基礎模板提供了完整的報表功能架構，包括查詢條件、統計摘要、數據展示、匯出功能等。

## 🏗️ 模板架構

### 基礎模板位置
```
reporting/templates/reporting/base/report_base.html
```

### 樣式檔案位置
```
reporting/static/reporting/css/report.css
```

### 範例模板位置
```
reporting/templates/reporting/example_report.html
```

## 📝 使用方法

### 1. 繼承基礎模板

```html
{% extends 'reporting/base/report_base.html' %}
{% load static %}

{% block title %}您的報表標題 - MES系統{% endblock %}
```

### 2. 自訂查詢表單

```html
{% block query_form %}
<!-- 您的自訂查詢表單 -->
<form method="get" id="queryForm" class="needs-validation" novalidate>
    <div class="row g-3">
        <div class="col-md-3">
            <label for="date_from" class="form-label">
                <i class="fas fa-calendar-alt me-1"></i>開始日期
            </label>
            <input type="date" class="form-control" id="date_from" name="date_from" 
                   value="{{ date_from|default:'' }}" required>
            <div class="invalid-feedback">
                請選擇開始日期
            </div>
        </div>
        <!-- 更多查詢欄位... -->
    </div>
    <div class="row mt-3">
        <div class="col-12">
            <button type="submit" class="btn btn-primary">
                <i class="fas fa-search me-1"></i>查詢
            </button>
            <button type="button" class="btn btn-outline-secondary" onclick="resetForm()">
                <i class="fas fa-undo me-1"></i>重置
            </button>
        </div>
    </div>
</form>
{% endblock %}
```

### 3. 自訂統計摘要

```html
{% block statistics %}
<div class="row">
    <div class="col-md-3">
        <div class="stat-card text-center" style="--animation-order: 1;">
            <div class="stat-icon">
                <i class="fas fa-users"></i>
            </div>
            <div class="stat-value">{{ total_operators|default:"0" }}</div>
            <div class="stat-label">總作業員數</div>
        </div>
    </div>
    <!-- 更多統計卡片... -->
</div>

<!-- 圖表容器 -->
<div class="row mt-4">
    <div class="col-md-6">
        <div class="chart-container">
            <h6><i class="fas fa-chart-pie me-2"></i>圖表標題</h6>
            <canvas id="myChart" width="400" height="200"></canvas>
        </div>
    </div>
</div>
{% endblock %}
```

### 4. 自訂報表內容

```html
{% block report_content %}
{% if report_data %}
    <!-- 數據摘要 -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                查詢期間：{{ date_from|date:"Y-m-d" }} 至 {{ date_to|date:"Y-m-d" }} | 
                共 {{ report_data|length }} 筆記錄
            </div>
        </div>
    </div>

    <!-- 報表表格 -->
    <div class="report-table">
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th><i class="fas fa-calendar me-1"></i>日期</th>
                        <th><i class="fas fa-user me-1"></i>作業員</th>
                        <!-- 更多欄位... -->
                    </tr>
                </thead>
                <tbody>
                    {% for item in report_data %}
                    <tr>
                        <td>{{ item.date|date:"Y-m-d" }}</td>
                        <td>{{ item.operator.name }}</td>
                        <!-- 更多欄位... -->
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="5" class="text-center text-muted py-4">
                            <i class="fas fa-inbox fa-2x mb-3"></i>
                            <br>暫無符合條件的資料
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
{% else %}
    <!-- 無資料時的提示 -->
    <div class="text-center py-5">
        <i class="fas fa-chart-bar fa-3x text-muted mb-3"></i>
        <h5 class="text-muted">請選擇查詢條件並點擊查詢按鈕以顯示報表內容</h5>
    </div>
{% endif %}
{% endblock %}
```

### 5. 自訂 JavaScript

```html
{% block extra_js %}
<script>
// 初始化圖表
function initializeCharts() {
    const ctx = document.getElementById('myChart');
    if (ctx) {
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: {{ chart_labels|safe }},
                datasets: [{
                    label: '數據標籤',
                    data: {{ chart_data|safe }},
                    backgroundColor: '#667eea'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
        currentCharts.push(chart);
    }
}

// 自訂函數
function customFunction() {
    // 您的自訂邏輯
}
</script>
{% endblock %}
```

## 🎨 樣式類別

### 統計卡片
```html
<div class="stat-card text-center">
    <div class="stat-icon">
        <i class="fas fa-users"></i>
    </div>
    <div class="stat-value">123</div>
    <div class="stat-label">標籤</div>
</div>
```

### 圖表容器
```html
<div class="chart-container">
    <h6>圖表標題</h6>
    <canvas id="chartId"></canvas>
</div>
```

### 報表表格
```html
<div class="report-table">
    <div class="table-responsive">
        <table class="table table-hover">
            <!-- 表格內容 -->
        </table>
    </div>
</div>
```

### 警告訊息
```html
<div class="alert alert-info">
    <i class="fas fa-info-circle me-2"></i>
    訊息內容
</div>
```

## 🔧 內建功能

### 1. 自動表單驗證
- 使用 Bootstrap 的表單驗證
- 自動顯示錯誤訊息
- 支援自訂驗證規則

### 2. AJAX 查詢
- 無需重新載入頁面
- 自動更新統計和內容區域
- 支援載入動畫

### 3. 匯出功能
- 支援 Excel、CSV、PDF 格式
- 可自訂匯出範圍
- 自動檔案命名

### 4. 響應式設計
- 支援桌面和移動設備
- 自適應佈局
- 觸控友善介面

### 5. 圖表支援
- 使用 Chart.js 圖表庫
- 支援多種圖表類型
- 自動響應式調整

## 📊 可用的 JavaScript 函數

### 基礎函數
```javascript
// 顯示載入遮罩
showLoading()

// 隱藏載入遮罩
hideLoading()

// 顯示成功訊息
showSuccess('操作成功')

// 顯示錯誤訊息
showError('操作失敗')

// 顯示警告訊息
showWarning('警告訊息')

// 顯示資訊訊息
showInfo('資訊訊息')

// 重新整理報表
refreshReport()

// 重置表單
resetForm()

// 顯示匯出模態框
showExportModal()

// 執行匯出
executeExport()
```

### 格式化函數
```javascript
// 格式化數字
formatNumber(1234.56) // 1,234.56

// 格式化日期
formatDate('2025-01-15') // 2025/01/15

// 格式化時間
formatTime('14:30:00') // 14:30:00
```

### 圖表函數
```javascript
// 初始化圖表
initializeCharts()

// 清除現有圖表
currentCharts.forEach(chart => chart.destroy())
```

## 🎯 最佳實踐

### 1. 查詢表單設計
- 使用適當的欄位類型（date、select、text）
- 提供預設值和預選選項
- 加入必填欄位驗證
- 使用圖示增強可讀性

### 2. 統計摘要設計
- 顯示關鍵指標
- 使用適當的圖示
- 保持一致的樣式
- 考慮動畫效果

### 3. 數據展示設計
- 使用響應式表格
- 加入適當的圖示和徽章
- 提供操作按鈕
- 處理空數據情況

### 4. 圖表設計
- 選擇合適的圖表類型
- 使用一致的配色方案
- 提供圖表標題和說明
- 考慮數據更新機制

### 5. 用戶體驗設計
- 提供載入提示
- 顯示操作結果
- 支援鍵盤快捷鍵
- 保持介面一致性

## 🔍 除錯技巧

### 1. 檢查模板繼承
```html
<!-- 確保正確繼承基礎模板 -->
{% extends 'reporting/base/report_base.html' %}
```

### 2. 檢查區塊定義
```html
<!-- 確保所有必要的區塊都有定義 -->
{% block query_form %}{% endblock %}
{% block statistics %}{% endblock %}
{% block report_content %}{% endblock %}
```

### 3. 檢查 JavaScript 錯誤
```javascript
// 在瀏覽器開發者工具中檢查 Console
console.log('除錯訊息');
```

### 4. 檢查 CSS 載入
```html
<!-- 確保 CSS 檔案正確載入 -->
<link rel="stylesheet" href="{% static 'reporting/css/report.css' %}">
```

## 📚 範例檔案

完整的範例請參考：
- `reporting/templates/reporting/example_report.html`

## 🆘 常見問題

### Q: 為什麼圖表沒有顯示？
A: 檢查是否正確載入 Chart.js 庫，並確保在 `initializeCharts()` 函數中正確初始化圖表。

### Q: 匯出功能無法使用？
A: 檢查後端是否實作了對應的匯出視圖，並確保 URL 配置正確。

### Q: 查詢表單驗證不工作？
A: 確保表單有 `needs-validation` 類別，並在 JavaScript 中正確設定驗證邏輯。

### Q: 響應式設計有問題？
A: 檢查是否正確載入 Bootstrap CSS，並確保使用適當的響應式類別。

## 📞 技術支援

如有問題，請參考：
1. 基礎模板原始碼
2. 範例檔案
3. 設計規範文件
4. 系統開發文檔 