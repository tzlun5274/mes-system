from django.urls import path
from . import views

app_name = "workorder"

urlpatterns = [
    # 工單管理基本功能
    path("", views.index, name="index"),
    path("create/", views.create, name="create"),
    path("edit/<int:pk>/", views.edit, name="edit"),
    path("delete/<int:pk>/", views.delete, name="delete"),
    path("detail/<int:pk>/", views.detail, name="detail"),
    path("list/", views.list_view, name="list"),
    
    # 派工單管理
    path("dispatch/", views.dispatch_list, name="dispatch_list"),
    
    # 完工工單管理
    path("completed/", views.completed_workorders, name="completed_workorders"),
    
    # 公司製令單管理
    path("company/", views.company_orders, name="company_orders"),
    
    # 清除數據功能
    path("clear/", views.clear_data, name="clear_data"),
    path("clear_reports/", views.clear_all_production_reports, name="clear_all_production_reports"),
    path("clear_completed/", views.clear_completed_workorders, name="clear_completed_workorders"),
    
    # 工單工序詳情
    path("process/<int:workorder_id>/", views.workorder_process_detail, name="workorder_process_detail"),
    
    # 工單操作功能
    path("start_production/<int:pk>/", views.start_production, name="start_production"),
    path("stop_production/<int:pk>/", views.stop_production, name="stop_production"),
    path("delete_pending/", views.delete_pending_workorders, name="delete_pending_workorders"),
    path("delete_in_progress/", views.delete_in_progress_workorders, name="delete_in_progress_workorders"),
    
    # 公司製令單操作
    path("manual_sync/", views.manual_sync_orders, name="manual_sync_orders"),
    path("manual_convert/", views.manual_convert_orders, name="manual_convert_orders"),
    path("selective_revert/", views.selective_revert_orders, name="selective_revert_orders"),
    
    # 歷史工單管理
    path("import_historical/", views.import_historical_workorders, name="import_historical_workorders"),
    path("download_template/", views.download_historical_workorder_template, name="download_historical_workorder_template"),
    
    # API 路由
    path("api/company_order_info/", views.get_company_order_info, name="get_company_order_info"),
    
    # 報工管理首頁
    path("report/", views.report_index, name="report_index"),
    
    # 作業員報工功能
    path("report/operator/", views.operator_report_index, name="operator_report_index"),
    path("report/smt/", views.smt_report_index, name="smt_report_index"),
    
    # 作業員補登報工功能
    path("report/operator/supplement/", views.operator_supplement_report_index, name="operator_supplement_report_index"),
    path("report/operator/supplement/create/", views.operator_supplement_report_create, name="operator_supplement_report_create"),
    path("report/operator/supplement/edit/<int:report_id>/", views.operator_supplement_report_edit, name="operator_supplement_report_edit"),
    path("report/operator/supplement/delete/<int:report_id>/", views.operator_supplement_report_delete, name="operator_supplement_report_delete"),
    path("report/operator/supplement/detail/<int:report_id>/", views.operator_supplement_report_detail, name="operator_supplement_report_detail"),
    path("report/operator/supplement/approve/<int:report_id>/", views.operator_supplement_report_approve, name="operator_supplement_report_approve"),
    path("report/operator/supplement/reject/<int:report_id>/", views.operator_supplement_report_reject, name="operator_supplement_report_reject"),
    path("report/operator/supplement/batch/", views.operator_supplement_batch, name="operator_supplement_batch"),
    path("report/operator/supplement/export/", views.operator_supplement_export, name="operator_supplement_export"),
    path("report/operator/supplement/template/", views.operator_supplement_template, name="operator_supplement_template"),
    
    # SMT補登報工功能
    path("report/smt/supplement/", views.smt_supplement_report_index, name="smt_supplement_report_index"),
    path("report/smt/supplement/create/", views.smt_supplement_report_create, name="smt_supplement_report_create"),
    path("report/smt/supplement/edit/<int:report_id>/", views.smt_supplement_report_edit, name="smt_supplement_report_edit"),
    path("report/smt/supplement/delete/<int:report_id>/", views.smt_supplement_report_delete, name="smt_supplement_report_delete"),
    path("report/smt/supplement/detail/<int:report_id>/", views.smt_supplement_report_detail, name="smt_supplement_report_detail"),
    path("report/smt/supplement/approve/<int:report_id>/", views.smt_supplement_report_approve, name="smt_supplement_report_approve"),
    path("report/smt/supplement/reject/<int:report_id>/", views.smt_supplement_report_reject, name="smt_supplement_report_reject"),
    path("report/smt/supplement/batch/", views.smt_supplement_batch, name="smt_supplement_batch"),
    path("report/smt/supplement/export/", views.smt_supplement_export, name="smt_supplement_export"),
    path("report/smt/supplement/template/", views.smt_supplement_template, name="smt_supplement_template"),
    
    # 作業員現場報工功能
    path("report/operator/on_site/", views.operator_on_site_report, name="operator_on_site_report"),
    
    # SMT現場報工功能
    path("report/smt/on_site/", views.smt_on_site_report, name="smt_on_site_report"),
    
    # 主管功能
    path("report/supervisor/", views.supervisor_index, name="supervisor_index"),
    path("report/supervisor/functions/", views.supervisor_functions, name="supervisor_functions"),
    path("report/supervisor/reports/", views.supervisor_report_index, name="supervisor_report_index"),
    path("report/statistics/", views.report_statistics, name="report_statistics"),
    path("report/approved/", views.approved_reports_list, name="approved_reports_list"),
    
    # 工序管理
    path("process/create/<int:workorder_id>/", views.create_workorder_processes, name="create_workorder_processes"),
    path("process/logs/<int:process_id>/", views.process_logs, name="process_logs"),
    
    # API 路由
    path("api/operator/supplement/batch_create/", views.operator_supplement_batch_create, name="operator_supplement_batch_create"),
    path("api/smt/supplement/batch_create/", views.smt_supplement_batch_create, name="smt_supplement_batch_create"),
    path("api/operator/get_workorders_by_operator/", views.get_workorders_by_operator, name="get_workorders_by_operator"),
    path("api/operator/get_processes_by_workorder/", views.get_processes_by_workorder_for_operator, name="get_processes_by_workorder_for_operator"),
    path("api/operator/submit_report/", views.submit_operator_report, name="submit_operator_report"),
    path("api/smt/get_workorders_by_equipment/", views.get_smt_workorders_by_equipment, name="get_smt_workorders_by_equipment"),
    path("api/get_workorders_by_product/", views.get_workorders_by_product, name="get_workorders_by_product"),
    path("api/get_workorder_details/", views.get_workorder_details, name="get_workorder_details"),
    path("api/operator/get_workorder_info/", views.get_workorder_info, name="get_workorder_info"),
    path("api/operators_equipments/", views.get_operators_and_equipments, name="get_operators_and_equipments"),
    path("api/operators/", views.get_operators_only, name="get_operators_only"),
    path("api/equipments/", views.get_equipments_only, name="get_equipments_only"),
    path("api/processes/", views.get_processes_only, name="get_processes_only"),
    path("api/product_codes/", views.get_product_codes, name="get_product_codes"),
    path("api/quick_product_codes/", views.quick_get_product_codes, name="quick_get_product_codes"),
    path("api/operator_reports/", views.api_get_operator_reports, name="api_get_operator_reports"),
    path("api/smt_reports/", views.api_get_smt_reports, name="api_get_smt_reports"),
    path("api/export_operator_reports/", views.export_operator_reports, name="export_operator_reports"),
    path("api/export_smt_reports/", views.export_smt_reports, name="export_smt_reports"),
    path("api/supplement_statistics/", views.supplement_statistics, name="supplement_statistics"),
    path("api/capacity_info/<int:process_id>/", views.get_process_capacity_info, name="get_process_capacity_info"),
    path("api/update_capacity/<int:process_id>/", views.update_process_capacity, name="update_process_capacity"),
    path("api/capacity_calculation/<int:process_id>/", views.get_capacity_calculation_info, name="get_capacity_calculation_info"),
    path("api/update_status/<int:process_id>/", views.update_process_status, name="update_process_status"),
    path("api/move_process/", views.move_process, name="move_process"),
    path("api/add_process/<int:workorder_id>/", views.add_process, name="add_process"),
    path("api/edit_process/<int:process_id>/", views.edit_process, name="edit_process"),
    path("api/delete_process/<int:process_id>/", views.delete_process, name="delete_process"),
    path("api/batch_approve_supplements/", views.batch_approve_supplements, name="batch_approve_supplements"),
    path("api/batch_approve_pending/", views.batch_approve_pending, name="batch_approve_pending"),
    path("api/quick_approve_workorder/<int:workorder_id>/", views.quick_approve_workorder, name="quick_approve_workorder"),
    path("api/submit_smt_report/", views.submit_smt_report, name="submit_smt_report"),
    path("api/supervisor_approve_reports/", views.supervisor_approve_reports, name="supervisor_approve_reports"),
    path("api/approve_report/<int:report_id>/", views.approve_report, name="approve_report"),
    path("api/reject_report/<int:report_id>/", views.reject_report, name="reject_report"),
    path("api/batch_resolve_abnormal/", views.batch_resolve_abnormal, name="batch_resolve_abnormal"),
    path("api/execute_maintenance/", views.execute_maintenance, name="execute_maintenance"),
    
    # 異常管理
    path("abnormal/", views.abnormal_management, name="abnormal_management"),
    path("abnormal/<str:abnormal_type>/<int:abnormal_id>/", views.abnormal_detail, name="abnormal_detail"),
    
    # 數據維護
    path("data_maintenance/", views.data_maintenance, name="data_maintenance"),
    
    # 測試頁面
    path("test_report/", views.test_report_page, name="test_report_page"),
    
    # 用戶補登功能
    path("user_supplement/<int:workorder_id>/", views.user_supplement_form, name="user_supplement_form"),
    path("edit_my_supplement/<int:supplement_id>/", views.edit_my_supplement, name="edit_my_supplement"),
    path("delete_my_supplement/<int:supplement_id>/", views.delete_my_supplement, name="delete_my_supplement"),
    
    # 待審核列表
    path("pending_approval/", views.pending_approval_list, name="pending_approval_list"),
    
    # 移動端功能
    path("mobile/quick_supplement/", views.mobile_quick_supplement_index, name="mobile_quick_supplement_index"),
    path("mobile/quick_supplement/<int:workorder_id>/", views.mobile_quick_supplement_form, name="mobile_quick_supplement_form"),
    path("mobile/edit_supplement/", views.edit_supplement_mobile, name="edit_supplement_mobile"),
    path("mobile/api_test/", views.mobile_api_test, name="mobile_api_test"),
    path("mobile/get_workorder_info/", views.mobile_get_workorder_info, name="mobile_get_workorder_info"),
    path("mobile/get_process_info/", views.mobile_get_process_info, name="mobile_get_process_info"),
    path("mobile/submit_supplement/", views.mobile_submit_supplement, name="mobile_submit_supplement"),
]
