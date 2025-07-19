from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils import timezone
from scheduling.models import OrderMain, OrderUpdateSchedule  # type: ignore
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger("workorder.views")


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
def orders(request):
    try:
        logger.debug("進入 orders 視圖")
        # 這裡的 OperationLog 請依照 workorder 實際日誌模型調整
        # SchedulingOperationLog.objects.create(
        #     user=request.user.username,
        #     action="查看訂單列表",
        #     timestamp=timezone.now(),
        #     ip_address=request.META.get('REMOTE_ADDR')
        # )
        queryset = OrderMain.objects.filter(product_id__startswith="PFP-")  # type: ignore
        today = datetime.now(ZoneInfo("Asia/Taipei")).date()
        queryset = queryset.filter(pre_in_date__gt=today)
        product_id = request.GET.get("product_id")
        if product_id:
            queryset = queryset.filter(product_id__icontains=product_id)
        order_by = request.GET.get("order_by", "pre_in_date")
        order_dir = request.GET.get("order_dir", "desc")
        if order_by not in ["pre_in_date", "qty_remain"]:
            order_by = "pre_in_date"
        if order_dir == "asc":
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by("-" + order_by)
        orders = queryset
        order_schedule = OrderUpdateSchedule.objects.first()  # type: ignore
        last_updated = order_schedule.last_updated if order_schedule else None
        logger.debug(f"訂單數量: {orders.count()}, 上次更新時間: {last_updated}")
        return render(
            request,
            "workorder/order_list.html",
            {"orders": orders, "last_updated": last_updated},
        )
    except Exception as e:
        logger.error(f"處理 /workorder/orders/ 請求時發生錯誤: {str(e)}")
        messages.error(request, _("無法加載訂單列表，請聯繫管理員"))
        return render(
            request, "workorder/order_list.html", {"orders": [], "last_updated": None}
        )


def order_list(request):
    """
    訂單主檔列表頁面，顯示所有訂單主檔資料。
    """
    workorders = OrderMain.objects.all().order_by("-id")  # type: ignore
    return render(
        request, "workorder/workorder_main_list.html", {"workorders": workorders}
    )
