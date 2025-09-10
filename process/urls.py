from django.urls import path
from . import views, api

app_name = "process"
module_display_name = "工序管理"

urlpatterns = [
    path("", views.index, name="index"),
    # 工序工藝名稱
    path("process_names/", views.process_names, name="process_names"),
    path("add_process_name/", views.add_process_name, name="add_process_name"),
    path(
        "edit_process_name/<int:name_id>/",
        views.edit_process_name,
        name="edit_process_name",
    ),
    path(
        "delete_process_name/<int:name_id>/",
        views.delete_process_name,
        name="delete_process_name",
    ),
    path(
        "export_process_names/", views.export_process_names, name="export_process_names"
    ),
    path(
        "import_process_names/", views.import_process_names, name="import_process_names"
    ),
    # 作業員與技能管理
    path("operators/", views.operators, name="operators"),
    path("add_operator/", views.add_operator, name="add_operator"),
    path("edit_operator/<int:operator_id>/", views.edit_operator, name="edit_operator"),
    path(
        "delete_operator/<int:operator_id>/",
        views.delete_operator,
        name="delete_operator",
    ),
    path("export_operators/", views.export_operators, name="export_operators"),
    path("import_operators/", views.import_operators, name="import_operators"),
    # 產品工藝路線
    path("product_routes/", views.product_routes, name="product_routes"),
    path("add_product_route/", views.add_product_route, name="add_product_route"),
    path(
        "view_product_route/<str:product_id>/",
        views.view_product_route,
        name="view_product_route",
    ),
    path(
        "edit_product_route/<str:product_id>/",
        views.edit_product_route,
        name="edit_product_route",
    ),
    path(
        "delete_product_route/<str:product_id>/",
        views.delete_product_route,
        name="delete_product_route",
    ),
    path(
        "export_product_routes/",
        views.export_product_routes,
        name="export_product_routes",
    ),
    path(
        "import_product_routes/",
        views.import_product_routes,
        name="import_product_routes",
    ),
    path(
        "force_delete_product_route/<str:product_id>/",
        views.force_delete_product_route,
        name="force_delete_product_route",
    ),
    # API 端點
    path("api/process_names/", views.api_process_names, name="api_process_names"),
    path("api/operators/", views.api_operators, name="api_operators"),
    path("api/product_routes/", views.api_product_routes, name="api_product_routes"),
    path(
        "api/calculate_capacity/",
        views.api_calculate_capacity,
        name="api_calculate_capacity",
    ),
    path(
        "standard_capacity/",
        views.standard_capacity_list,
        name="standard_capacity_list",
    ),
    path(
        "standard_capacity/create/",
        views.standard_capacity_create,
        name="standard_capacity_create",
    ),
    path(
        "standard_capacity/update/<int:pk>/",
        views.standard_capacity_update,
        name="standard_capacity_update",
    ),
    path(
        "standard_capacity/delete/<int:pk>/",
        views.standard_capacity_delete,
        name="standard_capacity_delete",
    ),
    path(
        "standard_capacity/delete_all/",
        views.standard_capacity_delete_all,
        name="standard_capacity_delete_all",
    ),
    path(
        "standard_capacity/export/",
        views.standard_capacity_export,
        name="standard_capacity_export",
    ),
    path(
        "standard_capacity/import/",
        views.standard_capacity_import,
        name="standard_capacity_import",
    ),
    path("capacity_calculator/", views.capacity_calculator, name="capacity_calculator"),
    
    # process API 路由
    path("api/process-name/", api.ProcessNameAPIView.as_view(), name="api_process_name_list"),
    path("api/process-name/<int:process_id>/", api.ProcessNameAPIView.as_view(), name="api_process_name_detail"),
    path("api/operator-skills/", api.get_operator_skills, name="api_operator_skills"),
    path("api/product-route/", api.get_product_process_route, name="api_product_process_route"),
    path("api/operation-logs/", api.get_process_operation_logs, name="api_process_operation_logs"),
    path("api/process-by-name/", api.get_process_by_name, name="api_process_by_name"),
    path("api/active-processes/", api.get_active_processes, name="api_active_processes"),
    path("api/skilled-operators/", api.get_skilled_operators, name="api_skilled_operators"),
]
