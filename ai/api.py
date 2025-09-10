"""
AI 模組 API
提供 AI 相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import AIPrediction, AIAnomaly, AIOptimization

# 設定日誌
logger = logging.getLogger(__name__)

class PredictionAPIView(View):
    """
    預測 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, prediction_id=None):
        """
        獲取預測資訊
        GET /api/ai/prediction/ - 獲取所有預測
        GET /api/ai/prediction/{id}/ - 獲取單一預測
        """
        try:
            if prediction_id:
                try:
                    prediction = AIPrediction.objects.get(id=prediction_id)
                    data = {
                        'id': prediction.id,
                        'prediction_type': prediction.prediction_type,
                        'model_name': prediction.model_name,
                        'input_data': prediction.input_data,
                        'prediction_result': prediction.prediction_result,
                        'confidence': float(prediction.confidence) if prediction.confidence else None,
                        'created_at': prediction.created_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '預測資訊獲取成功'
                    })
                except AIPrediction.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '預測不存在'
                    }, status=404)
            else:
                predictions = AIPrediction.objects.all()
                data = []
                for prediction in predictions:
                    data.append({
                        'id': prediction.id,
                        'prediction_type': prediction.prediction_type,
                        'model_name': prediction.model_name,
                        'input_data': prediction.input_data,
                        'prediction_result': prediction.prediction_result,
                        'confidence': float(prediction.confidence) if prediction.confidence else None,
                        'created_at': prediction.created_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '預測列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取預測資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取預測資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_anomalies(request):
    """
    獲取異常檢測結果
    GET /api/ai/anomalies/?limit=50
    """
    try:
        limit = int(request.GET.get('limit', 50))
        
        anomalies = AIAnomaly.objects.all().order_by('-created_at')[:limit]
        
        data = []
        for anomaly in anomalies:
            data.append({
                'id': anomaly.id,
                'anomaly_type': anomaly.anomaly_type,
                'detected_data': anomaly.detected_data,
                'anomaly_score': float(anomaly.anomaly_score) if anomaly.anomaly_score else None,
                'status': anomaly.status,
                'created_at': anomaly.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '異常檢測結果獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取異常檢測結果失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取異常檢測結果失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_optimizations(request):
    """
    獲取優化建議
    GET /api/ai/optimizations/?limit=50
    """
    try:
        limit = int(request.GET.get('limit', 50))
        
        optimizations = AIOptimization.objects.all().order_by('-created_at')[:limit]
        
        data = []
        for optimization in optimizations:
            data.append({
                'id': optimization.id,
                'optimization_type': optimization.optimization_type,
                'target_area': optimization.target_area,
                'current_value': optimization.current_value,
                'optimized_value': optimization.optimized_value,
                'improvement_percentage': float(optimization.improvement_percentage) if optimization.improvement_percentage else None,
                'status': optimization.status,
                'created_at': optimization.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '優化建議獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取優化建議失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取優化建議失敗: {str(e)}'
        }, status=500)
