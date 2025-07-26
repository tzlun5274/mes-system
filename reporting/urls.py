from django.urls import path
from . import views

app_name = "reporting"
module_display_name = "報表模組"

urlpatterns = [
    path("", views.index, name="index"),
    path("production_daily/", views.production_daily, name="production_daily"),
    path(
        "operator_performance/", views.operator_performance, name="operator_performance"
    ),
    path(
        "api/production_daily/", views.get_production_daily, name="get_production_daily"
    ),
    path(
        "api/operator_performance/",
        views.get_operator_performance,
        name="get_operator_performance",
    ),
    path(
        "api/manual_sync_smt_report/",
        views.manual_sync_smt_report,
        name="manual_sync_smt_report",
    ),
    path(
        "api/manual_sync_operator_performance/",
        views.manual_sync_operator_performance,
        name="manual_sync_operator_performance",
    ),
    path(
        "api/update_sync_interval/",
        views.update_sync_interval,
        name="update_sync_interval",
    ),
    path("api/get_sync_settings/", views.get_sync_settings, name="get_sync_settings"),
    # 報表郵件發送設定
    path("email_schedule/", views.email_schedule_list, name="email_schedule_list"),
    path(
        "email_schedule/create/",
        views.email_schedule_create,
        name="email_schedule_create",
    ),
    path(
        "email_schedule/<int:schedule_id>/edit/",
        views.email_schedule_edit,
        name="email_schedule_edit",
    ),
    path(
        "email_schedule/<int:schedule_id>/delete/",
        views.email_schedule_delete,
        name="email_schedule_delete",
    ),
    path("email_log/", views.email_log_list, name="email_log_list"),
    path(
        "api/test_send_report_email/",
        views.test_send_report_email,
        name="test_send_report_email",
    ),
    # 清除報表資料
    path("clear_data/", views.clear_report_data, name="clear_report_data"),
    path(
        "manufacturing_workhour_list/",
        views.manufacturing_workhour_list,
        name="manufacturing_workhour_list",
    ),
]
