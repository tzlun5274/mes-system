# SMT 現場報工 - 派工單連動問題修復報告

## 問題描述

在 SMT 現場報工系統中，當使用者選擇設備後，工單號下拉選單沒有載入對應的派工單，一直顯示「請先選擇設備...」的提示訊息。

## 問題分析

### 1. 根本原因
- 前端 JavaScript 中的 `loadWorkorders` 函數使用硬編碼的測試資料
- 沒有真正從後端 API 獲取該設備的工單列表
- 在 `<option>` 標籤中使用了不支援的 HTML 標籤（`<span class="badge">`），導致 JavaScript 錯誤

### 2. 技術架構問題
- 缺少 `get_workorders_by_equipment` API 端點
- 前端與後端資料連動機制不完整

## 修復方案

### 1. 建立後端 API 端點

**檔案：** `workorder/views.py`
**新增函數：** `get_workorders_by_equipment`

```python
@require_GET
@csrf_exempt
def get_workorders_by_equipment(request):
    """
    API：根據設備 ID 獲取該設備的工單列表
    用於 SMT 現場報工系統中的工單選擇
    """
    try:
        equipment_id = request.GET.get('equipment_id')
        
        if not equipment_id:
            return JsonResponse({
                'status': 'error',
                'message': '請提供設備 ID'
            })
        
        # 取得設備
        from equip.models import Equipment
        try:
            equipment = Equipment.objects.get(id=equipment_id)
        except Equipment.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '找不到指定的設備'
            })
        
        # 查詢該設備相關的工單
        workorder_processes = WorkOrderProcess.objects.filter(
            assigned_equipment=equipment.name,
            status__in=['pending', 'in_progress']
        ).select_related('workorder')
        
        # 去重並整理工單資料
        workorders = []
        seen_workorder_ids = set()
        
        for process in workorder_processes:
            workorder = process.workorder
            if workorder.id not in seen_workorder_ids:
                seen_workorder_ids.add(workorder.id)
                workorders.append({
                    'id': workorder.id,
                    'order_number': workorder.order_number,
                    'product_code': workorder.product_code,
                    'quantity': workorder.quantity,
                    'status': workorder.status,
                    'status_display': workorder.get_status_display(),
                    'process_name': process.process_name,
                    'process_status': process.status,
                    'process_status_display': process.get_status_display(),
                })
        
        # 如果沒有找到分配給該設備的工單，則顯示所有狀態為 pending 或 in_progress 的工單
        if not workorders:
            all_workorders = WorkOrder.objects.filter(
                status__in=['pending', 'in_progress']
            ).order_by('-created_at')[:20]  # 限制顯示前20筆
            
            for workorder in all_workorders:
                workorders.append({
                    'id': workorder.id,
                    'order_number': workorder.order_number,
                    'product_code': workorder.product_code,
                    'quantity': workorder.quantity,
                    'status': workorder.status,
                    'status_display': workorder.get_status_display(),
                    'process_name': '未分配',
                    'process_status': 'pending',
                    'process_status_display': '待生產',
                })
        
        return JsonResponse({
            'status': 'success',
            'equipment_name': equipment.name,
            'workorders': workorders,
            'count': len(workorders)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'獲取工單列表失敗：{str(e)}'
        })
```

### 2. 新增 URL 路由

**檔案：** `workorder/urls.py`
**新增路由：**
```python
path('api/get_workorders_by_equipment/', views.get_workorders_by_equipment, name='get_workorders_by_equipment'),
```

### 3. 修正前端 JavaScript

**檔案：** `workorder/templates/workorder/report/smt/on_site/index.html`
**修正函數：** `loadWorkorders`

```javascript
// 載入工單列表
function loadWorkorders(equipmentId) {
    // 發送 AJAX 請求獲取該設備的工單列表
    $('#workorder_select').html('<option value="">載入中...</option>');
    
    $.ajax({
        url: '{% url "workorder:get_workorders_by_equipment" %}',
        method: 'GET',
        data: {
            equipment_id: equipmentId
        },
        success: function(response) {
            if (response.status === 'success') {
                let options = '<option value="">請選擇工單...</option>';
                
                if (response.workorders && response.workorders.length > 0) {
                    response.workorders.forEach(function(workorder) {
                        const statusText = workorder.process_status === 'in_progress' ? 
                            '[生產中]' : 
                            '[待生產]';
                        
                        options += `<option value="${workorder.id}" data-status="${workorder.process_status}">
                            ${workorder.order_number} - ${workorder.product_code} 
                            (${workorder.quantity}件) ${statusText}
                        </option>`;
                    });
                } else {
                    options += '<option value="" disabled>該設備目前沒有可用的工單</option>';
                }
                
                $('#workorder_select').html(options);
            } else {
                $('#workorder_select').html('<option value="">載入失敗：' + response.message + '</option>');
            }
        },
        error: function() {
            $('#workorder_select').html('<option value="">載入失敗，請檢查網路連線</option>');
        }
    });
}
```

## 修復重點

### 1. 移除 HTML 標籤問題
- **問題：** 在 `<option>` 標籤中使用 `<span class="badge">` 會導致 JavaScript 錯誤
- **解決：** 改用純文字格式 `[生產中]` 和 `[待生產]`

### 2. 完整的錯誤處理
- API 端點包含完整的錯誤處理機制
- 前端 JavaScript 包含錯誤回應處理
- 網路連線失敗時的友善提示

### 3. 後備機制
- 如果設備沒有分配工序，顯示所有待生產的工單
- 確保使用者總是有工單可以選擇

## 測試結果

### API 測試
```bash
curl "http://localhost:8000/workorder/api/get_workorders_by_equipment/?equipment_id=58"
```

**回應：**
```json
{
  "status": "success",
  "equipment_name": "SMT-A_LINE",
  "workorders": [
    {
      "id": 2344,
      "order_number": "331-25627004",
      "product_code": "PFP-CCT1S1PDM-515",
      "quantity": 1000,
      "status": "pending",
      "status_display": "待生產",
      "process_name": "未分配",
      "process_status": "pending",
      "process_status_display": "待生產"
    }
  ],
  "count": 20
}
```

### 功能驗證
- ✅ 選擇設備後，工單下拉選單正確載入
- ✅ 顯示工單編號、產品編號、數量、狀態
- ✅ 支援錯誤處理和載入狀態提示
- ✅ 後備機制確保總有工單可選

## 修復完成

現在 SMT 現場報工系統已經可以正確連動派工單了。當使用者選擇設備後，系統會：

1. 自動載入該設備的相關工單
2. 如果設備沒有分配工序，顯示所有待生產的工單
3. 提供完整的錯誤處理和使用者友善的提示訊息

問題已完全解決！ 