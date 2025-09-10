"""
物料管理模組 API
提供物料相關的 API 接口，供其他模組調用
完全獨立，無外鍵依賴
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from .models import Product, Material, Route, MaterialRequirement, MaterialInventory

# 設定日誌
logger = logging.getLogger(__name__)

class ProductAPIView(View):
    """
    產品 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, product_id=None):
        """
        獲取產品資訊
        GET /api/material/product/ - 獲取所有產品
        GET /api/material/product/{id}/ - 獲取單一產品
        """
        try:
            if product_id:
                try:
                    product = Product.objects.get(id=product_id)
                    data = {
                        'id': product.id,
                        'name': product.name,
                        'code': product.code,
                        'description': product.description,
                        'unit': product.unit,
                        'is_active': product.is_active,
                        'created_at': product.created_at.isoformat(),
                        'updated_at': product.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '產品資訊獲取成功'
                    })
                except Product.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '產品不存在'
                    }, status=404)
            else:
                products = Product.objects.all()
                data = []
                for product in products:
                    data.append({
                        'id': product.id,
                        'name': product.name,
                        'code': product.code,
                        'description': product.description,
                        'unit': product.unit,
                        'is_active': product.is_active,
                        'created_at': product.created_at.isoformat(),
                        'updated_at': product.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '產品列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取產品資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取產品資訊失敗: {str(e)}'
            }, status=500)


class MaterialAPIView(View):
    """
    物料 API 視圖類
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, material_id=None):
        """
        獲取物料資訊
        GET /api/material/material/ - 獲取所有物料
        GET /api/material/material/{id}/ - 獲取單一物料
        """
        try:
            if material_id:
                try:
                    material = Material.objects.get(id=material_id)
                    data = {
                        'id': material.id,
                        'name': material.name,
                        'code': material.code,
                        'description': material.description,
                        'unit': material.unit,
                        'category': material.category,
                        'is_active': material.is_active,
                        'created_at': material.created_at.isoformat(),
                        'updated_at': material.updated_at.isoformat(),
                    }
                    return JsonResponse({
                        'success': True,
                        'data': data,
                        'message': '物料資訊獲取成功'
                    })
                except Material.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '物料不存在'
                    }, status=404)
            else:
                materials = Material.objects.all()
                data = []
                for material in materials:
                    data.append({
                        'id': material.id,
                        'name': material.name,
                        'code': material.code,
                        'description': material.description,
                        'unit': material.unit,
                        'category': material.category,
                        'is_active': material.is_active,
                        'created_at': material.created_at.isoformat(),
                        'updated_at': material.updated_at.isoformat(),
                    })
                
                return JsonResponse({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'message': '物料列表獲取成功'
                })
                
        except Exception as e:
            logger.error(f"獲取物料資訊失敗: {e}")
            return JsonResponse({
                'success': False,
                'message': f'獲取物料資訊失敗: {str(e)}'
            }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_material_requirements(request):
    """
    獲取物料需求
    GET /api/material/requirements/?product_id=xxx
    """
    try:
        product_id = request.GET.get('product_id')
        
        if not product_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 product_id 參數'
            }, status=400)
        
        requirements = MaterialRequirement.objects.filter(product_id=product_id)
        
        data = []
        for requirement in requirements:
            data.append({
                'id': requirement.id,
                'product_id': requirement.product_id,
                'material_id': requirement.material_id,
                'quantity_per_unit': float(requirement.quantity_per_unit),
                'created_at': requirement.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '物料需求獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取物料需求失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取物料需求失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_material_inventory(request):
    """
    獲取物料庫存
    GET /api/material/inventory/?material_id=xxx
    """
    try:
        material_id = request.GET.get('material_id')
        
        if not material_id:
            return JsonResponse({
                'success': False,
                'message': '請提供 material_id 參數'
            }, status=400)
        
        inventory = MaterialInventory.objects.filter(material_id=material_id)
        
        data = []
        for item in inventory:
            data.append({
                'id': item.id,
                'material_id': item.material_id,
                'warehouse': item.warehouse,
                'quantity': float(item.quantity),
                'unit': item.unit,
                'last_updated': item.last_updated.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'data': data,
            'count': len(data),
            'message': '物料庫存獲取成功'
        })
        
    except Exception as e:
        logger.error(f"獲取物料庫存失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'獲取物料庫存失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_product_by_code(request):
    """
    根據產品編號獲取產品資訊
    GET /api/material/product-by-code/?code=xxx
    """
    try:
        code = request.GET.get('code')
        
        if not code:
            return JsonResponse({
                'success': False,
                'message': '請提供 code 參數'
            }, status=400)
        
        try:
            product = Product.objects.get(code=code)
            data = {
                'id': product.id,
                'name': product.name,
                'code': product.code,
                'description': product.description,
                'unit': product.unit,
                'is_active': product.is_active,
                'created_at': product.created_at.isoformat(),
            }
            
            return JsonResponse({
                'success': True,
                'data': data,
                'message': '產品資訊獲取成功'
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'產品編號 "{code}" 不存在'
            }, status=404)
        
    except Exception as e:
        logger.error(f"根據產品編號獲取產品資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據產品編號獲取產品資訊失敗: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_material_by_code(request):
    """
    根據物料編號獲取物料資訊
    GET /api/material/material-by-code/?code=xxx
    """
    try:
        code = request.GET.get('code')
        
        if not code:
            return JsonResponse({
                'success': False,
                'message': '請提供 code 參數'
            }, status=400)
        
        try:
            material = Material.objects.get(code=code)
            data = {
                'id': material.id,
                'name': material.name,
                'code': material.code,
                'description': material.description,
                'unit': material.unit,
                'category': material.category,
                'is_active': material.is_active,
                'created_at': material.created_at.isoformat(),
            }
            
            return JsonResponse({
                'success': True,
                'data': data,
                'message': '物料資訊獲取成功'
            })
            
        except Material.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'物料編號 "{code}" 不存在'
            }, status=404)
        
    except Exception as e:
        logger.error(f"根據物料編號獲取物料資訊失敗: {e}")
        return JsonResponse({
            'success': False,
            'message': f'根據物料編號獲取物料資訊失敗: {str(e)}'
        }, status=500)
