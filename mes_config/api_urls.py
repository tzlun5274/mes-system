"""
純 API 模式的 URL 配置
只包含 API 路由，不包含 admin 和靜態檔案
"""
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    """API 根目錄"""
    return JsonResponse({
        'message': 'MES 系統 API',
        'version': '1.0',
        'endpoints': {
            'workorder': '/workorder/api/',
            'equipment': '/equip/api/',
            'material': '/material/api/',
            'process': '/process/api/',
            'quality': '/quality/api/',
            'kanban': '/kanban/api/',
            'reporting': '/reporting/api/',
        }
    })

urlpatterns = [
    path('', api_root, name='api_root'),
    
    # 各模組的 API 路由
    path("workorder/", include("workorder.urls", namespace="workorder")),
    path("equip/", include("equip.urls", namespace="equip")),
    path("material/", include("material.urls", namespace="material")),
    path("process/", include("process.urls", namespace="process")),
    path("quality/", include("quality.urls", namespace="quality")),
    path("kanban/", include("kanban.urls", namespace="kanban")),
    path("reporting/", include("reporting.urls", namespace="reporting")),
    path("system/", include("system.urls", namespace="system")),
    path("ai/", include("ai.urls", namespace="ai")),
    path("erp_integration/", include("erp_integration.urls", namespace="erp_integration")),
]
