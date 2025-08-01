"""
主管功能子模組URL路由
"""
from django.urls import path
from . import views

app_name = 'supervisor'

urlpatterns = [
    # 主管功能首頁
    path('functions/', views.supervisor_functions, name='supervisor_functions'),
    
    # 審核管理
    path('reports/', views.supervisor_report_index, name='supervisor_report_index'),
    path('pending_approval_list/', views.pending_approval_list, name='pending_approval_list'),
    path('approve_report/<int:report_id>/', views.approve_report, name='approve_report'),
    path('reject_report/<int:report_id>/', views.reject_report, name='reject_report'),
    path('batch_approve_reports/', views.batch_approve_reports, name='batch_approve_reports'),
    
    # 統計分析
    path('statistics/', views.report_statistics, name='report_statistics'),
    
    # 異常處理
    path('abnormal/', views.abnormal_management, name='abnormal_management'),
    path('abnormal/<str:abnormal_type>/<int:abnormal_id>/', views.abnormal_detail, name='abnormal_detail'),
    
    # 資料維護
    path('maintenance/', views.data_maintenance, name='data_maintenance'),
    path('maintenance/execute/', views.execute_maintenance, name='execute_maintenance'),
] 