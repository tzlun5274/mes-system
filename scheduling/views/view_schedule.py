from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from ..models import Event, OrderMain, SchedulingOperationLog
import logging
from datetime import timedelta
import re
import unicodedata
from django.http import JsonResponse
from django.views.decorators.http import require_POST

logger = logging.getLogger('scheduling.views')

def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name='排程使用者').exists()

@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def view_schedule(request):
    try:
        logger.info("開始查詢排程事件")
        events = Event.objects.filter(type='production').order_by('start')
        logger.info(f"查詢到 {events.count()} 筆排程事件")
        
        event_data = []
        seen_orders = set()
        product_id_choices = []

        # 批量查詢 OrderData
        order_ids = {event.order_id for event in events if event.order_id}
        logger.debug(f"訂單 ID 列表: {order_ids}")
        if order_ids:
            orders = OrderMain.objects.filter(id__in=[int(oid) for oid in order_ids]).values('id', 'product_id', 'pre_in_date')
            order_map = {str(order['id']): order for order in orders if order['product_id']}
            logger.debug(f"查詢到 {len(orders)} 筆訂單數據")
        else:
            orders = []
            order_map = {}

        for event in events:
            product_id = 'N/A'
            pre_in_date = 'N/A'
            order_id = event.order_id or 'N/A'
            process_name = 'N/A'

            # 提取工序名稱
            if event.description:
                description = unicodedata.normalize('NFKC', event.description.strip())
                logger.debug(f"事件 {event.id} description: {repr(description)}")
                match = re.search(r'工序[\s:]*([^\s-]+)', description, re.UNICODE)
                if match:
                    process_name = match.group(1).strip()
                    logger.debug(f"事件 {event.id} 工序名稱: {process_name}")
                else:
                    logger.warning(f"事件 {event.id} 未匹配工序名稱: {repr(description)}")

            if order_id in order_map:
                product_id = order_map[order_id].get('product_id', 'N/A')
                pre_in_date = order_map[order_id].get('pre_in_date', 'N/A')
                if order_id not in seen_orders and product_id != 'N/A':
                    product_id_choices.append({
                        'order_id': order_id,
                        'product_id': product_id
                    })
                    seen_orders.add(order_id)
                elif order_id not in seen_orders and product_id == 'N/A':
                    logger.warning(f"事件 {event.id} 的訂單 {order_id} 產品編號為 N/A，跳過")

            # 計算天數
            if event.start and event.end:
                days_span = (event.end.date() - event.start.date()).days + 1
            else:
                days_span = 0
                logger.warning(f"事件 {event.id} 缺少時間，無法計算天數")

            # 計算工時
            if event.start and event.end:
                duration = event.end - event.start
                duration_hours = round(duration.total_seconds() / 3600, 2)
            else:
                duration_hours = 0
                logger.warning(f"事件 {event.id} 缺少時間，無法計算工時")

            event_data.append({
                'event': event,
                'product_id': product_id,
                'pre_in_date': pre_in_date,
                'days_span': days_span,
                'duration_hours': duration_hours,
                'process_name': process_name
            })

        logger.info(f"生成 product_id_choices: {product_id_choices}")
        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action="查看排程",
            timestamp=timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return render(request, 'scheduling/view_schedule.html', {
            'event_data': event_data,
            'product_id_choices': product_id_choices
        })
    except Exception as e:
        logger.error(f"處理 /scheduling/view_schedule/ 請求時發生錯誤: {str(e)}", exc_info=True)
        messages.error(request, _("無法加載排程，請聯繫管理員"))
        return render(request, 'scheduling/view_schedule.html', {
            'event_data': [],
            'product_id_choices': []
        })

@require_POST
@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def delete_all_production_events(request):
    try:
        deleted_count, _ = Event.objects.filter(type='production').delete()
        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action="刪除全部排程事件",
            timestamp=timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return JsonResponse({'status': 'success', 'deleted_count': deleted_count})
    except Exception as e:
        logger.error(f"刪除全部排程事件失敗: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
@login_required
@user_passes_test(scheduling_user_required, login_url='/accounts/login/')
def delete_order_production_events(request):
    order_id = request.POST.get('order_id')
    if not order_id:
        return JsonResponse({'status': 'error', 'message': '缺少訂單編號'}, status=400)
    try:
        deleted_count, _ = Event.objects.filter(type='production', order_id=order_id).delete()
        SchedulingOperationLog.objects.create(
            user=request.user.username,
            action=f"刪除訂單 {order_id} 的所有排程事件",
            timestamp=timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return JsonResponse({'status': 'success', 'deleted_count': deleted_count})
    except Exception as e:
        logger.error(f"刪除訂單 {order_id} 的排程事件失敗: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
