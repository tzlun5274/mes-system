"""
報表模組 URL 配置
"""

from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # 報表模組首頁
    path('', views.ReportingIndexView.as_view(), name='index'),
    
    # 待審核報工清單
    path('pending_approval_list/', views.pending_approval_list, name='pending_approval_list'),
    
    # 報表匯出功能
    path('report_export/', views.report_export, name='report_export'),
    
    # 通用佔位符 - 用於所有未實現的功能
    path('<str:function_name>/', views.placeholder_view, name='placeholder'),
] 