from django.contrib import messages  # 新增這行
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext as _
from django.utils import timezone
from datetime import datetime
from ..models import Unit, SchedulingOperationLog
import logging

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def update_unit_work_hours(request):
    if request.method != "POST":
        return HttpResponseBadRequest("無效的請求方法".encode())

    try:
        unit_id = request.POST.get("unit_id", "").strip()
        work_start = request.POST.get("work_start", "").strip()
        work_end = request.POST.get("work_end", "").strip()
        has_lunch_break = request.POST.get("has_lunch_break", "true").lower() == "true"
        lunch_start = request.POST.get("lunch_start", "").strip()
        lunch_end = request.POST.get("lunch_end", "").strip()
        overtime_start = request.POST.get("overtime_start", "").strip()
        overtime_end = request.POST.get("overtime_end", "").strip()

        if not unit_id or not work_start or not work_end:
            messages.error(
                request, _("請填寫所有必填字段（單位、上班開始時間、下班時間）")
            )
            return JsonResponse(
                {"status": "error", "message": "請填寫所有必填字段"}, status=400
            )

        unit = Unit.objects.get(id=unit_id)
        # 防呆：禁止修改預設單位名稱
        if (
            unit.name == "預設單位"
            and request.POST.get("unit_name")
            and request.POST.get("unit_name") != "預設單位"
        ):
            messages.error(request, "預設單位名稱不可修改")
            return JsonResponse(
                {"status": "error", "message": "預設單位名稱不可修改"}, status=400
            )
        unit.work_start = datetime.strptime(work_start, "%H:%M").time()
        unit.work_end = datetime.strptime(work_end, "%H:%M").time()
        unit.has_lunch_break = has_lunch_break
        if has_lunch_break and lunch_start and lunch_end:
            unit.lunch_start = datetime.strptime(lunch_start, "%H:%M").time()
            unit.lunch_end = datetime.strptime(lunch_end, "%H:%M").time()
        else:
            unit.lunch_start = None
            unit.lunch_end = None
        if overtime_start and overtime_end:
            unit.overtime_start = datetime.strptime(overtime_start, "%H:%M").time()
            unit.overtime_end = datetime.strptime(overtime_end, "%H:%M").time()
        else:
            unit.overtime_start = None
            unit.overtime_end = None
        unit.save()

        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action=f"更新單位工作時間：{unit.name} (ID: {unit.id})",
            ip_address=request.META.get("REMOTE_ADDR"),
            timestamp=timezone.now(),
        )

        messages.success(request, _("單位工作時間更新成功！"))
        return JsonResponse({"status": "success", "message": "單位工作時間更新成功"})
    except ValueError as e:
        messages.error(request, _("時間格式無效，請使用 HH:MM 格式"))
        return JsonResponse({"status": "error", "message": "時間格式無效"}, status=400)
    except Unit.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "指定單位不存在"}, status=404
        )
    except Exception as e:
        messages.error(request, _("更新單位工作時間失敗，請聯繫管理員"))
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
