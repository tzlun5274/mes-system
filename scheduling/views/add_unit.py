from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext as _
from ..models import Unit
from ..utils import log_user_operation
import logging
from datetime import datetime
from django.contrib import messages  # 添加這行

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def add_unit(request):
    if request.method != "POST":
        return HttpResponseBadRequest("無效的請求方法")
    try:
        unit_name = request.POST.get("unit_name", "").strip()
        work_start = request.POST.get("work_start", "").strip()
        work_end = request.POST.get("work_end", "").strip()
        has_lunch_break = request.POST.get("has_lunch_break", "true").lower() == "true"
        lunch_start = request.POST.get("lunch_start", "").strip()
        lunch_end = request.POST.get("lunch_end", "").strip()
        overtime_start = request.POST.get("overtime_start", "").strip()
        overtime_end = request.POST.get("overtime_end", "").strip()

        if not unit_name or not work_start or not work_end:
            messages.error(
                request, _("請填寫所有必填字段（單位名稱、上班開始時間、下班時間）")
            )
            return JsonResponse(
                {"status": "error", "message": "請填寫所有必填字段"}, status=400
            )

        if Unit.objects.filter(name=unit_name).exists():
            messages.error(request, _("單位名稱已存在，請選擇其他名稱"))
            return JsonResponse(
                {"status": "error", "message": "單位名稱已存在"}, status=400
            )

        try:
            work_start_time = datetime.strptime(work_start, "%H:%M").time()
            work_end_time = datetime.strptime(work_end, "%H:%M").time()
            lunch_start_time = (
                datetime.strptime(lunch_start, "%H:%M").time()
                if has_lunch_break and lunch_start
                else None
            )
            lunch_end_time = (
                datetime.strptime(lunch_end, "%H:%M").time()
                if has_lunch_break and lunch_end
                else None
            )
            overtime_start_time = (
                datetime.strptime(overtime_start, "%H:%M").time()
                if overtime_start
                else None
            )
            overtime_end_time = (
                datetime.strptime(overtime_end, "%H:%M").time()
                if overtime_end
                else None
            )
        except ValueError as e:
            messages.error(request, _("時間格式無效，請使用 HH:MM 格式"))
            return JsonResponse(
                {"status": "error", "message": "時間格式無效"}, status=400
            )

        unit = Unit.objects.create(
            name=unit_name,
            work_start=work_start_time,
            work_end=work_end_time,
            has_lunch_break=has_lunch_break,
            lunch_start=lunch_start_time,
            lunch_end=lunch_end_time,
            overtime_start=overtime_start_time,
            overtime_end=overtime_end_time,
        )

        log_user_operation(
            username=request.user.username,
            module="scheduling",
            action=f"新增單位：{unit_name} (ID: {unit.id})",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        messages.success(request, _("單位新增成功！"))
        return JsonResponse({"status": "success", "message": "單位新增成功"})
    except Exception as e:
        logger.error(f"新增單位失敗: {str(e)}", exc_info=True)
        messages.error(request, _("新增單位失敗，請聯繫管理員"))
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
