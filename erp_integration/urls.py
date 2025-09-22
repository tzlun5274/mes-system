from django.urls import path
from . import views, api

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
    path("api_test/", views.api_test, name="api_test"),
    path("api/config/", views.get_config, name="get_config"),
    path("api/companies/", views.get_companies, name="get_companies"),
    path("api/operation_logs/", views.get_operation_logs, name="get_operation_logs"),
    
    # ERP 整合 API 路由
    path("api/company-config/", api.CompanyConfigAPIView.as_view(), name="api_company_config_list"),
    path("api/company-config/<int:company_id>/", api.CompanyConfigAPIView.as_view(), name="api_company_config_detail"),
    path("api/erp-config/", api.ERPConfigAPIView.as_view(), name="api_erp_config_list"),
    path("api/erp-config/<int:config_id>/", api.ERPConfigAPIView.as_view(), name="api_erp_config_detail"),
    path("api/company-by-code/", api.get_company_by_code, name="api_company_by_code"),
    path("api/erp-operation-logs/", api.get_erp_operation_logs, name="api_erp_operation_logs"),
    path("api/active-companies/", api.get_active_companies, name="api_active_companies"),
    path("api/active-erp-configs/", api.get_active_erp_configs, name="api_active_erp_configs"),
]
