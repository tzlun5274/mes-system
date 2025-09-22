/**
 * 工單模組主要JavaScript檔案
 * 包含工單管理、報工管理等功能的前端互動邏輯
 * 使用原生JavaScript，符合設計規範
 */

// 全域變數
let workorderApp = {
    // 配置設定
    config: {
        apiBaseUrl: '/workorder/api/',
        csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        debug: false
    },
    
    // 初始化
    init: function() {
        this.bindEvents();
        this.initComponents();
        this.log('工單模組初始化完成');
    },
    
    // 事件綁定
    bindEvents: function() {
        // 搜尋功能
        this.bindSearchEvents();
        
        // 表單驗證
        this.bindFormValidation();
        
        // 動態載入
        this.bindDynamicLoading();
        
        // 確認對話框
        this.bindConfirmDialogs();
    },
    
    // 初始化組件
    initComponents: function() {
        // 初始化工具提示
        this.initTooltips();
        
        // 初始化載入動畫
        this.initLoadingSpinners();
        
        // 初始化表格排序
        this.initTableSorting();
    },
    
    // 搜尋功能事件綁定
    bindSearchEvents: function() {
        const searchInputs = document.querySelectorAll('.search-input');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.debounce(this.handleSearch, 300));
        });
        
        // 清除搜尋按鈕
        const clearSearchBtns = document.querySelectorAll('.clear-search');
        clearSearchBtns.forEach(btn => {
            btn.addEventListener('click', this.clearSearch);
        });
    },
    
    // 搜尋處理
    handleSearch: function(event) {
        const searchTerm = event.target.value.trim();
        const searchType = event.target.dataset.searchType || 'general';
        
        workorderApp.log(`執行搜尋: ${searchTerm}, 類型: ${searchType}`);
        
        // 顯示載入動畫
        workorderApp.showLoading();
        
        // 執行搜尋
        workorderApp.performSearch(searchTerm, searchType)
            .then(results => {
                workorderApp.updateSearchResults(results);
                workorderApp.hideLoading();
            })
            .catch(error => {
                workorderApp.showError('搜尋失敗: ' + error.message);
                workorderApp.hideLoading();
            });
    },
    
    // 執行搜尋
    performSearch: async function(searchTerm, searchType) {
        const url = new URL(window.location);
        url.searchParams.set('search', searchTerm);
        url.searchParams.set('search_type', searchType);
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    },
    
    // 更新搜尋結果
    updateSearchResults: function(results) {
        const resultsContainer = document.querySelector('.search-results');
        if (!resultsContainer) return;
        
        if (results.length === 0) {
            resultsContainer.innerHTML = '<div class="alert alert-info">沒有找到符合的結果</div>';
            return;
        }
        
        let html = '';
        results.forEach(item => {
            html += this.renderSearchResultItem(item);
        });
        
        resultsContainer.innerHTML = html;
        this.animateResults();
    },
    
    // 渲染搜尋結果項目
    renderSearchResultItem: function(item) {
        return `
            <div class="search-result-item fade-in-up">
                <div class="card workorder-card">
                    <div class="card-body">
                        <h5 class="card-title">${item.title || item.order_number}</h5>
                        <p class="card-text">${item.description || ''}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="status-badge status-${item.status}">${item.status_display}</span>
                            <a href="${item.detail_url}" class="btn btn-primary btn-sm">查看詳情</a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },
    
    // 清除搜尋
    clearSearch: function() {
        const searchInputs = document.querySelectorAll('.search-input');
        searchInputs.forEach(input => {
            input.value = '';
        });
        
        const resultsContainer = document.querySelector('.search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
        
        // 重新載入頁面或重置表格
        location.reload();
    },
    
    // 表單驗證事件綁定
    bindFormValidation: function() {
        const forms = document.querySelectorAll('.form-workorder');
        forms.forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit);
            
            // 即時驗證
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', this.validateField);
                input.addEventListener('input', this.clearFieldError);
            });
        });
    },
    
    // 表單提交處理
    handleFormSubmit: function(event) {
        const form = event.target;
        
        if (!workorderApp.validateForm(form)) {
            event.preventDefault();
            workorderApp.showError('請檢查表單中的錯誤');
            return false;
        }
        
        // 顯示載入動畫
        workorderApp.showFormLoading(form);
        
        workorderApp.log('表單提交: ' + form.action);
    },
    
    // 表單驗證
    validateForm: function(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!workorderApp.validateField({ target: field })) {
                isValid = false;
            }
        });
        
        return isValid;
    },
    
    // 欄位驗證
    validateField: function(event) {
        const field = event.target;
        const value = field.value.trim();
        const fieldName = field.name;
        
        // 清除之前的錯誤
        workorderApp.clearFieldError(event);
        
        // 必填欄位驗證
        if (field.hasAttribute('required') && !value) {
            workorderApp.showFieldError(field, '此欄位為必填');
            return false;
        }
        
        // 特定欄位驗證
        switch (fieldName) {
            case 'order_number':
                if (value && !/^[A-Z0-9-]+$/.test(value)) {
                    workorderApp.showFieldError(field, '工單號碼格式不正確');
                    return false;
                }
                break;
                
            case 'quantity':
                if (value && (isNaN(value) || parseInt(value) <= 0)) {
                    workorderApp.showFieldError(field, '數量必須為正整數');
                    return false;
                }
                break;
                
            case 'start_time':
            case 'end_time':
                if (value && !workorderApp.validateTimeFormat(value)) {
                    workorderApp.showFieldError(field, '時間格式不正確 (HH:MM)');
                    return false;
                }
                break;
        }
        
        return true;
    },
    
    // 顯示欄位錯誤
    showFieldError: function(field, message) {
        field.classList.add('is-invalid');
        
        let errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            field.parentNode.appendChild(errorDiv);
        }
        
        errorDiv.textContent = message;
    },
    
    // 清除欄位錯誤
    clearFieldError: function(event) {
        const field = event.target;
        field.classList.remove('is-invalid');
        
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    },
    
    // 時間格式驗證
    validateTimeFormat: function(timeStr) {
        const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
        return timeRegex.test(timeStr);
    },
    
    // 動態載入事件綁定
    bindDynamicLoading: function() {
        // 無限滾動
        this.bindInfiniteScroll();
        
        // 動態載入下拉選單
        this.bindDynamicSelects();
    },
    
    // 無限滾動
    bindInfiniteScroll: function() {
        let isLoading = false;
        let page = 1;
        
        window.addEventListener('scroll', this.debounce(() => {
            if (isLoading) return;
            
            const scrollTop = window.pageYOffset;
            const windowHeight = window.innerHeight;
            const documentHeight = document.documentElement.scrollHeight;
            
            if (scrollTop + windowHeight >= documentHeight - 100) {
                isLoading = true;
                page++;
                
                this.loadMoreItems(page)
                    .then(() => {
                        isLoading = false;
                    })
                    .catch(error => {
                        this.showError('載入更多項目失敗: ' + error.message);
                        isLoading = false;
                    });
            }
        }, 100));
    },
    
    // 載入更多項目
    loadMoreItems: async function(page) {
        const url = new URL(window.location);
        url.searchParams.set('page', page);
        
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.items && data.items.length > 0) {
            this.appendItems(data.items);
        }
    },
    
    // 添加項目到列表
    appendItems: function(items) {
        const container = document.querySelector('.items-container');
        if (!container) return;
        
        items.forEach(item => {
            const itemElement = this.createItemElement(item);
            container.appendChild(itemElement);
        });
        
        this.animateResults();
    },
    
    // 創建項目元素
    createItemElement: function(item) {
        const div = document.createElement('div');
        div.className = 'item-element fade-in-up';
        div.innerHTML = this.renderItem(item);
        return div;
    },
    
    // 確認對話框事件綁定
    bindConfirmDialogs: function() {
        const confirmButtons = document.querySelectorAll('[data-confirm]');
        confirmButtons.forEach(button => {
            button.addEventListener('click', this.handleConfirmClick);
        });
    },
    
    // 確認點擊處理
    handleConfirmClick: function(event) {
        const message = event.target.dataset.confirm || '確定要執行此操作嗎？';
        
        if (!confirm(message)) {
            event.preventDefault();
            return false;
        }
    },
    
    // 工具提示初始化
    initTooltips: function() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', this.showTooltip);
            element.addEventListener('mouseleave', this.hideTooltip);
        });
    },
    
    // 顯示工具提示
    showTooltip: function(event) {
        const element = event.target;
        const text = element.dataset.tooltip;
        
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip-custom';
        tooltip.innerHTML = `
            <span class="tooltip-text">${text}</span>
        `;
        
        document.body.appendChild(tooltip);
        
        // 定位工具提示
        const rect = element.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) + 'px';
        tooltip.style.top = rect.top - 10 + 'px';
        
        element.tooltipElement = tooltip;
    },
    
    // 隱藏工具提示
    hideTooltip: function(event) {
        const element = event.target;
        if (element.tooltipElement) {
            element.tooltipElement.remove();
            element.tooltipElement = null;
        }
    },
    
    // 載入動畫初始化
    initLoadingSpinners: function() {
        const loadingElements = document.querySelectorAll('.loading-spinner');
        loadingElements.forEach(element => {
            element.style.display = 'inline-block';
        });
    },
    
    // 顯示載入動畫
    showLoading: function() {
        const loadingOverlay = document.querySelector('.loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
    },
    
    // 隱藏載入動畫
    hideLoading: function() {
        const loadingOverlay = document.querySelector('.loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    },
    
    // 顯示表單載入動畫
    showFormLoading: function(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading-spinner"></span> 處理中...';
        }
    },
    
    // 表格排序初始化
    initTableSorting: function() {
        const sortableHeaders = document.querySelectorAll('th[data-sort]');
        sortableHeaders.forEach(header => {
            header.addEventListener('click', this.handleTableSort);
        });
    },
    
    // 表格排序處理
    handleTableSort: function(event) {
        const header = event.target;
        const sortField = header.dataset.sort;
        const currentOrder = header.dataset.order || 'asc';
        const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
        
        // 更新所有表頭的排序狀態
        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.dataset.order = '';
            th.classList.remove('sort-asc', 'sort-desc');
        });
        
        // 設置當前表頭的排序狀態
        header.dataset.order = newOrder;
        header.classList.add(`sort-${newOrder}`);
        
        // 執行排序
        workorderApp.sortTable(sortField, newOrder);
    },
    
    // 表格排序
    sortTable: function(sortField, order) {
        const table = document.querySelector('.table-workorder');
        if (!table) return;
        
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aValue = a.querySelector(`[data-${sortField}]`)?.dataset[sortField] || '';
            const bValue = b.querySelector(`[data-${sortField}]`)?.dataset[sortField] || '';
            
            if (order === 'asc') {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        });
        
        // 重新排列行
        rows.forEach(row => tbody.appendChild(row));
    },
    
    // 動畫效果
    animateResults: function() {
        const elements = document.querySelectorAll('.fade-in-up');
        elements.forEach((element, index) => {
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 100);
        });
    },
    
    // 顯示錯誤訊息
    showError: function(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.main-container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        // 自動移除
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    },
    
    // 顯示成功訊息
    showSuccess: function(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.main-container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        // 自動移除
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    },
    
    // 防抖函數
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // 日誌記錄
    log: function(message) {
        if (this.config.debug) {
            console.log(`[工單模組] ${message}`);
        }
    }
};

// 頁面載入完成後初始化
document.addEventListener('DOMContentLoaded', function() {
    workorderApp.init();
});

// 全域函數供其他模組使用
window.workorderApp = workorderApp; 