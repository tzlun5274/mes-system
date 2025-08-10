from django.urls import path, include
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path("", views.home, name="home_page"),
    path("home/", views.home, name="home"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico")),
    path("system/", include("system.urls")),
    path("equip/", include("equip.urls")),
    path("material/", include("material.urls")),
    path("process/", include("process.urls")),
    path("scheduling/", include("scheduling.urls")),
    path("production/", include("production.urls", namespace="production")),
    path("quality/", include("quality.urls")),
    path("kanban/", include("kanban.urls")),
    path("erp_integration/", include("erp_integration.urls")),
    path("ai/", include("ai.urls")),
    path("rosetta/", include("rosetta.urls")),
    path("workorder/", include("workorder.urls", namespace="workorder")),
    path("reporting/", include("reporting.urls", namespace="reporting")),
    path("work-reporting-management/", include("work_reporting_management.urls", namespace="work_reporting_management")),  # 原 unified_work_reporting 改名
    path("database-error/", views.database_error, name="database_error"),
]
