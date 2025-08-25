"""
報表模組 URL 配置
"""

from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # 報表首頁
    path('', views.index, name='index'),
    
    # 評分儀表板
    path('scoring/dashboard/', views.scoring_dashboard, name='scoring_dashboard'),
    
    # 評分報表
    path('scoring/reports/', views.scoring_report_list, name='scoring_report_list'),
    path('scoring/reports/<int:report_id>/', views.scoring_report_detail, name='scoring_report_detail'),
    path('scoring/reports/generate/', views.generate_scoring_report, name='generate_scoring_report'),
    path('scoring/reports/<int:report_id>/export/', views.export_scoring_report, name='export_scoring_report'),
    
    # 作業員評分
    path('operator/scores/', views.operator_score_list, name='operator_score_list'),
    path('operator/scores/<int:score_id>/', views.operator_score_detail, name='operator_score_detail'),
    path('operator/scores/<int:score_id>/supervisor-score/', views.supervisor_score_form, name='supervisor_score_form'),
    
    # 評分週期管理
    path('score-period/', views.score_period_management, name='score_period_management'),
    path('score-period/<str:period_type>/', views.score_period_detail, name='score_period_detail'),
    
    # 工作時數報表
    path('work-hour/', views.work_hour_report_index, name='work_hour_report_index'),
    path('work-hour/daily/', views.daily_report, name='daily_report'),
    path('work-hour/daily/export/', views.daily_report_export, name='daily_report_export'),
    path('work-hour/weekly/', views.weekly_report, name='weekly_report'),
    path('work-hour/monthly/', views.monthly_report, name='monthly_report'),
    path('work-hour/quarterly/', views.quarterly_report, name='quarterly_report'),
    path('work-hour/yearly/', views.yearly_report, name='yearly_report'),
    
    # 報表排程
    path('schedule/', views.report_schedule_list, name='report_schedule_list'),
    path('schedule/add/', views.report_schedule_form, name='report_schedule_add'),
    path('schedule/<int:schedule_id>/edit/', views.report_schedule_form, name='report_schedule_edit'),
    path('schedule/<int:schedule_id>/execute/', views.execute_report_schedule, name='execute_report_schedule'),
    path('schedule/logs/', views.report_execution_log, name='report_execution_log'),
    
    # 資料同步
    path('sync/', views.sync_report_data, name='sync_report_data'),
    
    # 已完工工單報表
    path('completed-workorder/', views.completed_workorder_report_index, name='completed_workorder_report_index'),
    path('completed-workorder/list/', views.completed_workorder_report_list, name='completed_workorder_report_list'),
    path('completed-workorder/<int:report_id>/', views.completed_workorder_report_detail, name='completed_workorder_report_detail'),
    path('completed-workorder/sync/', views.sync_completed_workorder_data, name='sync_completed_workorder_data'),
    
    # API 端點
    path('api/chart-data/', views.chart_data, name='chart_data'),
    path('api/report-data/', views.report_data_list, name='report_data_list'),
    path('api/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('api/work-hour-stats/', views.work_hour_stats, name='work_hour_stats'),
    path('api/detailed-stats/', views.detailed_stats, name='detailed_stats'),
] 