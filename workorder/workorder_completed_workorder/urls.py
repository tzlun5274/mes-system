"""
已完工工單管理子模組 - URL 配置
負責定義已完工工單相關的 URL 路由
"""

from django.urls import path
from . import views

app_name = "completed_workorder"

urlpatterns = [
    # 已完工工單基本功能
    path("", views.CompletedWorkOrderListView.as_view(), name="completed_workorder_list"),
    path("create/", views.CompletedWorkOrderCreateView.as_view(), name="completed_workorder_create"),
    path("edit/<int:pk>/", views.CompletedWorkOrderUpdateView.as_view(), name="completed_workorder_edit"),
    path("delete/<int:pk>/", views.CompletedWorkOrderDeleteView.as_view(), name="completed_workorder_delete"),
    path("detail/<int:pk>/", views.CompletedWorkOrderDetailView.as_view(), name="completed_workorder_detail"),
    
    # 工單轉換功能
    path("transfer/<int:workorder_id>/", views.transfer_workorder_to_completed, name="transfer_workorder_to_completed"),
    path("batch-transfer/", views.batch_transfer_completed_workorders, name="batch_transfer_completed_workorders"),
    
    # 自動分配設定
    path("auto-allocation/", views.AutoAllocationSettingsListView.as_view(), name="auto_allocation_settings_list"),
    path("auto-allocation/create/", views.AutoAllocationSettingsCreateView.as_view(), name="auto_allocation_settings_create"),
    path("auto-allocation/edit/<int:pk>/", views.AutoAllocationSettingsUpdateView.as_view(), name="auto_allocation_settings_edit"),
    path("auto-allocation/delete/<int:pk>/", views.AutoAllocationSettingsDeleteView.as_view(), name="auto_allocation_settings_delete"),
    
    # API 端點
    path("api/list/", views.get_completed_workorder_list_api, name="api_completed_workorder_list"),
    path("api/detail/<int:pk>/", views.get_completed_workorder_detail_api, name="api_completed_workorder_detail"),
] 