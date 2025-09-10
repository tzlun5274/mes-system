"""
報表模組 URL 配置
"""

from django.urls import path
from . import views, api

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
    path('work-hour/unified/', views.unified_report_form, name='unified_report_form'),
    path('work-hour/daily/', views.daily_report, name='daily_report'),
    path('work-hour/daily/export/', views.daily_report_export, name='daily_report_export'),
    path('work-hour/custom/', views.custom_report, name='custom_report'),
    path('work-hour/custom/export/', views.custom_report_export, name='custom_report_export'),
    path('work-hour/weekly/', views.weekly_report, name='weekly_report'),
    path('work-hour/monthly/', views.monthly_report, name='monthly_report'),
    path('work-hour/quarterly/', views.quarterly_report, name='quarterly_report'),
    path('work-hour/yearly/', views.yearly_report, name='yearly_report'),
    
    # 報表排程
    path('schedule/', views.report_schedule_list, name='report_schedule_list'),
    path('schedule/add/', views.report_schedule_form, name='report_schedule_add'),
    path('schedule/<int:schedule_id>/edit/', views.report_schedule_form, name='report_schedule_edit'),
    path('schedule/<int:schedule_id>/delete/', views.delete_report_schedule, name='report_schedule_delete'),
    path('schedule/<int:schedule_id>/execute/', views.execute_report_schedule, name='execute_report_schedule'),
    path('schedule/logs/', views.report_execution_log, name='report_execution_log'),
    
    # 資料同步
    path('sync/', views.sync_report_data, name='sync_report_data'),
    

    
    # 已完工工單分析報表
    path('completed-workorder-analysis/', views.CompletedWorkOrderAnalysisIndexView.as_view(), name='completed_workorder_analysis'),
    path('completed-workorder-analysis/list/', views.CompletedWorkOrderAnalysisListView.as_view(), name='completed_workorder_analysis_list'),
    path('completed-workorder-analysis/<int:analysis_id>/', views.CompletedWorkOrderAnalysisDetailView.as_view(), name='completed_workorder_analysis_detail'),

    # 工單分析管理
    path('workorder-analysis/', views.WorkOrderAnalysisManagementView.as_view(), name='workorder_analysis_management'),
    path('workorder-analysis/single/', views.analyze_single_workorder, name='analyze_single_workorder'),
    path('workorder-analysis/batch/', views.analyze_batch_workorders, name='analyze_batch_workorders'),
    path('workorder-analysis/setup-schedule/', views.setup_analysis_schedule, name='setup_analysis_schedule'),
    path('workorder-analysis/schedule-status/', views.get_analysis_schedule_status, name='get_analysis_schedule_status'),
    
    # API 端點
    path('api/chart-data/', views.chart_data, name='chart_data'),
    path('api/report-data/', views.report_data_list, name='report_data_list'),
    path('api/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('api/work-hour-stats/', views.work_hour_stats, name='work_hour_stats'),
    path('api/detailed-stats/', views.detailed_stats, name='detailed_stats'),
    
    # 工作日曆測試
    path('test-workday-calendar/', views.test_workday_calendar, name='test_workday_calendar'),
    
    # 假期設定管理
    path('holiday-setup/', views.holiday_setup_management, name='holiday_setup_management'),
    
    # 前一個工作日報表
    path('execute-previous-workday-report/', views.execute_previous_workday_report, name='execute_previous_workday_report'),
    path('test-previous-workday-report/', views.test_previous_workday_report, name='test_previous_workday_report'),
    path('previous-workday-report-management/', views.previous_workday_report_management, name='previous_workday_report_management'),
    
    # 政府行事曆 API 同步
    path('government-calendar-sync/', views.government_calendar_sync, name='government_calendar_sync'),
    
    # CSV 國定假日匯入
    path('csv-holiday-import/', views.csv_holiday_import, name='csv_holiday_import'),
    # reporting API 路由
    path("api/workorder-report/", api.WorkOrderReportAPIView.as_view(), name="api_workorder_report_list"),
    path("api/workorder-report/<int:report_id>/", api.WorkOrderReportAPIView.as_view(), name="api_workorder_report_detail"),
    path("api/production-reports/", api.get_production_reports, name="api_production_reports"),
    path("api/quality-reports/", api.get_quality_reports, name="api_quality_reports"),
]