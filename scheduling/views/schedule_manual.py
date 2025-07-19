print("schedule_manual.py 被載入")
# scheduling/views/schedule_manual.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from process.models import ProductProcessRoute, ProcessName, ProcessEquipment
from scheduling.models import OrderMain  # 訂單主檔標準名稱
from scheduling.algorithms import calculate_task_duration
from equip.models import Equipment
import logging

logger = logging.getLogger(__name__)


def scheduling_user_required(user):
    return user.is_superuser or user.groups.filter(name="排程使用者").exists()


def get_standard_capacity_for_route(product_code, process_name):
    """
    查詢產品工序的標準產能資料
    
    參數：
        product_code: 產品編號
        process_name: 工序名稱
    
    回傳：
        標準每小時產能，如果找不到則回傳預設值 1000
    """
    try:
        from process.models import ProductProcessStandardCapacity
        
        # 查詢最新的有效標準產能資料
        capacity_data = ProductProcessStandardCapacity.objects.filter(
            product_code=product_code,
            process_name=process_name,
            is_active=True
        ).order_by('-version').first()
        
        if capacity_data:
            return capacity_data.standard_capacity_per_hour
        else:
            return 1000  # 預設值
            
    except Exception as e:
        logger.error(f"查詢標準產能資料失敗: {str(e)}")
        return 1000  # 預設值


def product_capacity_setting(request):
    orders = OrderMain.objects.all().order_by("-updated_at")
    selected_order_id = request.GET.get("order_id") or request.POST.get("order_id")
    selected_order = None
    tasks = []
    processes = ProcessName.objects.all()
    show_manual_form = False
    qty_remain = 0
    overtime_hours = 3
    equipments = Equipment.objects.all()

    if selected_order_id:
        try:
            selected_order = orders.get(id=selected_order_id)
            qty_remain = selected_order.qty_remain
            routes = ProductProcessRoute.objects.filter(
                product_id=selected_order.product_id
            ).order_by("step_order")
            for route in routes:
                route_id = route.id
                parallel = 1
                overtime = False
                if request.method == "POST":
                    parallel = int(request.POST.get(f"tasks[{route_id}][parallel]", 1))
                    overtime = (
                        request.POST.get(f"tasks[{route_id}][overtime]", "0") == "1"
                    )
                hours = 0
                
                # 使用標準產能資料計算工時
                capacity_per_hour = get_standard_capacity_for_route(
                    product_code=selected_order.product_id,
                    process_name=route.process_name.name
                )
                
                if capacity_per_hour > 0 and qty_remain > 0 and parallel > 0:
                    hours = qty_remain / (capacity_per_hour * parallel)
                daily_hours = 8 + (overtime_hours if overtime else 0)
                days = round(hours / daily_hours, 2) if daily_hours > 0 else 0
                is_smt_process = False
                if (
                    "SMT" in route.process_name.name.upper()
                    or "貼片" in route.process_name.name
                ):
                    is_smt_process = True
                smt_equipment_count = ProcessEquipment.objects.filter(
                    process_name=route.process_name, equipment_type="smt"
                ).count()
                if smt_equipment_count > 0:
                    is_smt_process = True
                tasks.append(
                    {
                        "step_order": route.step_order,
                        "process": route.process_name,
                        "description": route.process_name.description,
                        "days": days,
                        "hours": round(hours, 1),
                        "capacity_per_hour": route.capacity_per_hour,
                        "overtime_hours": overtime_hours,
                        "overtime": overtime,
                        "parallel": parallel,
                        "route": route,
                        "is_smt_process": is_smt_process,
                    }
                )
            show_manual_form = True
        except Exception as e:
            return render(
                request,
                "scheduling/product_capacity_setting.html",
                {
                    "orders": orders,
                    "selected_order_id": selected_order_id,
                    "error_message": f"查詢訂單或工序時發生錯誤：{str(e)}",
                    "equipments": equipments,
                },
            )

    context = {
        "orders": orders,
        "selected_order_id": selected_order_id,
        "tasks": tasks,
        "processes": processes,
        "show_manual_form": show_manual_form,
        "qty_remain": qty_remain,
        "overtime_hours": overtime_hours,
        "equipments": equipments,
    }
    return render(request, "scheduling/product_capacity_setting.html", context)
