"""
資料服務 API 模組
提供統一的資料查詢服務，避免直接使用外鍵關係
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from .models import ProductProcessRoute, ProcessName
from equip.models import Equipment

logger = logging.getLogger(__name__)


class DataServiceAPI(View):
    """
    統一資料服務 API
    提供工序名稱、設備資訊等資料查詢服務
    """
    
    @method_decorator(login_required)
    def get(self, request):
        """取得各種資料的 API"""
        data_type = request.GET.get('type')
        
        if data_type == 'process_names':
            return self._get_process_names()
        elif data_type == 'equipments':
            return self._get_equipments()
        elif data_type == 'product_route_detail':
            product_id = request.GET.get('product_id')
            return self._get_product_route_detail(product_id)
        elif data_type == 'all_product_routes_export':
            return self._get_all_product_routes_for_export()
        else:
            return JsonResponse({'error': '不支援的資料類型'}, status=400)
    
    def _get_process_names(self):
        """取得所有工序名稱"""
        try:
            process_names = ProcessName.objects.all().values('id', 'name', 'description')
            return JsonResponse({
                'success': True,
                'data': list(process_names)
            })
        except Exception as e:
            logger.error(f"取得工序名稱失敗: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _get_equipments(self):
        """取得所有設備資訊"""
        try:
            equipments = Equipment.objects.all().values('id', 'name', 'status')
            return JsonResponse({
                'success': True,
                'data': list(equipments)
            })
        except Exception as e:
            logger.error(f"取得設備資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _get_product_route_detail(self, product_id):
        """取得產品工藝路線詳細資訊"""
        try:
            if not product_id:
                return JsonResponse({
                    'success': False,
                    'error': '缺少產品編號參數'
                }, status=400)
            
            # 取得產品工藝路線
            routes = ProductProcessRoute.objects.filter(
                product_id=product_id
            ).order_by('step_order')
            
            if not routes.exists():
                return JsonResponse({
                    'success': False,
                    'error': f'找不到產品編號 {product_id} 的工藝路線'
                }, status=404)
            
            # 取得所有工序名稱和設備資訊
            process_names = {
                str(p['id']): p['name'] 
                for p in ProcessName.objects.all().values('id', 'name')
            }
            
            equipments = {
                str(e['id']): e['name'] 
                for e in Equipment.objects.all().values('id', 'name')
            }
            
            # 組裝詳細資料
            route_details = []
            for route in routes:
                # 處理設備ID列表
                equipment_ids = []
                equipment_names = []
                if route.usable_equipment_ids:
                    equipment_ids = [
                        eid.strip() 
                        for eid in route.usable_equipment_ids.split(',')
                        if eid.strip() and eid.strip().isdigit()
                    ]
                    equipment_names = [
                        equipments.get(eid, f'未知設備({eid})') 
                        for eid in equipment_ids
                    ]
                
                route_details.append({
                    'id': route.id,
                    'step_order': route.step_order,
                    'process_name_id': route.process_name_id,
                    'process_name': route.process_name,
                    'process_name_display': process_names.get(
                        route.process_name_id, 
                        route.process_name or '未知工序'
                    ),
                    'usable_equipment_ids': equipment_ids,
                    'usable_equipment_names': equipment_names,
                    'dependent_semi_product': route.dependent_semi_product or ''
                })
            
            return JsonResponse({
                'success': True,
                'data': {
                    'product_id': product_id,
                    'routes': route_details
                }
            })
            
        except Exception as e:
            logger.error(f"取得產品工藝路線詳細資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _get_all_product_routes_for_export(self):
        """取得所有產品工藝路線用於匯出"""
        try:
            # 取得所有產品工藝路線
            routes = ProductProcessRoute.objects.all().order_by('product_id', 'step_order')
            
            # 取得所有工序名稱和設備資訊
            process_names = {
                str(p['id']): p['name'] 
                for p in ProcessName.objects.all().values('id', 'name')
            }
            
            equipments = {
                str(e['id']): e['name'] 
                for e in Equipment.objects.all().values('id', 'name')
            }
            
            # 組裝匯出資料
            export_data = []
            for route in routes:
                # 處理設備ID列表
                equipment_ids = []
                equipment_names = []
                if route.usable_equipment_ids:
                    equipment_ids = [
                        eid.strip() 
                        for eid in route.usable_equipment_ids.split(',')
                        if eid.strip() and eid.strip().isdigit()
                    ]
                    equipment_names = [
                        equipments.get(eid, f'未知設備({eid})') 
                        for eid in equipment_ids
                    ]
                
                # 取得正確的工序名稱顯示
                process_name_display = process_names.get(
                    route.process_name_id, 
                    route.process_name or '未知工序'
                )
                
                export_data.append({
                    'product_id': route.product_id,
                    'step_order': route.step_order,
                    'process_name': process_name_display,
                    'process_name_id': route.process_name_id,
                    'usable_equipment_names': ', '.join(equipment_names) if equipment_names else '',
                    'usable_equipment_ids': equipment_ids,
                    'dependent_semi_product': route.dependent_semi_product or ''
                })
            
            return JsonResponse({
                'success': True,
                'data': export_data
            })
            
        except Exception as e:
            logger.error(f"取得所有產品工藝路線失敗: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@login_required
@require_http_methods(["GET"])
def get_process_name_by_id(request, process_name_id):
    """根據ID取得工序名稱"""
    try:
        process_name = ProcessName.objects.filter(id=process_name_id).first()
        if process_name:
            return JsonResponse({
                'success': True,
                'data': {
                    'id': process_name.id,
                    'name': process_name.name,
                    'description': process_name.description
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '找不到指定的工序名稱'
            }, status=404)
    except Exception as e:
        logger.error(f"取得工序名稱失敗: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_equipment_by_ids(request):
    """根據ID列表取得設備資訊"""
    try:
        equipment_ids = request.GET.get('ids', '')
        if not equipment_ids:
            return JsonResponse({
                'success': False,
                'error': '缺少設備ID參數'
            }, status=400)
        
        # 解析ID列表
        ids = [eid.strip() for eid in equipment_ids.split(',') if eid.strip()]
        
        equipments = Equipment.objects.filter(id__in=ids).values('id', 'name', 'status')
        
        return JsonResponse({
            'success': True,
            'data': list(equipments)
        })
        
    except Exception as e:
        logger.error(f"取得設備資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
