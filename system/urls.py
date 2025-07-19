from django.urls import path
from . import views

app_name = 'system'
module_display_name = '系統管理'

urlpatterns = [
    path('', views.index, name='index'),
    path('user/list/', views.user_list, name='user_list'),
    path('user/add/', views.user_add, name='user_add'),
    path('user/edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('user/edit/<int:user_id>/password/', views.user_change_password, name='user_change_password'),
    path('user/delete/<int:user_id>/', views.user_delete, name='user_delete'),
    path('group/list/', views.group_list, name='group_list'),
    path('group/add/', views.group_add, name='group_add'),
    path('group/edit/<int:group_id>/', views.group_edit, name='group_edit'),
    path('group/delete/<int:group_id>/', views.group_delete, name='group_delete'),
    path('email_config/', views.email_config, name='email_config'),
    path('backup/', views.backup_database, name='backup'),
    path('backup/download/<str:filename>/', views.download_backup, name='download_backup'),
    path('backup/restore/', views.restore_database, name='restore_database'),
    path('backup_schedule/', views.backup_schedule, name='backup_schedule'),
    path('user/export/', views.export_users, name='user_export'),
    path('user/import/', views.import_users, name='user_import'),
    path('operation_log_manage/', views.operation_log_manage, name='operation_log_manage'),
    path('clean_operation_logs/', views.clean_operation_logs, name='clean_operation_logs'),
    path('change-password/', views.change_password, name='change_password'),  # 新增路由：一般使用者變更密碼
    
    # 環境管理相關路由
    path('environment/', views.environment_management, name='environment_management'),
    path('environment/log/<str:filename>/', views.view_log_file, name='view_log_file'),
    path('environment/log/<str:filename>/download/', views.download_log_file, name='download_log_file'),
    path('environment/clean_logs/', views.clean_logs, name='clean_logs'),
]
