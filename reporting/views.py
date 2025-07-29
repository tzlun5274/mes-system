# -*- coding: utf-8 -*-
"""
報表模組主視圖檔案
根據報表系統架構規範，所有視圖函數都應該組織在對應的子模組中
"""

import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

# 從子模組導入視圖
from .views.report_views import ReportDashboardView
from .views.sync_views import (
    SyncStatusListView, SyncDetailView, SyncDashboardView, 
    SyncSettingsView, ManualSyncView, SyncAPIView, WorkOrderAllocationView
)
from .views.setting_views import (
    AddSyncSettingView, EditSyncSettingView, 
    DeleteSyncSettingView, ToggleSyncSettingView
)

# 設定日誌記錄器
logger = logging.getLogger(__name__)

def reporting_user_required(user):
    """檢查用戶是否為超級用戶或屬於「報表使用者」群組"""
    return user.is_superuser or user.groups.filter(name="報表使用者").exists()

def log_user_operation(username, module, action):
    """記錄用戶操作"""
    logger.info(f"用戶操作 - 用戶: {username}, 模組: {module}, 動作: {action}")

# 其他視圖函數都已經移到對應的子模組中：
# - report_views.py: 報表相關視圖
# - sync_views.py: 同步相關視圖  
# - setting_views.py: 設定相關視圖
