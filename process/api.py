"""
製程管理模組 API
提供製程相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import ProcessName, OperatorSkill, ProductProcessRoute, ProcessOperationLog

# 設定日誌
logger = logging.getLogger(__name__)

class ProcessNameAPIView(View):
    """
    工序名稱 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, process_id=None):
        """
        獲取工序資訊
        GET /api/process/process-name/ - 獲取所有工序
        GET /api/process/process-name/{id}/ - 獲取單一工序
        """
        try:
            if process_id:
                try:
                    process = ProcessName.objects.get(id=process_id)
                    data = {
                        'id': process.id,
                        'name': process.name,
                        'description': process.description,
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '工序資訊獲取成功'
                    })
                except ProcessName.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '工序不存在'
                    }, status=404)
            else:
                processes = ProcessName.objects.all()
                data = []
                for process in processes:
                    data.append({
                        'id': process.id,
                        'name': process.name,
                        'description': process.description,
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '工序列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取工序資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取工序資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_operator_skills(request):
    """
    獲取作業員技能
    GET /api/process/operator-skills/?operator_id=xxx
    """
    try:
        operator_id = request.GET.get('operator_id')
        
        if not operator_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 operator_id 參數'
            }, status=400)
        
        skills = OperatorSkill.objects.filter(operator_id=operator_id)
        
        data = []
        for skill in skills:
            data.append({
                'id': skill.id,
                'operator_id': skill.operator_id,
                'operator_name': skill.operator_name,
                'process_name_id': skill.process_name_id,
                'process_name': skill.process_name,
                'priority': skill.priority,
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '作業員技能獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取作業員技能失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取作業員技能失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_product_process_route(request):
    """
    獲取產品工序路線
    GET /api/process/product-route/?product_id=xxx
    """
    try:
        product_id = request.GET.get('product_id')
        
        if not product_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 product_id 參數'
            }, status=400)
        
        routes = ProductProcessRoute.objects.filter(product_id=product_id).order_by('step_order')
        
        data = []
        for route in routes:
            data.append({
                'id': route.id,
                'product_id': route.product_id,
                'process_name_id': route.process_name_id,
                'process_name': route.process_name,
                'step_order': route.step_order,
                'usable_equipment_ids': route.usable_equipment_ids,
                'dependent_semi_product': route.dependent_semi_product,
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '產品工序路線獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取產品工序路線失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取產品工序路線失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_process_operation_logs(request):
    """
    獲取工序操作日誌
    GET /api/process/operation-logs/?limit=50
    """
    try:
        limit = int(request.GET.get('limit', 50))
        
        logs = ProcessOperationLog.objects.all().order_by('-timestamp')[:limit]
        
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'action': log.action,
                'user': log.user,
                'timestamp': log.timestamp.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '工序操作日誌獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取工序操作日誌失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取工序操作日誌失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_process_by_name(request):
    """
    根據工序名稱獲取工序資訊
    GET /api/process/process-by-name/?name=xxx
    """
    try:
        name = request.GET.get('name')
        
        if not name:
            return JsonResponse({
                'success': False,
                'message': '請提供 name 參數'
            }, status=400)
        
        try:
            process = ProcessName.objects.get(name=name)
            data = {
                'id': process.id,
                'name': process.name,
                'description': process.description,
            }
            
            return JsonResponse({
                'success': True,
                'data': data,
                'message': '工序資訊獲取成功'
            })
            
        except ProcessName.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'工序名稱 "{name}" 不存在'
            }, status=404)
        
    except Exception as e:
        logger.error(f"根據工序名稱獲取工序資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據工序名稱獲取工序資訊失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_active_processes(request):
    """
    獲取所有啟用的工序
    GET /api/process/active-processes/
    """
    try:
        processes = ProcessName.objects.all()
        
        data = []
        for process in processes:
            data.append({
                'id': process.id,
                'name': process.name,
                'description': process.description,
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '啟用工序列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取啟用工序列表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取啟用工序列表失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_skilled_operators(request):
    """
    獲取具備特定工序技能的作業員
    GET /api/process/skilled-operators/?process_name_id=xxx
    """
    try:
        process_name_id = request.GET.get('process_name_id')
        
        if not process_name_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 process_name_id 參數'
            }, status=400)
        
        skills = OperatorSkill.objects.filter(process_name_id=process_name_id).order_by('priority')
        
        data = []
        for skill in skills:
            data.append({
                'id': skill.id,
                'operator_id': skill.operator_id,
                'operator_name': skill.operator_name,
                'process_name_id': skill.process_name_id,
                'process_name': skill.process_name,
                'priority': skill.priority,
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '具備技能作業員列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取具備技能作業員列表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取具備技能作業員列表失敗: {str(e)}'
        }, status=500)
