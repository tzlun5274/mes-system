/**
 * 工單表單通用 JavaScript 模組
 * 統一處理所有工單表單的功能：產品編號、工單號碼、公司名稱、作業員、工序、設備
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
        // 基本欄位
        this.productSelect = document.getElementById('product_id');
        this.workorderSelect = document.getElementById('workorder');
        this.companySelect = document.getElementById('company_name');
        this.plannedQuantityInput = document.getElementById('planned_quantity');
        
        // 作業員、工序、設備欄位
        this.operatorSelect = document.getElementById('operator');
        this.operatorDisplay = document.getElementById('operator_display');
        this.processSelect = document.getElementById('process');
        this.equipmentSelect = document.getElementById('equipment');
        
        // 除錯資訊
        console.log('初始化元素結果:');
        console.log('- productSelect:', this.productSelect ? '找到' : '未找到');
        console.log('- workorderSelect:', this.workorderSelect ? '找到' : '未找到');
        console.log('- companySelect:', this.companySelect ? '找到' : '未找到');
        console.log('- operatorSelect:', this.operatorSelect ? '找到' : '未找到');
        console.log('- operatorDisplay:', this.operatorDisplay ? '找到' : '未找到');
        console.log('- processSelect:', this.processSelect ? '找到' : '未找到');
        console.log('- equipmentSelect:', this.equipmentSelect ? '找到' : '未找到');
        
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
            this.handleProductChange();
        });

        // 工單號碼變更事件
        this.workorderSelect.addEventListener('change', () => {
            this.handleWorkorderChange();
        });

        // 設備選擇事件（已移至各模板中處理）
        // 設備選擇自動填入作業員功能已移至各模板中處理
        // SMT模板：在 smt_backfill_form.html 中處理
        // 作業員模板：在 operator_backfill_form.html 中處理
    }

    // 載入初始資料
    async loadInitialData() {
        try {
            // 先載入公司名稱
            await this.loadCompanies();
            
            // 再載入產品編號
            await this.loadProducts();
            
            // 最後載入工單號碼
            await this.loadWorkorders();
            
            // 載入作業員、工序、設備選項
            await this.loadOperatorProcessEquipment();
            
            // 檢查是否有預先填入的產品編號，如果有則觸發載入工單
            if (this.productSelect.value) {
                console.log('檢測到預先填入的產品編號:', this.productSelect.value);
                // 延遲執行，確保DOM完全載入
                setTimeout(() => {
                    console.log('延遲載入工單，產品編號:', this.productSelect.value);
                    this.handleProductChange();
                }, 500);
            } else {
                console.log('沒有預先填入的產品編號');
            }
        } catch (error) {
            console.error('載入初始資料失敗:', error);
        }
    }

    // 通用 API 呼叫方法
    async fetchAPI(url, options = {}) {
        try {
            const response = await fetch(url, {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`API請求失敗: ${response.status} ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API呼叫失敗 (${url}):`, error);
            throw error;
        }
    }

    // 通用選項填充方法
    populateSelect(selectElement, data, options = {}) {
        if (!selectElement) return;
        
        const {
            placeholder = '請選擇',
            valueKey = 'name',
            textKey = 'name',
            filter = null,
            sort = true,
            preserveValue = true
        } = options;
        
        // 保存當前選中的值
        const currentValue = preserveValue ? selectElement.value : '';
        
        // 清空選項
        selectElement.innerHTML = `<option value="">${placeholder}</option>`;
        
        // 處理資料
        let processedData = Array.isArray(data) ? data : [];
        
        // 應用過濾器
        if (filter) {
            processedData = processedData.filter(filter);
        }
        
        // 排序
        if (sort) {
            processedData.sort((a, b) => {
                const aText = typeof a === 'string' ? a : a[textKey];
                const bText = typeof b === 'string' ? b : b[textKey];
                return aText.localeCompare(bText);
            });
        }
        
        // 填充選項
        processedData.forEach(item => {
            const option = document.createElement('option');
            
            if (typeof item === 'string') {
                option.value = item;
                option.textContent = item;
            } else {
                option.value = item[valueKey];
                option.textContent = item[textKey];
                
                // 複製額外的資料屬性
                if (item.company_name) option.dataset.company = item.company_name;
                if (item.planned_quantity) option.dataset.quantity = item.planned_quantity;
                if (item.product_id) option.dataset.product = item.product_id;
            }
            
            selectElement.appendChild(option);
        });
        
        // 恢復之前選中的值
        if (currentValue && preserveValue) {
            selectElement.value = currentValue;
        }
        
        console.log(`填充選項完成，共 ${processedData.length} 個選項`);
        return processedData.length;
    }

    // 載入公司名稱
    async loadCompanies() {
        try {
            const data = await this.fetchAPI('/workorder/static/api/workorder-list/');
            if (data.success && data.workorders) {
                // 從工單資料中提取公司名稱，過濾掉純數字的公司代號和null值
                const companies = [...new Set(data.workorders.map(w => w.company_name))]
                    .filter(company => company && company.trim() !== '' && !/^\d+$/.test(company));
                
                this.populateSelect(this.companySelect, companies, {
                    placeholder: '請選擇公司名稱'
                });
            }
        } catch (error) {
            console.error('載入公司名稱失敗:', error);
        }
    }

    // 載入產品編號
    async loadProducts(companyName = '') {
        try {
            let url = '/workorder/static/api/product-list/';
            if (companyName) {
                url = `/workorder/static/api/products-by-company/?company_name=${encodeURIComponent(companyName)}`;
            }
            
            console.log('載入產品編號，URL:', url);
            const data = await this.fetchAPI(url);
            console.log('產品編號API回應:', data);
            
            if (data.success && data.products) {
                // 根據表單類型過濾產品
                let filteredProducts = data.products;
                const formType = this.getFormType();
                
                if (formType === 'smt' || formType === 'smt_rd') {
                    // SMT表單：顯示所有產品（SMT設備可以處理所有產品）
                    // 不進行產品過濾，因為產品編號本身不包含SMT字串
                    console.log('SMT表單：顯示所有產品');
                } else if (formType === 'operator_rd') {
                    // 作業員RD樣品表單：顯示所有產品（取消PFP-CCT開頭限制）
                    console.log('作業員RD樣品表單：顯示所有產品');
                } else {
                    // 作業員表單：顯示所有產品（因為產品編號不包含SMT字串）
                    console.log('作業員表單：顯示所有產品');
                }
                
                console.log('過濾後的產品:', filteredProducts);
                
                this.populateSelect(this.productSelect, filteredProducts, {
                    placeholder: '請選擇產品編號',
                    valueKey: 'product_id',
                    textKey: 'product_id'
                });
            }
        } catch (error) {
            console.error('載入產品編號失敗:', error);
        }
    }

    // 載入工單號碼
    async loadWorkorders(productId = '', companyName = '') {
        try {
            let url = '/workorder/static/api/workorder-list/';
            if (productId) {
                url = `/workorder/static/api/workorder-by-product/?product_id=${encodeURIComponent(productId)}`;
                console.log('載入特定產品編號的工單:', productId);
            } else {
                console.log('載入所有工單');
            }
            
            const data = await this.fetchAPI(url);
            if (data.success && data.workorders) {
                // 如果使用特定產品編號的API，直接使用返回的資料
                // 如果使用通用API，則需要篩選
                let filteredWorkorders = data.workorders;
                if (!productId && companyName) {
                    // 只有在使用通用API且有公司名稱時才篩選
                    filteredWorkorders = filteredWorkorders.filter(w => w.company_name === companyName);
                }
                
                this.populateSelect(this.workorderSelect, filteredWorkorders, {
                    placeholder: '請選擇工單號碼',
                    valueKey: 'workorder',
                    textKey: 'workorder',
                    preserveValue: false
                });
            }
        } catch (error) {
            console.error('載入工單號碼失敗:', error);
        }
    }

    // 載入作業員、工序、設備
    async loadOperatorProcessEquipment() {
        try {
            // 載入作業員
            if (this.operatorSelect) {
                await this.loadOperators();
            }
            
            // 載入工序
            if (this.processSelect) {
                await this.loadProcesses();
            }
            
            // 載入設備
            if (this.equipmentSelect) {
                await this.loadEquipment();
            }
        } catch (error) {
            console.error('載入作業員、工序、設備失敗:', error);
        }
    }

    // 載入作業員
    async loadOperators() {
        try {
            // 如果是SMT表單且有作業員顯示欄位，不需要載入作業員選項
            if (this.getFormType() === 'smt' && this.operatorDisplay) {
                console.log('SMT表單：作業員欄位為唯讀顯示，不載入選項');
                return;
            }
            
            // 作業員表單才載入作業員選項
            const data = await this.fetchAPI('/workorder/static/api/operator-list/');
            if (data.success && data.operators) {
                this.populateSelect(this.operatorSelect, data.operators, {
                    placeholder: '請選擇作業員'
                });
            }
        } catch (error) {
            console.error('載入作業員失敗:', error);
        }
    }

    // 載入工序
    async loadProcesses() {
        try {
            // 根據表單類型決定API參數
            const formType = this.getFormType();
            const url = `/workorder/static/api/process-list/?form_type=${formType}`;
            const data = await this.fetchAPI(url);
            if (data.success && data.processes) {
                this.populateSelect(this.processSelect, data.processes, {
                    placeholder: '請選擇此次報工的工序'
                });
            }
        } catch (error) {
            console.error('載入工序失敗:', error);
        }
    }

    // 載入設備
    async loadEquipment() {
        try {
            // 根據表單類型決定API參數
            const formType = this.getFormType();
            const url = `/workorder/static/api/equipment-list/?form_type=${formType}`;
            const data = await this.fetchAPI(url);
            if (data.success && data.equipments) {
                this.populateSelect(this.equipmentSelect, data.equipments, {
                    placeholder: '請選擇設備',
                    preserveValue: false  // 不保留之前的值，避免觸發change事件
                });
            }
        } catch (error) {
            console.error('載入設備失敗:', error);
        }
    }

    // 獲取表單類型
    getFormType() {
        // 檢查URL路徑來判斷表單類型
        const pathname = window.location.pathname;
        
        // 檢查是否為RD樣品表單
        if (pathname.includes('/rd/') || pathname.includes('rd_')) {
            if (pathname.includes('/smt/') || pathname.includes('smt_')) {
                return 'smt_rd';  // SMT RD樣品
            } else {
                return 'operator_rd';  // 作業員 RD樣品
            }
        }
        
        // 檢查是否為SMT表單
        if (pathname.includes('/smt/') || pathname.includes('smt_')) {
            return 'smt';
        } else {
            return 'operator';
        }
    }

    // 處理產品編號變更
    async handleProductChange() {
        const productId = this.productSelect.value;
        if (productId) {
            console.log('產品編號變更為:', productId);
            
            // 載入對應的工單號碼
            await this.loadWorkorders(productId, this.companySelect.value);
            
            // 檢查是否有工單選項載入
            const actualOptions = this.workorderSelect.options.length - 1; // 減去預設選項
            console.log('載入的工單選項數量:', actualOptions);
            
            if (actualOptions === 1) {
                // 如果只有一個工單，自動選擇並觸發工單變更事件
                const workorderOption = this.workorderSelect.options[1]; // 第一個實際選項
                if (workorderOption) {
                    this.workorderSelect.value = workorderOption.value;
                    console.log('自動選擇唯一工單:', workorderOption.value);
                    this.handleWorkorderChange();
                }
            } else if (actualOptions > 1) {
                console.log('有多個工單選項，請手動選擇');
            } else {
                console.log('沒有找到對應的工單');
            }
        } else {
            // 清空工單號碼選項
            this.workorderSelect.innerHTML = '<option value="">請選擇工單號碼</option>';
            // 清空預設生產數量
            if (this.plannedQuantityInput) {
                this.plannedQuantityInput.value = '';
            }
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

    // 處理設備變更（已移至各模板中處理）
    handleEquipmentChange() {
        console.log('handleEquipmentChange 被呼叫 - 此功能已移至各模板中處理');
        // 設備選擇自動填入作業員功能已移至各模板中處理
        // SMT模板：在 smt_backfill_form.html 中處理
        // 作業員模板：在 operator_backfill_form.html 中處理
    }

    // 獲取CSRF Token
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // 重置所有選項
    resetAllOptions() {
        // 重置基本欄位
        this.productSelect.innerHTML = '<option value="">請選擇產品編號</option>';
        this.workorderSelect.innerHTML = '<option value="">請選擇工單號碼</option>';
        if (this.plannedQuantityInput) {
            this.plannedQuantityInput.value = '';
        }
        
        // 重置作業員、工序、設備欄位
        if (this.operatorSelect) {
            this.operatorSelect.innerHTML = '<option value="">請選擇作業員</option>';
        }
        if (this.operatorDisplay) {
            this.operatorDisplay.value = '';
        }
        if (this.processSelect) {
            this.processSelect.innerHTML = '<option value="">請選擇此次報工的工序</option>';
        }
        if (this.equipmentSelect) {
            this.equipmentSelect.innerHTML = '<option value="">請選擇設備</option>';
        }
        
        // 重新載入資料
        this.loadInitialData();
    }
}

// 全域函數，供其他腳本使用
window.FillWorkController = FillWorkController; 