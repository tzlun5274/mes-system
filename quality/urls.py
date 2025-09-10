from django.urls import path
from . import views, api

app_name = "quality"
module_display_name = "品質管理"

urlpatterns = [
    path("", views.index, name="index"),
    path("inspection_items/", views.inspection_items, name="inspection_items"),
    path("inspection_records/", views.inspection_records, name="inspection_records"),
    path("defective_products/", views.defective_products, name="defective_products"),
    path("final_inspection/", views.final_inspection, name="final_inspection"),
    path("aoi_test_report/", views.aoi_test_report, name="aoi_test_report"),
    path(
        "api/inspection_items/", views.get_inspection_items, name="get_inspection_items"
    ),
    path(
        "api/inspection_records/",
        views.get_inspection_records,
        name="get_inspection_records",
    ),
    path(
        "api/defective_products/",
        views.get_defective_products,
        name="get_defective_products",
    ),
    path(
        "api/final_inspections/",
        views.get_final_inspections,
        name="get_final_inspections",
    ),
    path(
        "api/aoi_test_reports/", views.get_aoi_test_reports, name="get_aoi_test_reports"
    ),
    
    # quality API 路由
    path("api/inspection/", api.InspectionAPIView.as_view(), name="api_inspection_list"),
    path("api/inspection/<int:inspection_id>/", api.InspectionAPIView.as_view(), name="api_inspection_detail"),
    path("api/defects/", api.get_defects, name="api_defects"),
]
