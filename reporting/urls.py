# -*- coding: utf-8 -*-
"""
報表模組 URL 路由設定
包含報表查看、同步管理等功能的路由
"""

from django.urls import path
from . import views
from .views import sync_views
# 直接從主 views.py 文件導入函數
from .views.report_views import report_export, execute_report_export

app_name = 'reporting'

urlpatterns = [
    # 報表首頁
    path('', views.ReportDashboardView.as_view(), name='dashboard'),
    path('', views.ReportDashboardView.as_view(), name='index'),  # 為了與其他模組保持一致
    
    # 工作時間報表
    path('work-time/', views.WorkTimeReportListView.as_view(), name='work_time_list'),
    path('work-time/detail/<int:pk>/', views.WorkTimeReportDetailView.as_view(), name='work_time_detail'),
    path('work-time/export/', views.WorkTimeReportExportView.as_view(), name='work_time_export'),
    
    # 工時單查詢（生產日報）
    path('production-daily/', views.WorkTimeReportListView.as_view(), name='production_daily'),
    
    # 工單機種報表
    path('work-order/', views.WorkOrderProductReportListView.as_view(), name='work_order_list'),
    path('work-order/detail/<int:pk>/', views.WorkOrderProductReportDetailView.as_view(), name='work_order_detail'),
    path('work-order/export/', views.WorkOrderProductReportExportView.as_view(), name='work_order_export'),
    
    # 報表匯出
    path('export/', views.ReportExportView.as_view(), name='export'),
    path('report-export/', report_export, name='report_export'),
    path('execute-report-export/', execute_report_export, name='execute_report_export'),
    
    # 同步管理相關路由
    path('sync/', sync_views.SyncStatusListView.as_view(), name='sync_status_list'),
    path('sync/detail/<int:pk>/', sync_views.SyncDetailView.as_view(), name='sync_detail'),
    path('sync/dashboard/', sync_views.SyncDashboardView.as_view(), name='sync_dashboard'),
    path('sync/settings/', sync_views.SyncSettingsView.as_view(), name='sync_settings'),
    path('sync/manual/', sync_views.ManualSyncView.as_view(), name='manual_sync'),
    path('sync/api/', sync_views.SyncAPIView.as_view(), name='sync_api'),
    path('sync/allocation/', sync_views.WorkOrderAllocationView.as_view(), name='workorder_allocation'),
    
    # 同步設定管理
    path('sync/settings/add/', views.AddSyncSettingView.as_view(), name='add_sync_setting'),
    path('sync/settings/edit/', views.EditSyncSettingView.as_view(), name='edit_sync_setting'),
    path('sync/settings/delete/<int:pk>/', views.DeleteSyncSettingView.as_view(), name='delete_sync_setting'),
    path('sync/settings/toggle/<int:pk>/', views.ToggleSyncSettingView.as_view(), name='toggle_sync_setting'),
]
