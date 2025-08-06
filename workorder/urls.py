from django.urls import path, include
from . import views_main as workorder_views
from . import views_import as import_views
from .supervisor import views as supervisor_views
from .views.workorder_views import (
    WorkOrderListView, WorkOrderDetailView, WorkOrderCreateView, 
    WorkOrderUpdateView, WorkOrderDeleteView, CompanyOrderListView,
    get_company_order_info
)
from .views.report_views import (
    ReportIndexView, OperatorSupplementReportListView, OperatorSupplementReportCreateView,
    OperatorSupplementReportUpdateView, OperatorSupplementReportDetailView, 
    OperatorSupplementReportDeleteView, SMTProductionReportListView, SMTProductionReportCreateView,
    SMTProductionReportUpdateView, SMTProductionReportDetailView, SMTProductionReportDeleteView,
    SMTRDSampleProductionReportCreateView, SMTRDSampleProductionReportUpdateView,
    OperatorRDSampleSupplementReportCreateView,
    approve_report, reject_report
)
from .views.completed_workorder_views import (
    CompletedWorkOrderListView, CompletedWorkOrderDetailView,
    transfer_workorder_to_completed, batch_transfer_completed_workorders
)
from .views import api_views
from .views.auto_allocation_views import (
    auto_allocation_status, auto_allocation_settings, auto_allocation_execute,
    auto_allocation_stop, auto_allocation_log, auto_allocation_summary
)
from .views.auto_management_views import (
    AutoManagementConfigListView, AutoManagementConfigCreateView,
    AutoManagementConfigUpdateView, AutoManagementConfigDeleteView,
    execute_auto_function, toggle_auto_function
)
from .views.completion_automation_views import (
    CompletionAutomationManagementView
)

app_name = "workorder"

urlpatterns = [
    # 工單管理基本功能 - 使用新的類別視圖
    path("", WorkOrderListView.as_view(), name="index"),
    path("create/", WorkOrderCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", WorkOrderUpdateView.as_view(), name="edit"),
    path("delete/<int:pk>/", WorkOrderDeleteView.as_view(), name="delete"),
    path("detail/<int:pk>/", WorkOrderDetailView.as_view(), name="detail"),
    path("list/", WorkOrderListView.as_view(), name="list"),
    path("active/", workorder_views.active_workorders, name="active_workorders"),
    path("completion-check/", workorder_views.check_workorder_completion, name="completion_check"),
    
    # 已完工工單相關 URL
    path('completed/', CompletedWorkOrderListView.as_view(), name='completed_workorder_list'),
    path('completed/<int:pk>/', CompletedWorkOrderDetailView.as_view(), name='completed_workorder_detail'),
    path('completed/transfer/<int:workorder_id>/', transfer_workorder_to_completed, name='transfer_workorder_to_completed'),
    path('completed/batch-transfer/', batch_transfer_completed_workorders, name='batch_transfer_completed_workorders'),
    
    # 公司製令單管理 - 使用類別視圖
    path("company/", CompanyOrderListView.as_view(), name="company_orders"),
    
    # API 路由
    path("api/company_order_info/", get_company_order_info, name="get_company_order_info"),
    
    # 工序 API 路由
    path("api/process/<int:process_id>/", api_views.get_process_detail, name="get_process_detail"),
    path("api/process/<int:process_id>/edit/", api_views.edit_process, name="edit_process"),
    path("api/process/<int:process_id>/delete/", api_views.delete_process, name="delete_process"),
    
    # 報工管理首頁 - 使用新的類別視圖
    path("report/", ReportIndexView.as_view(), name="report_index"),
    
    # 作業員補登報工功能 - 使用新的類別視圖
    path("report/operator/supplement/", OperatorSupplementReportListView.as_view(), name="operator_supplement_report_index"),
    path("report/operator/supplement/create/", OperatorSupplementReportCreateView.as_view(), name="operator_supplement_report_create"),
    path("report/operator/supplement/edit/<int:pk>/", OperatorSupplementReportUpdateView.as_view(), name="operator_supplement_report_edit"),
    path("report/operator/supplement/detail/<int:pk>/", OperatorSupplementReportDetailView.as_view(), name="operator_supplement_report_detail"),
    path("report/operator/supplement/delete/<int:pk>/", OperatorSupplementReportDeleteView.as_view(), name="operator_supplement_report_delete"),
    
    # 作業員RD樣品補登報工功能 - 只保留新增功能
    path("report/operator/rd_sample_supplement/create/", OperatorRDSampleSupplementReportCreateView.as_view(), name="operator_rd_sample_supplement_create"),
    
    # 作業員補登報工批量匯入功能
    path("report/operator/supplement/batch/", import_views.operator_report_import_page, name="operator_supplement_batch"),
    path("report/operator/supplement/batch/file/", import_views.operator_report_import_file, name="operator_supplement_batch_file"),
    path("report/operator/supplement/batch/template/", import_views.download_import_template, name="operator_supplement_batch_template"),
    path("report/operator/supplement/batch/export/", import_views.operator_report_export, name="operator_supplement_batch_export"),
    
    # SMT補登報工功能 - 使用新的類別視圖
    path("report/smt/supplement/", SMTProductionReportListView.as_view(), name="smt_supplement_report_index"),
    path("report/smt/supplement/create/", SMTProductionReportCreateView.as_view(), name="smt_supplement_report_create"),
    path("report/smt/supplement/edit/<int:pk>/", SMTProductionReportUpdateView.as_view(), name="smt_supplement_report_edit"),
    path("report/smt/supplement/delete/<int:pk>/", SMTProductionReportDeleteView.as_view(), name="smt_supplement_report_delete"),
    path("report/smt/supplement/detail/<int:pk>/", SMTProductionReportDetailView.as_view(), name="smt_supplement_report_detail"),
    
    # SMT RD樣品補登報工功能
    path("report/smt/rd_sample/create/", SMTRDSampleProductionReportCreateView.as_view(), name="smt_rd_sample_report_create"),
    path("report/smt/rd_sample/edit/<int:pk>/", SMTRDSampleProductionReportUpdateView.as_view(), name="smt_rd_sample_report_edit"),
    

    
    # 報工核准功能
    path("report/approve/<int:report_id>/", approve_report, name="approve_report"),
    path("report/reject/<int:report_id>/", reject_report, name="reject_report"),
    
    # 保留原有函數式視圖的路由（向後相容）
    # 派工單管理 - 直接定義路由
    path("dispatch/", workorder_views.dispatch_list, name="dispatch_list"),
    path("dispatch/dashboard/", workorder_views.dispatch_dashboard, name="dispatch_dashboard"),
    path("dispatch/add/", workorder_views.dispatch_add, name="dispatch_add"),
    path("dispatch/edit/<int:pk>/", workorder_views.dispatch_edit, name="dispatch_edit"),
    path("dispatch/detail/<int:pk>/", workorder_views.dispatch_detail, name="dispatch_detail"),
    path("dispatch/delete/<int:pk>/", workorder_views.dispatch_delete, name="dispatch_delete"),
    # 完工工單子模組路由 - 已移除
    path("clear/", workorder_views.clear_data, name="clear_data"),
    path("clear_reports/", workorder_views.clear_all_production_reports, name="clear_all_production_reports"),
    # 完工工單相關路由已移除
    path("process/<int:workorder_id>/", workorder_views.workorder_process_detail, name="workorder_process_detail"),
    path("start_production/<int:pk>/", workorder_views.start_production, name="start_production"),
    path("stop_production/<int:pk>/", workorder_views.stop_production, name="stop_production"),
    path("delete_pending/", workorder_views.delete_pending_workorders, name="delete_pending_workorders"),
    path("delete_in_progress/", workorder_views.delete_in_progress_workorders, name="delete_in_progress_workorders"),
    path("manual_sync/", workorder_views.manual_sync_orders, name="manual_sync_orders"),
    path("manual_convert/", workorder_views.manual_convert_orders, name="manual_convert_orders"),
    path("selective_revert/", workorder_views.selective_revert_orders, name="selective_revert_orders"),
    # path("import_historical/", workorder_views.import_historical_workorders, name="import_historical_workorders"),  # 已移除
    # path("download_template/", workorder_views.download_historical_workorder_template, name="download_historical_workorder_template"),  # 已移除
    # 完工工單相關路由已移除
    
    # 報工管理功能（已遷移到類別視圖，保留向後相容路由）
    # path("report/operator/", workorder_views.operator_report_index, name="operator_report_index"),  # 已重複，使用類別視圖
    # path("report/smt/", workorder_views.smt_report_index, name="smt_report_index"),  # 已重複，使用類別視圖
    path("report/operator/supplement/approve/<int:report_id>/", workorder_views.operator_supplement_report_approve, name="operator_supplement_report_approve"),
    path("report/operator/supplement/reject/<int:report_id>/", workorder_views.operator_supplement_report_reject, name="operator_supplement_report_reject"),
    path("report/operator/supplement/batch/", workorder_views.operator_supplement_batch, name="operator_supplement_batch"),
    path("report/operator/supplement/export/", workorder_views.operator_supplement_export, name="operator_supplement_export"),
    path("report/operator/supplement/template/", workorder_views.operator_supplement_template, name="operator_supplement_template"),
    path("report/smt/supplement/approve/<int:report_id>/", workorder_views.smt_supplement_report_approve, name="smt_supplement_report_approve"),
    path("report/smt/supplement/reject/<int:report_id>/", workorder_views.smt_supplement_report_reject, name="smt_supplement_report_reject"),
    path("report/smt/supplement/batch/", workorder_views.smt_supplement_batch, name="smt_supplement_batch"),


    path("report/operator/on_site/", workorder_views.operator_on_site_report, name="operator_on_site_report"),
    path("report/smt/on_site/", workorder_views.smt_on_site_report, name="smt_on_site_report"),
    path("report/supervisor/", workorder_views.supervisor_index, name="supervisor_index"),
    
    # 主管功能子模組路由
    path("supervisor/", include('workorder.supervisor.urls')),
    path("report/approved/", workorder_views.approved_reports_list, name="approved_reports_list"),
    
    # 作業員報工資料匯入功能
    path("import/operator_report/", import_views.operator_report_import_page, name="operator_report_import_page"),
    path("import/operator_report/file/", import_views.operator_report_import_file, name="operator_report_import_file"),
    path("export/operator_report/", import_views.operator_report_export, name="operator_report_export"),
    path("import/operator_report/template/", import_views.download_import_template, name="download_import_template"),
    path("import/operator_report/field_guide/", import_views.get_import_field_guide, name="get_import_field_guide"),
    
    # SMT設備報工資料匯入功能
    path("import/smt_report/", import_views.smt_report_import_page, name="smt_report_import_page"),
    path("import/smt_report/file/", import_views.smt_report_import_file, name="smt_report_import_file"),
    path("import/smt_report/template/", import_views.download_smt_import_template, name="download_smt_import_template"),
    path("import/smt_report/field_guide/", import_views.get_smt_import_field_guide, name="get_smt_import_field_guide"),
    path("import/smt_report/export/", import_views.smt_report_export, name="smt_report_export"),
    


    path("process/create/<int:workorder_id>/", workorder_views.create_workorder_processes, name="create_workorder_processes"),
    path("process/logs/<int:process_id>/", workorder_views.process_logs, name="process_logs"),
    path("process/move/", workorder_views.move_process, name="move_process"),
    path("process/add/<int:workorder_id>/", workorder_views.add_process, name="add_process"),
    path("process/edit/<int:process_id>/", workorder_views.edit_process, name="edit_process"),
    path("process/delete/<int:process_id>/", workorder_views.delete_process, name="delete_process"),
    path("process/batch_approve_supplements/", workorder_views.batch_approve_supplements, name="batch_approve_supplements"),
    path("process/batch_approve_pending/", workorder_views.batch_approve_pending, name="batch_approve_pending"),
    path("process/quick_approve/<int:workorder_id>/", workorder_views.quick_approve_workorder, name="quick_approve_workorder"),
    path("process/statistics/", workorder_views.supplement_statistics, name="supplement_statistics"),
    path("process/capacity/<int:process_id>/", workorder_views.get_process_capacity_info, name="get_process_capacity_info"),
    path("process/capacity/update/<int:process_id>/", workorder_views.update_process_capacity, name="update_process_capacity"),
    path("process/capacity/calculation/<int:process_id>/", workorder_views.get_capacity_calculation_info, name="get_capacity_calculation_info"),
    path("process/status/update/<int:process_id>/", workorder_views.update_process_status, name="update_process_status"),
    path("test_report/", workorder_views.test_report_page, name="test_report_page"),
    path("supervisor_report/", workorder_views.supervisor_report_index, name="supervisor_report_index"),
    # 這些功能已遷移到主管功能子模組，保留向後相容的路由
    path("supervisor_functions/", supervisor_views.supervisor_functions, name="supervisor_functions"),
    path("report_statistics/", supervisor_views.report_statistics, name="report_statistics"),
    path("abnormal_management/", supervisor_views.abnormal_management, name="abnormal_management"),
    path("batch_resolve_abnormal/", workorder_views.batch_resolve_abnormal, name="batch_resolve_abnormal"),
    path("abnormal_detail/<str:abnormal_type>/<int:abnormal_id>/", supervisor_views.abnormal_detail, name="abnormal_detail"),
    path("data_maintenance/", supervisor_views.data_maintenance, name="data_maintenance"),
    path("execute_maintenance/", supervisor_views.execute_maintenance, name="execute_maintenance"),
    path("submit_smt_report/", workorder_views.submit_smt_report, name="submit_smt_report"),
    path("user_supplement_form/<int:workorder_id>/", workorder_views.user_supplement_form, name="user_supplement_form"),
    path("edit_my_supplement/<int:supplement_id>/", workorder_views.edit_my_supplement, name="edit_my_supplement"),
    path("delete_my_supplement/<int:supplement_id>/", workorder_views.delete_my_supplement, name="delete_my_supplement"),
    path("edit_supplement_mobile/", workorder_views.edit_supplement_mobile, name="edit_supplement_mobile"),
    path("pending_approval/", workorder_views.pending_approval_list, name="pending_approval_list"),
    path("approved_reports/", workorder_views.approved_reports_list, name="approved_reports_list"),
    path("get_operators_and_equipments/", workorder_views.get_operators_and_equipments, name="get_operators_and_equipments"),
    path("get_operators_only/", workorder_views.get_operators_only, name="get_operators_only"),
    path("get_equipments_only/", workorder_views.get_equipments_only, name="get_equipments_only"),
    path("mobile_quick_supplement/", workorder_views.mobile_quick_supplement_index, name="mobile_quick_supplement_index"),
    path("mobile_quick_supplement_form/<int:workorder_id>/", workorder_views.mobile_quick_supplement_form, name="mobile_quick_supplement_form"),
    path("mobile_get_workorder_info/", workorder_views.mobile_get_workorder_info, name="mobile_get_workorder_info"),
    path("mobile_get_process_info/", workorder_views.mobile_get_process_info, name="mobile_get_process_info"),
    path("mobile_submit_supplement/", workorder_views.mobile_submit_supplement, name="mobile_submit_supplement"),
    path("mobile_api_test/", workorder_views.mobile_api_test, name="mobile_api_test"),
    path("quick_get_product_codes/", workorder_views.quick_get_product_codes, name="quick_get_product_codes"),
    path("get_product_codes/", workorder_views.get_product_codes, name="get_product_codes"),
    path("supervisor_approve_reports/", workorder_views.supervisor_approve_reports, name="supervisor_approve_reports"),
    path("api_get_operator_reports/", workorder_views.api_get_operator_reports, name="api_get_operator_reports"),
    path("api_get_smt_reports/", workorder_views.api_get_smt_reports, name="api_get_smt_reports"),
    path("export_operator_reports/", workorder_views.export_operator_reports, name="export_operator_reports"),

    path("operator_supplement_batch_create/", workorder_views.operator_supplement_batch_create, name="operator_supplement_batch_create"),
    path("smt_supplement_batch_create/", workorder_views.smt_supplement_batch_create, name="smt_supplement_batch_create"),
    path("supervisor_index/", workorder_views.supervisor_index, name="supervisor_index"),
    path("get_workorders_by_operator/", workorder_views.get_workorders_by_operator, name="get_workorders_by_operator"),
    path("get_processes_by_workorder_for_operator/", workorder_views.get_processes_by_workorder_for_operator, name="get_processes_by_workorder_for_operator"),
    path("submit_operator_report/", workorder_views.submit_operator_report, name="submit_operator_report"),
    path("get_smt_workorders_by_equipment/", workorder_views.get_smt_workorders_by_equipment, name="get_smt_workorders_by_equipment"),
    path("get_workorders_by_product/", workorder_views.get_workorders_by_product, name="get_workorders_by_product"),
    path("get_workorder_details/", workorder_views.get_workorder_details, name="get_workorder_details"),
    path("get_product_by_workorder/", workorder_views.get_product_by_workorder, name="get_product_by_workorder"),
    path("get_product_codes_for_autocomplete/", workorder_views.get_product_codes_for_autocomplete, name="get_product_codes_for_autocomplete"),
    path("get_workorder_info/", workorder_views.get_workorder_info, name="get_workorder_info"),

    # 自動分配管理相關 URL
    path("auto_allocation/status/", auto_allocation_status, name="auto_allocation_status"),
    path("auto_allocation/settings/", auto_allocation_settings, name="auto_allocation_settings"),
    path("auto_allocation/execute/", auto_allocation_execute, name="auto_allocation_execute"),
    path("auto_allocation/stop/", auto_allocation_stop, name="auto_allocation_stop"),
    path("auto_allocation/log/", auto_allocation_log, name="auto_allocation_log"),
    path("auto_allocation/summary/", auto_allocation_summary, name="auto_allocation_summary"),

    # 完工自動化管理相關 URL
    path("completion-automation/", CompletionAutomationManagementView.as_view(), name="completion_automation_management"),
    path("auto-management/execute/<str:function_type>/", execute_auto_function, name="execute_auto_function"),
    path("auto-management/toggle/<str:function_type>/", toggle_auto_function, name="toggle_auto_function"),
    
    # 自動管理功能相關 URL (保留原有功能)
    path("auto-management/", AutoManagementConfigListView.as_view(), name="auto_management_config_list"),
    path("auto-management/create/", AutoManagementConfigCreateView.as_view(), name="auto_management_config_create"),
    path("auto-management/edit/<int:pk>/", AutoManagementConfigUpdateView.as_view(), name="auto_management_config_update"),
    path("auto-management/delete/<int:pk>/", AutoManagementConfigDeleteView.as_view(), name="auto_management_config_delete"),

    # 已完工工單相關 URL
    # path('completed/', workorder_views.CompletedWorkOrderListView.as_view(), name='completed_workorder_list'), # This line is removed as per the edit hint
    # path('completed/<int:pk>/', workorder_views.CompletedWorkOrderDetailView.as_view(), name='completed_workorder_detail'), # This line is removed as per the edit hint
    # path('completed/transfer/<int:workorder_id>/', workorder_views.transfer_workorder_to_completed, name='transfer_workorder_to_completed'), # This line is removed as per the edit hint
    # path('completed/batch-transfer/', workorder_views.batch_transfer_completed_workorders, name='batch_transfer_completed_workorders'), # This line is removed as per the edit hint
]
