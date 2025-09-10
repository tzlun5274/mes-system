# 產線管理 URL 路由
# 此檔案定義產線管理模組的網頁路徑

from django.urls import path
from . import views, api

app_name = "production"
module_display_name = "產線管理"

urlpatterns = [
    # 首頁
    path("", views.index, name="index"),
    # 產線類型管理
    path("line-types/", views.line_type_list, name="line_type_list"),
    path("line-types/create/", views.line_type_create, name="line_type_create"),
    path("line-types/<int:pk>/edit/", views.line_type_edit, name="line_type_edit"),
    path(
        "line-types/<int:pk>/delete/", views.line_type_delete, name="line_type_delete"
    ),
    # 產線管理
    path("lines/", views.line_list, name="line_list"),
    path("lines/create/", views.line_create, name="line_create"),
    path("lines/<int:pk>/", views.line_detail, name="line_detail"),
    path("lines/<int:pk>/edit/", views.line_edit, name="line_edit"),
    path("lines/<int:pk>/delete/", views.line_delete, name="line_delete"),
    # 排程記錄管理
    path("schedules/", views.schedule_list, name="schedule_list"),
    path("schedules/create/", views.schedule_create, name="schedule_create"),
    path("schedules/<int:pk>/edit/", views.schedule_edit, name="schedule_edit"),
    path("schedules/<int:pk>/delete/", views.schedule_delete, name="schedule_delete"),
    # 匯出功能
    path("export/lines/", views.export_production_lines, name="export_production_lines"),
    path("export/line-types/", views.export_line_types, name="export_line_types"),
    
    # 匯入功能
    path("import/lines/", views.import_production_lines, name="import_production_lines"),
    path("import/line-types/", views.import_line_types, name="import_line_types"),
    
    # API 端點
    path("api/line-types/", views.api_line_types, name="api_line_types"),
    path(
        "api/production-lines/", views.api_production_lines, name="api_production_lines"
    ),
    
    # production API 路由
    path("api/production-line/", api.ProductionLineAPIView.as_view(), name="api_production_line_list"),
    path("api/production-line/<int:line_id>/", api.ProductionLineAPIView.as_view(), name="api_production_line_detail"),
    path("api/execution/", api.ProductionExecutionAPIView.as_view(), name="api_production_execution_list"),
    path("api/execution/<int:execution_id>/", api.ProductionExecutionAPIView.as_view(), name="api_production_execution_detail"),
    path("api/production-line-by-code/", api.get_production_line_by_code, name="api_production_line_by_code"),
    path("api/active-production-lines/", api.get_active_production_lines, name="api_active_production_lines"),
    path("api/executions-by-workorder/", api.get_production_executions_by_workorder, name="api_production_executions_by_workorder"),
    path("api/monitor-data/", api.get_production_monitor_data, name="api_production_monitor_data"),
]