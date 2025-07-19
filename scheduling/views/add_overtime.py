from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext_lazy as gettext_lazy
from django.utils import timezone
from datetime import datetime
from ..models import Unit, Event, SchedulingOperationLog
import logging
from django.contrib import messages  # 添加這行

logger = logging.getLogger('scheduling.views')

def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name='排程使用者').exists()

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def add_overtime(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("無效的請求方法")
    try:
        unit_id = request.POST.get('unit_id', '').strip()
        date = request.POST.get('date', '').strip()

        if not unit_id or not date:
            messages.error(request, gettext_lazy("請填寫所有必填字段（單位、加班日期）"))
            return JsonResponse({'status': 'error', 'message': '請填寫所有必填字段'}, status=400)

        try:
            unit = Unit.objects.get(id=unit_id)
        except Unit.DoesNotExist:
            messages.error(request, gettext_lazy("指定單位不存在"))
            return JsonResponse({'status': 'error', 'message': '指定單位不存在'}, status=404)

        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
        except ValueError as e:
            messages.error(request, gettext_lazy("日期格式無效，請使用 YYYY-MM-DD 格式"))
            return JsonResponse({'status': 'error', 'message': '日期格式無效'}, status=400)

        start_time = unit.overtime_start or datetime.strptime('17:30', '%H:%M').time()
        end_time = unit.overtime_end or datetime.strptime('20:30', '%H:%M').time()
        start_dt = timezone.make_aware(datetime.combine(date_obj, start_time))
        end_dt = timezone.make_aware(datetime.combine(date_obj, end_time))

        event = Event.objects.create(
            unit=unit,
            title=f"{unit.name} 加班",
            start=start_dt,
            end=end_dt,
            type='overtime',
            description=f"單位 {unit.name} 在 {date} 的加班安排",
            classNames='overtime',
            all_day=False,
            category='general',
            created_by=request.user.username
        )

        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action=f"新增加班事件：{unit.name} (ID: {event.id})",
            event_related=event,
            ip_address=request.META.get('REMOTE_ADDR'),
            timestamp=timezone.now()
        )

        messages.success(request, gettext_lazy("加班事件新增成功！"))
        return JsonResponse({'status': 'success', 'message': '加班事件新增成功'})
    except Exception as e:
        logger.error(f"新增加班事件失敗: {str(e)}", exc_info=True)
        messages.error(request, gettext_lazy("新增加班事件失敗，請聯繫管理員"))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
