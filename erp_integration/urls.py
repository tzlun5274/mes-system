from django.urls import path
from . import views

app_name = "erp_integration"
module_display_name = "ERP 整合"

urlpatterns = [
    path("", views.index, name="index"),
    path("config/", views.config, name="config"),
    path("company_config/", views.company_config, name="company_config"),
    path("company_detail/", views.company_detail, name="company_detail"),
    path(
        "company_detail/<int:company_id>/", views.company_detail, name="company_detail"
    ),
    path(
        "company_config/delete/<int:company_id>/",
        views.delete_company,
        name="delete_company",
    ),
    path("table_search/", views.table_search, name="table_search"),
    path("manual_search/", views.manual_search, name="manual_search"),
    path("operation_log/", views.operation_log, name="operation_log"),
    path("api/config/", views.get_config, name="get_config"),
    path("api/companies/", views.get_companies, name="get_companies"),
    path("api/operation_logs/", views.get_operation_logs, name="get_operation_logs"),
]
