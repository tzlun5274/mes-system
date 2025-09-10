"""
排程管理模組 API
提供排程相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .scheduling_models import Event, Unit, ScheduleWarning

# 設定日誌
logger = logging.getLogger(__name__)

class EventAPIView(View):
    """
    事件 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, event_id=None):
        """
        獲取事件資訊
        GET /api/scheduling/event/ - 獲取所有事件
        GET /api/scheduling/event/{id}/ - 獲取單一事件
        """
        try:
            if event_id:
                try:
                    event = Event.objects.get(id=event_id)
                    data = {
                        'id': event.id,
                        'title': event.title,
                        'start': event.start.isoformat() if event.start else None,
                        'end': event.end.isoformat() if event.end else None,
                        'all_day': event.all_day,
                        'color': event.color,
                        'description': event.description,
                        'created_at': event.created_at.isoformat(),
                        'updated_at': event.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '事件資訊獲取成功'
                    })
                except Event.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '事件不存在'
                    }, status=404)
            else:
                events = Event.objects.all()
                data = []
                for event in events:
                    data.append({
                        'id': event.id,
                        'title': event.title,
                        'start': event.start.isoformat() if event.start else None,
                        'end': event.end.isoformat() if event.end else None,
                        'all_day': event.all_day,
                        'color': event.color,
                        'description': event.description,
                        'created_at': event.created_at.isoformat(),
                        'updated_at': event.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '事件列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取事件資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取事件資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_units(request):
    """
    獲取單位資訊
    GET /api/scheduling/units/
    """
    try:
        units = Unit.objects.all()
        
        data = []
        for unit in units:
            data.append({
                'id': unit.id,
                'unit_name': unit.unit_name,
                'unit_type': unit.unit_type,
                'description': unit.description,
                'created_at': unit.created_at.isoformat(),
                'updated_at': unit.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '單位列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取單位列表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取單位列表失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_schedule_warnings(request):
    """
    獲取排程警告
    GET /api/scheduling/warnings/
    """
    try:
        warnings = ScheduleWarning.objects.all()
        
        data = []
        for warning in warnings:
            data.append({
                'id': warning.id,
                'warning_type': warning.warning_type,
                'message': warning.message,
                'severity': warning.severity,
                'created_at': warning.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '排程警告列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取排程警告失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取排程警告失敗: {str(e)}'
        }, status=500)
