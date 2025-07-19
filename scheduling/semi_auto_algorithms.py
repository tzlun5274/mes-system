import logging
import random
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Tuple, Optional
from django.db.models import Q
from .models import Event, Unit

logger = logging.getLogger(__name__)

TAIWAN_TZ = ZoneInfo("Asia/Taipei")
global_schedule_time: datetime = datetime.now(TAIWAN_TZ)


def set_global_schedule_time(start_time: datetime) -> None:
    global global_schedule_time
    global_schedule_time = start_time


def calculate_task_duration(order_qty: int, capacity_per_hour: float) -> int:
    if capacity_per_hour <= 0:
        logger.error("產能每小時必須大於 0")
        raise ValueError("產能每小時無效")
    hours_needed = order_qty / capacity_per_hour
    minutes_needed = int(hours_needed * 60)
    print(
        f"[DEBUG] calculate_task_duration: order_qty={order_qty}, capacity_per_hour={capacity_per_hour}, hours_needed={hours_needed}, minutes_needed={minutes_needed}"
    )
    return max(minutes_needed, 1)


def select_operator(process_id: int, operators: List[Dict[str, Any]]) -> Optional[Dict]:
    try:
        available_operators = [
            op
            for op in operators
            if any(
                skill.get("process_name__id") == process_id
                for skill in op.get("skills", [])
            )
        ]
        if not available_operators:
            logger.debug(f"工序 ID {process_id} 無可用作業員")
            return None
        return random.choice(available_operators)
    except Exception as e:
        logger.error(f"選擇作業員失敗: {str(e)}")
        return None


def is_workday(date: datetime) -> bool:
    if date.weekday() >= 5:
        workday_exists = Event.objects.filter(
            type="workday",
            start__lte=date.replace(hour=23, minute=59, second=59, microsecond=999999),
            end__gte=date.replace(hour=0, minute=0, second=0, microsecond=0),
            all_day=True,
        ).exists()
        if not workday_exists:
            return False
    holiday_exists = Event.objects.filter(
        type="holiday",
        start__lte=date.replace(hour=23, minute=59, second=59, microsecond=999999),
        end__gte=date.replace(hour=0, minute=0, second=0, microsecond=0),
        all_day=True,
    ).exists()
    return not holiday_exists


def find_next_workday(current_time: datetime) -> datetime:
    next_time = current_time
    while not is_workday(next_time):
        next_time = next_time.replace(
            hour=8, minute=30, second=0, microsecond=0
        ) + timedelta(days=1)
    return next_time


def adjust_time_within_work_hours(
    current_time: datetime, duration_minutes: int, unit_obj, overtime: bool
) -> Tuple[datetime, datetime]:
    """
    根據單位設定與加班狀態，計算跨日工時，支援午休與加班時段。
    """
    print(
        f"[DEBUG] adjust_time_within_work_hours: current_time={current_time}, duration_minutes={duration_minutes}, work_start={unit_obj.work_start}, work_end={unit_obj.work_end}, overtime={overtime}"
    )
    if not unit_obj.work_start or not unit_obj.work_end:
        raise ValueError("工作單位必須設定有效上班時間")
    # 準備時段
    work_periods = [(unit_obj.work_start, unit_obj.work_end)]
    if overtime and unit_obj.overtime_start and unit_obj.overtime_end:
        work_periods.append((unit_obj.overtime_start, unit_obj.overtime_end))
    remaining_minutes = duration_minutes
    start_time = current_time
    # 調整到下個工作日的上班時間
    while not is_workday(start_time):
        start_time = find_next_workday(start_time)
    first_start_time = start_time
    first_loop = True
    while remaining_minutes > 0:
        # 跳過假日
        while not is_workday(start_time):
            start_time = find_next_workday(start_time)
        used_today = False
        for period_start, period_end in work_periods:
            work_start_dt = start_time.replace(
                hour=period_start.hour,
                minute=period_start.minute,
                second=0,
                microsecond=0,
            )
            work_end_dt = start_time.replace(
                hour=period_end.hour, minute=period_end.minute, second=0, microsecond=0
            )
            if not first_loop:
                start_time = work_start_dt
            first_loop = False
            if start_time > work_end_dt:
                continue
            # 當天剩餘可用工時
            available_minutes = int((work_end_dt - start_time).total_seconds() // 60)
            # 扣除午休
            if unit_obj.has_lunch_break and unit_obj.lunch_start and unit_obj.lunch_end:
                lunch_start_dt = start_time.replace(
                    hour=unit_obj.lunch_start.hour,
                    minute=unit_obj.lunch_start.minute,
                    second=0,
                    microsecond=0,
                )
                lunch_end_dt = start_time.replace(
                    hour=unit_obj.lunch_end.hour,
                    minute=unit_obj.lunch_end.minute,
                    second=0,
                    microsecond=0,
                )
                if start_time < lunch_end_dt and lunch_start_dt < work_end_dt:
                    lunch_overlap_start = max(start_time, lunch_start_dt)
                    lunch_overlap_end = min(work_end_dt, lunch_end_dt)
                    lunch_minutes = max(
                        0,
                        int(
                            (lunch_overlap_end - lunch_overlap_start).total_seconds()
                            // 60
                        ),
                    )
                    available_minutes -= lunch_minutes
            print(
                f"[DEBUG] 當天: {start_time.date()} start_time={start_time}, work_start_dt={work_start_dt}, work_end_dt={work_end_dt}, 可用工時(分鐘): {available_minutes}, 剩餘: {remaining_minutes}"
            )
            if available_minutes <= 0:
                continue
            if remaining_minutes <= available_minutes:
                end_time = start_time + timedelta(minutes=remaining_minutes)
                # 若跨午休，需再往後推移
                if (
                    unit_obj.has_lunch_break
                    and unit_obj.lunch_start
                    and unit_obj.lunch_end
                ):
                    lunch_start_dt = start_time.replace(
                        hour=unit_obj.lunch_start.hour,
                        minute=unit_obj.lunch_start.minute,
                        second=0,
                        microsecond=0,
                    )
                    lunch_end_dt = start_time.replace(
                        hour=unit_obj.lunch_end.hour,
                        minute=unit_obj.lunch_end.minute,
                        second=0,
                        microsecond=0,
                    )
                    if start_time < lunch_start_dt < end_time:
                        end_time += lunch_end_dt - lunch_start_dt
                print(
                    f"[DEBUG] 累計完成: start_time={first_start_time}, end_time={end_time}"
                )
                return first_start_time, end_time
            else:
                print(
                    f"[DEBUG] 當天用完: {start_time} ~ {work_end_dt}, 用掉: {available_minutes} 分鐘"
                )
                remaining_minutes -= available_minutes
                start_time = work_end_dt
                used_today = True
        # 若今天所有時段都用完，進入下一天
        if used_today or not any(
            start_time
            < start_time.replace(hour=period_end.hour, minute=period_end.minute)
            for _, period_end in work_periods
        ):
            start_time = find_next_workday(start_time + timedelta(days=1))
    raise RuntimeError("工時累計異常")


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


def generate_semi_auto_tasks(
    order: Any,
    processes: List[Dict[str, Any]],
    operators: List[Dict[str, Any]],
    equipments: List[Dict[str, Any]],
    matched_routes: List[Dict[str, Any]],
    overtime_list: Optional[list] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
    global global_schedule_time
    tasks = []
    current_time = global_schedule_time

    try:
        if Event.objects.filter(type="production", order_id=str(order.id)).exists():
            return [], f"訂單 {order.id} 已排程", "請選擇其他訂單"
        if not Unit.objects.exists():
            return [], "未設定工作單位", "請先設定工作單位"
        unit = Unit.objects.first()
        if not unit.work_start or not unit.work_end:
            return [], f"單位 {unit.name} 無有效上班時間", "請設定單位時間"
        order_qty = int(order.qty_remain)
        if order_qty <= 0:
            return [], f"訂單 {order.id} 剩餘數量無效", "請檢查訂單"
        if not matched_routes:
            logger.warning(f"訂單 {order.id} 未找到產品路線")
            return [], f"訂單 {order.id} 無產品路線", "請設定產品路線"

        for idx, route in enumerate(matched_routes):
            process_id = route["process_name__id"]
            step_order = route["step_order"]
            equipment_ids = route.get("usable_equipment_ids", "")
            process = next((p for p in processes if p["id"] == process_id), None)
            if not process:
                logger.error(f"工序 ID {process_id} 不存在")
                return [], f"工序 ID {process_id} 不存在", "請檢查工序資料"
            
            # 使用標準產能資料計算持續時間
            capacity_per_hour = get_standard_capacity_for_route(
                product_code=order.product_id,
                process_name=process["name"]
            )
            duration_minutes = calculate_task_duration(order_qty, capacity_per_hour)

            # 取得設備的 unit_name
            unit_name = None
            selected_equipment = None
            if equipment_ids:
                valid_ids = [
                    int(eid)
                    for eid in equipment_ids.split(",")
                    if eid.strip().isdigit()
                ]
                for eq in equipments:
                    if eq["id"] in valid_ids:
                        selected_equipment = eq
                        unit_name = eq.get("unit_name")
                        break

            # 根據 unit_name 取得 Unit，若無則用「其他單位」
            if unit_name:
                unit_obj = Unit.objects.filter(name=unit_name).first()
                if not unit_obj:
                    unit_obj = (
                        Unit.objects.filter(name="其他單位").first()
                        or Unit.objects.first()
                    )
            else:
                unit_obj = (
                    Unit.objects.filter(name="其他單位").first() or Unit.objects.first()
                )
            if not unit_obj or not unit_obj.work_start or not unit_obj.work_end:
                return (
                    [],
                    f"單位 {unit_name or unit_obj.name if unit_obj else '未知'} 無有效上班時間",
                    "請設定單位時間",
                )

            if not is_workday(current_time):
                current_time = find_next_workday(current_time)
                logger.debug(f"調整到工作日: {current_time}")
            try:
                # overtime_list: 每個工序的 overtime 狀態
                overtime = False
                if overtime_list and idx < len(overtime_list):
                    overtime = overtime_list[idx]
                start_time, end_time = adjust_time_within_work_hours(
                    current_time, duration_minutes, unit_obj, overtime
                )
            except ValueError as e:
                logger.error(f"時間設定錯誤: {str(e)}")
                return [], f"時間設定錯誤: {str(e)}", "請檢查單位時間"
            selected_operator = select_operator(process_id, operators)
            task = {
                "order_id": order.id,
                "order_qty": order_qty,  # 傳遞訂單數量供前端使用
                "step_order": step_order,
                "process": {
                    "id": process_id,
                    "name": process["name"],
                },
                "operators": operators,
                "equipments": equipments if not unit_name else [],
                "selected_equipment": selected_equipment,
                "description": f"半自動排程 - 訂單 {order.id} - 工序 {process['name']}",
                "overtime": overtime,
            }
            print(
                f'[DEBUG] 工序: {process["name"]}, order_qty={order_qty}, duration_minutes={duration_minutes}, 單位={unit_name or unit_obj.name if unit_obj else "未知"}, overtime={overtime}'
            )
            print(
                f'[DEBUG] 工序: {process["name"]}, start_time={start_time}, end_time={end_time}'
            )
            tasks.append(task)
            current_time = end_time

        global_schedule_time = current_time
        return tasks, None, None
    except Exception as e:
        logger.error(f"生成半自動任務失敗: {str(e)}", exc_info=True)
        return (
            [],
            f"半自動排程失敗: {str(e)}",
            "請檢查日誌以獲取更多詳情，或聯繫系統管理員",
        )
