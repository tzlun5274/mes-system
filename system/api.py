"""
系統管理模組 API
提供系統相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import ScheduledTask, UserPermissionDetail, AutoApprovalTask, CleanupLog, EmailConfig, OperationLogConfig, OrderSyncLog, OrderSyncSettings, UserWorkPermission

# 設定日誌
logger = logging.getLogger(__name__)

class ScheduledTaskAPIView(View):
    """
    排程任務 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, task_id=None):
        """
        獲取排程任務資訊
        GET /api/system/scheduled-task/ - 獲取所有任務
        GET /api/system/scheduled-task/{id}/ - 獲取單一任務
        """
        try:
            if task_id:
                try:
                    task = ScheduledTask.objects.get(id=task_id)
                    data = {
                        'id': task.id,
                        'name': task.name,
                        'task_type': task.task_type,
                        'task_function': task.task_function,
                        'execution_type': task.execution_type,
                        'interval_minutes': task.interval_minutes,
                        'fixed_time': task.fixed_time.isoformat() if task.fixed_time else None,
                        'is_enabled': task.is_enabled,
                        'last_execution_time': task.last_execution_time.isoformat() if task.last_execution_time else None,
                        'next_execution_time': task.next_execution_time.isoformat() if task.next_execution_time else None,
                        'execution_count': task.execution_count,
                        'success_count': task.success_count,
                        'failure_count': task.failure_count,
                        'last_error_message': task.last_error_message,
                        'created_at': task.created_at.isoformat(),
                        'updated_at': task.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '排程任務資訊獲取成功'
                    })
                except ScheduledTask.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '排程任務不存在'
                    }, status=404)
            else:
                tasks = ScheduledTask.objects.all()
                data = []
                for task in tasks:
                    data.append({
                        'id': task.id,
                        'name': task.name,
                        'task_type': task.task_type,
                        'task_function': task.task_function,
                        'execution_type': task.execution_type,
                        'interval_minutes': task.interval_minutes,
                        'fixed_time': task.fixed_time.isoformat() if task.fixed_time else None,
                        'is_enabled': task.is_enabled,
                        'last_execution_time': task.last_execution_time.isoformat() if task.last_execution_time else None,
                        'next_execution_time': task.next_execution_time.isoformat() if task.next_execution_time else None,
                        'execution_count': task.execution_count,
                        'success_count': task.success_count,
                        'failure_count': task.failure_count,
                        'last_error_message': task.last_error_message,
                        'created_at': task.created_at.isoformat(),
                        'updated_at': task.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '排程任務列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取排程任務資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取排程任務資訊失敗: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """
        創建排程任務
        POST /api/system/scheduled-task/
        """
        try:
            data = json.loads(request.body)
            
            # 驗證必填欄位
            required_fields = ['name', 'task_type', 'task_function', 'execution_type']
            for field in required_fields:
                if field not in data or not data[field]:
                    return JsonResponse({
                        'success': False,
                        'message': f'缺少必填欄位: {field}'
                    }, status=400)
            
            # 創建排程任務
            task = ScheduledTask.objects.create(
                name=data['name'],
                task_type=data['task_type'],
                task_function=data['task_function'],
                execution_type=data['execution_type'],
                interval_minutes=data.get('interval_minutes'),
                fixed_time=data.get('fixed_time'),
                is_enabled=data.get('is_enabled', True),
            )
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': task.id,
                    'name': task.name,
                    'task_type': task.task_type,
                    'task_function': task.task_function,
                    'execution_type': task.execution_type,
                    'is_enabled': task.is_enabled,
                    'created_at': task.created_at.isoformat(),
                },
                'message': '排程任務創建成功'
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'JSON 格式錯誤'
            }, status=400)
        except Exception as e:
            logger.error(f"創建排程任務失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'創建排程任務失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_user_permissions(request):
    """
    獲取用戶權限資訊
    GET /api/system/user-permissions/?user_id=xxx
    """
    try:
        user_id = request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 user_id 參數'
            }, status=400)
        
        permissions = UserPermissionDetail.objects.filter(user_id=user_id)
        
        data = []
        for permission in permissions:
            data.append({
                'id': permission.id,
                'user_id': permission.user_id,
                'module_name': permission.module_name,
                'permission_type': permission.permission_type,
                'is_granted': permission.is_granted,
                'created_at': permission.created_at.isoformat(),
                'updated_at': permission.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '用戶權限資訊獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取用戶權限資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取用戶權限資訊失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_auto_approval_tasks(request):
    """
    獲取自動核准任務
    GET /api/system/auto-approval-tasks/
    """
    try:
        tasks = AutoApprovalTask.objects.all()
        
        data = []
        for task in tasks:
            data.append({
                'id': task.id,
                'task_name': task.task_name,
                'task_type': task.task_type,
                'approval_condition': task.approval_condition,
                'is_enabled': task.is_enabled,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '自動核准任務獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取自動核准任務失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取自動核准任務失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_email_config(request):
    """
    獲取郵件配置
    GET /api/system/email-config/
    """
    try:
        configs = EmailConfig.objects.all()
        
        data = []
        for config in configs:
            data.append({
                'id': config.id,
                'config_name': config.config_name,
                'smtp_server': config.smtp_server,
                'smtp_port': config.smtp_port,
                'username': config.username,
                'use_tls': config.use_tls,
                'is_active': config.is_active,
                'created_at': config.created_at.isoformat(),
                'updated_at': config.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '郵件配置獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取郵件配置失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取郵件配置失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_operation_logs(request):
    """
    獲取操作日誌
    GET /api/system/operation-logs/?limit=50
    """
    try:
        limit = int(request.GET.get('limit', 50))
        
        logs = CleanupLog.objects.all().order_by('-created_at')[:limit]
        
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'log_type': log.log_type,
                'description': log.description,
                'status': log.status,
                'created_at': log.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '操作日誌獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取操作日誌失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取操作日誌失敗: {str(e)}'
        }, status=500)
