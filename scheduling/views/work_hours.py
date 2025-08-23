from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils import timezone
from ..models import (
    OrderUpdateSchedule,
    ProductionSafetySettings,
    ProcessIntervalSettings,
    SchedulingOperationLog,
)
import logging


logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def work_hours(request):
    try:
        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action="查看工作時間設定頁面",
            timestamp=timezone.now(),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        order_schedule = OrderUpdateSchedule.objects.first()
        safety_settings = ProductionSafetySettings.objects.first()
        process_interval_settings = ProcessIntervalSettings.objects.first()
        return render(
            request,
            "scheduling/work_hours.html",
            {
                "order_schedule": order_schedule,
                "safety_settings": safety_settings,
                "process_interval_settings": process_interval_settings,
            },
        )
    except Exception as e:
        logger.error(f"處理 /scheduling/work_hours/ 請求時發生錯誤: {str(e)}")
        messages.error(request, _("無法加載工作時間設定頁面，請聯繫管理員"))
        return render(request, "scheduling/work_hours.html")
