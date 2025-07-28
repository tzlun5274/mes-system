from django.urls import path
from . import views

app_name = "system"
module_display_name = "系統管理"

urlpatterns = [
    path("", views.index, name="index"),
    path("user/list/", views.user_list, name="user_list"),
    path("user/add/", views.user_add, name="user_add"),
    path("user/edit/<int:user_id>/", views.user_edit, name="user_edit"),
    path(
        "user/edit/<int:user_id>/password/",
        views.user_change_password,
        name="user_change_password",
    ),
    path("user/delete/<int:user_id>/", views.user_delete, name="user_delete"),
    path("group/list/", views.group_list, name="group_list"),
    path("group/add/", views.group_add, name="group_add"),
    path("group/edit/<int:group_id>/", views.group_edit, name="group_edit"),
    path("group/delete/<int:group_id>/", views.group_delete, name="group_delete"),
    # 權限管理相關路由
    path("permission/list/", views.permission_list, name="permission_list"),
    path(
        "permission/detail/<int:permission_id>/",
        views.permission_detail,
        name="permission_detail",
    ),
    path("permission/assign/", views.permission_assign, name="permission_assign"),
    path("email_config/", views.email_config, name="email_config"),
    path("backup/", views.backup_database, name="backup"),
    path(
        "backup/download/<str:filename>/", views.download_backup, name="download_backup"
    ),
    path("backup/restore/", views.restore_database, name="restore_database"),
    path("backup_schedule/", views.backup_schedule, name="backup_schedule"),
    path("user/export/", views.export_users, name="user_export"),
    path("user/import/", views.import_users, name="user_import"),
    path(
        "operation_log_manage/", views.operation_log_manage, name="operation_log_manage"
    ),
    path(
        "clean_operation_logs/", views.clean_operation_logs, name="clean_operation_logs"
    ),
    path(
        "change-password/",
        views.change_password,
        name="change_password"
    ),
    path("workorder_settings/", views.workorder_settings, name="workorder_settings"),
    # 環境管理相關路由
    path("environment/", views.environment_management, name="environment_management"),
    path("environment/log/<str:filename>/", views.view_log_file, name="view_log_file"),
    path(
        "environment/log/<str:filename>/download/",
        views.download_log_file,
        name="download_log_file",
    ),
    path("environment/clean_logs/", views.clean_logs, name="clean_logs"),
    
    # 報表設定相關路由
    path("report_settings/", views.report_settings, name="report_settings"),
    path("report_sync_settings/", views.report_sync_settings, name="report_sync_settings_add"),
    path("report_sync_settings/<int:setting_id>/", views.report_sync_settings, name="report_sync_settings_edit"),
    path("report_email_settings/", views.report_email_settings, name="report_email_settings_add"),
    path("report_email_settings/<int:setting_id>/", views.report_email_settings, name="report_email_settings_edit"),
    path("delete_report_sync_setting/<int:setting_id>/", views.delete_report_sync_setting, name="delete_report_sync_setting"),
    path("delete_report_email_setting/<int:setting_id>/", views.delete_report_email_setting, name="delete_report_email_setting"),
    path("manual_sync_reports/", views.manual_sync_reports, name="manual_sync_reports"),
    path("sync_logs/", views.sync_logs, name="sync_logs"),
    path("sync_log_detail/<int:log_id>/", views.sync_log_detail, name="sync_log_detail"),
]
