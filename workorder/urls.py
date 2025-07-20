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
        "clear_completed_workorders/",
        views.clear_completed_workorders,
        name="clear_completed_workorders",
    ),
    path("clear_data/", views.clear_data, name="clear_data"),
    path("get_processes_only/", views.get_processes_only, name="get_processes_only"),
    path('get_operators_and_equipments/', views.get_operators_and_equipments, name='get_operators_and_equipments'),
    path('get_operators_only/', views.get_operators_only, name='get_operators_only'),
    path('get_equipments_only/', views.get_equipments_only, name='get_equipments_only'),
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
    path("delete_process/<int:process_id>/", views.delete_process, name="delete_process"),

    # SMT設備報班功能


    path('get_process_capacity_info/<int:process_id>/', views.get_process_capacity_info, name='get_process_capacity_info'),
    path('update_process_capacity/<int:process_id>/', views.update_process_capacity, name='update_process_capacity'),
    path('get_capacity_calculation_info/<int:process_id>/', views.get_capacity_calculation_info, name='get_capacity_calculation_info'),
    path('update_process_status/<int:process_id>/', views.update_process_status, name='update_process_status'),
    
    # 報工管理功能
    path('report/', views.report_index, name='report_index'),
    path('report/manager/', views.manager_report_index, name='manager_report_index'),
    path('report/operator/', views.operator_report_index, name='operator_report_index'),
    path('report/smt/', views.smt_report_index, name='smt_report_index'),
    path('report/smt/on_site/', views.smt_on_site_report, name='smt_on_site_report'),
    path('report/smt/submit/', views.submit_smt_report, name='submit_smt_report'),
    path('api/get_workorders_by_equipment/', views.get_workorders_by_equipment, name='get_workorders_by_equipment'),
    
    # SMT補登報工功能
    path('report/smt/supplement/', views.smt_supplement_report_index, name='smt_supplement_report_index'),
    path('report/smt/supplement/create/', views.smt_supplement_report_create, name='smt_supplement_report_create'),
    path('report/smt/supplement/edit/<int:report_id>/', views.smt_supplement_report_edit, name='smt_supplement_report_edit'),
    path('report/smt/supplement/delete/<int:report_id>/', views.smt_supplement_report_delete, name='smt_supplement_report_delete'),
    path('report/smt/supplement/detail/<int:report_id>/', views.smt_supplement_report_detail, name='smt_supplement_report_detail'),
    path('report/smt/supplement/approve/<int:report_id>/', views.smt_supplement_report_approve, name='smt_supplement_report_approve'),
    path('report/smt/supplement/reject/<int:report_id>/', views.smt_supplement_report_reject, name='smt_supplement_report_reject'),
    path('api/smt/supplement/batch_create/', views.smt_supplement_batch_create, name='smt_supplement_batch_create'),
    path('api/smt/get_workorders_by_equipment/', views.get_smt_workorders_by_equipment, name='get_smt_workorders_by_equipment'),
    path('api/get_workorders_by_product/', views.get_workorders_by_product, name='get_workorders_by_product'),
    path('api/get_workorder_details/', views.get_workorder_details, name='get_workorder_details'),
]
