from django.urls import path
from . import views

app_name = "kanban"
module_display_name = "看板功能"

urlpatterns = [
    path("", views.index, name="index"),
    path("production_progress/", views.production_progress, name="production_progress"),
    path("equipment_status/", views.equipment_status, name="equipment_status"),
    path("quality_monitoring/", views.quality_monitoring, name="quality_monitoring"),
    path("material_stock/", views.material_stock, name="material_stock"),
    path("delivery_schedule/", views.delivery_schedule, name="delivery_schedule"),
    path(
        "api/production_progress/",
        views.get_production_progress,
        name="get_production_progress",
    ),
    path(
        "api/equipment_status/", views.get_equipment_status, name="get_equipment_status"
    ),
    path(
        "api/quality_monitoring/",
        views.get_quality_monitoring,
        name="get_quality_monitoring",
    ),
    path("api/material_stock/", views.get_material_stock, name="get_material_stock"),
    path(
        "api/delivery_schedule/",
        views.get_delivery_schedule,
        name="get_delivery_schedule",
    ),
    path(
        "schedule_warning_board/",
        views.schedule_warning_board,
        name="schedule_warning_board",
    ),
]
