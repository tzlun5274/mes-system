# 產線管理 URL 路由
# 此檔案定義產線管理模組的網頁路徑

from django.urls import path
from . import views

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
]
