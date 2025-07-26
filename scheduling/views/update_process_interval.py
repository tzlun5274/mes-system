from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.utils import timezone
from ..models import ProcessIntervalSettings, SchedulingOperationLog
import logging

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def update_process_interval(request):
    if request.method != "POST":
        logger.warning(f"無效的請求方法: {request.method}")
        return JsonResponse(
            {"status": "error", "message": "無效的請求方法"}, status=400
        )
    try:
        process_interval_minutes = request.POST.get(
            "process_interval_minutes", ""
        ).strip()
        logger.debug(f"接收到的 process_interval_minutes: '{process_interval_minutes}'")
        if not process_interval_minutes:
            logger.error("process_interval_minutes 為空")
            return JsonResponse(
                {"status": "error", "message": "請提供工序間隔時間"}, status=400
            )
        try:
            process_interval_minutes = int(process_interval_minutes)
            if process_interval_minutes < 0:
                logger.error(
                    f"無效的 process_interval_minutes: {process_interval_minutes}，不能為負數"
                )
                return JsonResponse(
                    {"status": "error", "message": "工序間隔時間不能為負數"}, status=400
                )
        except ValueError as ve:
            logger.error(
                f"無效的 process_interval_minutes: {process_interval_minutes}, 錯誤: {str(ve)}"
            )
            return JsonResponse(
                {"status": "error", "message": "請輸入有效的工序間隔時間（非負整數）"},
                status=400,
            )

        process_interval_settings, created = (
            ProcessIntervalSettings.objects.get_or_create(id=1)
        )
        process_interval_settings.process_interval_minutes = process_interval_minutes
        process_interval_settings.save(update_fields=["process_interval_minutes"])
        logger.debug(f"已更新工序間隔時間: {process_interval_minutes}")

        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action=f"更新工序間隔時間為 {process_interval_minutes} 分鐘",
            ip_address=request.META.get("REMOTE_ADDR"),
            timestamp=timezone.now(),
        )
        return JsonResponse(
            {"status": "success", "message": "工序間隔時間設定成功"}, status=200
        )
    except Exception as e:
        logger.error(f"更新工序間隔時間失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"更新失敗: {str(e)}"}, status=500
        )
