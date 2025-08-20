/**
 * 工單管理統一API端點
 * 統一資料來源：workorder_workorder
 * API路徑：/var/www/mes/workorder/static/api/
 * 
 * 本檔案提供工單管理系統的統一API介面，確保所有子模組都基於統一的資料來源
 */

// 統一API配置
const WorkOrderUnifiedAPI = {
    // API基礎路徑
    baseUrl: '/var/www/mes/workorder/static/api/',
    
    // 統一資料來源
    dataSource: 'workorder_workorder',
    
    // API端點定義
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
    },
    
    // 統一請求方法
    request: async function(endpoint, method = 'GET', data = null, params = {}) {
        try {
            const url = this.baseUrl + endpoint;
            const queryString = new URLSearchParams(params).toString();
            const fullUrl = queryString ? `${url}?${queryString}` : url;
            
            const requestOptions = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            };
            
            if (data && method !== 'GET') {
                requestOptions.body = JSON.stringify(data);
            }
            
            const response = await fetch(fullUrl, requestOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API請求失敗:', error);
            throw error;
        }
    },
    
    // 取得CSRF Token
    getCSRFToken: function() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    },
    
    // 統一錯誤處理
    handleError: function(error, context = '') {
        console.error(`工單統一API錯誤 [${context}]:`, error);
        
        const errorMessage = error.message || '操作失敗，請稍後再試';
        
        if (typeof showToast === 'function') {
            showToast('error', errorMessage);
        } else {
            alert(errorMessage);
        }
    }
};

// 工單資料管理
const WorkOrderDataManager = {
    // 快取管理
    cache: new Map(),
    
    // 取得工單資料（帶快取）
    async getWorkOrderData(workorderId, companyCode = null) {
        const cacheKey = `workorder_${workorderId}_${companyCode || 'all'}`;
        
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }
        
        try {
            const params = { workorder_id: workorderId };
            if (companyCode) {
                params.company_code = companyCode;
            }
            
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.workorderDetail,
                'GET',
                null,
                params
            );
            
            if (data.success) {
                this.cache.set(cacheKey, data.workorder);
                return data.workorder;
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getWorkOrderData');
            throw error;
        }
    },
    
    // 取得工單列表（多公司架構）
    async getWorkOrderList(companyCode = null, status = null, page = 1) {
        try {
            const params = { page: page };
            if (companyCode) {
                params.company_code = companyCode;
            }
            if (status) {
                params.status = status;
            }
            
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.workorderList,
                'GET',
                null,
                params
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getWorkOrderList');
            throw error;
        }
    },
    
    // 清除快取
    clearCache() {
        this.cache.clear();
    },
    
    // 清除特定工單快取
    clearWorkOrderCache(workorderId, companyCode = null) {
        const cacheKey = `workorder_${workorderId}_${companyCode || 'all'}`;
        this.cache.delete(cacheKey);
    }
};

// 生產監控管理
const ProductionMonitor = {
    // 取得生產狀態
    async getProductionStatus(workorderId) {
        try {
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.productionStatus,
                'GET',
                null,
                { workorder_id: workorderId }
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getProductionStatus');
            throw error;
        }
    },
    
    // 取得生產進度
    async getProductionProgress(workorderId) {
        try {
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.productionProgress,
                'GET',
                null,
                { workorder_id: workorderId }
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getProductionProgress');
            throw error;
        }
    },
    
    // 取得完工狀態（工序紀錄 + 填報紀錄合併計算）
    async getCompletionStatus(workorderId) {
        try {
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.completionStatus,
                'GET',
                null,
                { workorder_id: workorderId }
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getCompletionStatus');
            throw error;
        }
    }
};

// 現場報工管理
const OnsiteReportManager = {
    // 取得現場報工列表
    async getOnsiteReportList(workorderId) {
        try {
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.onsiteReportList,
                'GET',
                null,
                { workorder_id: workorderId }
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getOnsiteReportList');
            throw error;
        }
    },
    
    // 建立現場報工記錄
    async createOnsiteReport(reportData) {
        try {
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.onsiteReportCreate,
                'POST',
                reportData
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'createOnsiteReport');
            throw error;
        }
    }
};

// 填報管理
const FillWorkManager = {
    // 取得填報記錄列表
    async getFillWorkList(workorderId) {
        try {
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.fillWorkList,
                'GET',
                null,
                { workorder_id: workorderId }
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getFillWorkList');
            throw error;
        }
    },
    
    // 建立填報記錄
    async createFillWork(fillWorkData) {
        try {
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.fillWorkCreate,
                'POST',
                fillWorkData
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'createFillWork');
            throw error;
        }
    }
};

// 統計報表
const WorkOrderStatistics = {
    // 取得工單統計資料
    async getStatistics(companyCode = null, dateRange = null) {
        try {
            const params = {};
            if (companyCode) {
                params.company_code = companyCode;
            }
            if (dateRange) {
                params.start_date = dateRange.start;
                params.end_date = dateRange.end;
            }
            
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.statistics,
                'GET',
                null,
                params
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getStatistics');
            throw error;
        }
    },
    
    // 取得儀表板資料
    async getDashboard(companyCode = null) {
        try {
            const params = {};
            if (companyCode) {
                params.company_code = companyCode;
            }
            
            const data = await WorkOrderUnifiedAPI.request(
                WorkOrderUnifiedAPI.endpoints.dashboard,
                'GET',
                null,
                params
            );
            
            return data;
        } catch (error) {
            WorkOrderUnifiedAPI.handleError(error, 'getDashboard');
            throw error;
        }
    }
};

// 匯出模組
window.WorkOrderUnifiedAPI = WorkOrderUnifiedAPI;
window.WorkOrderDataManager = WorkOrderDataManager;
window.ProductionMonitor = ProductionMonitor;
window.OnsiteReportManager = OnsiteReportManager;
window.FillWorkManager = FillWorkManager;
window.WorkOrderStatistics = WorkOrderStatistics;

// 全域配置
window.workOrderUnifiedConfig = {
    apiPrefix: '/var/www/mes/workorder/static/api/workorder_unified_api.js',
    dataSource: 'workorder_workorder',
    enableCache: true,
    enableMultiCompany: true
};

console.log('工單管理統一API模組已載入'); 