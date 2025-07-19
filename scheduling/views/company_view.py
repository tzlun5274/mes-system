from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils import timezone
from ..models import CompanyView, SchedulingOperationLog
import logging

logger = logging.getLogger('scheduling.views')

def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name='排程使用者').exists()

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def company_view(request):
    try:
        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action="查看公司檢視頁面",
            timestamp=timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        companies = CompanyView.objects.all()
        logger.debug(f"成功從 CompanyView 獲取公司數據: {companies}")
        return render(request, 'scheduling/company_view.html', {
            'companies': companies
        })
    except Exception as e:
        logger.error(f"處理 /scheduling/company_view/ 請求時發生錯誤: {str(e)}", exc_info=True)
        messages.error(request, _("無法加載公司檢視頁面，請聯繫管理員"))
        return render(request, 'scheduling/company_view.html', {
            'companies': []
        })
