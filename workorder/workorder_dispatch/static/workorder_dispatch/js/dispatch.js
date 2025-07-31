/**
 * 派工單管理模組 JavaScript
 * 提供派工單相關的互動功能
 */

$(document).ready(function() {
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
    // 為表單欄位添加驗證
    $('#dispatchForm').on('submit', function(e) {
        var isValid = true;
        
        // 檢查必填欄位
        $(this).find('[required]').each(function() {
            if (!$(this).val()) {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        // 檢查數量欄位
        var plannedQuantity = $('#id_planned_quantity').val();
        if (plannedQuantity && (isNaN(plannedQuantity) || plannedQuantity <= 0)) {
            $('#id_planned_quantity').addClass('is-invalid');
            isValid = false;
        }
        
        if (!isValid) {
            e.preventDefault();
            showAlert('請檢查表單中的錯誤', 'danger');
        }
    });
    
    // 即時驗證
    $('#id_planned_quantity').on('input', function() {
        var value = $(this).val();
        if (value && (isNaN(value) || value <= 0)) {
            $(this).addClass('is-invalid');
        } else {
            $(this).removeClass('is-invalid');
        }
    });
}

/**
 * 初始化搜尋功能
 */
function initSearchFunction() {
    // 搜尋框自動完成
    $('input[name="search"]').on('input', function() {
        var searchTerm = $(this).val();
        if (searchTerm.length >= 2) {
            // 這裡可以添加 AJAX 搜尋建議功能
            console.log('搜尋:', searchTerm);
        }
    });
    
    // 搜尋表單提交
    $('.dispatch-search-form form').on('submit', function(e) {
        var searchTerm = $(this).find('input[name="search"]').val();
        if (!searchTerm.trim()) {
            e.preventDefault();
            showAlert('請輸入搜尋關鍵字', 'warning');
        }
    });
}

/**
 * 初始化狀態篩選
 */
function initStatusFilter() {
    $('select[name="status"]').on('change', function() {
        // 自動提交表單以應用篩選
        $(this).closest('form').submit();
    });
}

/**
 * 初始化日期選擇器
 */
function initDatePickers() {
    // 為日期欄位添加日期選擇器
    $('input[type="date"]').each(function() {
        $(this).on('change', function() {
            var startDate = $('input[name="start_date"]').val();
            var endDate = $('input[name="end_date"]').val();
            
            if (startDate && endDate && startDate > endDate) {
                showAlert('開始日期不能晚於結束日期', 'warning');
                $(this).val('');
            }
        });
    });
}

/**
 * 初始化工具提示
 */
function initTooltips() {
    // 初始化 Bootstrap 工具提示
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // 為操作按鈕添加工具提示
    $('.btn[title]').each(function() {
        if (!$(this).attr('data-bs-toggle')) {
            $(this).attr('data-bs-toggle', 'tooltip');
        }
    });
}

/**
 * 顯示警告訊息
 */
function showAlert(message, type) {
    var alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // 移除現有的警告
    $('.alert').remove();
    
    // 添加新的警告
    $('.container-fluid').prepend(alertHtml);
    
    // 自動隱藏警告
    setTimeout(function() {
        $('.alert').fadeOut();
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
    
    $.ajax({
        url: '/workorder/dispatch/api/work-order-info/',
        method: 'GET',
        data: { work_order_no: workOrderId },
        success: function(data) {
            // 更新表單欄位
            if (data.product_code) {
                $('#id_product_code').val(data.product_code);
            }
            if (data.quantity) {
                $('#id_planned_quantity').val(data.quantity);
            }
        },
        error: function(xhr, status, error) {
            console.error('載入工單資訊失敗:', error);
            showAlert('載入工單資訊失敗', 'danger');
        }
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
    
    $.ajax({
        url: '/workorder/dispatch/api/bulk-dispatch/',
        method: 'POST',
        data: JSON.stringify({
            work_order_nos: workOrderNos,
            operator_id: operatorId,
            process: process
        }),
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(data) {
            if (data.success) {
                showAlert(data.message, 'success');
                // 重新載入頁面
                setTimeout(function() {
                    location.reload();
                }, 1500);
            } else {
                showAlert(data.error || '批量派工失敗', 'danger');
            }
        },
        error: function(xhr, status, error) {
            console.error('批量派工失敗:', error);
            showAlert('批量派工失敗', 'danger');
        }
    });
}

/**
 * 更新派工單狀態
 */
function updateDispatchStatus(dispatchId, newStatus) {
    $.ajax({
        url: `/workorder/dispatch/${dispatchId}/update-status/`,
        method: 'POST',
        data: { status: newStatus },
        headers: {
            'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
        },
        success: function(data) {
            if (data.success) {
                showAlert('狀態更新成功', 'success');
                // 重新載入頁面
                setTimeout(function() {
                    location.reload();
                }, 1000);
            } else {
                showAlert(data.error || '狀態更新失敗', 'danger');
            }
        },
        error: function(xhr, status, error) {
            console.error('狀態更新失敗:', error);
            showAlert('狀態更新失敗', 'danger');
        }
    });
}

/**
 * 匯出派工單資料
 */
function exportDispatchData(format) {
    var searchParams = new URLSearchParams(window.location.search);
    var url = `/workorder/dispatch/export/?format=${format}`;
    
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