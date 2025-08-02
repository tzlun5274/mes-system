"""
工單工序 API 視圖
處理工序相關的 AJAX 請求
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from workorder.models import WorkOrderProcess


@require_http_methods(["GET"])
@login_required
def get_process_detail(request, process_id):
    """
    獲取工序詳細資料
    GET /workorder/api/process/{process_id}/
    """
    try:
        process = get_object_or_404(WorkOrderProcess, id=process_id)
        
        data = {
            'id': process.id,
            'process_name': process.process_name,
            'step_order': process.step_order,
            'planned_quantity': process.planned_quantity,
            'completed_quantity': process.completed_quantity,
            'status': process.status,
            'assigned_operator': process.assigned_operator or '',
            'assigned_equipment': process.assigned_equipment or '',
            'actual_start_time': process.actual_start_time.isoformat() if process.actual_start_time else None,
            'actual_end_time': process.actual_end_time.isoformat() if process.actual_end_time else None,
        }
        
        return JsonResponse({
            'status': 'success',
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'獲取工序資料失敗：{str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@login_required
def edit_process(request, process_id):
    """
    編輯工序資料
    POST /workorder/api/process/{process_id}/edit/
    """
    try:
        process = get_object_or_404(WorkOrderProcess, id=process_id)
        
        # 獲取表單資料
        process_name = request.POST.get('process_name')
        step_order = request.POST.get('step_order')
        planned_quantity = request.POST.get('planned_quantity')
        status = request.POST.get('status')
        assigned_operator = request.POST.get('assigned_operator')
        assigned_equipment = request.POST.get('assigned_equipment')
        
        # 更新工序資料
        if process_name:
            process.process_name = process_name
        if step_order:
            process.step_order = int(step_order)
        if planned_quantity:
            process.planned_quantity = int(planned_quantity)
        if status:
            process.status = status
        if assigned_operator is not None:
            process.assigned_operator = assigned_operator
        if assigned_equipment is not None:
            process.assigned_equipment = assigned_equipment
        
        process.save()
        
        return JsonResponse({
            'status': 'success',
            'message': '工序更新成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'更新工序失敗：{str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@login_required
def delete_process(request, process_id):
    """
    刪除工序
    POST /workorder/api/process/{process_id}/delete/
    """
    try:
        process = get_object_or_404(WorkOrderProcess, id=process_id)
        workorder_id = process.workorder.id
        process.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': '工序刪除成功'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'刪除工序失敗：{str(e)}'
        }, status=500) 