from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from ..models import Event
import json

# 權限檢查


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


# 取得所有排程任務與依賴
@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
@require_GET
def api_schedule(request):
    events = Event.objects.filter(type="production").order_by("start")
    tasks = []
    for e in events:
        tasks.append(
            {
                "id": e.id,
                "text": e.title,
                "start_date": e.start.strftime("%Y-%m-%d %H:%M"),
                "end_date": e.end.strftime("%Y-%m-%d %H:%M"),
                "resource": e.equipment_id or "",
                "order_id": e.order_id or "",
                "progress": 0,
                "parent": 0,  # 可擴充分群
            }
        )
    # links: 目前無依賴資料，預留空陣列
    return JsonResponse({"tasks": tasks, "links": []})


# 任務調整（拖曳/縮放）
@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
@csrf_exempt
@require_POST
def api_schedule_manual(request):
    try:
        data = json.loads(request.body)
        event_id = data.get("id")
        start = data.get("start_date")
        end = data.get("end_date")
        event = Event.objects.get(id=event_id)
        event.start = timezone.datetime.strptime(start, "%Y-%m-%d %H:%M")
        event.end = timezone.datetime.strptime(end, "%Y-%m-%d %H:%M")
        event.save()
        return JsonResponse({"status": "success", "message": "任務已更新"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# 依賴線管理（暫不實作，預留接口）
@login_required
@user_passes_test(scheduling_user_required, login_url="/accounts/login/")
@csrf_exempt
@require_POST
def api_schedule_links(request):
    # 可擴充儲存依賴線資料
    return JsonResponse({"status": "success"})


@csrf_exempt
def calculate_task_duration(request):
    """
    接收前端傳來的所有工序資料，計算每個工序的工時與天數（每天8小時），回傳 JSON 結果。
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "msg": "只支援POST"}, status=400)
    try:
        data = json.loads(request.body)
        tasks = data.get("tasks", [])
        result = []
        for task in tasks:
            qty_remain = float(task.get("qty_remain", 0))
            # capacity_per_hour 相關程式碼已移除，請改用標準產能或其他欄位。
            parallel = int(task.get("parallel", 1))
            hours = qty_remain / (parallel) if parallel > 0 else 0
            days = hours / 8 if hours > 0 else 0
            result.append(
                {
                    "index": task.get("index"),
                    "hours": round(hours, 1),
                    "days": round(days, 2),
                }
            )
        return JsonResponse({"success": True, "result": result})
    except Exception as e:
        return JsonResponse({"success": False, "msg": str(e)}, status=500)
