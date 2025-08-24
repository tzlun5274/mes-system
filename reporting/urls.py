"""
報表模組 URL 配置
"""

from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # 報表首頁
    path('', views.index, name='index'),
    
    # 工作時數報表 - 新設計
    path('work-time/', views.work_time_report_index, name='work_time_report_index'),
    path('work-time/daily/', views.work_time_daily_report, name='work_time_daily_report'),
    path('work-time/weekly/', views.work_time_weekly_report, name='work_time_weekly_report'),
    path('work-time/monthly/', views.work_time_monthly_report, name='work_time_monthly_report'),
    path('work-time/list/', views.work_time_report_list, name='work_time_report_list'),
    path('work-time/<int:report_id>/', views.work_time_report_detail, name='work_time_report_detail'),
    path('work-time/export/', views.work_time_report_export, name='work_time_report_export'),
    
    # 工作時數報表 - 保留原有功能
    path('work-hour/', views.work_hour_report_index, name='work_hour_report_index'),
    path('work-hour/daily/', views.daily_report, name='daily_report'),
    path('work-hour/operator-daily/', views.operator_daily_report, name='operator_daily_report'),
    path('work-hour/weekly/', views.weekly_report, name='weekly_report'),
    path('work-hour/monthly/', views.monthly_report, name='monthly_report'),
    path('work-hour/quarterly/', views.quarterly_report, name='quarterly_report'),
    path('work-hour/yearly/', views.yearly_report, name='yearly_report'),
] 