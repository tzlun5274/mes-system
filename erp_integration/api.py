"""
ERP 整合模組 API
提供 ERP 整合相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import CompanyConfig, ERPConfig, ERPIntegrationOperationLog

# 設定日誌
logger = logging.getLogger(__name__)

class CompanyConfigAPIView(View):
    """
    公司配置 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, company_id=None):
        """
        獲取公司配置資訊
        GET /api/erp/company-config/ - 獲取所有公司配置
        GET /api/erp/company-config/{id}/ - 獲取單一公司配置
        """
        try:
            if company_id:
                try:
                    company = CompanyConfig.objects.get(id=company_id)
                    data = {
                        'id': company.id,
                        'company_code': company.company_code,
                        'company_name': company.company_name,
                        'database': company.database,
                        'is_active': company.is_active,
                        'created_at': company.created_at.isoformat(),
                        'updated_at': company.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '公司配置資訊獲取成功'
                    })
                except CompanyConfig.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '公司配置不存在'
                    }, status=404)
            else:
                companies = CompanyConfig.objects.all()
                data = []
                for company in companies:
                    data.append({
                        'id': company.id,
                        'company_code': company.company_code,
                        'company_name': company.company_name,
                        'database': company.database,
                        'is_active': company.is_active,
                        'created_at': company.created_at.isoformat(),
                        'updated_at': company.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '公司配置列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取公司配置資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取公司配置資訊失敗: {str(e)}'
            }, status=500)


class ERPConfigAPIView(View):
    """
    ERP 配置 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, config_id=None):
        """
        獲取 ERP 配置資訊
        GET /api/erp/erp-config/ - 獲取所有 ERP 配置
        GET /api/erp/erp-config/{id}/ - 獲取單一 ERP 配置
        """
        try:
            if config_id:
                try:
                    config = ERPConfig.objects.get(id=config_id)
                    data = {
                        'id': config.id,
                        'config_name': config.config_name,
                        'server_host': config.server_host,
                        'server_port': config.server_port,
                        'database_name': config.database_name,
                        'username': config.username,
                        'is_active': config.is_active,
                        'created_at': config.created_at.isoformat(),
                        'updated_at': config.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': 'ERP 配置資訊獲取成功'
                    })
                except ERPConfig.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'ERP 配置不存在'
                    }, status=404)
            else:
                configs = ERPConfig.objects.all()
                data = []
                for config in configs:
                    data.append({
                        'id': config.id,
                        'config_name': config.config_name,
                        'server_host': config.server_host,
                        'server_port': config.server_port,
                        'database_name': config.database_name,
                        'username': config.username,
                        'is_active': config.is_active,
                        'created_at': config.created_at.isoformat(),
                        'updated_at': config.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': 'ERP 配置列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取 ERP 配置資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取 ERP 配置資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_company_by_code(request):
    """
    根據公司代號獲取公司資訊
    GET /api/erp/company-by-code/?company_code=xxx
    """
    try:
        company_code = request.GET.get('company_code')
        
        if not company_code:
            return JsonResponse({
                'success': False,
                'message': '請提供 company_code 參數'
            }, status=400)
        
        try:
            company = CompanyConfig.objects.get(company_code=company_code)
            data = {
                'id': company.id,
                'company_code': company.company_code,
                'company_name': company.company_name,
                'database': company.database,
                'is_active': company.is_active,
                'created_at': company.created_at.isoformat(),
                'updated_at': company.updated_at.isoformat(),
            }
            
            return JsonResponse({
                'success': True,
                'data': data,
                'message': '公司資訊獲取成功'
            })
            
        except CompanyConfig.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'公司代號 "{company_code}" 不存在'
            }, status=404)
        
    except Exception as e:
        logger.error(f"根據公司代號獲取公司資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據公司代號獲取公司資訊失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_erp_operation_logs(request):
    """
    獲取 ERP 整合操作日誌
    GET /api/erp/operation-logs/?limit=50
    """
    try:
        limit = int(request.GET.get('limit', 50))
        
        logs = ERPIntegrationOperationLog.objects.all().order_by('-created_at')[:limit]
        
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'operation_type': log.operation_type,
                'table_name': log.table_name,
                'company_code': log.company_code,
                'status': log.status,
                'message': log.message,
                'created_at': log.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': 'ERP 整合操作日誌獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取 ERP 整合操作日誌失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取 ERP 整合操作日誌失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_active_companies(request):
    """
    獲取所有啟用的公司
    GET /api/erp/active-companies/
    """
    try:
        companies = CompanyConfig.objects.filter(is_active=True)
        
        data = []
        for company in companies:
            data.append({
                'id': company.id,
                'company_code': company.company_code,
                'company_name': company.company_name,
                'database': company.database,
                'created_at': company.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '啟用公司列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取啟用公司列表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取啟用公司列表失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_active_erp_configs(request):
    """
    獲取所有啟用的 ERP 配置
    GET /api/erp/active-erp-configs/
    """
    try:
        configs = ERPConfig.objects.filter(is_active=True)
        
        data = []
        for config in configs:
            data.append({
                'id': config.id,
                'config_name': config.config_name,
                'server_host': config.server_host,
                'server_port': config.server_port,
                'database_name': config.database_name,
                'username': config.username,
                'created_at': config.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '啟用 ERP 配置列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取啟用 ERP 配置列表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取啟用 ERP 配置列表失敗: {str(e)}'
        }, status=500)
