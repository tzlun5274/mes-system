"""
報表模組 URL 配置
"""

from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # 報表模組首頁
    path('', views.reporting_index, name='index'),
    
    # 報表匯出
    path('export/', views.report_export, name='report_export'),
    
    # 匯出日誌
    path('export-logs/', views.export_log_list, name='export_log_list'),
    
    # 報表預覽 (AJAX)
    path('preview/', views.report_preview, name='report_preview'),
] 