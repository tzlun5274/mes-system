# -*- coding: utf-8 -*-
"""
報表模組視圖包
包含報表查看、同步管理等功能
"""

from .report_views import (
    ReportDashboardView,
    WorkTimeReportListView,
    WorkTimeReportDetailView,
    WorkTimeReportExportView,
    WorkOrderProductReportListView,
    WorkOrderProductReportDetailView,
    WorkOrderProductReportExportView,
    ReportExportView,
    report_export,
    execute_report_export,
)

from .sync_views import (
    SyncStatusListView,
    SyncDetailView,
    ManualSyncView,
    SyncDashboardView,
    SyncSettingsView,
    SyncAPIView,
    WorkOrderAllocationView,
)

from .setting_views import (
    AddSyncSettingView,
    EditSyncSettingView,
    DeleteSyncSettingView,
    ToggleSyncSettingView,
)

__all__ = [
    'ReportDashboardView',
    'WorkTimeReportListView',
    'WorkTimeReportDetailView',
    'WorkTimeReportExportView',
    'WorkOrderProductReportListView',
    'WorkOrderProductReportDetailView',
    'WorkOrderProductReportExportView',
    'ReportExportView',
    'SyncStatusListView',
    'SyncDetailView',
    'ManualSyncView',
    'SyncDashboardView',
    'SyncSettingsView',
    'SyncAPIView',
    'WorkOrderAllocationView',
    'AddSyncSettingView',
    'EditSyncSettingView',
    'DeleteSyncSettingView',
    'ToggleSyncSettingView',
    'report_export',
    'execute_report_export',
] 