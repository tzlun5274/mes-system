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
            this.handleProductChange();
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
    }

    // 載入公司名稱
    async loadCompanies() {
        try {
            const response = await fetch('/workorder/api/workorder-list/');
            const data = await response.json();
            if (data.success && data.workorders) {
                // 保存當前選中的值
                const currentValue = this.companySelect.value;
                
                // 從工單資料中提取公司名稱，過濾掉純數字的公司代號
                const companies = [...new Set(data.workorders.map(w => w.company_name))]
                    .filter(company => {
                        // 過濾掉純數字的公司代號（如 "01", "02" 等）
                        return !/^\d+$/.test(company) && company.trim() !== '';
                    })
                    .sort();
                
                this.companySelect.innerHTML = '<option value="">請選擇公司名稱</option>';
                companies.forEach(company => {
                    const option = document.createElement('option');
                    option.value = company;
                    option.textContent = company;
                    this.companySelect.appendChild(option);
                });
                
                // 恢復之前選中的值
                if (currentValue) {
                    this.companySelect.value = currentValue;
                }
                
                console.log(`載入公司名稱完成，共 ${companies.length} 個選項`);
            }
        } catch (error) {
            console.error('載入公司名稱失敗:', error);
        }
    }

    // 載入產品編號
    async loadProducts(companyName = '') {
        try {
            let url = '/workorder/api/product-list/';
            if (companyName) {
                url = `/workorder/api/products-by-company/?company_name=${encodeURIComponent(companyName)}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            if (data.success && data.products) {
                // 保存當前選中的值
                const currentValue = this.productSelect.value;
                
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
                
                // 恢復之前選中的值
                if (currentValue) {
                    this.productSelect.value = currentValue;
                }
            }
        } catch (error) {
            console.error('載入產品編號失敗:', error);
        }
    }

    // 載入工單號碼
    async loadWorkorders(productId = '', companyName = '') {
        try {
            let url = '/workorder/api/workorder-list/';
            if (productId) {
                url = `/workorder/api/workorder-by-product/?product_id=${encodeURIComponent(productId)}`;
                console.log('載入特定產品編號的工單:', productId);
            } else {
                console.log('載入所有工單');
            }
            
            const response = await fetch(url);
            const data = await response.json();
            console.log('API回應:', data);
            
            if (data.success && data.workorders) {
                this.workorderSelect.innerHTML = '<option value="">請選擇工單號碼</option>';
                
                // 篩選工單（根據產品編號和公司名稱）
                let filteredWorkorders = data.workorders;
                if (productId) {
                    filteredWorkorders = filteredWorkorders.filter(w => w.product_id === productId);
                }
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
                
                // 如果選擇了產品編號且只有一個工單，自動選擇
                if (productId && filteredWorkorders.length === 1) {
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

    // 處理產品編號變更
    async handleProductChange() {
        const productId = this.productSelect.value;
        if (productId) {
            console.log('產品編號變更為:', productId);
            
            // 載入對應的工單號碼
            await this.loadWorkorders(productId, this.companySelect.value);
            
            // 如果只有一個工單，自動選擇並觸發工單變更事件
            if (this.workorderSelect.options.length === 2) { // 1個選項 + 1個預設選項
                const workorderOption = this.workorderSelect.options[1]; // 第一個實際選項
                if (workorderOption) {
                    this.workorderSelect.value = workorderOption.value;
                    this.handleWorkorderChange();
                }
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

/**
 * 作業員、工序、設備統一管理模組
 * 處理所有填報表單中的作業員、工序、設備選擇功能
 */
class OperatorProcessEquipmentController {
    constructor(options = {}) {
        this.options = {
            // 表單類型：'operator'（作業員）或 'smt'（SMT）
            formType: options.formType || 'operator',
            // 是否啟用設備自動填入作業員功能（SMT專用）
            enableEquipmentAutoFill: options.enableEquipmentAutoFill || false,
            // API端點前綴
            apiPrefix: options.apiPrefix || '/workorder/api',
            // 元素ID
            operatorId: options.operatorId || 'operator',
            operatorDisplayId: options.operatorDisplayId || 'operator_display',
            processId: options.processId || 'process',
            equipmentId: options.equipmentId || 'equipment',
            ...options
        };
        
        this.initializeElements();
        this.initializeEventListeners();
        this.loadInitialData();
        
        console.log(`作業員、工序、設備控制器初始化完成，表單類型: ${this.options.formType}`);
    }

    // 初始化 DOM 元素
    initializeElements() {
        this.operatorSelect = document.getElementById(this.options.operatorId);
        this.operatorDisplay = document.getElementById(this.options.operatorDisplayId);
        this.processSelect = document.getElementById(this.options.processId);
        this.equipmentSelect = document.getElementById(this.options.equipmentId);
        
        // 檢查必要元素是否存在
        if (!this.processSelect) {
            console.error('找不到必要的工序下拉選單元素');
            return;
        }
    }

    // 初始化事件監聽器
    initializeEventListeners() {
        // 設備選擇事件（SMT專用）
        if (this.equipmentSelect && this.options.enableEquipmentAutoFill) {
            this.equipmentSelect.addEventListener('change', () => {
                this.handleEquipmentChange();
            });
        }
    }

    // 載入初始資料
    loadInitialData() {
        this.loadOperators();
        this.loadProcesses();
        if (this.equipmentSelect) {
            this.loadEquipment();
        }
    }

    // 載入作業員
    async loadOperators() {
        try {
            const response = await fetch(`${this.options.apiPrefix}/operator-list/`);
            const data = await response.json();
            if (data.success) {
                // 如果是SMT表單且有作業員顯示欄位，不需要載入作業員選項
                if (this.options.formType === 'smt' && this.operatorDisplay) {
                    console.log('SMT表單：作業員欄位為唯讀顯示，不載入選項');
                    return;
                }
                
                // 如果是作業員表單，載入作業員選項
                if (this.operatorSelect) {
                    this.operatorSelect.innerHTML = '<option value="">請選擇作業員</option>';
                    data.operators.forEach(operator => {
                        const option = document.createElement('option');
                        option.value = operator.name;
                        option.textContent = operator.name;
                        this.operatorSelect.appendChild(option);
                    });
                    console.log(`載入作業員完成，共 ${data.operators.length} 個選項`);
                }
            }
        } catch (error) {
            console.error('載入作業員失敗:', error);
        }
    }

    // 載入工序（根據表單類型過濾）
    async loadProcesses() {
        try {
            const response = await fetch(`${this.options.apiPrefix}/process-list/?form_type=${this.options.formType}`);
            const data = await response.json();
            if (data.success) {
                this.processSelect.innerHTML = '<option value="">請選擇此次報工的工序</option>';
                
                data.processes.forEach(process => {
                    const option = document.createElement('option');
                    option.value = process.name;
                    option.textContent = process.name;
                    this.processSelect.appendChild(option);
                });
                
                console.log(`載入工序完成，表單類型: ${this.options.formType}`);
            }
        } catch (error) {
            console.error('載入工序失敗:', error);
        }
    }

    // 載入設備（根據表單類型過濾）
    async loadEquipment() {
        try {
            const response = await fetch(`${this.options.apiPrefix}/equipment-list/?form_type=${this.options.formType}`);
            const data = await response.json();
            if (data.success) {
                this.equipmentSelect.innerHTML = '<option value="">請選擇設備</option>';
                
                data.equipments.forEach(equipment => {
                    const option = document.createElement('option');
                    option.value = equipment.name;
                    option.textContent = equipment.name;
                    this.equipmentSelect.appendChild(option);
                });
                
                console.log(`載入設備完成，表單類型: ${this.options.formType}`);
            }
        } catch (error) {
            console.error('載入設備失敗:', error);
        }
    }

    // 處理設備變更（SMT專用）
    handleEquipmentChange() {
        if (!this.options.enableEquipmentAutoFill) return;
        
        const equipmentName = this.equipmentSelect.value;
        if (equipmentName) {
            // 自動填入作業員欄位為設備名稱
            if (this.options.formType === 'smt' && this.operatorDisplay) {
                // SMT表單：填入顯示欄位和隱藏欄位
                this.operatorDisplay.value = equipmentName;
                if (this.operatorSelect) {
                    this.operatorSelect.value = equipmentName;
                }
                console.log('SMT表單：設備選擇時自動填入作業員:', equipmentName);
            } else if (this.operatorSelect) {
                // 作業員表單：填入下拉選單
                this.operatorSelect.value = equipmentName;
                console.log('作業員表單：設備選擇時自動填入作業員:', equipmentName);
            }
        } else {
            // 如果沒有選擇設備，清空作業員欄位
            if (this.options.formType === 'smt' && this.operatorDisplay) {
                this.operatorDisplay.value = '';
                if (this.operatorSelect) {
                    this.operatorSelect.value = '';
                }
            } else if (this.operatorSelect) {
                this.operatorSelect.value = '';
            }
        }
    }

    // 重置所有選項
    resetAllOptions() {
        if (this.operatorSelect) {
            this.operatorSelect.innerHTML = '<option value="">請選擇作業員</option>';
        }
        if (this.processSelect) {
            this.processSelect.innerHTML = '<option value="">請選擇此次報工的工序</option>';
        }
        if (this.equipmentSelect) {
            this.equipmentSelect.innerHTML = '<option value="">請選擇設備</option>';
        }
        this.loadInitialData();
    }

    // 取得選中的值
    getSelectedValues() {
        return {
            operator: this.operatorSelect ? this.operatorSelect.value : '',
            process: this.processSelect ? this.processSelect.value : '',
            equipment: this.equipmentSelect ? this.equipmentSelect.value : ''
        };
    }

    // 設定值
    setValues(values) {
        if (values.operator && this.operatorSelect) {
            this.operatorSelect.value = values.operator;
        }
        if (values.process && this.processSelect) {
            this.processSelect.value = values.process;
        }
        if (values.equipment && this.equipmentSelect) {
            this.equipmentSelect.value = values.equipment;
        }
    }
}

// 全域函數，供其他腳本使用
window.FillWorkController = FillWorkController;
window.OperatorProcessEquipmentController = OperatorProcessEquipmentController;

// 全域重置函數，供按 F5 時使用
window.resetFillWorkForm = function() {
    if (window.fillWorkController) {
        window.fillWorkController.resetAllOptions();
    }
};

// 全域作業員、工序、設備重置函數
window.resetOperatorProcessEquipmentForm = function() {
    if (window.operatorProcessEquipmentController) {
        window.operatorProcessEquipmentController.resetAllOptions();
    }
}; 