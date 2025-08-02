"""
主管功能子模組URL路由 (Supervisor Module URL Configuration)
定義主管功能的所有URL路由
"""
from django.urls import path
from . import views

app_name = 'supervisor'

urlpatterns = [
    # 主管功能首頁 (Supervisor Functions Homepage)
    path('functions/', views.supervisor_functions, name='supervisor_functions'),
    
    # 審核管理 (Approval Management)
    path('reports/', views.supervisor_report_index, name='supervisor_report_index'),
    path('pending_approval_list/', views.pending_approval_list, name='pending_approval_list'),
    path('approved_reports_list/', views.approved_reports_list, name='approved_reports_list'),
    path('report_detail/<int:report_id>/', views.report_detail, name='report_detail'),
    path('approve_report/<int:report_id>/', views.approve_report, name='approve_report'),
    path('reject_report/<int:report_id>/', views.reject_report, name='reject_report'),
    path('approve_smt_report/<int:report_id>/', views.approve_smt_report, name='approve_smt_report'),
    path('reject_smt_report/<int:report_id>/', views.reject_smt_report, name='reject_smt_report'),
    path('revert_approved_report/<int:report_id>/', views.revert_approved_report, name='revert_approved_report'),
    path('batch_revert_all_approved_reports/', views.batch_revert_all_approved_reports, name='batch_revert_all_approved_reports'),
    # 移除主管報工核准和駁回路由 - 主管不應該有報工記錄
    path('batch_approve_reports/', views.batch_approve_reports, name='batch_approve_reports'),
    path('batch_delete_reports/', views.batch_delete_reports, name='batch_delete_reports'),
    
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