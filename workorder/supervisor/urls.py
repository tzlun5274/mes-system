"""
主管功能子模組URL路由 (Supervisor Module URL Configuration)
定義主管功能的所有URL路由
注意：舊的報工系統已棄用，相關路由已移除
"""
from django.urls import path
from . import views

app_name = 'supervisor'

urlpatterns = [
    # 主管功能首頁 (Supervisor Functions Homepage)
    path('functions/', views.supervisor_functions, name='supervisor_functions'),
    
    # 統計分析 (Statistics Analysis)
    path('statistics/', views.report_statistics, name='report_statistics'),
    
    # 異常處理 (Abnormal Management)
    path('abnormal/', views.abnormal_management, name='abnormal_management'),
    path('abnormal/<str:abnormal_type>/<int:abnormal_id>/', views.abnormal_detail, name='abnormal_detail'),
    path('batch_resolve_abnormal/', views.batch_resolve_abnormal, name='batch_resolve_abnormal'),
    
    # 資料維護 (Data Maintenance)
    path('maintenance/', views.data_maintenance, name='data_maintenance'),
    path('maintenance/execute/', views.execute_maintenance, name='execute_maintenance'),
] 