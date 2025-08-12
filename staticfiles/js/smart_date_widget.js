/**
 * 智慧日期輸入小工具 JavaScript
 * 提供即時格式轉換和友好的使用者體驗
 * 完全取代瀏覽器原生的限制性日期輸入
 */

(function() {
    'use strict';
    
    // 日期格式正規化函數
    function normalizeDateString(dateStr) {
        if (!dateStr) return '';
        
        const str = dateStr.toString().trim();
        if (!str) return '';
        
        // 移除所有非數字字符，用於檢測純數字格式
        const digitsOnly = str.replace(/[^0-9]/g, '');
        
        // YYYYMMDD 格式
        if (/^\d{8}$/.test(digitsOnly)) {
            const y = parseInt(digitsOnly.slice(0, 4), 10);
            const m = parseInt(digitsOnly.slice(4, 6), 10);
            const d = parseInt(digitsOnly.slice(6, 8), 10);
            if (isValidDate(y, m, d)) {
                return formatDate(y, m, d);
            }
        }
        
        // YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
        let match = str.match(/^(\d{4})[\-\/\.](\d{1,2})[\-\/\.](\d{1,2})$/);
        if (match) {
            const y = parseInt(match[1], 10);
            const m = parseInt(match[2], 10);
            const d = parseInt(match[3], 10);
            if (isValidDate(y, m, d)) {
                return formatDate(y, m, d);
            }
        }
        
        // DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
        match = str.match(/^(\d{1,2})[\-\/\.](\d{1,2})[\-\/\.](\d{4})$/);
        if (match) {
            const d = parseInt(match[1], 10);
            const m = parseInt(match[2], 10);
            const y = parseInt(match[3], 10);
            if (isValidDate(y, m, d)) {
                return formatDate(y, m, d);
            }
        }
        
        // MM-DD-YYYY, MM/DD/YYYY, MM.DD.YYYY (美式格式)
        match = str.match(/^(\d{1,2})[\-\/\.](\d{1,2})[\-\/\.](\d{4})$/);
        if (match) {
            const m = parseInt(match[1], 10);
            const d = parseInt(match[2], 10);
            const y = parseInt(match[3], 10);
            if (isValidDate(y, m, d)) {
                return formatDate(y, m, d);
            }
        }
        
        return str; // 無法解析時返回原字串
    }
    
    // 檢查日期是否有效
    function isValidDate(year, month, day) {
        if (year < 1900 || year > 2100) return false;
        if (month < 1 || month > 12) return false;
        if (day < 1 || day > 31) return false;
        
        const date = new Date(year, month - 1, day);
        return date.getFullYear() === year && 
               date.getMonth() === month - 1 && 
               date.getDate() === day;
    }
    
    // 格式化日期為 YYYY-MM-DD
    function formatDate(year, month, day) {
        return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
    }
    
    // 初始化智慧日期輸入
    function initSmartDateInput(input) {
        if (input.dataset.smartDateInitialized) return;
        input.dataset.smartDateInitialized = 'true';
        
        // 創建提示元素
        const hint = document.createElement('div');
        hint.className = 'smart-date-hint';
        hint.style.cssText = `
            font-size: 12px;
            color: #6c757d;
            margin-top: 4px;
            display: none;
        `;
        input.parentNode.insertBefore(hint, input.nextSibling);
        
        // 輸入事件處理
        input.addEventListener('input', function() {
            const value = this.value;
            const normalized = normalizeDateString(value);
            
            if (normalized && normalized !== value) {
                hint.textContent = `將轉換為：${normalized}`;
                hint.style.display = 'block';
                hint.style.color = '#28a745';
            } else if (value && !normalized) {
                hint.textContent = '無法識別的日期格式';
                hint.style.display = 'block';
                hint.style.color = '#dc3545';
            } else {
                hint.style.display = 'none';
            }
        });
        
        // 失去焦點時自動轉換
        input.addEventListener('blur', function() {
            const value = this.value;
            const normalized = normalizeDateString(value);
            
            if (normalized && normalized !== value) {
                this.value = normalized;
                hint.textContent = '已自動轉換格式';
                hint.style.color = '#28a745';
                setTimeout(() => {
                    hint.style.display = 'none';
                }, 2000);
            }
        });
        
        // 貼上事件處理
        input.addEventListener('paste', function(e) {
            setTimeout(() => {
                const value = this.value;
                const normalized = normalizeDateString(value);
                
                if (normalized && normalized !== value) {
                    this.value = normalized;
                    hint.textContent = '已自動轉換貼上的日期格式';
                    hint.style.display = 'block';
                    hint.style.color = '#28a745';
                    setTimeout(() => {
                        hint.style.display = 'none';
                    }, 3000);
                }
            }, 100);
        });
        
        // 表單提交前最後檢查
        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                const value = input.value;
                const normalized = normalizeDateString(value);
                
                if (normalized && normalized !== value) {
                    input.value = normalized;
                }
            });
        }
    }
    
    // 頁面載入完成後初始化
    document.addEventListener('DOMContentLoaded', function() {
        // 初始化所有智慧日期輸入
        document.querySelectorAll('.smart-date-input, input[data-smart-date]').forEach(initSmartDateInput);
        
        // 監控動態添加的元素
        if (window.MutationObserver) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            if (node.classList && (node.classList.contains('smart-date-input') || node.hasAttribute('data-smart-date'))) {
                                initSmartDateInput(node);
                            } else if (node.querySelectorAll) {
                                node.querySelectorAll('.smart-date-input, input[data-smart-date]').forEach(initSmartDateInput);
                            }
                        }
                    });
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    });
    
    // 全域函數，供外部調用
    window.initSmartDateInput = initSmartDateInput;
    window.normalizeDateString = normalizeDateString;
    
})(); 