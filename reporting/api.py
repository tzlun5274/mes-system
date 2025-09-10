"""
報表模組 API
提供報表相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import WorkOrderReportData

# 設定日誌
logger = logging.getLogger(__name__)

class WorkOrderReportAPIView(View):
    """
    工單報表 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, report_id=None):
        """
        獲取工單報表資訊
        GET /api/reporting/workorder-report/ - 獲取所有工單報表
        GET /api/reporting/workorder-report/{id}/ - 獲取單一工單報表
        """
        try:
            if report_id:
                try:
                    report = WorkOrderReportData.objects.get(id=report_id)
                    data = {
                        'id': report.id,
                        'report_name': report.report_name,
                        'report_type': report.report_type,
                        'company_code': report.company_code,
                        'date_range_start': report.date_range_start.isoformat() if report.date_range_start else None,
                        'date_range_end': report.date_range_end.isoformat() if report.date_range_end else None,
                        'report_data': report.report_data,
                        'created_at': report.created_at.isoformat(),
                        'updated_at': report.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '工單報表資訊獲取成功'
                    })
                except WorkOrderReportData.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '工單報表不存在'
                    }, status=404)
            else:
                reports = WorkOrderReportData.objects.all()
                data = []
                for report in reports:
                    data.append({
                        'id': report.id,
                        'report_name': report.report_name,
                        'report_type': report.report_type,
                        'company_code': report.company_code,
                        'date_range_start': report.date_range_start.isoformat() if report.date_range_start else None,
                        'date_range_end': report.date_range_end.isoformat() if report.date_range_end else None,
                        'report_data': report.report_data,
                        'created_at': report.created_at.isoformat(),
                        'updated_at': report.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '工單報表列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取工單報表資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取工單報表資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_production_reports(request):
    """
    獲取生產報表
    GET /api/reporting/production-reports/?company_code=xxx
    """
    try:
        company_code = request.GET.get('company_code')
        
        if not company_code:
            return JsonResponse({
                'success': False,
                'message': '請提供 company_code 參數'
            }, status=400)
        
        # 暫時返回空數據，因為 ProductionReportData 模型不存在
        data = []
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '生產報表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取生產報表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取生產報表失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_quality_reports(request):
    """
    獲取品質報表
    GET /api/reporting/quality-reports/?company_code=xxx
    """
    try:
        company_code = request.GET.get('company_code')
        
        if not company_code:
            return JsonResponse({
                'success': False,
                'message': '請提供 company_code 參數'
            }, status=400)
        
        # 暫時返回空數據，因為 QualityReportData 模型不存在
        data = []
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '品質報表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取品質報表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取品質報表失敗: {str(e)}'
        }, status=500)
