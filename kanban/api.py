"""
看板管理模組 API
提供看板相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import KanbanBoard, KanbanItem, KanbanProductionProgress, KanbanEquipmentStatus, KanbanQualityMonitoring, KanbanMaterialStock, KanbanDeliverySchedule, KanbanOperationLog

# 設定日誌
logger = logging.getLogger(__name__)

class KanbanBoardAPIView(View):
    """
    看板 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, board_id=None):
        """
        獲取看板資訊
        GET /api/kanban/board/ - 獲取所有看板
        GET /api/kanban/board/{id}/ - 獲取單一看板
        """
        try:
            if board_id:
                try:
                    board = KanbanBoard.objects.get(id=board_id)
                    data = {
                        'id': board.id,
                        'board_name': board.board_name,
                        'board_type': board.board_type,
                        'description': board.description,
                        'is_active': board.is_active,
                        'created_at': board.created_at.isoformat(),
                        'updated_at': board.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '看板資訊獲取成功'
                    })
                except KanbanBoard.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '看板不存在'
                    }, status=404)
            else:
                boards = KanbanBoard.objects.all()
                data = []
                for board in boards:
                    data.append({
                        'id': board.id,
                        'board_name': board.board_name,
                        'board_type': board.board_type,
                        'description': board.description,
                        'is_active': board.is_active,
                        'created_at': board.created_at.isoformat(),
                        'updated_at': board.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '看板列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取看板資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取看板資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_kanban_items(request):
    """
    獲取看板項目
    GET /api/kanban/items/?board_id=xxx
    """
    try:
        board_id = request.GET.get('board_id')
        
        if not board_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 board_id 參數'
            }, status=400)
        
        items = KanbanItem.objects.filter(board_id=board_id)
        
        data = []
        for item in items:
            data.append({
                'id': item.id,
                'board_id': item.board_id,
                'item_name': item.item_name,
                'item_type': item.item_type,
                'status': item.status,
                'priority': item.priority,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '看板項目獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取看板項目失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取看板項目失敗: {str(e)}'
        }, status=500)
