"""
統一補登報工 URL 配置
定義統一補登報工模組的所有 URL 路由
"""

from django.urls import path
from . import views

app_name = 'work_reporting_management'

urlpatterns = [
    # 主要功能頁面
    path('', views.unified_work_report_list, name='unified_work_report_list'),
    path('dashboard/', views.unified_work_report_dashboard, name='unified_work_report_dashboard'),
    
    # 基本 CRUD 操作
    path('create/', views.unified_work_report_create, name='unified_work_report_create'),
    path('<int:pk>/', views.unified_work_report_detail, name='unified_work_report_detail'),
    path('<int:pk>/edit/', views.unified_work_report_update, name='unified_work_report_update'),
    path('<int:pk>/delete/', views.unified_work_report_delete, name='unified_work_report_delete'),
    
    # 核准功能
    path('<int:pk>/approval/', views.unified_work_report_approval, name='unified_work_report_approval'),
    
    # 匯入匯出功能
    path('export/', views.unified_work_report_export, name='unified_work_report_export'),
    path('import/', views.unified_work_report_import, name='unified_work_report_import'),
    
    # API 介面
    path('api/', views.unified_work_report_api, name='unified_work_report_api'),
] 