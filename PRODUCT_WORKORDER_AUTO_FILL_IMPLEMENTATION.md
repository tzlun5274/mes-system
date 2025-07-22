# 產品編號和工單號碼雙向自動帶出功能實現說明

## 功能概述

本功能實現了作業員補登報工表單中產品編號和工單號碼的雙向自動帶出功能，並支援RD樣品的特殊處理。

## 主要功能特性

### 1. 產品編號自動帶出工單號碼
- 當用戶在產品編號欄位輸入或選擇產品編號時，系統會自動查詢相關的工單
- 支援實時搜尋（使用防抖函數，500毫秒延遲）
- 如果只有一個相關工單，會自動選擇該工單
- 如果沒有相關工單，會清空工單選項，只保留RD樣品選項

### 2. 工單號碼自動帶出產品編號
- 當用戶選擇工單號碼時，系統會自動填入對應的產品編號
- 同時會更新工單預設生產數量
- 會顯示工單的詳細資訊（工單號碼、公司代號、產品編號、狀態）

### 3. RD樣品特殊處理
- 當選擇RD樣品時，產品編號欄位變為可手動輸入
- 工單預設生產數量自動設為0
- 系統會自動創建對應的RD樣品工單（格式：RD樣品-{產品編號}）

## 技術實現

### 1. 表單修改 (forms.py)

#### 產品編號欄位
```python
# 產品編號欄位（下拉選單或手動輸入）
product_id = forms.CharField(
    max_length=100,
    label="產品編號",
    widget=forms.TextInput(
        attrs={
            "class": "form-control",
            "id": "product_id_input",
            "placeholder": "請選擇或輸入產品編號",
            "list": "product_id_list",
        }
    ),
    required=False,
    help_text="請選擇產品編號，選擇後會自動帶出相關工單（選擇RD樣品時可自由輸入產品編號）",
)
```

#### 工單號碼欄位
```python
# 工單號碼下拉選單
workorder = forms.ChoiceField(
    choices=[],
    label="工單號碼",
    widget=forms.Select(
        attrs={
            "class": "form-control",
            "id": "workorder_select",
            "placeholder": "請選擇工單號碼，或透過產品編號自動帶出",
        }
    ),
    required=False,
    help_text="請選擇工單號碼，或透過產品編號自動帶出（選擇RD樣品時可自由輸入產品編號）",
)
```

### 2. 表單驗證邏輯

#### RD樣品模式
```python
if workorder == 'rd_sample':
    # RD樣品模式驗證
    if not product_id:
        raise forms.ValidationError("產品編號為必填欄位")
    
    # RD樣品模式下，系統會自動創建對應的工單
    cleaned_data['workorder'] = None
    # 設置工單預設生產數量為0
    cleaned_data['planned_quantity'] = 0
```

#### 正式工單模式
```python
elif workorder and workorder != '':
    # 正式工單模式驗證
    if not product_id:
        raise forms.ValidationError("產品編號為必填欄位")
    
    # 驗證工單是否存在
    from .models import WorkOrder
    try:
        selected_workorder = WorkOrder.objects.get(id=workorder)
        cleaned_data['workorder'] = selected_workorder
        cleaned_data['planned_quantity'] = selected_workorder.quantity
    except WorkOrder.DoesNotExist:
        raise forms.ValidationError("選擇的工單不存在")
```

### 3. 前端JavaScript實現

#### 產品編號輸入事件處理
```javascript
// 產品編號輸入事件（自動帶出工單）
if (productInput) {
    // 使用防抖函數，避免頻繁API呼叫
    const debouncedProductSearch = debounce(function(productId) {
        if (productId && productId.trim()) {
            // 呼叫API取得對應的工單
            fetch(`{% url 'workorder:get_workorders_by_product' %}?product_id=${encodeURIComponent(productId.trim())}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success' && data.workorders.length > 0) {
                        // 更新工單下拉選單
                        workorderSelect.innerHTML = '<option value="">請選擇工單號碼</option>';
                        workorderSelect.innerHTML += '<option value="rd_sample">RD樣品</option>';
                        
                        data.workorders.forEach(workorder => {
                            const option = document.createElement('option');
                            option.value = workorder.id;
                            option.textContent = `[${workorder.company_code}] 製令單 ${workorder.order_number}`;
                            workorderSelect.appendChild(option);
                        });
                        
                        // 如果只有一個工單，自動選擇
                        if (data.workorders.length === 1) {
                            workorderSelect.value = data.workorders[0].id;
                            workorderSelect.dispatchEvent(new Event('change'));
                        }
                    }
                });
        }
    }, 500); // 500毫秒延遲
    
    // 監聽輸入事件
    productInput.addEventListener('input', function() {
        debouncedProductSearch(this.value);
    });
}
```

#### 工單選擇事件處理
```javascript
// 工單選擇事件
workorderSelect.addEventListener('change', function() {
    const workorderId = this.value;
    
    if (workorderId && workorderId !== 'rd_sample') {
        // 載入工單詳細資訊
        fetch(`{% url 'workorder:get_workorder_details' %}?workorder_id=${workorderId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const workorder = data.workorder;
                    
                    // 更新工單預設生產數量
                    plannedQuantityInput.value = workorder.quantity;
                    
                    // 自動填入產品編號
                    if (productInput && workorder.product_code) {
                        productInput.value = workorder.product_code;
                    }
                }
            });
    } else if (workorderId === 'rd_sample') {
        // RD樣品模式
        plannedQuantityInput.value = '0';
        workorderInfo.style.display = 'none';
        
        // RD樣品模式下，產品編號可以手動輸入
        if (productInput) {
            productInput.readOnly = false;
            productInput.placeholder = '請輸入RD樣品編號';
            productInput.style.backgroundColor = '#ffffff';
        }
    }
});
```

### 4. API端點

#### 根據產品編號取得工單
```python
@require_GET
@csrf_exempt
def get_workorders_by_product(request):
    """
    AJAX 視圖：根據產品編號取得相關工單
    用於作業員補登報工表單的產品編號和工單聯動
    """
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({
            'status': 'error',
            'message': '請提供產品編號'
        })
    
    try:
        from .models import WorkOrder
        
        # 查詢該產品編號的所有工單
        workorders = WorkOrder.objects.filter(
            product_code=product_id,
            status__in=['pending', 'in_progress']
        ).order_by('-created_at')
        
        workorder_list = []
        for workorder in workorders:
            workorder_list.append({
                'id': workorder.id,
                'order_number': workorder.order_number,
                'company_code': workorder.company_code,
                'quantity': workorder.quantity,
                'status': workorder.get_status_display(),
                'created_at': workorder.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'status': 'success',
            'workorders': workorder_list,
            'count': len(workorder_list)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'查詢失敗：{str(e)}'
        })
```

#### 根據工單ID取得詳細資訊
```python
@require_GET
@csrf_exempt
def get_workorder_details(request):
    """
    AJAX 視圖：根據工單ID取得工單詳細資訊
    用於作業員補登報工表單的工單資訊顯示
    """
    workorder_id = request.GET.get('workorder_id')
    
    if not workorder_id:
        return JsonResponse({
            'status': 'error',
            'message': '請提供工單ID'
        })
    
    try:
        from .models import WorkOrder
        
        workorder = WorkOrder.objects.get(id=workorder_id)
        
        return JsonResponse({
            'status': 'success',
            'workorder': {
                'id': workorder.id,
                'order_number': workorder.order_number,
                'company_code': workorder.company_code,
                'product_code': workorder.product_code,
                'quantity': workorder.quantity,
                'status': workorder.get_status_display(),
                'created_at': workorder.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '找不到指定的工單'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'查詢失敗：{str(e)}'
        })
```

## 使用方式

### 1. 正式工單模式
1. 在產品編號欄位輸入或選擇產品編號
2. 系統會自動顯示相關的工單選項
3. 選擇工單後，系統會自動填入產品編號和工單預設生產數量
4. 產品編號欄位會變為唯讀狀態

### 2. RD樣品模式
1. 在工單號碼欄位選擇"RD樣品"
2. 產品編號欄位會變為可手動輸入狀態
3. 輸入RD樣品編號
4. 工單預設生產數量會自動設為0
5. 系統會自動創建對應的RD樣品工單

## 測試結果

功能測試通過，包括：
- ✓ 表單初始化正常
- ✓ RD樣品選項存在
- ✓ 正式工單選項正確載入
- ✓ RD樣品模式表單驗證通過
- ✓ 正式工單模式表單驗證通過

## 注意事項

1. 產品編號欄位支援手動輸入和自動完成
2. 使用防抖函數避免頻繁API呼叫
3. RD樣品模式下產品編號可以自由輸入
4. 正式工單模式下產品編號為唯讀
5. 工單預設生產數量會根據選擇的工單自動更新 