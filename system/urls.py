from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = "system"
module_display_name = "系統管理"

# 添加一個重定向函數來處理錯誤的 URL
def redirect_wrong_password_url(request):
    """重定向錯誤的密碼更改 URL 到正確的頁面"""
    return redirect('system:change_password')

urlpatterns = [
    path("", views.index, name="index"),
    
    # 用戶管理相關路由
    path("user/list/", views.user_list, name="user_list"),
    path("user/add/", views.user_add, name="user_add"),
    path("user/detail/<int:user_id>/", views.user_detail, name="user_detail"),
    path("user/edit/<int:user_id>/", views.user_edit, name="user_edit"),
    path("user/edit/<int:user_id>/password/", views.user_change_password, name="user_change_password"),
    path("user/delete/<int:user_id>/", views.user_delete, name="user_delete"),
    path("user/toggle/<int:user_id>/", views.user_toggle_status, name="user_toggle_status"),
    path("user/<int:user_id>/permissions/", views.user_permissions, name="user_permissions"),
    
    # 用戶工作權限管理相關路由
    path("user/<int:user_id>/work_permissions/", views.user_work_permissions, name="user_work_permissions"),
    path("user/work_permissions/list/", views.user_work_permissions_list, name="user_work_permissions_list"),
    path("user/work_permissions/bulk/", views.bulk_work_permissions, name="bulk_work_permissions"),
    
    # 權限管理相關路由
    path("permission/list/", views.permission_list, name="permission_list"),
    path("permission/detail/<int:permission_id>/", views.permission_detail, name="permission_detail"),
    path("permission/assign/", views.permission_assign, name="permission_assign"),
    path("permission/bulk_assign/", views.permission_bulk_assign, name="permission_bulk_assign"),
    path("permission/sync/", views.permission_sync, name="permission_sync"),
    
    # 系統設定相關路由
    path("email_config/", views.email_config, name="email_config"),
    path("backup/", views.backup_database, name="backup"),
    path("backup/download/<str:filename>/", views.download_backup, name="download_backup"),
    path("backup/restore/", views.restore_database, name="restore_database"),
    path("backup_schedule/", views.backup_schedule, name="backup_schedule"),
    
    # 用戶資料匯入匯出
    path("user/export/", views.export_users, name="user_export"),
    path("user/export/excel/", views.export_users_excel, name="user_export_excel"),
    path("user/import/", views.import_users, name="user_import"),
    path("user/test-import/", views.test_import, name="test_import"),
    
    # 操作日誌管理
    path("operation_log_manage/", views.operation_log_manage, name="operation_log_manage"),
    path("clean_operation_logs/", views.clean_operation_logs, name="clean_operation_logs"),
    
    # 密碼管理
    path("change-password/", views.change_password, name="change_password"),
    
    # 環境管理相關路由
    path("environment/", views.environment_management, name="environment_management"),
    path("environment/log/<str:filename>/", views.view_log_file, name="view_log_file"),
    path("environment/log/<str:filename>/download/", views.download_log_file, name="download_log_file"),
    path("environment/clean_logs/", views.clean_logs, name="clean_logs"),
    
    # 系統儀表板
    path("dashboard/", views.system_dashboard, name="system_dashboard"),
    
    # 自動審核定時任務管理
    path("auto_approval_tasks/", views.auto_approval_tasks, name="auto_approval_tasks"),
    path("auto_approval_task/<int:task_id>/", views.auto_approval_task_detail, name="auto_approval_task_detail"),
    
    # 訂單同步設定
    path("order_sync_settings/", views.order_sync_settings, name="order_sync_settings"),
    path("manual_order_sync/", views.manual_order_sync, name="manual_order_sync"),
    
    # 工單設定
    path("workorder_settings/", views.workorder_settings, name="workorder_settings"),
    path("execute_auto_allocation/", views.execute_auto_allocation, name="execute_auto_allocation"),
    path("execute_completion_check/", views.execute_completion_check, name="execute_completion_check"),
    path("execute_data_transfer/", views.execute_data_transfer, name="execute_data_transfer"),
    path("add_auto_approval_task/", views.add_auto_approval_task, name="add_auto_approval_task"),
    path("delete_auto_approval_task/", views.delete_auto_approval_task, name="delete_auto_approval_task"),
    path("execute_specific_auto_approval_task/", views.execute_specific_auto_approval_task, name="execute_specific_auto_approval_task"),
    path("execute_all_auto_approval_tasks/", views.execute_all_auto_approval_tasks, name="execute_all_auto_approval_tasks"),
    path("enable_auto_completion/", views.enable_auto_completion, name="enable_auto_completion"),
    path("disable_auto_completion/", views.disable_auto_completion, name="disable_auto_completion"),
    
    # 報表設定
    path("report_settings/", views.report_settings, name="report_settings"),
    path("manual_sync_reports/", views.manual_sync_reports, name="manual_sync_reports"),
]
