from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.utils import timezone
from ..models import ProductionSafetySettings, SchedulingOperationLog
import logging

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def update_safety_settings(request):
    if request.method != "POST":
        logger.warning(f"無效的請求方法: {request.method}")
        return JsonResponse(
            {"status": "error", "message": "無效的請求方法"}, status=400
        )
    try:
        safety_days = request.POST.get("delivery_to_completion_safety_days", "").strip()
        logger.debug(f"接收到的 safety_days: '{safety_days}'")
        if not safety_days:
            logger.error("safety_days 為空")
            return JsonResponse(
                {"status": "error", "message": "請提供安全天數"}, status=400
            )
        try:
            safety_days = int(safety_days)
            if safety_days < 0:
                logger.error(f"無效的 safety_days: {safety_days}，不能為負數")
                return JsonResponse(
                    {"status": "error", "message": "安全天數不能為負數"}, status=400
                )
        except ValueError as ve:
            logger.error(f"無效的 safety_days: {safety_days}, 錯誤: {str(ve)}")
            return JsonResponse(
                {"status": "error", "message": "請輸入有效的安全天數（非負整數）"},
                status=400,
            )

        safety_settings, created = ProductionSafetySettings.objects.get_or_create(id=1)
        safety_settings.delivery_to_completion_safety_days = safety_days
        safety_settings.save(update_fields=["delivery_to_completion_safety_days"])
        logger.debug(f"已更新安全天數: {safety_days}")

        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action=f"更新安全天數為 {safety_days} 天",
            ip_address=request.META.get("REMOTE_ADDR"),
            timestamp=timezone.now(),
        )
        return JsonResponse(
            {"status": "success", "message": "安全天數設定成功"}, status=200
        )
    except Exception as e:
        logger.error(f"更新安全天數失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"更新失敗: {str(e)}"}, status=500
        )
