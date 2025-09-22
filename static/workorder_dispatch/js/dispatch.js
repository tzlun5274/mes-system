/**
 * 派工單管理模組 JavaScript
 * 提供派工單相關的互動功能
 * 使用原生 JavaScript，嚴禁使用 jQuery
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化派工單模組
    initDispatchModule();
});

/**
 * 初始化派工單模組
 */
function initDispatchModule() {
    console.log('派工單模組初始化中...');
    
    // 初始化表單驗證
    initFormValidation();
    
    // 初始化搜尋功能
    initSearchFunction();
    
    // 初始化狀態篩選
    initStatusFilter();
    
    // 初始化日期選擇器
    initDatePickers();
    
    // 初始化工具提示
    initTooltips();
    
    console.log('派工單模組初始化完成');
}

/**
 * 初始化表單驗證
 */
function initFormValidation() {
    const dispatchForm = document.getElementById('dispatchForm');
    if (!dispatchForm) return;
    
    // 為表單欄位添加驗證
    dispatchForm.addEventListener('submit', function(e) {
        let isValid = true;
        
        // 檢查必填欄位
        const requiredFields = this.querySelectorAll('[required]');
        requiredFields.forEach(function(field) {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        // 檢查數量欄位
        const plannedQuantityField = document.getElementById('id_planned_quantity');
        if (plannedQuantityField) {
            const plannedQuantity = plannedQuantityField.value;
            if (plannedQuantity && (isNaN(plannedQuantity) || plannedQuantity <= 0)) {
                plannedQuantityField.classList.add('is-invalid');
                isValid = false;
            }
        }
        
        if (!isValid) {
            e.preventDefault();
            showAlert('請檢查表單中的錯誤', 'danger');
        }
    });
    
    // 即時驗證
    const plannedQuantityField = document.getElementById('id_planned_quantity');
    if (plannedQuantityField) {
        plannedQuantityField.addEventListener('input', function() {
            const value = this.value;
            if (value && (isNaN(value) || value <= 0)) {
                this.classList.add('is-invalid');
            } else {
                this.classList.remove('is-invalid');
            }
        });
    }
}

/**
 * 初始化搜尋功能
 */
function initSearchFunction() {
    // 搜尋框自動完成
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value;
            if (searchTerm.length >= 2) {
                // 這裡可以添加 AJAX 搜尋建議功能
                console.log('搜尋:', searchTerm);
            }
        });
    }
    
    // 搜尋表單提交
    const searchForm = document.querySelector('.dispatch-search-form form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchInput = this.querySelector('input[name="search"]');
            const searchTerm = searchInput ? searchInput.value : '';
            if (!searchTerm.trim()) {
                e.preventDefault();
                showAlert('請輸入搜尋關鍵字', 'warning');
            }
        });
    }
}

/**
 * 初始化狀態篩選
 */
function initStatusFilter() {
    const statusSelect = document.querySelector('select[name="status"]');
    if (statusSelect) {
        statusSelect.addEventListener('change', function() {
            // 自動提交表單以應用篩選
            const form = this.closest('form');
            if (form) {
                form.submit();
            }
        });
    }
}

/**
 * 初始化日期選擇器
 */
function initDatePickers() {
    // 為日期欄位添加日期選擇器
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            const startDateInput = document.querySelector('input[name="start_date"]');
            const endDateInput = document.querySelector('input[name="end_date"]');
            
            if (startDateInput && endDateInput) {
                const startDate = startDateInput.value;
                const endDate = endDateInput.value;
                
                if (startDate && endDate && startDate > endDate) {
                    showAlert('開始日期不能晚於結束日期', 'warning');
                    this.value = '';
                }
            }
        });
    });
}

/**
 * 初始化工具提示
 */
function initTooltips() {
    // 初始化 Bootstrap 工具提示
    const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipElements.forEach(function(element) {
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            new bootstrap.Tooltip(element);
        }
    });
    
    // 為操作按鈕添加工具提示
    const buttonsWithTitle = document.querySelectorAll('.btn[title]');
    buttonsWithTitle.forEach(function(button) {
        if (!button.hasAttribute('data-bs-toggle')) {
            button.setAttribute('data-bs-toggle', 'tooltip');
        }
    });
}

/**
 * 顯示警告訊息
 */
function showAlert(message, type) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // 移除現有的警告
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(function(alert) {
        alert.remove();
    });
    
    // 添加新的警告
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);
    }
    
    // 自動隱藏警告
    setTimeout(function() {
        const newAlert = document.querySelector('.alert');
        if (newAlert) {
            newAlert.style.opacity = '0';
            newAlert.style.transition = 'opacity 0.5s';
            setTimeout(function() {
                if (newAlert.parentNode) {
                    newAlert.parentNode.removeChild(newAlert);
                }
            }, 500);
        }
    }, 5000);
}

/**
 * 確認刪除
 */
function confirmDelete(message) {
    return confirm(message || '確定要刪除這個項目嗎？此操作無法復原。');
}

/**
 * 載入工單資訊
 */
function loadWorkOrderInfo(workOrderId) {
    if (!workOrderId) return;
    
    fetch('/workorder/dispatch/api/work-order-info/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ work_order_no: workOrderId })
    })
    .then(response => response.json())
    .then(data => {
        // 更新表單欄位
        if (data.product_code) {
            const productCodeField = document.getElementById('id_product_code');
            if (productCodeField) {
                productCodeField.value = data.product_code;
            }
        }
        if (data.quantity) {
            const quantityField = document.getElementById('id_planned_quantity');
            if (quantityField) {
                quantityField.value = data.quantity;
            }
        }
    })
    .catch(error => {
        console.error('載入工單資訊失敗:', error);
        showAlert('載入工單資訊失敗', 'danger');
    });
}

/**
 * 批量派工
 */
function bulkDispatch(workOrderNos, operatorId, process) {
    if (!workOrderNos || workOrderNos.length === 0) {
        showAlert('請選擇要派工的工單', 'warning');
        return;
    }
    
    if (!operatorId || !process) {
        showAlert('請選擇作業員和工序', 'warning');
        return;
    }
    
    // 獲取 CSRF Token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    const token = csrfToken ? csrfToken.value : '';
    
    fetch('/workorder/dispatch/api/bulk-dispatch/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': token
        },
        body: JSON.stringify({
            work_order_nos: workOrderNos,
            operator_id: operatorId,
            process: process
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message, 'success');
            // 重新載入頁面
            setTimeout(function() {
                location.reload();
            }, 1500);
        } else {
            showAlert(data.error || '批量派工失敗', 'danger');
        }
    })
    .catch(error => {
        console.error('批量派工失敗:', error);
        showAlert('批量派工失敗', 'danger');
    });
}

/**
 * 更新派工單狀態
 */
function updateDispatchStatus(dispatchId, newStatus) {
    // 獲取 CSRF Token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    const token = csrfToken ? csrfToken.value : '';
    
    const formData = new FormData();
    formData.append('status', newStatus);
    
    fetch(`/workorder/dispatch/${dispatchId}/update-status/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': token
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('狀態更新成功', 'success');
            // 重新載入頁面
            setTimeout(function() {
                location.reload();
            }, 1000);
        } else {
            showAlert(data.error || '狀態更新失敗', 'danger');
        }
    })
    .catch(error => {
        console.error('狀態更新失敗:', error);
        showAlert('狀態更新失敗', 'danger');
    });
}

/**
 * 匯出派工單資料
 */
function exportDispatchData(format) {
    const searchParams = new URLSearchParams(window.location.search);
    let url = `/workorder/dispatch/export/?format=${format}`;
    
    // 添加搜尋參數
    if (searchParams.has('search')) {
        url += `&search=${searchParams.get('search')}`;
    }
    if (searchParams.has('status')) {
        url += `&status=${searchParams.get('status')}`;
    }
    if (searchParams.has('start_date')) {
        url += `&start_date=${searchParams.get('start_date')}`;
    }
    if (searchParams.has('end_date')) {
        url += `&end_date=${searchParams.get('end_date')}`;
    }
    
    // 下載檔案
    window.location.href = url;
}

// 全域函數，供其他模組使用
window.DispatchModule = {
    showAlert: showAlert,
    confirmDelete: confirmDelete,
    loadWorkOrderInfo: loadWorkOrderInfo,
    bulkDispatch: bulkDispatch,
    updateDispatchStatus: updateDispatchStatus,
    exportDispatchData: exportDispatchData
}; 