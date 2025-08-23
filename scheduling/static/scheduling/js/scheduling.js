// Scheduling 模組腳本（全新重寫）
document.addEventListener('DOMContentLoaded', function() {
    console.log('Scheduling module loaded');
    // 取得一鍵自動優化按鈕
    const btnAutoOptimize = document.getElementById('btnAutoOptimize');
    if (btnAutoOptimize) {
        btnAutoOptimize.addEventListener('click', function() {
            const resultDiv = document.getElementById('autoOptimizeResult');
            if (resultDiv) {
                resultDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin"></i> 正在自動優化排程，請稍候...</div>';
                resultDiv.style.display = 'block';
            }
            // 按鈕立即變成優化中
            btnAutoOptimize.disabled = true;
            btnAutoOptimize.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 自動優化中...';
            // 取得表單資料
            const form = document.getElementById('hybridSchedulingForm');
            if (!form) {
                alert('找不到排程表單，請重新整理頁面！');
                btnAutoOptimize.disabled = false;
                btnAutoOptimize.innerHTML = '<i class="fas fa-magic"></i> 一鍵自動優化';
                return;
            }
            const formData = new FormData(form);
            // 發送 AJAX 請求到後端
            fetch('/scheduling/hybrid/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                // 處理回傳結果，渲染到 autoOptimizeResult
                if (resultDiv) {
                    if (data.status === 'success' || data.status === 'partial_success') {
                        let html = `<div class='alert alert-success'><i class='fas fa-check-circle'></i> ${data.message || '自動優化完成！'}</div>`;
                        html += `<div><b>剩餘衝突數：</b> ${data.validation_errors ? data.validation_errors.length : 0}</div>`;
                        if (data.validation_errors && data.validation_errors.length > 0) {
                            html += '<div class="mt-2"><b>詳細衝突列表：</b><ul>';
                            data.validation_errors.forEach(function(warn) {
                                html += `<li>${warn}</li>`;
                            });
                            html += '</ul></div>';
                        }
                        if (data.failed_orders && data.failed_orders.length > 0) {
                            html += '<div class="mt-2"><b>無法排程訂單：</b><ul>';
                            data.failed_orders.forEach(function(order) {
                                html += `<li>產品編號：${order.product_id}，原因：${order.reason}，建議：${order.suggestion}</li>`;
                            });
                            html += '</ul></div>';
                        }
                        resultDiv.innerHTML = html;
                    } else {
                        resultDiv.innerHTML = `<div class='alert alert-danger'><i class='fas fa-exclamation-triangle'></i> ${data.message || '自動優化失敗，請稍後再試！'}</div>`;
                    }
                }
                if (data.status === 'success') {
                    // 可選：自動刷新排程看板或其他區塊
                }
            })
            .catch(err => {
                if (resultDiv) {
                    resultDiv.innerHTML = '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> 自動優化失敗，請稍後再試！</div>';
                }
            })
            .finally(() => {
                // 按鈕恢復原狀
                btnAutoOptimize.disabled = false;
                btnAutoOptimize.innerHTML = '<i class="fas fa-magic"></i> 一鍵自動優化';
            });
        });
    }
});
// 本檔案負責混合排程頁面「一鍵自動優化」功能，點擊會即時切換狀態並呼叫後端 API。
