/**
 * 工單管理統一配置檔案
 * 統一資料來源：workorder_workorder
 * API路徑：/var/www/mes/workorder/static/api/
 * 
 * 本檔案提供工單管理系統的統一配置，確保所有子模組都基於統一的資料來源
 */

// 統一配置物件
const WorkOrderUnifiedConfig = {
    // 基本配置
    version: '1.0.0',
    dataSource: 'workorder_workorder',
    
    // API路徑配置
    api: {
        baseUrl: '/var/www/mes/workorder/static/api/',
        endpoints: {
            // 工單基本操作
            workorderList: '/get_workorder_list_unified/',
            workorderDetail: '/get_workorder_detail_unified/',
            workorderCreate: '/create_workorder_unified/',
            workorderUpdate: '/update_workorder_unified/',
            workorderDelete: '/delete_workorder_unified/',
            
            // 工單查詢（多公司架構）
            workorderByCompany: '/get_workorder_by_company_unified/',
            workorderByProduct: '/get_workorder_by_product_unified/',
            workorderByStatus: '/get_workorder_by_status_unified/',
            
            // 工序管理
            processList: '/get_process_list_unified/',
            processDetail: '/get_process_detail_unified/',
            processCreate: '/create_process_unified/',
            processUpdate: '/update_process_unified/',
            processDelete: '/delete_process_unified/',
            
            // 生產監控
            productionStatus: '/get_production_status_unified/',
            productionProgress: '/get_production_progress_unified/',
            productionReport: '/get_production_report_unified/',
            
            // 現場報工關聯
            onsiteReportList: '/get_onsite_report_list_unified/',
            onsiteReportDetail: '/get_onsite_report_detail_unified/',
            onsiteReportCreate: '/create_onsite_report_unified/',
            
            // 填報管理關聯
            fillWorkList: '/get_fill_work_list_unified/',
            fillWorkDetail: '/get_fill_work_detail_unified/',
            fillWorkCreate: '/create_fill_work_unified/',
            
            // 完工判斷
            completionStatus: '/get_completion_status_unified/',
            completionCalculate: '/calculate_completion_unified/',
            
            // 資料統計
            statistics: '/get_workorder_statistics_unified/',
            dashboard: '/get_workorder_dashboard_unified/'
        }
    },
    
    // 多公司架構配置
    multiCompany: {
        enabled: true,
        uniqueIdentifier: ['company_code', 'order_number', 'product_code'],
        dataIsolation: true
    },
    
    // 生產監控配置
    productionMonitor: {
        // 工序紀錄來源
        processRecordSource: 'onsite_report',
        // 填報紀錄來源
        fillRecordSource: 'fill_work',
        // 完工判斷方式
        completionCalculation: 'process_and_fill_merge'
    },
    
    // 快取配置
    cache: {
        enabled: true,
        defaultTTL: 300, // 5分鐘
        maxSize: 1000
    },
    
    // 錯誤處理配置
    errorHandling: {
        showUserFriendlyMessages: true,
        logToConsole: true,
        retryAttempts: 3
    }
};

// 統一工具函數
const WorkOrderUtils = {
    // 格式化公司代號
    formatCompanyCode: function(companyCode) {
        if (!companyCode) return '';
        return companyCode.toString().padStart(2, '0');
    },
    
    // 格式化工單顯示名稱
    formatWorkOrderDisplay: function(workorder, productCode, companyCode = null) {
        const formattedCompany = companyCode ? `[${this.formatCompanyCode(companyCode)}] ` : '';
        return `${formattedCompany}工單 ${workorder} - ${productCode}`;
    },
    
    // 驗證工單號碼格式
    validateWorkOrderNumber: function(orderNumber) {
        if (!orderNumber) return false;
        return /^[A-Z0-9\-_]+$/i.test(orderNumber);
    },
    
    // 驗證產品編號格式
    validateProductCode: function(productCode) {
        if (!productCode) return false;
        return /^[A-Z0-9\-_]+$/i.test(productCode);
    },
    
    // 驗證公司代號格式
    validateCompanyCode: function(companyCode) {
        if (!companyCode) return false;
        return /^[0-9]{1,2}$/.test(companyCode);
    },
    
    // 取得工單狀態顯示文字
    getStatusText: function(status) {
        const statusMap = {
            'pending': '待生產',
            'in_progress': '生產中',
            'paused': '暫停',
            'completed': '已完成'
        };
        return statusMap[status] || status;
    },
    
    // 取得工單狀態CSS類別
    getStatusClass: function(status) {
        const classMap = {
            'pending': 'badge-warning',
            'in_progress': 'badge-primary',
            'paused': 'badge-secondary',
            'completed': 'badge-success'
        };
        return classMap[status] || 'badge-light';
    },
    
    // 建立唯一識別碼
    createUniqueIdentifier: function(companyCode, orderNumber, productCode) {
        return `${this.formatCompanyCode(companyCode)}_${orderNumber}_${productCode}`;
    },
    
    // 解析唯一識別碼
    parseUniqueIdentifier: function(uniqueId) {
        const parts = uniqueId.split('_');
        if (parts.length >= 3) {
            return {
                companyCode: parts[0],
                orderNumber: parts[1],
                productCode: parts.slice(2).join('_')
            };
        }
        return null;
    }
};

// 資料驗證規則
const WorkOrderValidation = {
    // 工單資料驗證規則
    workorder: {
        companyCode: {
            required: true,
            pattern: /^[0-9]{1,2}$/,
            message: '公司代號必須是1-2位數字'
        },
        orderNumber: {
            required: true,
            pattern: /^[A-Z0-9\-_]+$/i,
            message: '工單號碼只能包含字母、數字、連字號和底線'
        },
        productCode: {
            required: true,
            pattern: /^[A-Z0-9\-_]+$/i,
            message: '產品編號只能包含字母、數字、連字號和底線'
        },
        quantity: {
            required: true,
            min: 1,
            message: '數量必須大於0'
        }
    },
    
    // 工序資料驗證規則
    process: {
        processName: {
            required: true,
            message: '工序名稱不能為空'
        },
        stepOrder: {
            required: true,
            min: 1,
            message: '工序順序必須大於0'
        },
        plannedQuantity: {
            required: true,
            min: 1,
            message: '計劃數量必須大於0'
        }
    }
};

// 統一錯誤處理
const WorkOrderErrorHandler = {
    // 處理API錯誤
    handleAPIError: function(error, context = '') {
        console.error(`工單API錯誤 [${context}]:`, error);
        
        let userMessage = '操作失敗，請稍後再試';
        
        if (error.response) {
            // 伺服器回應錯誤
            switch (error.response.status) {
                case 400:
                    userMessage = '請求資料格式錯誤';
                    break;
                case 401:
                    userMessage = '請先登入系統';
                    break;
                case 403:
                    userMessage = '沒有權限執行此操作';
                    break;
                case 404:
                    userMessage = '找不到指定的資料';
                    break;
                case 500:
                    userMessage = '伺服器內部錯誤';
                    break;
                default:
                    userMessage = `伺服器錯誤 (${error.response.status})`;
            }
        } else if (error.request) {
            // 網路錯誤
            userMessage = '網路連線錯誤，請檢查網路狀態';
        } else {
            // 其他錯誤
            userMessage = error.message || userMessage;
        }
        
        // 顯示錯誤訊息
        this.showErrorMessage(userMessage);
    },
    
    // 顯示錯誤訊息
    showErrorMessage: function(message) {
        if (typeof showToast === 'function') {
            showToast('error', message);
        } else if (typeof alert === 'function') {
            alert(message);
        } else {
            console.error('無法顯示錯誤訊息:', message);
        }
    },
    
    // 顯示成功訊息
    showSuccessMessage: function(message) {
        if (typeof showToast === 'function') {
            showToast('success', message);
        } else if (typeof alert === 'function') {
            alert(message);
        } else {
            console.log('成功訊息:', message);
        }
    }
};

// 統一配置載入器
const WorkOrderConfigLoader = {
    // 載入配置
    load: function() {
        // 檢查是否已載入
        if (window.workOrderUnifiedConfig) {
            console.log('工單統一配置已載入');
            return window.workOrderUnifiedConfig;
        }
        
        // 設定全域配置
        window.workOrderUnifiedConfig = WorkOrderUnifiedConfig;
        window.workOrderUtils = WorkOrderUtils;
        window.workOrderValidation = WorkOrderValidation;
        window.workOrderErrorHandler = WorkOrderErrorHandler;
        
        console.log('工單統一配置載入完成');
        return WorkOrderUnifiedConfig;
    },
    
    // 檢查配置完整性
    validate: function() {
        const config = this.load();
        
        // 檢查必要配置
        const requiredFields = [
            'dataSource',
            'api.baseUrl',
            'multiCompany.enabled'
        ];
        
        for (const field of requiredFields) {
            const value = this.getNestedValue(config, field);
            if (value === undefined || value === null) {
                console.error(`缺少必要配置: ${field}`);
                return false;
            }
        }
        
        console.log('工單統一配置驗證通過');
        return true;
    },
    
    // 取得巢狀物件值
    getNestedValue: function(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : undefined;
        }, obj);
    }
};

// 自動載入配置
document.addEventListener('DOMContentLoaded', function() {
    WorkOrderConfigLoader.load();
    WorkOrderConfigLoader.validate();
});

// 匯出模組
window.WorkOrderUnifiedConfig = WorkOrderUnifiedConfig;
window.WorkOrderUtils = WorkOrderUtils;
window.WorkOrderValidation = WorkOrderValidation;
window.WorkOrderErrorHandler = WorkOrderErrorHandler;
window.WorkOrderConfigLoader = WorkOrderConfigLoader;

console.log('工單管理統一配置模組已載入'); 