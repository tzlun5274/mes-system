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
    
    # 完工自動化管理
    path("completion-automation/", CompletionAutomationManagementView.as_view(), name="completion_automation_management"),
    
    # 自動管理功能設定
    path("auto-management/", AutoManagementConfigListView.as_view(), name="auto_management_config_list"),
    
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
    
    # 舊路徑導向新路徑（報工主索引）
    path("report/", RedirectView.as_view(url="/workorder/backup_report/", permanent=True)),
    
    # 備用報工管理首頁
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
