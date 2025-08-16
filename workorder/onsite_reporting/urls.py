"""
現場報工子模組 - URL 配置
負責現場報工的 URL 路由配置
"""

from django.urls import path
from . import views

app_name = "onsite_reporting"

urlpatterns = [
    # 現場報工首頁
    path("", views.OnsiteReportIndexView.as_view(), name="onsite_report_index"),

    # 現場報工列表
    path("list/", views.OnsiteReportListView.as_view(), name="onsite_report_list"),

    # 現場報工詳情
    path("detail/<int:pk>/", views.OnsiteReportDetailView.as_view(), name="onsite_report_detail"),

    # 作業選擇頁面
    path("operator-work-selection/", views.operator_work_selection, name="operator_work_selection"),
    path("smt-work-selection/", views.smt_work_selection, name="smt_work_selection"),
    
    # 現場報工新增
    path("create/operator/", views.operator_onsite_report_create, name="operator_onsite_report_create"),
    path("create/smt/", views.smt_onsite_report_create, name="smt_onsite_report_create"),
    path("create/operator-rd/", views.operator_rd_onsite_report_create, name="operator_rd_onsite_report_create"),
    path("create/smt-rd/", views.smt_rd_onsite_report_create, name="smt_rd_onsite_report_create"),

    # 現場報工編輯
    path("edit/<int:pk>/", views.onsite_report_update, name="onsite_report_edit"),

    # 現場報工刪除
    path("delete/<int:pk>/", views.OnsiteReportDeleteView.as_view(), name="onsite_report_delete"),

    # 現場報工監控
    path("monitoring/", views.OnsiteReportMonitoringView.as_view(), name="onsite_report_monitoring"),

    # 現場報工配置管理
    path("config/", views.OnsiteReportConfigView.as_view(), name="onsite_report_config"),
    path("config/create/", views.onsite_report_config_create, name="onsite_report_config_create"),
    path("config/edit/<int:pk>/", views.onsite_report_config_update, name="onsite_report_config_edit"),
    path("config/delete/<int:pk>/", views.OnsiteReportConfigDeleteView.as_view(), name="onsite_report_config_delete"),

    # API 路由
    path("api/update-status/<int:pk>/", views.update_onsite_report_status, name="update_onsite_report_status"),
    path("api/complete/<int:pk>/", views.complete_onsite_report, name="complete_onsite_report"),
    path("api/pause/<int:pk>/", views.pause_onsite_report, name="pause_onsite_report"),
    path("api/resume/<int:pk>/", views.resume_onsite_report, name="resume_onsite_report"),

    # 動態載入 API
    path("api/product-list/", views.product_list_api, name="product_list_api"),
    path("api/company-list/", views.company_list_api, name="company_list_api"),
    path("api/workorder-list/", views.workorder_list_api, name="workorder_list_api"),
    path("api/operator-list/", views.operator_list_api, name="operator_list_api"),
    path("api/equipment-list/", views.equipment_list_api, name="equipment_list_api"),
    path("api/workorder-by-product/", views.workorder_by_product_api, name="workorder_by_product_api"),
    path("api/products-by-company/", views.products_by_company_api, name="products_by_company_api"),
    path("api/workorder-detail/", views.workorder_detail_api, name="workorder_detail_api"),
    path("api/workorder-debug/", views.workorder_debug_api, name="workorder_debug_api"),
    path("api/simple-test/", views.simple_test_api, name="simple_test_api"),
    
    # 自動加入工序 API
    path("api/auto-add-process/", views.auto_add_process_to_workorder, name="auto_add_process_to_workorder"),
    path("api/get-workorder-processes/", views.get_workorder_processes, name="get_workorder_processes"),
    
    # RD 樣品工單管理
    path("rd-sample-workorder/list/", views.rd_sample_workorder_list, name="rd_sample_workorder_list"),
    path("rd-sample-workorder/create/", views.rd_sample_workorder_create, name="rd_sample_workorder_create"),
    path("rd-sample-workorder/detail/<int:pk>/", views.rd_sample_workorder_detail, name="rd_sample_workorder_detail"),
    path("rd-sample-workorder/delete/<int:pk>/", views.rd_sample_workorder_delete, name="rd_sample_workorder_delete"),

] 