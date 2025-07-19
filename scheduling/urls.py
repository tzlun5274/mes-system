from django.urls import path
from . import views
from .views.schedule_hybrid import schedule_hybrid, hybrid_scheduling_preview, schedule_warning_board
from .views.orders import order_list
from .views.order_api import OrderAPIView
from .views.unified_scheduling import (
    unified_scheduling_view, check_resource_conflicts, execute_scheduling,
    update_gantt_task, get_scheduling_progress, get_scheduling_parameters
)

app_name = 'scheduling'

urlpatterns = [
    path('', views.index, name='index'),
    path('calendar/', views.calendar, name='calendar'),
    path('work_hours/', views.work_hours, name='work_hours'),
    path('units/', views.units, name='units'),
    path('events/', views.events, name='events'),
    path('update_unit_work_hours/', views.update_unit_work_hours, name='update_unit_work_hours'),
    path('update_order_schedule/', views.update_order_schedule, name='update_order_schedule'),
    path('add_event/', views.add_event, name='add_event'),
    path('add_overtime/', views.add_overtime, name='add_overtime'),
    path('edit_event/<int:event_id>/', views.edit_event, name='edit_event'),
    path('delete_event/<int:event_id>/', views.delete_event, name='delete_event'),
    path('import_events/', views.import_events, name='import_events'),
    path('update_orders/', views.update_orders, name='update_orders'),
    path('company_view/', views.company_view, name='company_view'),
    path('sync_companies/', views.sync_companies, name='sync_companies'),
    path('view_schedule/', views.view_schedule, name='view_schedule'),
    path('add_unit/', views.add_unit, name='add_unit'),
    path('delete_unit/<int:unit_id>/', views.delete_unit, name='delete_unit'),
    path('update_safety_settings/', views.update_safety_settings, name='update_safety_settings'),
    path('update_process_interval/', views.update_process_interval, name='update_process_interval'),
    path('schedule_management/', views.schedule_management, name='schedule_management'),
    path('product_capacity_setting/', views.product_capacity_setting, name='product_capacity_setting'),
    path('schedule_semi_auto/', views.schedule_semi_auto, name='schedule_semi_auto'),
    path('schedule_auto/', views.schedule_auto, name='schedule_auto'),
    path('hybrid/', schedule_hybrid, name='schedule_hybrid'),
    path('hybrid/preview/', hybrid_scheduling_preview, name='hybrid_scheduling_preview'),
    path('warning_board/', schedule_warning_board, name='schedule_warning_board'),
    path('gantt/', views.gantt_view, name='gantt'),
    path('delete_all_production_events/', views.delete_all_production_events, name='delete_all_production_events'),
    path('delete_order_production_events/', views.delete_order_production_events, name='delete_order_production_events'),
    path('semi_auto/recalc/', views.recalc_log_api, name='recalc_log_api'),
    path('api/schedule/', views.api_schedule, name='api_schedule'),
    path('api/schedule/manual/', views.api_schedule_manual, name='api_schedule_manual'),
    path('api/schedule/links/', views.api_schedule_links, name='api_schedule_links'),
    path('api/calculate_task_duration/', views.calculate_task_duration, name='api_calculate_task_duration'),
    path('order_list/', order_list, name='order_list'),
    
    # 訂單 API 路由
    path('api/orders/', OrderAPIView.as_view(), name='api_orders'),
    path('api/orders/<str:action>/', OrderAPIView.as_view(), name='api_orders_action'),
    
    # 統一排程操作路由
    path('unified/', unified_scheduling_view, name='unified_scheduling'),
    path('api/check-conflicts/', check_resource_conflicts, name='check_resource_conflicts'),
    path('api/execute-scheduling/', execute_scheduling, name='execute_scheduling'),
    path('api/update-gantt-task/', update_gantt_task, name='update_gantt_task'),
    path('api/scheduling-progress/', get_scheduling_progress, name='get_scheduling_progress'),
    path('api/scheduling-parameters/', get_scheduling_parameters, name='get_scheduling_parameters'),
]
