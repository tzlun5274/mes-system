from django.urls import path
from . import views

app_name = "workorder"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/", views.create, name="create"),
    path(
        "get_company_order_info/",
        views.get_company_order_info,
        name="get_company_order_info",
    ),
    path("edit/<int:pk>/", views.edit, name="edit"),
    path("delete/<int:pk>/", views.delete, name="delete"),
    path(
        "delete_pending_workorders/",
        views.delete_pending_workorders,
        name="delete_pending_workorders",
    ),  # 刪除所有未派工工單
    path(
        "delete_in_progress_workorders/",
        views.delete_in_progress_workorders,
        name="delete_in_progress_workorders",
    ),  # 刪除所有已派工工單
    path("dispatch_list/", views.dispatch_list, name="dispatch_list"),
    path("company_orders/", views.company_orders, name="company_orders"),
    path("manual_sync_orders/", views.manual_sync_orders, name="manual_sync_orders"),
    path(
        "manual_convert_orders/",
        views.manual_convert_orders,
        name="manual_convert_orders",
    ),
    path(
        "selective_revert_orders/",
        views.selective_revert_orders,
        name="selective_revert_orders",
    ),
    path(
        "completed_workorders/", views.completed_workorders, name="completed_workorders"
    ),
    path(
        "import_historical_workorders/",
        views.import_historical_workorders,
        name="import_historical_workorders",
    ),
    path(
        "download_historical_workorder_template/",
        views.download_historical_workorder_template,
        name="download_historical_workorder_template",
    ),
    path(
        "clear_completed_workorders/",
        views.clear_completed_workorders,
        name="clear_completed_workorders",
    ),
    path("clear_data/", views.clear_data, name="clear_data"),
    path("clear_production_reports/", views.clear_all_production_reports, name="clear_all_production_reports"),
    path("get_processes_only/", views.get_processes_only, name="get_processes_only"),
    path(
        "get_operators_and_equipments/",
        views.get_operators_and_equipments,
        name="get_operators_and_equipments",
    ),
    path("get_operators_only/", views.get_operators_only, name="get_operators_only"),
    path("get_equipments_only/", views.get_equipments_only, name="get_equipments_only"),
    path(
        "workorder_process_detail/<int:workorder_id>/",
        views.workorder_process_detail,
        name="workorder_process_detail",
    ),
    path(
        "create_workorder_processes/<int:workorder_id>/",
        views.create_workorder_processes,
        name="create_workorder_processes",
    ),
    path("start_production/<int:pk>/", views.start_production, name="start_production"),
    path("stop_production/<int:pk>/", views.stop_production, name="stop_production"),
    path("process_logs/<int:process_id>/", views.process_logs, name="process_logs"),
    path("move_process/", views.move_process, name="move_process"),
    path("add_process/<int:workorder_id>/", views.add_process, name="add_process"),
    path("edit_process/<int:process_id>/", views.edit_process, name="edit_process"),
    path(
        "delete_process/<int:process_id>/", views.delete_process, name="delete_process"
    ),
    # SMT設備報班功能
    path(
        "get_process_capacity_info/<int:process_id>/",
        views.get_process_capacity_info,
        name="get_process_capacity_info",
    ),
    path(
        "update_process_capacity/<int:process_id>/",
        views.update_process_capacity,
        name="update_process_capacity",
    ),
    path(
        "get_capacity_calculation_info/<int:process_id>/",
        views.get_capacity_calculation_info,
        name="get_capacity_calculation_info",
    ),
    path(
        "update_process_status/<int:process_id>/",
        views.update_process_status,
        name="update_process_status",
    ),
    # 報工管理功能
    path("report/", views.report_index, name="report_index"),
    path("report/test/", views.test_report_page, name="test_report_page"),
    path(
        "report/supervisor/",
        views.supervisor_report_index,
        name="supervisor_report_index",
    ),
    path(
        "report/supervisor/functions/",
        views.supervisor_functions,
        name="supervisor_functions",
    ),
    path(
        "report/supervisor/statistics/",
        views.report_statistics,
        name="report_statistics",
    ),
    path(
        "report/supervisor/abnormal/",
        views.abnormal_management,
        name="abnormal_management",
    ),
    path(
        "report/supervisor/abnormal/batch-resolve/",
        views.batch_resolve_abnormal,
        name="batch_resolve_abnormal",
    ),
    path(
        "report/supervisor/abnormal/detail/<str:abnormal_type>/<int:abnormal_id>/",
        views.abnormal_detail,
        name="abnormal_detail",
    ),
    # 系統設定功能已移至系統管理模組，請使用 system:workorder_settings
    path("report/supervisor/export/", views.report_export, name="report_export"),
    path(
        "report/supervisor/maintenance/",
        views.data_maintenance,
        name="data_maintenance",
    ),
    path(
        "api/maintenance/execute/",
        views.execute_maintenance,
        name="execute_maintenance",
    ),
    path("report/operator/", views.operator_report_index, name="operator_report_index"),
    path("report/smt/", views.smt_report_index, name="smt_report_index"),
    path(
        "pending_approval_list/",
        views.pending_approval_list,
        name="pending_approval_list",
    ),
    path(
        "approved_reports_list/",
        views.approved_reports_list,
        name="approved_reports_list",
    ),
    path(
        "batch_approve_pending/",
        views.batch_approve_pending,
        name="batch_approve_pending",
    ),
    path("report/smt/on_site/", views.smt_on_site_report, name="smt_on_site_report"),
    path("report/smt/submit/", views.submit_smt_report, name="submit_smt_report"),
    path(
        "api/get_workorders_by_equipment/",
        views.get_workorders_by_equipment,
        name="get_workorders_by_equipment",
    ),
    path(
        "api/get_processes_by_workorder/",
        views.get_processes_by_workorder,
        name="get_processes_by_workorder",
    ),
    path(
        "api/operator/get_workorders_by_operator/",
        views.get_workorders_by_operator,
        name="get_workorders_by_operator",
    ),
    path(
        "api/operator/get_processes_by_workorder/",
        views.get_processes_by_workorder_for_operator,
        name="get_processes_by_workorder_for_operator",
    ),
    path(
        "api/operator/submit_report/",
        views.submit_operator_report,
        name="submit_operator_report",
    ),
    # SMT補登報工功能
    path(
        "report/smt/supplement/",
        views.smt_supplement_report_index,
        name="smt_supplement_report_index",
    ),
    path(
        "report/smt/supplement/create/",
        views.smt_supplement_report_create,
        name="smt_supplement_report_create",
    ),
    path(
        "report/smt/supplement/edit/<int:report_id>/",
        views.smt_supplement_report_edit,
        name="smt_supplement_report_edit",
    ),
    path(
        "report/smt/supplement/delete/<int:report_id>/",
        views.smt_supplement_report_delete,
        name="smt_supplement_report_delete",
    ),
    path(
        "report/smt/supplement/detail/<int:report_id>/",
        views.smt_supplement_report_detail,
        name="smt_supplement_report_detail",
    ),
    path(
        "report/smt/supplement/approve/<int:report_id>/",
        views.smt_supplement_report_approve,
        name="smt_supplement_report_approve",
    ),
    path(
        "report/smt/supplement/reject/<int:report_id>/",
        views.smt_supplement_report_reject,
        name="smt_supplement_report_reject",
    ),
    path(
        "report/smt/supplement/batch/",
        views.smt_supplement_batch,
        name="smt_supplement_batch",
    ),
    path(
        "report/smt/supplement/export/",
        views.smt_supplement_export,
        name="smt_supplement_export",
    ),
    path(
        "report/smt/supplement/template/",
        views.smt_supplement_template,
        name="smt_supplement_template",
    ),
    # SMTRD樣品補登功能 - 暫時停用，等待實作
    # path('report/smt/rd_sample_supplement/', views.smt_rd_sample_supplement_index, name='smt_rd_sample_supplement_index'),
    path(
        "api/smt/supplement/batch_create/",
        views.smt_supplement_batch_create,
        name="smt_supplement_batch_create",
    ),
    path(
        "api/smt/get_workorders_by_equipment/",
        views.get_smt_workorders_by_equipment,
        name="get_smt_workorders_by_equipment",
    ),
    path(
        "api/get_workorders_by_product/",
        views.get_workorders_by_product,
        name="get_workorders_by_product",
    ),
    path(
        "api/get_workorder_details/",
        views.get_workorder_details,
        name="get_workorder_details",
    ),
    # 作業員現場報工功能
    path(
        "report/operator/on_site/",
        views.operator_on_site_report,
        name="operator_on_site_report",
    ),
    path(
        "api/operator/get_workorder_info/",
        views.get_workorder_info,
        name="get_workorder_info",
    ),
    path(
        "report/operator/quick_report/",
        views.operator_quick_report,
        name="operator_quick_report",
    ),
    path(
        "report/operator/change_status/",
        views.operator_change_status,
        name="operator_change_status",
    ),
    path(
        "report/operator/delete_workorder/",
        views.operator_delete_workorder,
        name="operator_delete_workorder",
    ),
    path(
        "report/operator/start_process/",
        views.operator_start_process,
        name="operator_start_process",
    ),
    path(
        "report/operator/report_progress/",
        views.operator_report_progress,
        name="operator_report_progress",
    ),
    path(
        "report/operator/workorder_detail/",
        views.operator_workorder_detail,
        name="operator_workorder_detail",
    ),
    # 派工功能已移至派工單管理模組
    # path('report/operator/assign_workorder/', views.operator_assign_workorder, name='operator_assign_workorder'),
    path(
        "report/operator/report_work/",
        views.operator_report_work,
        name="operator_report_work",
    ),
    path("report/operator/detail/", views.operator_detail, name="operator_detail"),
    path(
        "report/operator/report_detail/",
        views.operator_report_detail,
        name="operator_report_detail",
    ),
    # 作業員補登報工功能
    path(
        "report/operator/supplement/",
        views.operator_supplement_report_index,
        name="operator_supplement_report_index",
    ),
    path(
        "report/operator/supplement/create/",
        views.operator_supplement_report_create,
        name="operator_supplement_report_create",
    ),
    path(
        "report/operator/supplement/edit/<int:report_id>/",
        views.operator_supplement_report_edit,
        name="operator_supplement_report_edit",
    ),
    path(
        "report/operator/supplement/delete/<int:report_id>/",
        views.operator_supplement_report_delete,
        name="operator_supplement_report_delete",
    ),
    path(
        "report/operator/supplement/detail/<int:report_id>/",
        views.operator_supplement_report_detail,
        name="operator_supplement_report_detail",
    ),
    path(
        "report/operator/supplement/approve/<int:report_id>/",
        views.operator_supplement_report_approve,
        name="operator_supplement_report_approve",
    ),
    path(
        "report/operator/supplement/reject/<int:report_id>/",
        views.operator_supplement_report_reject,
        name="operator_supplement_report_reject",
    ),
    path(
        "report/operator/supplement/batch/",
        views.operator_supplement_batch,
        name="operator_supplement_batch",
    ),
    path(
        "report/operator/supplement/export/",
        views.operator_supplement_export,
        name="operator_supplement_export",
    ),
    path(
        "report/operator/supplement/template/",
        views.operator_supplement_template,
        name="operator_supplement_template",
    ),
    path(
        "api/operator/supplement/batch_create/",
        views.operator_supplement_batch_create,
        name="operator_supplement_batch_create",
    ),
    path(
        "api/operator/get_workorders_by_operator/",
        views.get_workorders_by_operator,
        name="get_workorders_by_operator",
    ),
    # RD樣品補登報工功能 - 暫時停用，等待實作
    # path('report/operator/supplement/rd_sample/create/', views.rd_sample_supplement_report_create, name='rd_sample_supplement_report_create'),
    # path('report/operator/supplement/rd_sample/edit/<int:report_id>/', views.rd_sample_supplement_report_edit, name='rd_sample_supplement_report_edit'),
    # 主管審核功能 - 暫時停用，等待實作
    # path('report/supervisor/production/', views.SupervisorProductionReportListView.as_view(), name='supervisor_production_list'),
    # path('report/supervisor/production/create/', views.SupervisorProductionReportCreateView.as_view(), name='supervisor_production_create'),
    # path('report/supervisor/production/edit/<int:pk>/', views.SupervisorProductionReportUpdateView.as_view(), name='supervisor_production_edit'),
    # path('report/supervisor/production/detail/<int:pk>/', views.SupervisorProductionReportDetailView.as_view(), name='supervisor_production_detail'),
    # path('report/supervisor/production/delete/<int:pk>/', views.SupervisorProductionReportDeleteView.as_view(), name='supervisor_production_delete'),
    # path('report/supervisor/production/approve/<int:pk>/', views.SupervisorProductionReportApproveView.as_view(), name='supervisor_production_approve'),
    # path('report/supervisor/production/reject/<int:pk>/', views.SupervisorProductionReportRejectView.as_view(), name='supervisor_production_reject'),
    # path('report/supervisor/production/batch/', views.SupervisorProductionReportBatchView.as_view(), name='supervisor_production_batch'),
    # path('api/supervisor/production/get_workorders_by_product/', views.supervisor_get_workorders_by_product, name='supervisor_get_workorders_by_product'),
    # path('api/supervisor/production/batch_create/', views.supervisor_batch_create_api, name='supervisor_batch_create_api'),
    # 主管生產報工記錄 AJAX 版本 - 暫時停用，等待實作
    # path('report/supervisor/production/approve-ajax/<int:report_id>/', views.supervisor_production_report_approve_ajax, name='supervisor_production_approve_ajax'),
    # path('report/supervisor/production/reject-ajax/<int:report_id>/', views.supervisor_production_report_reject_ajax, name='supervisor_production_reject_ajax'),
]
