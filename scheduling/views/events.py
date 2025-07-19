from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from zoneinfo import ZoneInfo
from ..models import Event
import logging

logger = logging.getLogger('scheduling.views')
TAIWAN_TZ = ZoneInfo("Asia/Taipei")

def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name='排程使用者').exists()

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def events(request):
    try:
        type_filter = request.GET.get('type', '')
        category_filter = request.GET.get('category', '')
        event_id = request.GET.get('id', '')
        unit_id = request.GET.get('unit_id', '')
        logger.debug(f"收到 /scheduling/events/ 請求，type={type_filter}, category={category_filter}, id={event_id}, unit_id={unit_id}")

        events = Event.objects.all()
        if type_filter:
            events = events.filter(type=type_filter)
        if category_filter:
            events = events.filter(category=category_filter)
        if event_id:
            events = events.filter(id=event_id)
        if unit_id:
            events = events.filter(unit_id=unit_id)

        event_list = []
        for event in events:
            try:
                if not event.start or not event.end:
                    logger.warning(f"事件 {event.id} ({event.title}) 的日期為空，跳過")
                    continue

                start_with_tz = event.start
                end_with_tz = event.end
                if start_with_tz.tzinfo is None:
                    start_with_tz = start_with_tz.replace(tzinfo=TAIWAN_TZ)
                if end_with_tz.tzinfo is None:
                    end_with_tz = end_with_tz.replace(tzinfo=TAIWAN_TZ)

                if event.all_day:
                    start_date = start_with_tz.astimezone(TAIWAN_TZ).strftime('%Y-%m-%d')
                    end_date = end_with_tz.astimezone(TAIWAN_TZ).strftime('%Y-%m-%d')
                else:
                    start_date = start_with_tz.astimezone(TAIWAN_TZ).isoformat()
                    end_date = end_with_tz.astimezone(TAIWAN_TZ).isoformat()

                event_list.append({
                    'id': event.id,
                    'title': event.title,
                    'start': start_date,
                    'end': end_date,
                    'classNames': event.classNames,
                    'allDay': event.all_day,
                    'extendedProps': {
                        'type': event.type,
                        'category': event.category,
                        'description': event.description,
                        'created_by': event.created_by,
                        'created_at': event.created_at.isoformat() if event.created_at else None,
                        'updated_at': event.updated_at.isoformat() if event.updated_at else None,
                        'unit_id': event.unit_id,
                    }
                })
                logger.debug(f"事件 {event.title} 返回的日期: start={start_date}, end={end_date}, allDay={event.all_day}")
            except Exception as e:
                logger.error(f"處理事件 {event.id} ({event.title}) 時發生錯誤: {str(e)}")
                continue

        if not event_list:
            logger.warning("未找到任何事件")
        logger.debug(f"成功返回 {len(event_list)} 個事件")
        return JsonResponse(event_list, safe=False)
    except Exception as e:
        logger.error(f"處理 /scheduling/events/ 請求時發生錯誤: {str(e)}")
        return JsonResponse({'error': '無法加載事件，請聯繫管理員'}, status=500)
