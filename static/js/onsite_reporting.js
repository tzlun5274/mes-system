/**
 * 現場報工 JavaScript 功能
 * 包含自動加入工序、工序檢查等功能
 */

class OnsiteReportingManager {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.initProcessCheck();
    }

    bindEvents() {
        // 工單號碼變更時檢查工序
        $(document).on('change', '#id_workorder', function() {
            OnsiteReportingManager.checkWorkorderProcesses();
        });

        // 工序選擇變更時檢查是否需要加入
        $(document).on('change', '#id_process', function() {
            OnsiteReportingManager.checkProcessInWorkorder();
        });

        // 手動檢查工序按鈕
        $(document).on('click', '.check-processes-btn', function() {
            OnsiteReportingManager.checkWorkorderProcesses();
        });

        // 自動加入工序按鈕
        $(document).on('click', '.auto-add-process-btn', function() {
            OnsiteReportingManager.autoAddProcess();
        });
    }

    initProcessCheck() {
        // 頁面載入時檢查工序
        if ($('#id_workorder').val()) {
            OnsiteReportingManager.checkWorkorderProcesses();
        }
    }

    /**
     * 檢查工單的工序列表
     */
    static checkWorkorderProcesses() {
        const workorderNumber = $('#id_workorder').val();
        if (!workorderNumber) {
            OnsiteReportingManager.hideProcessInfo();
            return;
        }

        // 顯示載入中
        OnsiteReportingManager.showLoading('正在檢查工單工序...');

        $.ajax({
            url: '/workorder/onsite_reporting/api/get-workorder-processes/',
            method: 'GET',
            data: {
                workorder_number: workorderNumber
            },
            success: function(response) {
                if (response.success) {
                    OnsiteReportingManager.displayProcessList(response.processes);
                } else {
                    OnsiteReportingManager.showError('檢查工序失敗：' + response.message);
                }
            },
            error: function(xhr) {
                OnsiteReportingManager.showError('檢查工序失敗：' + xhr.responseText);
            }
        });
    }

    /**
     * 檢查選擇的工序是否在工單中
     */
    static checkProcessInWorkorder() {
        const workorderNumber = $('#id_workorder').val();
        const processName = $('#id_process').val();
        
        if (!workorderNumber || !processName) {
            return;
        }

        $.ajax({
            url: '/workorder/onsite_reporting/api/get-workorder-processes/',
            method: 'GET',
            data: {
                workorder_number: workorderNumber
            },
            success: function(response) {
                if (response.success) {
                    const processExists = response.processes.some(p => p.process_name === processName);
                    if (!processExists) {
                        OnsiteReportingManager.showProcessNotFound(processName);
                    } else {
                        OnsiteReportingManager.hideProcessNotFound();
                    }
                }
            }
        });
    }

    /**
     * 自動加入工序到工單
     */
    static autoAddProcess() {
        const workorderNumber = $('#id_workorder').val();
        const processName = $('#id_process').val();
        const operator = $('#id_operator').val();
        const equipment = $('#id_equipment').val() || '';

        if (!workorderNumber || !processName || !operator) {
            OnsiteReportingManager.showError('請填寫工單號碼、工序名稱和作業員');
            return;
        }

        // 顯示載入中
        OnsiteReportingManager.showLoading('正在加入工序...');

        $.ajax({
            url: '/workorder/onsite_reporting/api/auto-add-process/',
            method: 'POST',
            data: JSON.stringify({
                workorder_number: workorderNumber,
                process_name: processName,
                operator: operator,
                equipment: equipment
            }),
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    if (response.already_exists) {
                        OnsiteReportingManager.showSuccess('工序已存在於工單中');
                    } else {
                        OnsiteReportingManager.showSuccess('工序已成功加入到工單中');
                        // 重新檢查工序列表
                        OnsiteReportingManager.checkWorkorderProcesses();
                    }
                } else {
                    OnsiteReportingManager.showError('加入工序失敗：' + response.message);
                }
            },
            error: function(xhr) {
                OnsiteReportingManager.showError('加入工序失敗：' + xhr.responseText);
            }
        });
    }

    /**
     * 顯示工序列表
     */
    static displayProcessList(processes) {
        let html = '<div class="process-list-container">';
        html += '<h6><i class="fas fa-list"></i> 工單工序列表</h6>';
        
        if (processes.length === 0) {
            html += '<p class="text-muted">此工單目前沒有工序</p>';
        } else {
            html += '<div class="table-responsive">';
            html += '<table class="table table-sm table-bordered">';
            html += '<thead><tr>';
            html += '<th>步驟</th>';
            html += '<th>工序名稱</th>';
            html += '<th>狀態</th>';
            html += '<th>作業員</th>';
            html += '<th>設備</th>';
            html += '<th>計劃數量</th>';
            html += '<th>完成數量</th>';
            html += '</tr></thead>';
            html += '<tbody>';
            
            processes.forEach(function(process) {
                const statusClass = OnsiteReportingManager.getStatusClass(process.status);
                const completionRate = process.planned_quantity > 0 ? 
                    Math.round((process.completed_quantity / process.planned_quantity) * 100) : 0;
                
                html += '<tr>';
                html += `<td>${process.step_order}</td>`;
                html += `<td>${process.process_name}</td>`;
                html += `<td><span class="badge ${statusClass}">${OnsiteReportingManager.getStatusText(process.status)}</span></td>`;
                html += `<td>${process.assigned_operator || '-'}</td>`;
                html += `<td>${process.assigned_equipment || '-'}</td>`;
                html += `<td>${process.planned_quantity}</td>`;
                html += `<td>${process.completed_quantity} (${completionRate}%)</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            html += '</div>';
        }
        
        html += '</div>';
        
        OnsiteReportingManager.showProcessInfo(html);
    }

    /**
     * 顯示工序未找到的提示
     */
    static showProcessNotFound(processName) {
        const html = `
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>工序未找到：</strong>工序 "${processName}" 不在當前工單的工序列表中。
                <button type="button" class="btn btn-sm btn-warning ms-2 auto-add-process-btn">
                    <i class="fas fa-plus"></i> 自動加入此工序
                </button>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // 移除舊的提示
        $('.process-not-found-alert').remove();
        
        // 加入新的提示
        $('#id_process').after(`<div class="process-not-found-alert">${html}</div>`);
    }

    /**
     * 隱藏工序未找到的提示
     */
    static hideProcessNotFound() {
        $('.process-not-found-alert').remove();
    }

    /**
     * 顯示工序資訊
     */
    static showProcessInfo(html) {
        // 移除舊的工序資訊
        $('.process-info-container').remove();
        
        // 加入新的工序資訊
        $('#id_workorder').closest('.form-group').after(`<div class="process-info-container">${html}</div>`);
    }

    /**
     * 隱藏工序資訊
     */
    static hideProcessInfo() {
        $('.process-info-container').remove();
    }

    /**
     * 顯示載入中
     */
    static showLoading(message) {
        // 移除舊的載入提示
        $('.loading-alert').remove();
        
        const html = `
            <div class="alert alert-info loading-alert" role="alert">
                <i class="fas fa-spinner fa-spin"></i> ${message}
            </div>
        `;
        
        $('.container').prepend(html);
    }

    /**
     * 顯示成功訊息
     */
    static showSuccess(message) {
        // 移除載入提示
        $('.loading-alert').remove();
        
        const html = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="fas fa-check-circle"></i> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('.container').prepend(html);
        
        // 3秒後自動移除
        setTimeout(function() {
            $('.alert-success').fadeOut();
        }, 3000);
    }

    /**
     * 顯示錯誤訊息
     */
    static showError(message) {
        // 移除載入提示
        $('.loading-alert').remove();
        
        const html = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-circle"></i> ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        $('.container').prepend(html);
    }

    /**
     * 取得狀態樣式類別
     */
    static getStatusClass(status) {
        const statusClasses = {
            'pending': 'bg-secondary',
            'in_progress': 'bg-primary',
            'completed': 'bg-success',
            'paused': 'bg-warning',
            'cancelled': 'bg-danger'
        };
        return statusClasses[status] || 'bg-secondary';
    }

    /**
     * 取得狀態文字
     */
    static getStatusText(status) {
        const statusTexts = {
            'pending': '待生產',
            'in_progress': '生產中',
            'completed': '已完成',
            'paused': '暫停',
            'cancelled': '取消'
        };
        return statusTexts[status] || status;
    }
}

// 頁面載入完成後初始化
$(document).ready(function() {
    new OnsiteReportingManager();
}); 