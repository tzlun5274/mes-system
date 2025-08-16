/**
 * 填報表單通用 JavaScript 模組
 * 統一處理產品編號、工單號碼、公司名稱的雙向關聯選擇
 */

class FillWorkController {
    constructor() {
        this.initializeElements();
        this.initializeEventListeners();
        this.loadInitialData();
        
        // 儲存全域實例，供重置功能使用
        window.fillWorkController = this;
    }

    // 初始化 DOM 元素
    initializeElements() {
        this.productSelect = document.getElementById('product_id');
        this.workorderSelect = document.getElementById('workorder');
        this.companySelect = document.getElementById('company_name');
        this.plannedQuantityInput = document.getElementById('planned_quantity');
        
        // 檢查必要元素是否存在
        if (!this.productSelect || !this.workorderSelect || !this.companySelect) {
            console.error('找不到必要的下拉選單元素');
            return;
        }
    }

    // 初始化事件監聽器
    initializeEventListeners() {
        // 公司名稱變更事件
        this.companySelect.addEventListener('change', () => {
            const companyName = this.companySelect.value;
            console.log('公司名稱變更為:', companyName);
            this.loadProducts(companyName);
            this.loadWorkorders('', companyName);
        });

        // 產品編號變更事件
        this.productSelect.addEventListener('change', () => {
            const productId = this.productSelect.value;
            const companyName = this.companySelect.value;
            console.log('產品編號變更為:', productId, '公司名稱:', companyName);
            this.loadWorkorders(productId, companyName);
        });

        // 工單號碼變更事件
        this.workorderSelect.addEventListener('change', () => {
            this.handleWorkorderChange();
        });
    }

    // 載入初始資料
    loadInitialData() {
        this.loadCompanies();
        this.loadProducts();
        this.loadWorkorders();
    }

    // 載入公司名稱
    async loadCompanies() {
        try {
            const response = await fetch('/workorder/fill_work/api/workorder-list/');
            const data = await response.json();
            if (data.workorders) {
                // 從工單資料中提取公司名稱
                const companies = [...new Set(data.workorders.map(w => w.company_name))].sort();
                this.companySelect.innerHTML = '<option value="">請選擇公司名稱</option>';
                companies.forEach(company => {
                    const option = document.createElement('option');
                    option.value = company;
                    option.textContent = company;
                    this.companySelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('載入公司名稱失敗:', error);
        }
    }

    // 載入產品編號
    async loadProducts(companyName = '') {
        try {
            let url = '/workorder/fill_work/api/product-list/';
            if (companyName) {
                url = `/workorder/fill_work/api/products-by-company/?company_name=${encodeURIComponent(companyName)}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            if (data.products) {
                this.productSelect.innerHTML = '<option value="">請選擇產品編號</option>';
                data.products.forEach(product => {
                    const option = document.createElement('option');
                    // 處理不同的資料格式
                    if (typeof product === 'string') {
                        option.value = product;
                        option.textContent = product;
                    } else if (product && product.product_id) {
                        option.value = product.product_id;
                        option.textContent = product.product_id;
                    }
                    this.productSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('載入產品編號失敗:', error);
        }
    }

    // 載入工單號碼
    async loadWorkorders(productId = '', companyName = '') {
        try {
            let url = '/workorder/fill_work/api/workorder-list/';
            if (productId) {
                url = `/workorder/fill_work/api/workorder-by-product/?product_id=${encodeURIComponent(productId)}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            if (data.workorders) {
                this.workorderSelect.innerHTML = '<option value="">請選擇工單號碼</option>';
                
                // 篩選工單（根據產品編號和公司名稱）
                let filteredWorkorders = data.workorders;
                if (companyName) {
                    filteredWorkorders = filteredWorkorders.filter(w => w.company_name === companyName);
                }
                
                filteredWorkorders.forEach(workorder => {
                    const option = document.createElement('option');
                    option.value = workorder.workorder;
                    option.textContent = workorder.workorder;
                    option.dataset.company = workorder.company_name;
                    option.dataset.quantity = workorder.planned_quantity;
                    option.dataset.product = workorder.product_id;
                    this.workorderSelect.appendChild(option);
                });
                
                console.log(`載入工單號碼完成，共 ${filteredWorkorders.length} 個選項`);
                
                // 如果選擇了產品編號，自動選擇第一個工單
                if (productId && filteredWorkorders.length > 0) {
                    const firstWorkorder = filteredWorkorders[0].workorder;
                    this.workorderSelect.value = firstWorkorder;
                    // 觸發工單變更事件
                    this.handleWorkorderChange();
                }
            }
        } catch (error) {
            console.error('載入工單號碼失敗:', error);
        }
    }

    // 處理工單變更
    handleWorkorderChange() {
        const selectedOption = this.workorderSelect.options[this.workorderSelect.selectedIndex];
        if (selectedOption && selectedOption.value) {
            console.log('工單號碼變更為:', selectedOption.value);
            
            // 自動填入公司名稱
            if (selectedOption.dataset.company) {
                this.companySelect.value = selectedOption.dataset.company;
                console.log('自動填入公司名稱:', selectedOption.dataset.company);
            }
            
            // 自動填入預設生產數量
            const quantity = selectedOption.dataset.quantity || 0;
            if (this.plannedQuantityInput) {
                this.plannedQuantityInput.value = quantity;
                console.log('自動填入預設生產數量:', quantity);
            }
            
            // 自動填入產品編號
            if (selectedOption.dataset.product) {
                const productId = selectedOption.dataset.product;
                console.log('自動填入產品編號:', productId);
                
                // 檢查產品編號是否已存在於選項中
                const existingOption = this.productSelect.querySelector(`option[value="${productId}"]`);
                if (!existingOption) {
                    // 如果不存在，新增選項
                    const newOption = document.createElement('option');
                    newOption.value = productId;
                    newOption.textContent = productId;
                    this.productSelect.appendChild(newOption);
                }
                
                // 設定選中的產品編號
                this.productSelect.value = productId;
            }
            
        } else {
            // 清空預設生產數量
            if (this.plannedQuantityInput) {
                this.plannedQuantityInput.value = '';
                console.log('清空預設生產數量');
            }
        }
    }

    // 重置所有選項（當選錯時使用）
    resetAllOptions() {
        this.productSelect.innerHTML = '<option value="">請選擇產品編號</option>';
        this.workorderSelect.innerHTML = '<option value="">請選擇工單號碼</option>';
        if (this.plannedQuantityInput) {
            this.plannedQuantityInput.value = '';
        }
        this.loadInitialData();
    }
}

// 全域函數，供其他腳本使用
window.FillWorkController = FillWorkController;

// 全域重置函數，供按 F5 時使用
window.resetFillWorkForm = function() {
    if (window.fillWorkController) {
        window.fillWorkController.resetAllOptions();
    }
}; 