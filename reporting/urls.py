"""
報表模組 URL 配置
"""

from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # 報表模組首頁
    path('', views.ReportingIndexView.as_view(), name='index'),
    
    # 待審核清單
    path('pending_approval_list/', views.pending_approval_list, name='pending_approval_list'),
    
    # 已核准清單
    path('approved_reports_list/', views.approved_reports_list, name='approved_reports_list'),
    
    # 超級管理員批次刪除功能
    path('batch_delete_pending_confirm/', views.batch_delete_pending_confirm, name='batch_delete_pending_confirm'),
    path('batch_delete_pending_reports/', views.batch_delete_pending_reports, name='batch_delete_pending_reports'),
    path('batch_delete_selected_pending/', views.batch_delete_selected_pending, name='batch_delete_selected_pending'),
    path('force_delete_all_reports/', views.force_delete_all_reports, name='force_delete_all_reports'),
    path('get_pending_reports_count/', views.get_pending_reports_count, name='get_pending_reports_count'),
    
    # 通用佔位符 - 用於所有未實現的功能
    path('<str:function_name>/', views.placeholder_view, name='placeholder'),
] 