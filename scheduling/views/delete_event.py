from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext_lazy as gettext_lazy
from django.utils import timezone
from ..models import Event, SchedulingOperationLog
import logging

logger = logging.getLogger('scheduling.views')

def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name='排程使用者').exists()

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def delete_event(request, event_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("無效的請求方法")
    try:
        event = Event.objects.get(id=event_id)
        event_title = event.title
        event.delete()

        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action=f"刪除事件：{event_title} (ID: {event_id})",
            ip_address=request.META.get('REMOTE_ADDR'),
            timestamp=timezone.now()
        )

        messages.success(request, gettext_lazy("事件刪除成功！"))
        return JsonResponse({'status': 'success', 'message': '事件刪除成功'})
    except Event.DoesNotExist:
        messages.error(request, gettext_lazy("指定事件不存在"))
        return JsonResponse({'status': 'error', 'message': '指定事件不存在'}, status=404)
    except Exception as e:
        logger.error(f"刪除事件失敗: {str(e)}", exc_info=True)
        messages.error(request, gettext_lazy("刪除事件失敗，請聯繫管理員"))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
