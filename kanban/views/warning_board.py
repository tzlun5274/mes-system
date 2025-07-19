from django.shortcuts import render
from django.core.paginator import Paginator


def schedule_warning_board(request):
    """
    排程警告看板：分頁顯示所有排程驗證警告（每頁 20 筆）
    """
    from scheduling.scheduling_models import (
        ScheduleWarning,
    )  # 只在函式內 import，避免啟動卡住

    warnings_list = ScheduleWarning.objects.all().order_by("-created_at")
    paginator = Paginator(warnings_list, 20)  # 每頁 20 筆
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "kanban/schedule_warning_board.html", {"page_obj": page_obj})
