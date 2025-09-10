from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext as _
from ..customer_order_management import order_manager
import logging

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def update_orders(request):
    if request.method != "POST":
        return HttpResponseBadRequest("無效的請求方法")

    try:
        # 使用客戶訂單管理器執行同步
        result = order_manager.sync_orders_from_erp(
            user=request.user, ip_address=request.META.get("REMOTE_ADDR")
        )

        if result["status"] == "success":
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)

    except Exception as e:
        logger.error(f"手動觸發客戶訂單更新失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"更新失敗: {str(e)}"}, status=500
        )
