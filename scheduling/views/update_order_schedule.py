from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext_lazy as gettext_lazy
from django.contrib import messages
from ..order_management import order_schedule_manager
import logging

logger = logging.getLogger('scheduling.views')

def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name='排程使用者').exists()

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def update_order_schedule(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("無效的請求方法")
    
    try:
        sync_interval_minutes = request.POST.get('sync_interval_minutes', '').strip()
        if not sync_interval_minutes:
            messages.error(request, gettext_lazy("請提供同步間隔時間"))
            return JsonResponse({'status': 'error', 'message': '請提供同步間隔時間'}, status=400)

        try:
            sync_interval_minutes = int(sync_interval_minutes)
        except ValueError:
            messages.error(request, gettext_lazy("請輸入有效的同步間隔時間（非負整數）"))
            return JsonResponse({'status': 'error', 'message': '請輸入有效的同步間隔時間'}, status=400)

        # 使用訂單排程管理器更新設定
        result = order_schedule_manager.update_sync_schedule(
            sync_interval_minutes=sync_interval_minutes,
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if result['status'] == 'success':
            messages.success(request, gettext_lazy("訂單更新排程設定成功！"))
            return JsonResponse(result)
        else:
            messages.error(request, gettext_lazy("更新訂單排程失敗，請聯繫管理員"))
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"更新訂單排程失敗: {str(e)}", exc_info=True)
        messages.error(request, gettext_lazy("更新訂單排程失敗，請聯繫管理員"))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
