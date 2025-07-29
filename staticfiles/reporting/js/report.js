/*
報表系統標準化JavaScript功能
符合MES系統設計架構與結構規範
*/

// ===== 全域變數 =====
let currentReportData = null;
let currentFilters = {};
let isLoading = false;
let autoRefreshInterval = null;

// ===== 初始化函數 =====
document.addEventListener('DOMContentLoaded', function() {
    initializeReportSystem();
});

function initializeReportSystem() {
    console.log('初始化報表系統...');
    
    // 初始化工具提示
    initializeTooltips();
    
    // 初始化表單驗證
    initializeFormValidation();
    
    // 初始化日期選擇器
    initializeDatePickers();
    
    // 初始化自動刷新
    initializeAutoRefresh();
    
    // 初始化鍵盤快捷鍵
    initializeKeyboardShortcuts();
    
    // 初始化錯誤處理
    initializeErrorHandling();
    
    console.log('報表系統初始化完成');
}

// ===== 工具提示初始化 =====
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// ===== 表單驗證初始化 =====
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                showValidationErrors(form);
            }
            form.classList.add('was-validated');
        });
    });
}

// ===== 日期選擇器初始化 =====
function initializeDatePickers() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            input.value = new Date().toISOString().split('T')[0];
        }
        
        // 添加日期驗證
        input.addEventListener('change', function() {
            validateDateRange();
        });
    });
}

// ===== 自動刷新初始化 =====
function initializeAutoRefresh() {
    // 每5分鐘自動刷新
    autoRefreshInterval = setInterval(function() {
        if (!isLoading) {
            refreshReport();
        }
    }, 300000); // 5分鐘
}

// ===== 鍵盤快捷鍵初始化 =====
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Ctrl + R: 重新整理
        if (event.ctrlKey && event.key === 'r') {
            event.preventDefault();
            refreshReport();
        }
        
        // Ctrl + E: 匯出
        if (event.ctrlKey && event.key === 'e') {
            event.preventDefault();
            showExportModal();
        }
        
        // Ctrl + F: 搜尋
        if (event.ctrlKey && event.key === 'f') {
            event.preventDefault();
            focusSearchBox();
        }
        
        // Esc: 關閉模態框
        if (event.key === 'Escape') {
            closeAllModals();
        }
    });
}

// ===== 錯誤處理初始化 =====
function initializeErrorHandling() {
    window.addEventListener('error', function(event) {
        console.error('JavaScript錯誤:', event.error);
        showErrorMessage('系統發生錯誤，請稍後再試');
    });
    
    window.addEventListener('unhandledrejection', function(event) {
        console.error('未處理的Promise拒絕:', event.reason);
        showErrorMessage('網路連線異常，請檢查網路狀態');
    });
}

// ===== 報表重新整理 =====
function refreshReport() {
    if (isLoading) {
        console.log('正在載入中，跳過重新整理');
        return;
    }
    
    showLoading();
    isLoading = true;
    
    // 取得當前查詢條件
    const filters = getCurrentFilters();
    
    // 發送 AJAX 請求重新取得數據
    fetch(getReportApiUrl(), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            report_type: getCurrentReportType(),
            filters: filters
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            currentReportData = data.data;
            updateReportDisplay(data.data);
            showSuccessMessage('報表已重新整理');
            updateLastRefreshTime();
        } else {
            throw new Error(data.error || '重新整理失敗');
        }
    })
    .catch(error => {
        console.error('重新整理報表失敗:', error);
        showErrorMessage('重新整理失敗: ' + error.message);
    })
    .finally(() => {
        hideLoading();
        isLoading = false;
    });
}

// ===== 匯出報表 =====
function exportReport() {
    if (isLoading) {
        showWarningMessage('正在處理中，請稍候');
        return;
    }
    
    showLoading();
    isLoading = true;
    
    const formData = new FormData(document.getElementById('exportForm'));
    const queryString = new URLSearchParams(window.location.search);
    
    // 合併查詢參數
    for (const pair of queryString.entries()) {
        formData.append(pair[0], pair[1]);
    }
    
    fetch(getExportApiUrl(), {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.blob();
    })
    .then(blob => {
        downloadFile(blob, generateFileName(formData.get('format')));
        showSuccessMessage('報表匯出成功');
        
        // 關閉模態框
        closeModal('exportModal');
    })
    .catch(error => {
        console.error('匯出失敗:', error);
        showErrorMessage('匯出失敗: ' + error.message);
    })
    .finally(() => {
        hideLoading();
        isLoading = false;
    });
}

// ===== 快速匯出 =====
function quickExport(format) {
    if (isLoading) {
        showWarningMessage('正在處理中，請稍候');
        return;
    }
    
    showLoading();
    isLoading = true;
    
    const formData = new FormData();
    formData.append('format', format);
    formData.append('report_type', getCurrentReportType());
    
    // 添加當前查詢參數
    const queryString = new URLSearchParams(window.location.search);
    for (const pair of queryString.entries()) {
        formData.append(pair[0], pair[1]);
    }
    
    fetch(getExportApiUrl(), {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.blob();
    })
    .then(blob => {
        downloadFile(blob, generateFileName(format));
        showSuccessMessage(`${format.toUpperCase()} 格式匯出成功`);
    })
    .catch(error => {
        console.error('快速匯出失敗:', error);
        showErrorMessage('匯出失敗: ' + error.message);
    })
    .finally(() => {
        hideLoading();
        isLoading = false;
    });
}

// ===== 表單重置 =====
function resetForm() {
    const form = document.getElementById('queryForm');
    if (form) {
        form.reset();
        
        // 重置日期為今天
        const dateInputs = form.querySelectorAll('input[type="date"]');
        dateInputs.forEach(input => {
            input.value = new Date().toISOString().split('T')[0];
        });
        
        // 清除驗證狀態
        form.classList.remove('was-validated');
        
        showInfoMessage('表單已重置');
    }
}

// ===== 顯示匯出模態框 =====
function showExportModal() {
    const modal = new bootstrap.Modal(document.getElementById('exportModal'));
    modal.show();
}

// ===== 關閉模態框 =====
function closeModal(modalId) {
    const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
    if (modal) {
        modal.hide();
    }
}

// ===== 關閉所有模態框 =====
function closeAllModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
            modalInstance.hide();
        }
    });
}

// ===== 載入狀態管理 =====
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
    
    // 禁用所有按鈕
    disableButtons(true);
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
    
    // 啟用所有按鈕
    disableButtons(false);
}

// ===== 按鈕狀態管理 =====
function disableButtons(disabled) {
    const buttons = document.querySelectorAll('button, .btn');
    buttons.forEach(button => {
        button.disabled = disabled;
    });
}

// ===== 訊息顯示 =====
function showSuccessMessage(message) {
    showToast('success', '成功', message);
}

function showErrorMessage(message) {
    showToast('danger', '錯誤', message);
}

function showWarningMessage(message) {
    showToast('warning', '警告', message);
}

function showInfoMessage(message) {
    showToast('info', '資訊', message);
}

function showToast(type, title, message) {
    // 檢查是否已有 toast 容器
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // 建立 toast 元素
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // 顯示 toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: type === 'success' ? 3000 : 5000
    });
    toast.show();
    
    // 自動移除 toast 元素
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// ===== 表單驗證 =====
function showValidationErrors(form) {
    const invalidFields = form.querySelectorAll(':invalid');
    if (invalidFields.length > 0) {
        const firstInvalidField = invalidFields[0];
        firstInvalidField.focus();
        showErrorMessage(`請檢查 ${firstInvalidField.labels[0]?.textContent || '表單欄位'}`);
    }
}

function validateDateRange() {
    const startDate = document.getElementById('date_from');
    const endDate = document.getElementById('date_to');
    
    if (startDate && endDate && startDate.value && endDate.value) {
        if (new Date(startDate.value) > new Date(endDate.value)) {
            showErrorMessage('開始日期不能晚於結束日期');
            endDate.setCustomValidity('結束日期必須晚於開始日期');
        } else {
            endDate.setCustomValidity('');
        }
    }
}

// ===== 數據處理 =====
function getCurrentFilters() {
    const filters = {};
    
    // 日期範圍
    const startDate = document.getElementById('date_from');
    const endDate = document.getElementById('date_to');
    if (startDate && startDate.value) {
        filters.start_date = startDate.value;
    }
    if (endDate && endDate.value) {
        filters.end_date = endDate.value;
    }
    
    // 其他篩選條件
    const operatorName = document.getElementById('operator_name');
    if (operatorName && operatorName.value) {
        filters.operator_name = operatorName.value;
    }
    
    const workorderNumber = document.getElementById('workorder_number');
    if (workorderNumber && workorderNumber.value) {
        filters.workorder_number = workorderNumber.value;
    }
    
    return filters;
}

function updateReportDisplay(data) {
    // 更新統計摘要
    updateStatistics(data.statistics);
    
    // 更新表格
    updateTable(data.data);
    
    // 更新圖表
    updateCharts(data.charts);
}

function updateStatistics(statistics) {
    if (!statistics) return;
    
    // 更新統計卡片
    Object.keys(statistics).forEach(key => {
        const element = document.getElementById(`stat-${key}`);
        if (element) {
            element.textContent = formatNumber(statistics[key]);
        }
    });
}

function updateTable(data) {
    if (!data) return;
    
    const tableContainer = document.getElementById('table-container');
    if (!tableContainer) return;
    
    // 這裡可以根據具體的表格數據更新顯示
    // 例如重新渲染 DataTable
    console.log('更新表格數據:', data);
}

function updateCharts(charts) {
    if (!charts) return;
    
    // 這裡可以根據具體的圖表數據更新顯示
    // 例如重新繪製 Chart.js 圖表
    console.log('更新圖表數據:', charts);
}

// ===== 工具函數 =====
function getCSRFToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
}

function getCurrentReportType() {
    // 從 URL 或頁面元素取得當前報表類型
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('report_type') || 'daily';
}

function getReportApiUrl() {
    // 根據當前頁面取得對應的 API URL
    const currentPath = window.location.pathname;
    if (currentPath.includes('production-daily')) {
        return '/reporting/api/production-daily/';
    } else if (currentPath.includes('operator-performance')) {
        return '/reporting/api/operator-performance/';
    }
    return '/reporting/api/report-data/';
}

function getExportApiUrl() {
    return '/reporting/export/';
}

function generateFileName(format) {
    const reportTitle = document.title.replace(' - MES系統', '');
    const date = new Date().toISOString().split('T')[0];
    return `${reportTitle}_${date}.${format}`;
}

function downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function formatNumber(number) {
    if (typeof number === 'number') {
        return number.toLocaleString('zh-TW');
    }
    return number;
}

function updateLastRefreshTime() {
    const timeElement = document.getElementById('lastRefreshTime');
    if (timeElement) {
        timeElement.textContent = new Date().toLocaleString('zh-TW');
    }
}

function focusSearchBox() {
    const searchBox = document.querySelector('input[type="search"], input[name="search"]');
    if (searchBox) {
        searchBox.focus();
    }
}

// ===== 事件監聽器 =====
document.addEventListener('DOMContentLoaded', function() {
    // 日期範圍選擇處理
    const exportDateRange = document.getElementById('exportDateRange');
    if (exportDateRange) {
        exportDateRange.addEventListener('change', function() {
            const customRange = document.getElementById('customDateRange');
            if (customRange) {
                customRange.style.display = this.value === 'custom' ? 'block' : 'none';
            }
        });
    }
    
    // 表單提交處理
    const queryForm = document.getElementById('queryForm');
    if (queryForm) {
        queryForm.addEventListener('submit', function(event) {
            event.preventDefault();
            refreshReport();
        });
    }
    
    // 視窗失去焦點時暫停自動刷新
    window.addEventListener('blur', function() {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
        }
    });
    
    // 視窗重新獲得焦點時恢復自動刷新
    window.addEventListener('focus', function() {
        initializeAutoRefresh();
    });
});

// ===== 頁面卸載清理 =====
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

// ===== 匯出全域函數 =====
window.refreshReport = refreshReport;
window.exportReport = exportReport;
window.quickExport = quickExport;
window.resetForm = resetForm;
window.showExportModal = showExportModal; 