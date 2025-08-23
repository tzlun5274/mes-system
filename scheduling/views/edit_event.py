from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext_lazy as gettext_lazy
from django.utils import timezone
from datetime import datetime
from ..models import Unit, Event, SchedulingOperationLog
import logging

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def edit_event(request, event_id):
    if request.method != "POST":
        return HttpResponseBadRequest("無效的請求方法")
    try:
        event = Event.objects.get(id=event_id)
        unit_id = request.POST.get("unit_id", "").strip()
        title = request.POST.get("title", "").strip()
        start = request.POST.get("start", "").strip()
        end = request.POST.get("end", "").strip()
        event_type = request.POST.get("type", "").strip()
        category = request.POST.get("category", "general").strip()
        all_day = request.POST.get("all_day", "false").lower() == "true"
        description = request.POST.get("description", "").strip()

        if not title or not start or not end or not event_type:
            messages.error(
                request,
                gettext_lazy("請填寫所有必填字段（標題、開始時間、結束時間、類型）"),
            )
            return JsonResponse(
                {"status": "error", "message": "請填寫所有必填字段"}, status=400
            )

        try:
            start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M").replace(
                tzinfo=timezone.get_current_timezone()
            )
            end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M").replace(
                tzinfo=timezone.get_current_timezone()
            )
        except ValueError as e:
            messages.error(
                request, gettext_lazy("時間格式無效，請使用 YYYY-MM-DDTHH:MM 格式")
            )
            return JsonResponse(
                {"status": "error", "message": "時間格式無效"}, status=400
            )

        unit = None
        if unit_id:
            try:
                unit = Unit.objects.get(id=unit_id)
            except Unit.DoesNotExist:
                messages.error(request, gettext_lazy("指定單位不存在"))
                return JsonResponse(
                    {"status": "error", "message": "指定單位不存在"}, status=404
                )

        event.unit = unit
        event.title = title
        event.start = start_dt
        event.end = end_dt
        event.type = event_type
        event.description = description
        event.classNames = event_type
        event.all_day = all_day
        event.category = category
        event.save()

        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action=f"編輯事件：{title} (ID: {event.id})",
            event_related=event,
            ip_address=request.META.get("REMOTE_ADDR"),
            timestamp=timezone.now(),
        )

        messages.success(request, gettext_lazy("事件編輯成功！"))
        return JsonResponse({"status": "success", "message": "事件編輯成功"})
    except Event.DoesNotExist:
        messages.error(request, gettext_lazy("指定事件不存在"))
        return JsonResponse(
            {"status": "error", "message": "指定事件不存在"}, status=404
        )
    except Exception as e:
        logger.error(f"編輯事件失敗: {str(e)}", exc_info=True)
        messages.error(request, gettext_lazy("編輯事件失敗，請聯繫管理員"))
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
