"""
品質管理模組 API
提供品質相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import InspectionRecord, DefectiveProduct, FinalInspectionReport

# 設定日誌
logger = logging.getLogger(__name__)

class InspectionAPIView(View):
    """
    檢驗 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, inspection_id=None):
        """
        獲取檢驗資訊
        GET /api/quality/inspection/ - 獲取所有檢驗
        GET /api/quality/inspection/{id}/ - 獲取單一檢驗
        """
        try:
            if inspection_id:
                try:
                    inspection = InspectionRecord.objects.get(id=inspection_id)
                    data = {
                        'id': inspection.id,
                        'inspection_name': inspection.inspection_name,
                        'inspection_type': inspection.inspection_type,
                        'product_id': inspection.product_id,
                        'workorder_id': inspection.workorder_id,
                        'inspector': inspection.inspector,
                        'inspection_date': inspection.inspection_date.isoformat() if inspection.inspection_date else None,
                        'result': inspection.result,
                        'created_at': inspection.created_at.isoformat(),
                        'updated_at': inspection.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '檢驗資訊獲取成功'
                    })
                except InspectionRecord.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '檢驗不存在'
                    }, status=404)
            else:
                inspections = InspectionRecord.objects.all()
                data = []
                for inspection in inspections:
                    data.append({
                        'id': inspection.id,
                        'inspection_name': inspection.inspection_name,
                        'inspection_type': inspection.inspection_type,
                        'product_id': inspection.product_id,
                        'workorder_id': inspection.workorder_id,
                        'inspector': inspection.inspector,
                        'inspection_date': inspection.inspection_date.isoformat() if inspection.inspection_date else None,
                        'result': inspection.result,
                        'created_at': inspection.created_at.isoformat(),
                        'updated_at': inspection.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '檢驗列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取檢驗資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取檢驗資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_defects(request):
    """
    獲取不良品資訊
    GET /api/quality/defects/?workorder_id=xxx
    """
    try:
        workorder_id = request.GET.get('workorder_id')
        
        if not workorder_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 workorder_id 參數'
            }, status=400)
        
        defects = DefectiveProduct.objects.filter(workorder_id=workorder_id)
        
        data = []
        for defect in defects:
            data.append({
                'id': defect.id,
                'defect_name': defect.defect_name,
                'defect_type': defect.defect_type,
                'workorder_id': defect.workorder_id,
                'product_id': defect.product_id,
                'quantity': defect.quantity,
                'defect_date': defect.defect_date.isoformat() if defect.defect_date else None,
                'created_at': defect.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '不良品資訊獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取不良品資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取不良品資訊失敗: {str(e)}'
        }, status=500)
