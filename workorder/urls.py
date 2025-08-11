from django.urls import path, include
from django.views.generic import RedirectView
from . import views_main as workorder_views
from . import views_import as import_views
from .supervisor import views as supervisor_views
from .views.workorder_views import (
    WorkOrderListView, WorkOrderDetailView, WorkOrderCreateView, 
    WorkOrderUpdateView, WorkOrderDeleteView, CompanyOrderListView,
    get_company_order_info
)
from .views.report_views import (
    ReportIndexView, BackupReportIndexView, OperatorSupplementReportListView, OperatorSupplementReportCreateView,
    OperatorSupplementReportUpdateView, OperatorSupplementReportDetailView, 
    OperatorSupplementReportDeleteView, SMTSupplementReportListView, SMTSupplementReportCreateView,
    SMTSupplementReportUpdateView, SMTSupplementReportDetailView, SMTSupplementReportDeleteView,
    SMTRDSampleSupplementReportCreateView, SMTRDSampleSupplementReportUpdateView,
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
    path("process/<int:workorder_id>/", workorder_views.workorder_process_detail, name="workorder_process_detail"),
    path("delete-in-progress/", workorder_views.delete_in_progress_workorders, name="delete_in_progress_workorders"),
    path("start-production/<int:pk>/", workorder_views.start_production, name="start_production"),
    path("stop-production/<int:pk>/", workorder_views.stop_production, name="stop_production"),
    path("manual-sync-orders/", workorder_views.manual_sync_orders, name="manual_sync_orders"),
    path("manual-convert-orders/", workorder_views.manual_convert_orders, name="manual_convert_orders"),
    path("selective-revert-orders/", workorder_views.selective_revert_orders, name="selective_revert_orders"),
    path("delete-pending-workorders/", workorder_views.delete_pending_workorders, name="delete_pending_workorders"),
    
    # 完工自動化管理
    path("completion-automation/", CompletionAutomationManagementView.as_view(), name="completion_automation_management"),
    
    # 自動管理功能設定
    path("auto-management/", AutoManagementConfigListView.as_view(), name="auto_management_config_list"),
    path("auto-management/create/", AutoManagementConfigCreateView.as_view(), name="auto_management_config_create"),
    path("auto-management/edit/<int:pk>/", AutoManagementConfigUpdateView.as_view(), name="auto_management_config_update"),
    path("auto-management/delete/<int:pk>/", AutoManagementConfigDeleteView.as_view(), name="auto_management_config_delete"),
    path("api/auto-management/execute/", execute_auto_function, name="execute_auto_function"),
    path("api/auto-management/toggle/", toggle_auto_function, name="toggle_auto_function"),
    
    # 自動分配 API 路由
    path("api/auto-allocation/status/", auto_allocation_status, name="auto_allocation_status"),
    path("api/auto-allocation/settings/", auto_allocation_settings, name="auto_allocation_settings"),
    path("api/auto-allocation/execute/", auto_allocation_execute, name="auto_allocation_execute"),
    path("api/auto-allocation/stop/", auto_allocation_stop, name="auto_allocation_stop"),
    path("api/auto-allocation/log/", auto_allocation_log, name="auto_allocation_log"),
    path("api/auto-allocation/summary/", auto_allocation_summary, name="auto_allocation_summary"),
    
    # 已完工工單相關 URL
    path('completed/', CompletedWorkOrderListView.as_view(), name='completed_workorder_list'),
    path('completed/<int:pk>/', CompletedWorkOrderDetailView.as_view(), name='completed_workorder_detail'),
    path('completed/transfer/<int:workorder_id>/', transfer_workorder_to_completed, name='transfer_workorder_to_completed'),
    path('completed/batch-transfer/', batch_transfer_completed_workorders, name='batch_transfer_completed_workorders'),
    
    # 公司製令單管理 - 使用類別視圖
    path("company/", CompanyOrderListView.as_view(), name="company_orders"),
    
    # API 路由
    path("api/company_order_info/", get_company_order_info, name="get_company_order_info"),
    path("api/get_workorders_by_product/", workorder_views.get_workorders_by_product, name="get_workorders_by_product"),
    path("api/get_product_by_workorder/", workorder_views.get_product_by_workorder, name="get_product_by_workorder"),
    path("api/create_workorder_processes/<int:workorder_id>/", workorder_views.create_workorder_processes, name="create_workorder_processes"),
    path("api/get_operators_and_equipments/", workorder_views.get_operators_and_equipments, name="get_operators_and_equipments"),
    path("api/get_operators_only/", workorder_views.get_operators_only, name="get_operators_only"),
    path("api/get_equipments_only/", workorder_views.get_equipments_only, name="get_equipments_only"),
    path("api/add_process/<int:workorder_id>/", workorder_views.add_process, name="add_process"),
    path("api/move_process/", workorder_views.move_process, name="move_process"),
    
    # 工序 API 路由
    path("api/process/<int:process_id>/", api_views.get_process_detail, name="get_process_detail"),
    path("api/process/<int:process_id>/edit/", api_views.edit_process, name="edit_process"),
    path("api/process/<int:process_id>/delete/", api_views.delete_process, name="delete_process"),
    
    # 舊路徑導向新路徑（填報作業主索引）
    path("report/", RedirectView.as_view(url="/workorder/fill_work/", permanent=True)),
    
    # 填報作業管理首頁
    path("fill_work/", include('workorder.fill_work.urls')),
    
    # 備用報工管理首頁（保留向後相容）
    path("backup_report/", BackupReportIndexView.as_view(), name="backup_report_index"),
    
    # 作業員補登報工功能（備用）
    path("backup_report/operator/supplement/", OperatorSupplementReportListView.as_view(), name="operator_supplement_report_index"),
    path("backup_report/operator/supplement/create/", OperatorSupplementReportCreateView.as_view(), name="operator_supplement_report_create"),
    path("backup_report/operator/supplement/edit/<int:pk>/", OperatorSupplementReportUpdateView.as_view(), name="operator_supplement_report_edit"),
    path("backup_report/operator/supplement/detail/<int:pk>/", OperatorSupplementReportDetailView.as_view(), name="operator_supplement_report_detail"),
    path("backup_report/operator/supplement/delete/<int:pk>/", OperatorSupplementReportDeleteView.as_view(), name="operator_supplement_report_delete"),
    
    # 作業員RD樣品補登報工（備用）
    path("backup_report/operator/rd_sample_supplement/create/", OperatorRDSampleSupplementReportCreateView.as_view(), name="operator_rd_sample_supplement_create"),
    
    # 作業員補登報工批量匯入（備用）
    path("backup_report/operator/supplement/batch/", import_views.operator_report_import_page, name="operator_supplement_batch"),
    path("backup_report/operator/supplement/batch/file/", import_views.operator_report_import_file, name="operator_supplement_batch_file"),
    path("backup_report/operator/supplement/batch/template/", import_views.download_import_template, name="operator_supplement_batch_template"),
    path("backup_report/operator/supplement/batch/export/", import_views.operator_report_export, name="operator_supplement_batch_export"),
    
    # SMT 補登報工（備用）
    path("backup_report/smt/supplement/", SMTSupplementReportListView.as_view(), name="smt_supplement_report_index"),
    path("backup_report/smt/supplement/create/", SMTSupplementReportCreateView.as_view(), name="smt_supplement_report_create"),
    path("backup_report/smt/supplement/edit/<int:pk>/", SMTSupplementReportUpdateView.as_view(), name="smt_supplement_report_edit"),
    path("backup_report/smt/supplement/delete/<int:pk>/", SMTSupplementReportDeleteView.as_view(), name="smt_supplement_report_delete"),
    path("backup_report/smt/supplement/detail/<int:pk>/", SMTSupplementReportDetailView.as_view(), name="smt_supplement_report_detail"),
    
    # SMT RD 樣品（備用）
    path("backup_report/smt/rd_sample/create/", SMTRDSampleSupplementReportCreateView.as_view(), name="smt_rd_sample_report_create"),
    path("backup_report/smt/rd_sample/edit/<int:pk>/", SMTRDSampleSupplementReportUpdateView.as_view(), name="smt_rd_sample_report_edit"),
    
    # 報工核准/駁回（備用）
    path("backup_report/approve/<int:report_id>/", approve_report, name="approve_report"),
    path("backup_report/reject/<int:report_id>/", reject_report, name="reject_report"),
    
    # 舊函式式視圖向後相容（備用路徑）
    path("backup_report/operator/supplement/approve/<int:report_id>/", workorder_views.operator_supplement_report_approve, name="operator_supplement_report_approve"),
    path("backup_report/operator/supplement/reject/<int:report_id>/", workorder_views.operator_supplement_report_reject, name="operator_supplement_report_reject"),
    path("backup_report/operator/supplement/batch/", workorder_views.operator_supplement_batch, name="operator_supplement_batch"),
    path("backup_report/operator/supplement/export/", workorder_views.operator_supplement_export, name="operator_supplement_export"),
    path("backup_report/operator/supplement/template/", workorder_views.operator_supplement_template, name="operator_supplement_template"),
    path("backup_report/smt/supplement/approve/<int:report_id>/", workorder_views.smt_supplement_report_approve, name="smt_supplement_report_approve"),
    path("backup_report/smt/supplement/reject/<int:report_id>/", workorder_views.smt_supplement_report_reject, name="smt_supplement_report_reject"),
    path("backup_report/smt/supplement/batch/", workorder_views.smt_supplement_batch, name="smt_supplement_batch"),

    # 備用：即時報工與主管頁
    path("backup_report/operator/on_site/", workorder_views.operator_on_site_report, name="operator_on_site_report"),
    path("backup_report/smt/on_site/", workorder_views.smt_on_site_report, name="smt_on_site_report"),
    path("backup_report/supervisor/", workorder_views.supervisor_index, name="supervisor_index"),

    # 主管功能子模組（原路徑保留）
    path("supervisor/", include('workorder.supervisor.urls')),
    path("backup_report/approved/", workorder_views.approved_reports_list, name="approved_reports_list"),
    
    # 系統維護：清除數據（管理員專用）
    path("clear-data/", workorder_views.clear_data, name="clear_data"),
    
    # 系統維護：清除所有報工紀錄（管理員專用）
    path("clear-all-production-reports/", workorder_views.clear_all_production_reports, name="clear_all_production_reports"),
    
    # 派工單子模組
    path("dispatch/", include(("workorder.workorder_dispatch.urls", "workorder_dispatch"), namespace="workorder_dispatch")),
    
    # 報工管理子模組（已移除新的報工管理系統）
    # path("work-reporting/", include("work_reporting_management.urls", namespace="work_reporting_management")),
    
    # 其他功能保留
    path("import/operator_report/", import_views.operator_report_import_page, name="operator_report_import_page"),
    path("import/operator_report/file/", import_views.operator_report_import_file, name="operator_report_import_file"),
    path("export/operator_report/", import_views.operator_report_export, name="operator_report_export"),
    path("import/operator_report/template/", import_views.download_import_template, name="download_import_template"),
    path("import/operator_report/field_guide/", import_views.get_import_field_guide, name="get_import_field_guide"),
    
    path("import/smt_report/", import_views.smt_report_import_page, name="smt_report_import_page"),
    path("import/smt_report/file/", import_views.smt_report_import_file, name="smt_report_import_file"),
    path("import/smt_report/template/", import_views.download_smt_import_template, name="download_smt_import_template"),
    path("import/smt_report/field_guide/", import_views.get_smt_import_field_guide, name="get_smt_import_field_guide"),
    path("import/smt_report/export/", import_views.smt_report_export, name="smt_report_export"),
    
    # 其餘路由維持不變...
]
