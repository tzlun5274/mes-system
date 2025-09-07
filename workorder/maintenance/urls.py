"""
工單管理系統維護功能 URL 路由配置
包含相符性檢查、清除工單、Excel匯入工單等維護相關功能的路由
"""
from django.urls import path
from . import consistency_check_views, workorder_clear_views, workorder_import_views

app_name = "maintenance"

urlpatterns = [
    # 相符性檢查功能
    path("consistency-check/", consistency_check_views.ConsistencyCheckHomeView.as_view(), name="consistency_check_home"),
    path("consistency-check/ajax/", consistency_check_views.ConsistencyCheckAjaxView.as_view(), name="consistency_check_ajax"),
    path("consistency-check/detail/", consistency_check_views.ConsistencyCheckDetailView.as_view(), name="consistency_check_detail"),
    path("consistency-check/export/", consistency_check_views.ConsistencyCheckExportView.as_view(), name="consistency_check_export"),
    path("consistency-check/fix/", consistency_check_views.ConsistencyCheckFixView.as_view(), name="consistency_check_fix"),
    
    # 工單清除功能
    path("clear-workorders/", workorder_clear_views.WorkOrderClearView.as_view(), name="clear_workorders"),
    path("clear-workorders-ajax/", workorder_clear_views.WorkOrderClearAjaxView.as_view(), name="clear_workorders_ajax"),
    
    # Excel匯入工單功能
    path("import/", workorder_import_views.workorder_import_page, name="workorder_import"),
    path("import/file/", workorder_import_views.workorder_import_file, name="workorder_import_file"),
    path("import/template/", workorder_import_views.download_workorder_template, name="download_workorder_template"),
]
