"""
工單管理模組 API
提供工單相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import WorkOrder, WorkOrderProcess, WorkOrderProcessLog, WorkOrderAssignment, WorkOrderProcessCapacity, WorkOrderProduction, WorkOrderProductionDetail, CompletedWorkOrder, CompletedWorkOrderProcess, CompletedProductionReport, AutoAllocationSettings, AutoAllocationLog

# 設定日誌
logger = logging.getLogger(__name__)

class WorkOrderAPIView(View):
    """
    工單 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, workorder_id=None):
        """
        獲取工單資訊
        GET /api/workorder/workorder/ - 獲取所有工單
        GET /api/workorder/workorder/{id}/ - 獲取單一工單
        """
        try:
            if workorder_id:
                try:
                    workorder = WorkOrder.objects.get(id=workorder_id)
                    data = {
                        'id': workorder.id,
                        'company_code': workorder.company_code,
                        'workorder_number': workorder.workorder_number,
                        'product_id': workorder.product_id,
                        'product_name': workorder.product_name,
                        'planned_quantity': workorder.planned_quantity,
                        'actual_quantity': workorder.actual_quantity,
                        'status': workorder.status,
                        'priority': workorder.priority,
                        'start_date': workorder.start_date.isoformat() if workorder.start_date else None,
                        'end_date': workorder.end_date.isoformat() if workorder.end_date else None,
                        'created_at': workorder.created_at.isoformat(),
                        'updated_at': workorder.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '工單資訊獲取成功'
                    })
                except WorkOrder.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '工單不存在'
                    }, status=404)
            else:
                workorders = WorkOrder.objects.all()
                data = []
                for workorder in workorders:
                    data.append({
                        'id': workorder.id,
                        'company_code': workorder.company_code,
                        'workorder_number': workorder.workorder_number,
                        'product_id': workorder.product_id,
                        'product_name': workorder.product_name,
                        'planned_quantity': workorder.planned_quantity,
                        'actual_quantity': workorder.actual_quantity,
                        'status': workorder.status,
                        'priority': workorder.priority,
                        'start_date': workorder.start_date.isoformat() if workorder.start_date else None,
                        'end_date': workorder.end_date.isoformat() if workorder.end_date else None,
                        'created_at': workorder.created_at.isoformat(),
                        'updated_at': workorder.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '工單列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取工單資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取工單資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_workorder_by_number(request):
    """
    根據工單號碼獲取工單資訊
    GET /api/workorder/workorder-by-number/?company_code=xxx&workorder_number=xxx
    """
    try:
        company_code = request.GET.get('company_code')
        workorder_number = request.GET.get('workorder_number')
        
        if not company_code or not workorder_number:
            return JsonResponse({
                'success': False,
                'message': '請提供 company_code 和 workorder_number 參數'
            }, status=400)
        
        try:
            workorder = WorkOrder.objects.get(
                company_code=company_code,
                workorder_number=workorder_number
            )
            data = {
                'id': workorder.id,
                'company_code': workorder.company_code,
                'workorder_number': workorder.workorder_number,
                'product_id': workorder.product_id,
                'product_name': workorder.product_name,
                'planned_quantity': workorder.planned_quantity,
                'actual_quantity': workorder.actual_quantity,
                'status': workorder.status,
                'priority': workorder.priority,
                'start_date': workorder.start_date.isoformat() if workorder.start_date else None,
                'end_date': workorder.end_date.isoformat() if workorder.end_date else None,
                'created_at': workorder.created_at.isoformat(),
            }
            
            return JsonResponse({
                'success': True,
                'data': data,
                'message': '工單資訊獲取成功'
            })
            
        except WorkOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'工單 "{company_code}-{workorder_number}" 不存在'
            }, status=404)
        
    except Exception as e:
        logger.error(f"根據工單號碼獲取工單資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據工單號碼獲取工單資訊失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_workorder_processes(request):
    """
    獲取工單工序
    GET /api/workorder/processes/?workorder_id=xxx
    """
    try:
        workorder_id = request.GET.get('workorder_id')
        
        if not workorder_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 workorder_id 參數'
            }, status=400)
        
        processes = WorkOrderProcess.objects.filter(workorder_id=workorder_id).order_by('step_order')
        
        data = []
        for process in processes:
            data.append({
                'id': process.id,
                'workorder_id': process.workorder_id,
                'process_name': process.process_name,
                'step_order': process.step_order,
                'assigned_equipment': process.assigned_equipment,
                'assigned_operator': process.assigned_operator,
                'status': process.status,
                'start_time': process.start_time.isoformat() if process.start_time else None,
                'end_time': process.end_time.isoformat() if process.end_time else None,
                'created_at': process.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '工單工序獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取工單工序失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取工單工序失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_workorders_by_status(request):
    """
    根據狀態獲取工單列表
    GET /api/workorder/workorders-by-status/?status=xxx
    """
    try:
        status = request.GET.get('status')
        
        if not status:
            return JsonResponse({
                'success': False,
                'message': '請提供 status 參數'
            }, status=400)
        
        workorders = WorkOrder.objects.filter(status=status)
        
        data = []
        for workorder in workorders:
            data.append({
                'id': workorder.id,
                'company_code': workorder.company_code,
                'workorder_number': workorder.workorder_number,
                'product_id': workorder.product_id,
                'product_name': workorder.product_name,
                'planned_quantity': workorder.planned_quantity,
                'actual_quantity': workorder.actual_quantity,
                'status': workorder.status,
                'priority': workorder.priority,
                'start_date': workorder.start_date.isoformat() if workorder.start_date else None,
                'end_date': workorder.end_date.isoformat() if workorder.end_date else None,
                'created_at': workorder.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': f'狀態為 "{status}" 的工單列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"根據狀態獲取工單列表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據狀態獲取工單列表失敗: {str(e)}'
        }, status=500)
