"""
生產管理模組 API
提供生產相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import ProductionLine, ProductionLineType, ProductionLineSchedule, ProductionExecution, ProductionMonitor

# 設定日誌
logger = logging.getLogger(__name__)

class ProductionLineAPIView(View):
    """
    產線 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, line_id=None):
        """
        獲取產線資訊
        GET /api/production/production-line/ - 獲取所有產線
        GET /api/production/production-line/{id}/ - 獲取單一產線
        """
        try:
            if line_id:
                try:
                    line = ProductionLine.objects.get(id=line_id)
                    data = {
                        'id': line.id,
                        'line_name': line.line_name,
                        'line_code': line.line_code,
                        'description': line.description,
                        'capacity': line.capacity,
                        'is_active': line.is_active,
                        'created_at': line.created_at.isoformat(),
                        'updated_at': line.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '產線資訊獲取成功'
                    })
                except ProductionLine.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '產線不存在'
                    }, status=404)
            else:
                lines = ProductionLine.objects.all()
                data = []
                for line in lines:
                    data.append({
                        'id': line.id,
                        'line_name': line.line_name,
                        'line_code': line.line_code,
                        'description': line.description,
                        'capacity': line.capacity,
                        'is_active': line.is_active,
                        'created_at': line.created_at.isoformat(),
                        'updated_at': line.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '產線列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取產線資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取產線資訊失敗: {str(e)}'
            }, status=500)


class ProductionExecutionAPIView(View):
    """
    生產執行 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, execution_id=None):
        """
        獲取生產執行資訊
        GET /api/production/execution/ - 獲取所有生產執行
        GET /api/production/execution/{id}/ - 獲取單一生產執行
        """
        try:
            if execution_id:
                try:
                    execution = ProductionExecution.objects.get(id=execution_id)
                    data = {
                        'id': execution.id,
                        'workorder_id': execution.workorder_id,
                        'product_id': execution.product_id,
                        'production_line_id': execution.production_line_id,
                        'production_line_name': execution.production_line_name,
                        'start_time': execution.start_time.isoformat() if execution.start_time else None,
                        'end_time': execution.end_time.isoformat() if execution.end_time else None,
                        'planned_quantity': execution.planned_quantity,
                        'actual_quantity': execution.actual_quantity,
                        'status': execution.status,
                        'operator': execution.operator,
                        'created_at': execution.created_at.isoformat(),
                        'updated_at': execution.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '生產執行資訊獲取成功'
                    })
                except ProductionExecution.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '生產執行不存在'
                    }, status=404)
            else:
                executions = ProductionExecution.objects.all()
                data = []
                for execution in executions:
                    data.append({
                        'id': execution.id,
                        'workorder_id': execution.workorder_id,
                        'product_id': execution.product_id,
                        'production_line_id': execution.production_line_id,
                        'production_line_name': execution.production_line_name,
                        'start_time': execution.start_time.isoformat() if execution.start_time else None,
                        'end_time': execution.end_time.isoformat() if execution.end_time else None,
                        'planned_quantity': execution.planned_quantity,
                        'actual_quantity': execution.actual_quantity,
                        'status': execution.status,
                        'operator': execution.operator,
                        'created_at': execution.created_at.isoformat(),
                        'updated_at': execution.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '生產執行列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取生產執行資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取生產執行資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_production_line_by_code(request):
    """
    根據產線代號獲取產線資訊
    GET /api/production/production-line-by-code/?line_code=xxx
    """
    try:
        line_code = request.GET.get('line_code')
        
        if not line_code:
            return JsonResponse({
                'success': False,
                'message': '請提供 line_code 參數'
            }, status=400)
        
        try:
            line = ProductionLine.objects.get(line_code=line_code)
            data = {
                'id': line.id,
                'line_name': line.line_name,
                'line_code': line.line_code,
                'description': line.description,
                'capacity': line.capacity,
                'is_active': line.is_active,
                'created_at': line.created_at.isoformat(),
            }
            
            return JsonResponse({
                'success': True,
                'data': data,
                'message': '產線資訊獲取成功'
            })
            
        except ProductionLine.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'產線代號 "{line_code}" 不存在'
            }, status=404)
        
    except Exception as e:
        logger.error(f"根據產線代號獲取產線資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據產線代號獲取產線資訊失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_active_production_lines(request):
    """
    獲取所有啟用的產線
    GET /api/production/active-production-lines/
    """
    try:
        lines = ProductionLine.objects.filter(is_active=True)
        
        data = []
        for line in lines:
            data.append({
                'id': line.id,
                'line_name': line.line_name,
                'line_code': line.line_code,
                'description': line.description,
                'capacity': line.capacity,
                'created_at': line.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '啟用產線列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取啟用產線列表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取啟用產線列表失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_production_executions_by_workorder(request):
    """
    根據工單獲取生產執行記錄
    GET /api/production/executions-by-workorder/?workorder_id=xxx
    """
    try:
        workorder_id = request.GET.get('workorder_id')
        
        if not workorder_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 workorder_id 參數'
            }, status=400)
        
        executions = ProductionExecution.objects.filter(workorder_id=workorder_id)
        
        data = []
        for execution in executions:
            data.append({
                'id': execution.id,
                'workorder_id': execution.workorder_id,
                'product_id': execution.product_id,
                'production_line_id': execution.production_line_id,
                'production_line_name': execution.production_line_name,
                'start_time': execution.start_time.isoformat() if execution.start_time else None,
                'end_time': execution.end_time.isoformat() if execution.end_time else None,
                'planned_quantity': execution.planned_quantity,
                'actual_quantity': execution.actual_quantity,
                'status': execution.status,
                'operator': execution.operator,
                'created_at': execution.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '工單生產執行記錄獲取成功'
        })
        
    except Exception as e:
        logger.error(f"根據工單獲取生產執行記錄失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據工單獲取生產執行記錄失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_production_monitor_data(request):
    """
    獲取生產監控資料
    GET /api/production/monitor-data/?production_line_id=xxx
    """
    try:
        production_line_id = request.GET.get('production_line_id')
        
        if not production_line_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 production_line_id 參數'
            }, status=400)
        
        monitor_data = ProductionMonitor.objects.filter(production_line_id=production_line_id)
        
        data = []
        for monitor in monitor_data:
            data.append({
                'id': monitor.id,
                'production_line_id': monitor.production_line_id,
                'production_line_name': monitor.production_line_name,
                'monitor_time': monitor.monitor_time.isoformat(),
                'status': monitor.status,
                'efficiency': float(monitor.efficiency) if monitor.efficiency else None,
                'quality_rate': float(monitor.quality_rate) if monitor.quality_rate else None,
                'created_at': monitor.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '生產監控資料獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取生產監控資料失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取生產監控資料失敗: {str(e)}'
        }, status=500)
