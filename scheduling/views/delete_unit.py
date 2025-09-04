from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext as _
from ..models import Unit
# from ..utils import log_user_operation  # 暫時註解掉，避免導入錯誤
import logging

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def delete_unit(request, unit_id):
    if request.method != "POST":
        return HttpResponseBadRequest("無效的請求方法".encode())
    try:
        unit = Unit.objects.get(id=unit_id)
        unit_name = unit.name
        if unit_name == "預設單位":
            messages.error(request, "預設單位不可刪除")
            return JsonResponse(
                {"status": "error", "message": "預設單位不可刪除"}, status=400
            )
        unit.delete()

        # log_user_operation(  # 暫時註解掉，避免導入錯誤
        #     username=request.user.username,
        #     module="scheduling",
        #     action=f"刪除單位：{unit_id}",
        #     ip_address=request.META.get("REMOTE_ADDR"),
        # )

        messages.success(request, _("單位刪除成功！"))
        return JsonResponse({"status": "success", "message": "單位刪除成功"})
    except Unit.DoesNotExist:
        messages.error(request, _("指定單位不存在"))
        return JsonResponse(
            {"status": "error", "message": "指定單位不存在"}, status=404
        )
    except Exception as e:
        logger.error(f"刪除單位失敗: {str(e)}", exc_info=True)
        messages.error(request, _("刪除單位失敗，請聯繫管理員"))
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
