from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils import timezone
from ..models import Event, SchedulingOperationLog
import logging

import os
# 設定生產排程模組的日誌記錄器
scheduling_logger = logging.getLogger("scheduling")
from django.conf import settings
scheduling_handler = logging.FileHandler(os.path.join(settings.SCHEDULING_LOG_DIR, "scheduling.log"))
scheduling_handler.setFormatter(
    logging.Formatter("%(levelname)s %(asctime)s %(module)s %(message)s")
)
scheduling_logger.addHandler(scheduling_handler)
scheduling_logger.setLevel(logging.INFO)

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def index(request):
    try:
        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action="查看 scheduling 模組首頁",
            timestamp=timezone.now(),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        events = Event.objects.all()
        return render(request, "scheduling/index.html", {"events": events})
    except Exception as e:
        logger.error(f"處理 /scheduling/index/ 請求時發生錯誤: {str(e)}")
        messages.error(request, _("無法加載首頁，請聯繫管理員"))
        return render(request, "scheduling/index.html", {"events": []})
