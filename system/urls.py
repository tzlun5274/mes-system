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
    # 使用者工作權限管理路由
    path("user_work_permission/list/", views.user_work_permission_list, name="user_work_permission_list"),
    path("user_work_permission/add/", views.user_work_permission_add, name="user_work_permission_add"),
    path("user_work_permission/edit/<int:permission_id>/", views.user_work_permission_edit, name="user_work_permission_edit"),
    path("user_work_permission/delete/<int:permission_id>/", views.user_work_permission_delete, name="user_work_permission_delete"),
    path("user_work_permission/detail/<int:permission_id>/", views.user_work_permission_detail, name="user_work_permission_detail"),
    path("auto-approval-settings/", views.auto_approval_settings, name="auto_approval_settings"),
    path("test-switches/", views.test_switches, name="test_switches"),
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
    # path("workorder_settings/", views.workorder_settings, name="workorder_settings"),
    # 環境管理相關路由
    path("environment/", views.environment_management, name="environment_management"),
    path("environment/log/<str:filename>/", views.view_log_file, name="view_log_file"),
    path(
        "environment/log/<str:filename>/download/",
        views.download_log_file,
        name="download_log_file",
    ),
    path("environment/clean_logs/", views.clean_logs, name="clean_logs"),

    # 工單管理設定（已整合完工判斷功能）
    path("workorder_settings/", views.workorder_settings, name="workorder_settings"),
    
    # 手動執行 API 端點
    path("execute_auto_allocation/", views.execute_auto_allocation, name="execute_auto_allocation"),
    path("execute_auto_approval/", views.execute_auto_approval, name="execute_auto_approval"),
    path("execute_completion_check/", views.execute_completion_check, name="execute_completion_check"),
    path("execute_data_transfer/", views.execute_data_transfer, name="execute_data_transfer"),
    
    # 自動審核定時任務管理
    path("auto_approval_tasks/", views.auto_approval_tasks, name="auto_approval_tasks"),
    path("auto_approval_tasks/<int:task_id>/", views.auto_approval_task_detail, name="auto_approval_task_detail"),
    path("add_auto_approval_task/", views.add_auto_approval_task, name="add_auto_approval_task"),
    path("delete_auto_approval_task/", views.delete_auto_approval_task, name="delete_auto_approval_task"),
    path("execute_specific_auto_approval_task/", views.execute_specific_auto_approval_task, name="execute_specific_auto_approval_task"),
    path("execute_all_auto_approval_tasks/", views.execute_all_auto_approval_tasks, name="execute_all_auto_approval_tasks"),
    
    # 自動完工功能 API 端點
    path("enable_auto_completion/", views.enable_auto_completion, name="enable_auto_completion"),
    path("disable_auto_completion/", views.disable_auto_completion, name="disable_auto_completion"),

    # 完工檢查配置（已整合到工單管理設定中）
    # path('completion-check/config/', views.completion_check_config, name='completion_check_config'),
    # path('completion-check/status/', views.completion_check_status, name='completion_check_status'),
    
    # 報表清理設定
    path("report_cleanup_settings/", views.report_cleanup_settings, name="report_cleanup_settings"),
    path("update_cleanup_settings/", views.update_cleanup_settings, name="update_cleanup_settings"),
    path("execute_cleanup/", views.execute_cleanup, name="execute_cleanup"),
    
    # 報表設定相關
    path("report_settings/", views.report_settings, name="report_settings"),
    path("manual_sync_reports/", views.manual_sync_reports, name="manual_sync_reports"),
    
    # 定時任務管理
    path('scheduled-tasks/', views.ScheduledTaskListView.as_view(), name='scheduled_task_list'),
    path('scheduled-tasks/create/', views.ScheduledTaskCreateView.as_view(), name='scheduled_task_create'),
    path('scheduled-tasks/<int:pk>/update/', views.ScheduledTaskUpdateView.as_view(), name='scheduled_task_update'),
    path('scheduled-tasks/<int:pk>/delete/', views.ScheduledTaskDeleteView.as_view(), name='scheduled_task_delete'),
    path('scheduled-tasks/<int:pk>/toggle/', views.toggle_scheduled_task, name='toggle_scheduled_task'),
    path('test-cron-expression/', views.test_cron_expression, name='test_cron_expression'),
]
