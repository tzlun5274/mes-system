from .index import index
from .calendar import calendar
from .work_hours import work_hours
from .units import units
from .events import events
from .update_unit_work_hours import update_unit_work_hours
from .update_process_interval import update_process_interval
from .company_view import company_view
from .sync_companies import sync_companies
from .update_orders import update_orders
from .add_event import add_event
from .add_overtime import add_overtime
from .edit_event import edit_event
from .delete_event import delete_event
from .import_events import import_events
from .update_order_schedule import update_order_schedule
from .view_schedule import (
    view_schedule,
    delete_all_production_events,
    delete_order_production_events,
)
from .add_unit import add_unit
from .delete_unit import delete_unit
from .update_safety_settings import update_safety_settings
from .schedule_management import schedule_management
from .schedule_manual import product_capacity_setting
from .schedule_semi_auto import schedule_semi_auto, recalc_log_api
from .schedule_auto import schedule_auto
from .api_schedule import (
    api_schedule,
    api_schedule_manual,
    api_schedule_links,
    calculate_task_duration,
)
from django.shortcuts import render


def gantt_view(request):
    return render(request, "scheduling/gantt.html")
