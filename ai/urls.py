from django.urls import path
from . import views, api

app_name = "ai"
module_display_name = "AI 功能"

urlpatterns = [
    path("", views.index, name="index"),
    path(
        "run/production_prediction/",
        views.run_production_prediction,
        name="run_production_prediction",
    ),
    path(
        "run/demand_prediction/",
        views.run_demand_prediction,
        name="run_demand_prediction",
    ),
    path(
        "run/quality_prediction/",
        views.run_quality_prediction,
        name="run_quality_prediction",
    ),
    path(
        "run/production_optimization/",
        views.run_production_optimization,
        name="run_production_optimization",
    ),
    path("run/auto_scheduling/", views.run_auto_scheduling, name="run_auto_scheduling"),
    path(
        "run/production_anomaly_detection/",
        views.run_production_anomaly_detection,
        name="run_production_anomaly_detection",
    ),
    path(
        "run/defect_detection/", views.run_defect_detection, name="run_defect_detection"
    ),
    path("api/predictions/", views.get_predictions, name="get_predictions"),
    path("api/optimizations/", views.get_optimizations, name="get_optimizations"),
    path("api/anomalies/", views.get_anomalies, name="get_anomalies"),
    
    # ai API 路由
    path("api/prediction/", api.PredictionAPIView.as_view(), name="api_prediction_list"),
    path("api/prediction/<int:prediction_id>/", api.PredictionAPIView.as_view(), name="api_prediction_detail"),
    path("api/anomalies/", api.get_anomalies, name="api_anomalies"),
    path("api/optimizations/", api.get_optimizations, name="api_optimizations"),
]
