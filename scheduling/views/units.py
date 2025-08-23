from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from ..models import Unit
import logging

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def units(request):
    try:
        units = Unit.objects.all()
        unit_list = [
            {
                "id": unit.id,
                "name": unit.name,
                "work_start": unit.work_start.strftime("%H:%M:%S"),
                "work_end": unit.work_end.strftime("%H:%M:%S"),
                "has_lunch_break": unit.has_lunch_break,
                "lunch_start": (
                    unit.lunch_start.strftime("%H:%M:%S") if unit.lunch_start else None
                ),
                "lunch_end": (
                    unit.lunch_end.strftime("%H:%M:%S") if unit.lunch_end else None
                ),
                "overtime_start": (
                    unit.overtime_start.strftime("%H:%M:%S")
                    if unit.overtime_start
                    else None
                ),
                "overtime_end": (
                    unit.overtime_end.strftime("%H:%M:%S")
                    if unit.overtime_end
                    else None
                ),
            }
            for unit in units
        ]
        return JsonResponse(unit_list, safe=False)
    except Exception as e:
        logger.error(f"處理 /scheduling/units/ 請求時發生錯誤: {str(e)}")
        return JsonResponse({"error": "無法加載單位列表，請聯繫管理員"}, status=500)
