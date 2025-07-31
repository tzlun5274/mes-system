"""
派工單 URL 路由配置
定義派工單管理相關的所有 URL 路徑
"""

from django.urls import path
from . import views

app_name = 'workorder_dispatch'

urlpatterns = [
    # 派工單列表
    path('', views.DispatchListView.as_view(), name='dispatch_list'),
    
    # 派工單儀表板
    path('dashboard/', views.dispatch_dashboard, name='dispatch_dashboard'),
    
    # 派工單 CRUD 操作
    path('add/', views.DispatchCreateView.as_view(), name='dispatch_add'),
    path('edit/<int:pk>/', views.DispatchUpdateView.as_view(), name='dispatch_edit'),
    path('detail/<int:pk>/', views.DispatchDetailView.as_view(), name='dispatch_detail'),
    path('delete/<int:pk>/', views.DispatchDeleteView.as_view(), name='dispatch_delete'),
    
    # AJAX 端點
    path('api/work-order-info/', views.get_work_order_info, name='get_work_order_info'),
    path('api/bulk-dispatch/', views.bulk_dispatch, name='bulk_dispatch'),
] 