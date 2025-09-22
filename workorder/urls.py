from django.urls import path, include
from django.views.generic import RedirectView
from . import views, api as workorder_views
from . import views, views_import as import_views
from . import views_main
from .supervisor import views as supervisor_views
from .views.workorder_views import (
    WorkOrderListView, WorkOrderDetailView, WorkOrderCreateView, 
    WorkOrderUpdateView, WorkOrderDeleteView, ManufacturingOrderListView,
    get_manufacturing_order_info, MesOrderListView, unified_dispatch,
    mes_order_delete, mes_orders_set_auto_dispatch_interval, CreateMissingWorkOrdersView,
    update_dispatch_statistics
)


# 維護功能已移至 maintenance 模組
# from .views_main.workorder_clear_views import (
#     WorkOrderClearView, WorkOrderClearAjaxView
# )
# from .views_main.workorder_import_views import (
#     workorder_import_page, workorder_import_file, download_workorder_template
# )

from .views.completed_workorder_views import (
    CompletedWorkOrderListView, CompletedWorkOrderDetailView,
    transfer_workorder_to_completed, batch_transfer_completed_workorders
)
from .views.rollback_views import (
    WorkOrderRollbackConfirmView, rollback_completed_workorder,
    batch_rollback_completed_workorders, check_rollback_status
)
from .views import api_views
# 自動分配功能已移除
# 完工自動化管理功能已簡化，移除複雜的視圖
# from .views_main.completion_automation_views import (
#     CompletionAutomationManagementView,
#     AutoManagementConfigListView, AutoManagementConfigCreateView,
#     AutoManagementConfigUpdateView, AutoManagementConfigDeleteView,
#     execute_auto_function, toggle_auto_function
# )
# 相符性檢查功能已移至 maintenance 模組
# from .views_main.consistency_check_views import (
#     ConsistencyCheckHomeView, ConsistencyCheckAjaxView, ConsistencyCheckDetailView,
#     ConsistencyCheckExportView, ConsistencyCheckFixView
# )


app_name = "workorder"
module_display_name = "工單管理"

urlpatterns = [
    # 工單管理基本功能 - 使用新的類別視圖
    path("", WorkOrderListView.as_view(), name="index"),
    path("create/", WorkOrderCreateView.as_view(), name="create"),
    path("edit/<int:pk>/", WorkOrderUpdateView.as_view(), name="edit"),
    path("delete/<int:pk>/", WorkOrderDeleteView.as_view(), name="delete"),
    path("detail/<int:pk>/", WorkOrderDetailView.as_view(), name="production_workorder_detail"),
    path("update-statistics/<int:workorder_id>/", update_dispatch_statistics, name="update_dispatch_statistics"),
    path("force-complete/<int:pk>/", views_main.force_complete_workorder, name="force_complete_workorder"),
    path("auto-complete/<int:pk>/", views_main.auto_complete_workorder, name="auto_complete_workorder"),
    path("list/", WorkOrderListView.as_view(), name="list"),
    path("active/", views_main.active_workorders, name="active_workorders"),
    path("completion-check/", views_main.check_workorder_completion, name="completion_check"),
    path("process/<int:workorder_id>/", views_main.workorder_process_detail, name="workorder_process_detail"),
    path("delete-in-progress/", views_main.delete_in_progress_workorders, name="delete_in_progress_workorders"),
    path("start-production/<int:pk>/", views_main.start_production, name="start_production"),
    path("stop-production/<int:pk>/", views_main.stop_production, name="stop_production"),
    path("manual-sync-orders/", views_main.manual_sync_orders, name="manual_sync_orders"),
    path("manual-convert-orders/", views_main.manual_convert_orders, name="manual_convert_orders"),
    path("selective-revert-orders/", views_main.selective_revert_orders, name="selective_revert_orders"),
    path("delete-pending-workorders/", views_main.delete_pending_workorders, name="delete_pending_workorders"),


    

    
    # 工單清除功能已移至 maintenance 模組
    # path("clear-workorders/", WorkOrderClearView.as_view(), name="clear_workorders"),
    # path("clear-workorders-ajax/", WorkOrderClearAjaxView.as_view(), name="clear_workorders_ajax"),
    
    # Excel匯入工單功能已移至 maintenance 模組
    # path("import/", workorder_import_page, name="workorder_import"),
    # path("import/file/", workorder_import_file, name="workorder_import_file"),
    # path("import/template/", download_workorder_template, name="download_workorder_template"),
    
    # 完工自動化管理功能已簡化
    # path("completion-automation/", CompletionAutomationManagementView.as_view(), name="completion_automation_management"),
    
    # 相符性檢查功能已移至 maintenance 模組
    # path("consistency-check/", ConsistencyCheckHomeView.as_view(), name="consistency_check_home"),
    # path("consistency-check/ajax/", ConsistencyCheckAjaxView.as_view(), name="consistency_check_ajax"),
    # path("consistency-check/detail/", ConsistencyCheckDetailView.as_view(), name="consistency_check_detail"),
    # path("consistency-check/export/", ConsistencyCheckExportView.as_view(), name="consistency_check_export"),
    # path("consistency-check/fix/", ConsistencyCheckFixView.as_view(), name="consistency_check_fix"),
    
    # 自動管理功能設定已簡化
    # path("auto-management/", AutoManagementConfigListView.as_view(), name="auto_management_config_list"),
    # path("auto-management/create/", AutoManagementConfigCreateView.as_view(), name="auto_management_config_create"),
    # path("auto-management/edit/<int:pk>/", AutoManagementConfigUpdateView.as_view(), name="auto_management_config_update"),
    # path("auto-management/delete/<int:pk>/", AutoManagementConfigDeleteView.as_view(), name="auto_management_config_delete"),
    # path("static/api/auto-management/execute/", execute_auto_function, name="execute_auto_function"),
    # path("static/api/auto-management/toggle/", toggle_auto_function, name="toggle_auto_function"),
    
    # 自動分配功能已移除
    
    # 已完工工單相關 URL
    path('completed/', CompletedWorkOrderListView.as_view(), name='completed_workorder_list'),
    path('completed/<int:pk>/', CompletedWorkOrderDetailView.as_view(), name='completed_workorder_detail'),
    path('completed/transfer/<int:workorder_id>/', transfer_workorder_to_completed, name='transfer_workorder_to_completed'),
    path('completed/batch-transfer/', batch_transfer_completed_workorders, name='batch_transfer_completed_workorders'),
    
    # 工單回朔相關 URL
    path('rollback/<int:pk>/', WorkOrderRollbackConfirmView.as_view(), name='rollback_confirm'),
    path('rollback/<int:pk>/execute/', rollback_completed_workorder, name='rollback_execute'),
    path('rollback/batch/', batch_rollback_completed_workorders, name='batch_rollback'),
    path('rollback/<int:pk>/check/', check_rollback_status, name='rollback_status_check'),
    
    # 公司製造命令管理 - 使用類別視圖
    path("manufacturing_orders/", ManufacturingOrderListView.as_view(), name="manufacturing_orders"),
    
    # 統一API路由 - 整合填報和現場報工的API
    path("static/api/workorder-list/", views_main.get_workorder_list_unified, name="workorder_list"),
    path("static/api/workorder-by-product/", views_main.get_workorder_by_product_unified, name="workorder_by_product"),
    path("static/api/workorder-detail/", views_main.get_workorder_detail_unified, name="workorder_detail"),
    path("static/api/workorder-data/", views_main.get_workorder_data_unified, name="workorder_data"),
    path("static/api/workorder-info/", views_main.get_workorder_info_unified, name="workorder_info"),
    path("static/api/product-list/", views_main.get_product_list_unified, name="product_list"),
    path("static/api/products-by-company/", views_main.get_products_by_company_unified, name="products_by_company"),
    path("static/api/company-list/", views_main.get_company_list_unified, name="company_list"),
    path("static/api/operator-list/", views_main.get_operator_list_unified, name="operator_list"),
    path("static/api/process-list/", views_main.get_process_list_unified, name="process_list"),
    path("static/api/equipment-list/", views_main.get_equipment_list_unified, name="equipment_list"),
    
    # 原有API路由（保留作為備用）
    path("static/api/manufacturing_order_info/", get_manufacturing_order_info, name="get_manufacturing_order_info"),
    path("static/api/get_workorders_by_product/", views_main.get_workorders_by_product, name="get_workorders_by_product"),
    path("static/api/get_product_by_workorder/", views_main.get_product_by_workorder, name="get_product_by_workorder"),
    path("static/api/create_workorder_processes/<int:workorder_id>/", views_main.create_workorder_processes, name="create_workorder_processes"),
    path("quick-create-processes/<int:workorder_id>/", views_main.quick_create_processes_from_route, name="quick_create_processes_from_route"),
    path("static/api/get_operators_and_equipments/", views_main.get_operators_and_equipments, name="get_operators_and_equipments"),
    path("static/api/get_operators_only/", views_main.get_operators_only, name="get_operators_only"),
    path("static/api/get_equipments_only/", views_main.get_equipments_only, name="get_equipments_only"),
    path("static/api/add_process/<int:workorder_id>/", views_main.add_process, name="add_process"),
    path("static/api/move_process/", views_main.move_process, name="move_process"),
    
    # 工序 API 路由
    path("static/api/process/<int:process_id>/", api_views.get_process_detail, name="get_process_detail"),
    path("static/api/process/<int:process_id>/edit/", api_views.edit_process, name="edit_process"),
    path("static/api/process/<int:process_id>/delete/", api_views.delete_process, name="delete_process"),
    
    # 舊路徑導向新路徑（填報作業主索引）
    path("report/", RedirectView.as_view(url="/workorder/fill_work/", permanent=True)),
    
    # 填報作業管理首頁
    path("fill_work/", include('workorder.fill_work.urls', namespace='fill_work')),
    
    # 現場報工管理子模組
    path("onsite_reporting/", include(('workorder.onsite_reporting.urls', 'onsite_reporting'))),
    
    # 主管功能子模組（原路徑保留）
    path("supervisor/", include('workorder.supervisor.urls')),
    

    

    
    # 派工單子模組
    path("dispatch/", include(('workorder.workorder_dispatch.urls', 'workorder_dispatch'))),
    
    # 系統維護功能子模組
    path("maintenance/", include(('workorder.maintenance.urls', 'maintenance'))),
    
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
    path("mes-orders/", MesOrderListView.as_view(), name="mes_orders"),
    path("mes-orders/dispatch/", unified_dispatch, name="unified_dispatch"),
    path("mes-orders/delete/", mes_order_delete, name="mes_order_delete"),
    path("mes-orders/convert-to-production/", views_main.mes_orders_convert_to_production, name="mes_orders_convert_to_production"),
    path("mes-orders/set-auto-dispatch-interval/", mes_orders_set_auto_dispatch_interval, name="mes_orders_set_auto_dispatch_interval"),


    
    # workorder API 路由
    path("api/workorder/", workorder_views.WorkOrderAPIView.as_view(), name="api_workorder_list"),
    path("api/workorder/<int:workorder_id>/", workorder_views.WorkOrderAPIView.as_view(), name="api_workorder_detail"),
    path("api/workorder-by-number/", workorder_views.get_workorder_by_number, name="api_workorder_by_number"),
    path("api/processes/", workorder_views.get_workorder_processes, name="api_workorder_processes"),
    path("api/workorders-by-status/", workorder_views.get_workorders_by_status, name="api_workorders_by_status"),
]
