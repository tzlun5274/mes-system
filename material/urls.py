from django.urls import path
from . import views

app_name = "material"
module_display_name = "物料管理"

urlpatterns = [
    path("", views.index, name="index"),
    # 基本資料管理
    path("materials/", views.material_list, name="material_list"),
    path("products/", views.product_list, name="product_list"),
    # 物料需求計算
    path(
        "requirement_calculation/",
        views.material_requirement_calculation,
        name="requirement_calculation",
    ),
    # 缺料警告管理
    path("shortage_alerts/", views.shortage_alerts, name="shortage_alerts"),
    path(
        "shortage_alerts/<int:alert_id>/resolve/",
        views.resolve_shortage_alert,
        name="resolve_shortage_alert",
    ),
    # 物料供應計劃
    path("supply_plan/", views.supply_plan_list, name="supply_plan_list"),
    # 物料看板管理
    path("kanban/", views.kanban_list, name="kanban_list"),
    path(
        "kanban/<int:kanban_id>/update/",
        views.update_kanban_status,
        name="update_kanban_status",
    ),
    # 庫存管理功能
    path(
        "inventory_management/", views.inventory_management, name="inventory_management"
    ),
    path(
        "inventory_management/<int:inventory_id>/",
        views.inventory_detail,
        name="inventory_detail",
    ),
    path(
        "inventory_management/transaction/add/",
        views.add_inventory_transaction,
        name="add_inventory_transaction",
    ),
    # 物料需求估算功能
    path(
        "requirement_estimation/",
        views.requirement_estimation,
        name="requirement_estimation",
    ),
    path(
        "requirement_estimation/create/",
        views.create_requirement_estimation,
        name="create_requirement_estimation",
    ),
    path(
        "requirement_estimation/<int:estimation_id>/",
        views.estimation_detail,
        name="estimation_detail",
    ),
    # API 路由
    path(
        "api/inventory/<int:material_id>/",
        views.api_material_inventory,
        name="api_material_inventory",
    ),
    path("api/check_shortage/", views.api_check_shortage, name="api_check_shortage"),
    path(
        "api/inventory_status/", views.api_inventory_status, name="api_inventory_status"
    ),
    path(
        "api/requirement_estimation_summary/",
        views.api_requirement_estimation_summary,
        name="api_requirement_estimation_summary",
    ),
]
