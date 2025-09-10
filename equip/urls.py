from django.urls import path
from . import views, api

app_name = "equip"
module_display_name = "設備管理"

urlpatterns = [
    # 網頁視圖路由
    path("", views.index, name="index"),
    path("add/", views.add_equipment, name="add_equipment"),
    path("<int:equipment_id>/", views.equipment_detail, name="equipment_detail"),
    path("export/", views.export_equipment, name="export_equipment"),
    path("import/", views.import_equipment, name="import_equipment"),
    path("<int:equipment_id>/edit/", views.edit_equipment, name="edit_equipment"),
    path("<int:equipment_id>/delete/", views.delete_equipment, name="delete_equipment"),
    
    # API 路由
    path("api/equipment/", api.EquipmentAPIView.as_view(), name="api_equipment_list"),
    path("api/equipment/<int:equipment_id>/", api.EquipmentAPIView.as_view(), name="api_equipment_detail"),
    path("api/status/", api.get_equipment_status, name="api_equipment_status"),
    path("api/by-production-line/", api.get_equipment_by_production_line, name="api_equipment_by_line"),
    path("api/operation-logs/", api.get_equipment_operation_logs, name="api_equipment_logs"),
    
    # 舊版 API 路由（保持向後兼容）
    path("api/equipments/", views.get_equipments, name="get_equipments"),
]
