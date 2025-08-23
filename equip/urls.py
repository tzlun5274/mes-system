from django.urls import path
from . import views

app_name = "equip"
module_display_name = "設備管理"

urlpatterns = [
    path("", views.index, name="index"),
    path("add/", views.add_equipment, name="add_equipment"),
    path("<int:equipment_id>/", views.equipment_detail, name="equipment_detail"),
    path("export/", views.export_equipment, name="export_equipment"),
    path("import/", views.import_equipment, name="import_equipment"),
    path("<int:equipment_id>/edit/", views.edit_equipment, name="edit_equipment"),
    path("<int:equipment_id>/delete/", views.delete_equipment, name="delete_equipment"),
    path(
        "api/equipments/", views.get_equipments, name="get_equipments"
    ),  # 添加 API 路由
]
