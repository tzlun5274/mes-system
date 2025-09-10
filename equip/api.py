"""
設備管理模組 API
提供設備相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import Equipment, EquipOperationLog

# 設定日誌
logger = logging.getLogger(__name__)

class EquipmentAPIView(View):
    """
    設備 API 視圖類
    提供設備的 CRUD 操作
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, equipment_id=None):
        """
        獲取設備資訊
        GET /api/equip/equipment/ - 獲取所有設備
        GET /api/equip/equipment/{id}/ - 獲取單一設備
        """
        try:
            if equipment_id:
                # 獲取單一設備
                try:
                    equipment = Equipment.objects.get(id=equipment_id)
                    data = {
                        'id': equipment.id,
                        'name': equipment.name,
                        'model': equipment.model,
                        'status': equipment.status,
                        'status_display': equipment.get_status_display(),
                        'production_line_id': equipment.production_line_id,
                        'production_line_name': equipment.production_line_name,
                        'created_at': equipment.created_at.isoformat(),
                        'updated_at': equipment.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '設備資訊獲取成功'
                    })
                except Equipment.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '設備不存在'
                    }, status=404)
            else:
                # 獲取所有設備
                equipments = Equipment.objects.all()
                data = []
                for equipment in equipments:
                    data.append({
                        'id': equipment.id,
                        'name': equipment.name,
                        'model': equipment.model,
                        'status': equipment.status,
                        'status_display': equipment.get_status_display(),
                        'production_line_id': equipment.production_line_id,
                        'production_line_name': equipment.production_line_name,
                        'created_at': equipment.created_at.isoformat(),
                        'updated_at': equipment.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '設備列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取設備資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取設備資訊失敗: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """
        創建設備
        POST /api/equip/equipment/
        """
        try:
            data = json.loads(request.body)
            
            # 驗證必填欄位
            required_fields = ['name']
            for field in required_fields:
                if field not in data or not data[field]:
                    return JsonResponse({
                        'success': False,
                        'message': f'缺少必填欄位: {field}'
                    }, status=400)
            
            # 檢查設備名稱是否已存在
            if Equipment.objects.filter(name=data['name']).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'設備名稱 "{data["name"]}" 已存在'
                }, status=400)
            
            # 創建設備
            equipment = Equipment.objects.create(
                name=data['name'],
                model=data.get('model', ''),
                status=data.get('status', 'idle'),
                production_line_id=data.get('production_line_id'),
                production_line_name=data.get('production_line_name'),
            )
            
            # 記錄操作日誌
            EquipOperationLog.objects.create(
                user=data.get('user', 'system'),
                action=f'透過 API 創建設備: {equipment.name}'
            )
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': equipment.id,
                    'name': equipment.name,
                    'model': equipment.model,
                    'status': equipment.status,
                    'status_display': equipment.get_status_display(),
                    'production_line_id': equipment.production_line_id,
                    'production_line_name': equipment.production_line_name,
                    'created_at': equipment.created_at.isoformat(),
                    'updated_at': equipment.updated_at.isoformat(),
                },
                'message': '設備創建成功'
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'JSON 格式錯誤'
            }, status=400)
        except Exception as e:
            logger.error(f"創建設備失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'創建設備失敗: {str(e)}'
            }, status=500)
    
    def put(self, request, equipment_id):
        """
        更新設備
        PUT /api/equip/equipment/{id}/
        """
        try:
            data = json.loads(request.body)
            
            try:
                equipment = Equipment.objects.get(id=equipment_id)
            except Equipment.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': '設備不存在'
                }, status=404)
            
            # 更新設備資訊
            if 'name' in data:
                # 檢查名稱是否與其他設備重複
                if Equipment.objects.filter(name=data['name']).exclude(id=equipment_id).exists():
                    return JsonResponse({
                        'success': False,
                        'message': f'設備名稱 "{data["name"]}" 已存在'
                    }, status=400)
                equipment.name = data['name']
            
            if 'model' in data:
                equipment.model = data['model']
            
            if 'status' in data:
                equipment.status = data['status']
            
            if 'production_line_id' in data:
                equipment.production_line_id = data['production_line_id']
            
            if 'production_line_name' in data:
                equipment.production_line_name = data['production_line_name']
            
            equipment.save()
            
            # 記錄操作日誌
            EquipOperationLog.objects.create(
                user=data.get('user', 'system'),
                action=f'透過 API 更新設備: {equipment.name}'
            )
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': equipment.id,
                    'name': equipment.name,
                    'model': equipment.model,
                    'status': equipment.status,
                    'status_display': equipment.get_status_display(),
                    'production_line_id': equipment.production_line_id,
                    'production_line_name': equipment.production_line_name,
                    'created_at': equipment.created_at.isoformat(),
                    'updated_at': equipment.updated_at.isoformat(),
                },
                'message': '設備更新成功'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'JSON 格式錯誤'
            }, status=400)
        except Exception as e:
            logger.error(f"更新設備失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'更新設備失敗: {str(e)}'
            }, status=500)
    
    def delete(self, request, equipment_id):
        """
        刪除設備
        DELETE /api/equip/equipment/{id}/
        """
        try:
            try:
                equipment = Equipment.objects.get(id=equipment_id)
                equipment_name = equipment.name
                equipment.delete()
                
                # 記錄操作日誌
                EquipOperationLog.objects.create(
                    user=request.GET.get('user', 'system'),
                    action=f'透過 API 刪除設備: {equipment_name}'
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'設備 "{equipment_name}" 刪除成功'
                })
                
            except Equipment.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': '設備不存在'
                }, status=404)
                
        except Exception as e:
            logger.error(f"刪除設備失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'刪除設備失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_equipment_status(request):
    """
    獲取設備狀態統計
    GET /api/equip/status/
    """
    try:
        equipments = Equipment.objects.all()
        
        status_count = {
            'idle': 0,
            'running': 0,
            'maintenance': 0,
            'total': len(equipments)
        }
        
        for equipment in equipments:
            if equipment.status in status_count:
                status_count[equipment.status] += 1
        
        return JsonResponse({
            'success': True,
            'data': status_count,
            'message': '設備狀態統計獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取設備狀態統計失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取設備狀態統計失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_equipment_by_production_line(request):
    """
    根據產線獲取設備列表
    GET /api/equip/by-production-line/?line_id=xxx
    """
    try:
        line_id = request.GET.get('line_id')
        line_name = request.GET.get('line_name')
        
        if not line_id and not line_name:
            return JsonResponse({
                'success': False,
                'message': '請提供 line_id 或 line_name 參數'
            }, status=400)
        
        # 根據產線 ID 或名稱查詢設備
        if line_id:
            equipments = Equipment.objects.filter(production_line_id=line_id)
        else:
            equipments = Equipment.objects.filter(production_line_name=line_name)
        
        data = []
        for equipment in equipments:
            data.append({
                'id': equipment.id,
                'name': equipment.name,
                'model': equipment.model,
                'status': equipment.status,
                'status_display': equipment.get_status_display(),
                'production_line_id': equipment.production_line_id,
                'production_line_name': equipment.production_line_name,
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': f'產線設備列表獲取成功'
        })
        
    except Exception as e:
        logger.error(f"根據產線獲取設備列表失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據產線獲取設備列表失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_equipment_operation_logs(request):
    """
    獲取設備操作日誌
    GET /api/equip/operation-logs/?limit=50
    """
    try:
        limit = int(request.GET.get('limit', 50))
        
        logs = EquipOperationLog.objects.all().order_by('-timestamp')[:limit]
        
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'user': log.user,
                'action': log.action,
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '設備操作日誌獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取設備操作日誌失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取設備操作日誌失敗: {str(e)}'
        }, status=500)
