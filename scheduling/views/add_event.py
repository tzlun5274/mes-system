from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext_lazy as gettext_lazy
from django.utils import timezone
from datetime import datetime
from ..models import Unit, Event, SchedulingOperationLog
import logging
from django.contrib import messages  # 添加這行

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def add_event(request):
    if request.method != "POST":
        return HttpResponseBadRequest("無效的請求方法")
    try:
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

        event = Event.objects.create(
            unit=unit,
            title=title,
            start=start_dt,
            end=end_dt,
            type=event_type,
            description=description,
            classNames=event_type,
            all_day=all_day,
            category=category,
            created_by=request.user.username,
        )

        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action=f"新增事件：{title} (ID: {event.id})",
            event_related=event,
            ip_address=request.META.get("REMOTE_ADDR"),
            timestamp=timezone.now(),
        )

        messages.success(request, gettext_lazy("事件新增成功！"))
        return JsonResponse({"status": "success", "message": "事件新增成功"})
    except Exception as e:
        logger.error(f"新增事件失敗: {str(e)}", exc_info=True)
        messages.error(request, gettext_lazy("新增事件失敗，請聯繫管理員"))
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
