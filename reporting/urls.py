from django.urls import path
from . import views

app_name = "reporting"  # 報表管理

urlpatterns = [
    # 首頁
    path("", views.reporting_index, name="index"),
    
    # 生產日報表
    path("production-daily/", views.production_daily, name="production_daily"),
    path("production-daily/export/", views.execute_report_export, name="export_production_daily"),
    
    # 統一工作時間報表
    path("work-time-report/", views.work_time_report, name="work_time_report"),
    path("work-time-report/api/", views.api_work_time_report, name="api_work_time_report"),
    path("work-time-report/export/", views.export_work_time_report, name="export_work_time_report"),
    
    # 測試頁面
    path("test-work-time/", views.test_work_time, name="test_work_time"),
    
    # 作業員績效報表
    path("operator-performance/", views.operator_performance, name="operator_performance"),
    
    # API 端點
    path("api/production-daily/", views.get_production_daily, name="api_production_daily"),
    path("api/operator-performance/", views.get_operator_performance, name="api_operator_performance"),
    
    # 報表匯出
    path("export/", views.report_export, name="report_export"),
    path("export/<str:report_type>/", views.report_export, name="report_export"),
    
    # 郵件發送設定
    path("email-schedule/", views.email_schedule_list, name="email_schedule_list"),
    path("email-schedule/create/", views.email_schedule_create, name="email_schedule_add"),
    path("email-schedule/edit/<int:schedule_id>/", views.email_schedule_edit, name="email_schedule_edit"),
    path("email-schedule/delete/<int:schedule_id>/", views.email_schedule_delete, name="email_schedule_delete"),
    path("email-schedule/test/<int:schedule_id>/", views.test_send_report_email, name="email_schedule_test"),
    path("email-log/", views.email_log_list, name="email_log_list"),
    

    
    # 數量分配相關路由
    path('quantity-allocation/', views.quantity_allocation_dashboard, name='quantity_allocation_dashboard'),
    path('quantity-allocation/allocate/', views.allocate_workorder_quantities, name='allocate_workorder_quantities'),
    path('quantity-allocation/allocate-multiple/', views.allocate_multiple_workorders, name='allocate_multiple_workorders'),
    path('quantity-allocation/detail/<str:workorder_id>/', views.allocation_detail, name='allocation_detail'),
]
