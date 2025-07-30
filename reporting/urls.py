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
    
    # ==================== 從 workorder 模組移過來的報表匯出功能 ====================
    
    # SMT補登報工匯出
    path('smt-supplement-export/', views.smt_supplement_export, name='smt_supplement_export'),
    
    # 作業員補登報工匯出
    path('operator-supplement-export/', views.operator_supplement_export, name='operator_supplement_export'),
    
    # 報工審核列表
    path('pending-approval/', views.pending_approval_list, name='pending_approval_list'),
    path('approved-reports/', views.approved_reports_list, name='approved_reports_list'),
] 