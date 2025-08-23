from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.apps import apps
from django.utils.translation import gettext as _
from django.utils import timezone
from ..models import CompanyView, SchedulingOperationLog
import logging

logger = logging.getLogger("scheduling.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def sync_companies(request):
    if request.method != "POST":
        return HttpResponseBadRequest("無效的請求方法")
    try:
        try:
            CompanyConfig = apps.get_model("erp_integration", "CompanyConfig")
            erp_companies = CompanyConfig.objects.values(
                "company_name", "mes_database", "notes"
            )
            logger.debug(f"從 erp_integration 獲取公司數據: {erp_companies}")
        except LookupError:
            logger.warning("erp_integration 模組未找到")
            return JsonResponse(
                {"status": "error", "message": "ERP整合模組未啟用"}, status=404
            )
        except Exception as e:
            logger.error(f"讀取 CompanyConfig 失敗: {str(e)}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": "無法讀取公司數據"}, status=500
            )

        CompanyView.objects.all().delete()
        logger.debug("已清空 CompanyView 資料表")
        for company in erp_companies:
            try:
                CompanyView.objects.create(
                    company_name=company["company_name"],
                    mes_database=company["mes_database"],
                    sync_database=company["notes"] or "",
                )
                logger.debug(f"成功寫入公司數據: {company['company_name']}")
            except Exception as e:
                logger.error(
                    f"寫入公司數據失敗: {company['company_name']}, 錯誤: {str(e)}",
                    exc_info=True,
                )
                continue

        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action="將 CompanyConfig 數據寫入 CompanyView",
            timestamp=timezone.now(),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return JsonResponse({"status": "success", "message": "公司數據寫入成功"})
    except Exception as e:
        logger.error(
            f"處理 /scheduling/sync_companies/ 請求時發生錯誤: {str(e)}", exc_info=True
        )
        return JsonResponse(
            {"status": "error", "message": f"寫入公司數據失敗: {str(e)}"}, status=500
        )
