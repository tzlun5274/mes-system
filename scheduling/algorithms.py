import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

TAIWAN_TZ = ZoneInfo("Asia/Taipei")
global_schedule_time: datetime = datetime.now(TAIWAN_TZ)


def set_global_schedule_time(start_time: datetime) -> None:
    global global_schedule_time
    global_schedule_time = start_time


def check_holiday_conflicts(tasks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    from .models import Event

    conflicts = []
    for task in tasks:
        start_time = datetime.strptime(task["start_time"], "%Y-%m-%dT%H:%M").replace(
            tzinfo=TAIWAN_TZ
        )
        end_time = datetime.strptime(task["end_time"], "%Y-%m-%dT%H:%M").replace(
            tzinfo=TAIWAN_TZ
        )
        holidays = Event.objects.filter(
            type="holiday", start__lt=end_time, end__gt=start_time, all_day=True
        )
        for holiday in holidays:
            conflicts.append(
                {
                    "task_start": task["start_time"],
                    "task_end": task["end_time"],
                    "holiday_title": holiday.title,
                    "holiday_start": holiday.start.strftime("%Y-%m-%d %H:%M"),
                    "holiday_end": holiday.end.strftime("%Y-%m-%d %H:%M"),
                }
            )
    return conflicts


def check_resource_conflicts(
    equipment_id: Optional[int] = None,
    smt_equipment_id: Optional[int] = None,
    operator_id: Optional[int] = None,
    start_time: str = "",
    end_time: str = "",
    exclude_event_id: Optional[int] = None,
) -> List[str]:
    from .models import Event

    conflicts = []
    try:
        start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M").replace(
            tzinfo=TAIWAN_TZ
        )
        end_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M").replace(tzinfo=TAIWAN_TZ)
    except ValueError as e:
        return [f"時間格式無效: {str(e)}"]

    base_query = Event.objects.filter(start__lt=end_dt, end__gt=start_dt)
    if exclude_event_id:
        base_query = base_query.exclude(id=exclude_event_id)

    if equipment_id:
        conflicting_events = base_query.filter(equipment_id=equipment_id)
        for event in conflicting_events:
            conflicts.append(
                f"設備衝突: 設備 ID {equipment_id} 在 {event.start} 至 {event.end} 已被事件 '{event.title}' 占用"
            )

    if smt_equipment_id:
        conflicting_events = base_query.filter(smt_equipment_id=smt_equipment_id)
        for event in conflicting_events:
            conflicts.append(
                f"SMT 設備衝突: SMT 設備 ID {smt_equipment_id} 在 {event.start} 至 {event.end} 已被事件 '{event.title}' 占用"
            )

    if operator_id:
        conflicting_events = base_query.filter(employee_id=operator_id)
        for event in conflicting_events:
            conflicts.append(
                f"作業員衝突: 作業員 ID {operator_id} 在 {event.start} 至 {event.end} 已被事件 '{event.title}' 占用"
            )

    return conflicts


def calculate_task_duration(order_qty, capacity_per_hour):
    """
    計算任務持續時間（分鐘）
    
    參數：
        order_qty: 訂單數量
        capacity_per_hour: 每小時產能
    
    回傳：
        持續時間（分鐘）
    """
    if capacity_per_hour <= 0:
        return 60  # 預設 1 小時
    
    # 計算小時數，然後轉換為分鐘
    hours = order_qty / capacity_per_hour
    minutes = hours * 60
    
    # 最少 15 分鐘，最多 24 小時
    return max(15, min(minutes, 24 * 60))


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


def get_available_resources(
    process_id: int,
    processes: List[Dict[str, Any]],
    operators: List[Dict[str, Any]],
    equipments: List[Dict[str, Any]],
    smt_equipments: List[Dict[str, Any]],
    start_time: datetime,
    duration_minutes: int,
) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
    process = next((p for p in processes if p["id"] == process_id), None)
    if not process:
        logger.error(f"工序 ID {process_id} 不存在")
        return None, None, None

    end_time = start_time + timedelta(minutes=duration_minutes)
    available_operator = None
    available_equipment = None
    available_smt_equipment = None

    # 檢查是否為 SMT 工序
    is_smt = process.get("is_smt", False)

    # 查找可用作業員
    retry_attempts = 5
    retry_interval = 30  # 分鐘
    current_start_time = start_time

    for attempt in range(retry_attempts):
        for operator in operators:
            if process["id"] not in operator.get("process_names", []):
                continue
            conflicts = check_resource_conflicts(
                operator_id=operator["id"],
                start_time=current_start_time.strftime("%Y-%m-%dT%H:%M"),
                end_time=(
                    current_start_time + timedelta(minutes=duration_minutes)
                ).strftime("%Y-%m-%dT%H:%M"),
            )
            if not conflicts:
                available_operator = operator
                break
        if available_operator:
            break
        current_start_time += timedelta(minutes=retry_interval)
        logger.debug(
            f"作業員資源不可用，第 {attempt + 1} 次重試，調整開始時間為 {current_start_time}"
        )

    if not available_operator:
        logger.warning(
            f"無法為工序 {process_id} 找到可用作業員，嘗試了 {retry_attempts} 次"
        )
        return None, None, None

    # 根據工序類型查找可用設備
    current_start_time = start_time if not available_operator else current_start_time
    for attempt in range(retry_attempts):
        if is_smt:
            for smt_equipment in smt_equipments:
                conflicts = check_resource_conflicts(
                    smt_equipment_id=smt_equipment["id"],
                    start_time=current_start_time.strftime("%Y-%m-%dT%H:%M"),
                    end_time=(
                        current_start_time + timedelta(minutes=duration_minutes)
                    ).strftime("%Y-%m-%dT%H:%M"),
                )
                if not conflicts:
                    available_smt_equipment = smt_equipment
                    break
        else:
            for equipment in equipments:
                if process["id"] not in equipment.get("process_names", []):
                    continue
                conflicts = check_resource_conflicts(
                    equipment_id=equipment["id"],
                    start_time=current_start_time.strftime("%Y-%m-%dT%H:%M"),
                    end_time=(
                        current_start_time + timedelta(minutes=duration_minutes)
                    ).strftime("%Y-%m-%dT%H:%M"),
                )
                if not conflicts:
                    available_equipment = equipment
                    break
        if (
            available_equipment
            or available_smt_equipment
            or (not is_smt and not equipments)
        ):
            break
        current_start_time += timedelta(minutes=retry_interval)
        logger.debug(
            f"設備資源不可用，第 {attempt + 1} 次重試，調整開始時間為 {current_start_time}"
        )

    if not (
        available_equipment
        or available_smt_equipment
        or (not is_smt and not equipments)
    ):
        logger.warning(
            f"無法為工序 {process_id} 找到可用設備，嘗試了 {retry_attempts} 次"
        )
        return None, None, None

    return available_operator, available_equipment, available_smt_equipment


def generate_auto_tasks(
    order: Any,
    processes: List[Dict[str, Any]],
    operators: List[Dict[str, Any]],
    equipments: List[Dict[str, Any]],
    smt_equipments: List[Dict[str, Any]],
    matched_routes: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
    global global_schedule_time
    tasks = []
    current_time = global_schedule_time

    try:
        order_qty = int(order.qty_remain)
        if order_qty <= 0:
            return [], "訂單剩餘數量必須大於 0", "請檢查訂單數據"

        for route in matched_routes:
            process_id = route["process_name__id"]
            step_order = route["step_order"]

            process = next((p for p in processes if p["id"] == process_id), None)
            if not process:
                return [], f"工序 ID {process_id} 不存在", "請檢查工序數據"

            # 使用標準產能資料計算持續時間
            capacity_per_hour = get_standard_capacity_for_route(
                product_code=order.product_id,
                process_name=process["name"]
            )
            duration_minutes = calculate_task_duration(order_qty, capacity_per_hour)
            start_time = current_time

            operator, equipment, smt_equipment = get_available_resources(
                process_id=process_id,
                processes=processes,
                operators=operators,
                equipments=equipments,
                smt_equipments=smt_equipments,
                start_time=start_time,
                duration_minutes=duration_minutes,
            )

            if operator and (
                equipment or smt_equipment or not process.get("is_smt", False)
            ):
                end_time = start_time + timedelta(minutes=duration_minutes)
                task = {
                    "order_id": order.id,
                    "step_order": step_order,
                    "process": {"id": process_id, "name": process["name"]},
                    "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
                    "end_time": end_time.strftime("%Y-%m-%dT%H:%M"),
                    "selected_operator": operator,
                    "selected_equipment": equipment,
                    "selected_smt_equipment": smt_equipment,
                    "description": f"自動排程生成 - 訂單 {order.id} - 工序 {process['name']}",
                }
                tasks.append(task)
                current_time = end_time
            else:
                return (
                    [],
                    "無法找到可用資源來排程此任務",
                    "建議增加設備或作業員資源，或調整訂單的預交貨日期",
                )

        global_schedule_time = current_time
        return tasks, None, None

    except Exception as e:
        logger.error(f"生成全自動任務失敗: {str(e)}", exc_info=True)
        return (
            [],
            f"全自動排程失敗: {str(e)}",
            "請檢查日誌以獲取更多詳情，或聯繫系統管理員",
        )


# ==================== 優化全自動排程算法 ====================


class OptimizedAutoScheduler:
    """優化的全自動排程器"""

    def __init__(self, processes, operators, equipments, smt_equipments):
        self.processes = processes
        self.operators = operators
        self.equipments = equipments
        self.smt_equipments = smt_equipments
        self.resource_timeline = {}  # 資源時間線
        self.order_priority_scores = {}  # 訂單優先級分數

    def calculate_order_priority(self, order, current_time):
        """計算訂單優先級分數"""
        priority_score = 0

        # 交貨期緊急程度 (40%)
        if order.pre_in_date and order.pre_in_date != "N/A":
            try:
                pre_in_date = datetime.strptime(order.pre_in_date, "%Y-%m-%d").replace(
                    tzinfo=TAIWAN_TZ
                )
                days_until_delivery = (
                    pre_in_date
                    - current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                ).days
                if days_until_delivery <= 3:
                    priority_score += 40
                elif days_until_delivery <= 7:
                    priority_score += 30
                elif days_until_delivery <= 14:
                    priority_score += 20
                elif days_until_delivery <= 30:
                    priority_score += 10
            except ValueError:
                pass

        # 訂單數量 (20%)
        try:
            qty = int(order.qty_remain)
            if qty <= 100:
                priority_score += 20  # 小訂單優先
            elif qty <= 500:
                priority_score += 15
            elif qty <= 1000:
                priority_score += 10
            else:
                priority_score += 5
        except (ValueError, TypeError):
            pass

        # 訂單類型 (20%)
        if hasattr(order, "order_type"):
            if order.order_type == "urgent":
                priority_score += 20
            elif order.order_type == "normal":
                priority_score += 15
            elif order.order_type == "flexible":
                priority_score += 10

        # 客戶重要性 (20%)
        if hasattr(order, "customer_priority"):
            priority_score += order.customer_priority * 4

        return priority_score

    def find_optimal_resource_slot(
        self, process_id, duration_minutes, start_time, end_time
    ):
        """尋找最佳資源時間槽"""
        process = next((p for p in self.processes if p["id"] == process_id), None)
        if not process:
            return None, None, None, None

        is_smt = process.get("is_smt", False)
        best_slot = None
        best_score = float("inf")

        # 在時間範圍內尋找最佳時間槽
        current_time = start_time
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_score = self.evaluate_time_slot(
                current_time, duration_minutes, process_id, is_smt
            )
            if slot_score < best_score:
                best_score = slot_score
                best_slot = current_time
            current_time += timedelta(minutes=30)  # 30分鐘間隔

        if best_slot is None:
            return None, None, None, None

        # 為最佳時間槽分配資源
        operator, equipment, smt_equipment = self.allocate_resources_for_slot(
            process_id, best_slot, duration_minutes, is_smt
        )

        return best_slot, operator, equipment, smt_equipment

    def evaluate_time_slot(self, start_time, duration_minutes, process_id, is_smt):
        """評估時間槽的適合度"""
        score = 0
        end_time = start_time + timedelta(minutes=duration_minutes)

        # 檢查是否在工作時間內
        hour = start_time.hour
        if hour < 8 or hour > 18:  # 非工作時間
            score += 100

        # 檢查是否在週末
        if start_time.weekday() >= 5:  # 週六、週日
            score += 50

        # 檢查資源可用性
        available_operators = self.get_available_operators(
            start_time, end_time, process_id
        )
        if not available_operators:
            score += 1000  # 無可用作業員

        if is_smt:
            available_equipment = self.get_available_smt_equipment(start_time, end_time)
            if not available_equipment:
                score += 1000  # 無可用SMT設備
        else:
            available_equipment = self.get_available_equipment(
                start_time, end_time, process_id
            )
            if not available_equipment:
                score += 1000  # 無可用設備

        # 檢查與其他任務的間隔
        score += self.calculate_setup_time_penalty(start_time, end_time)

        return score

    def get_available_operators(self, start_time, end_time, process_id):
        """獲取可用作業員"""
        available = []
        for operator in self.operators:
            if process_id not in operator.get("process_names", []):
                continue
            conflicts = check_resource_conflicts(
                operator_id=operator["id"],
                start_time=start_time.strftime("%Y-%m-%dT%H:%M"),
                end_time=end_time.strftime("%Y-%m-%dT%H:%M"),
            )
            if not conflicts:
                available.append(operator)
        return available

    def get_available_equipment(self, start_time, end_time, process_id):
        """獲取可用設備"""
        available = []
        for equipment in self.equipments:
            if process_id not in equipment.get("process_names", []):
                continue
            conflicts = check_resource_conflicts(
                equipment_id=equipment["id"],
                start_time=start_time.strftime("%Y-%m-%dT%H:%M"),
                end_time=end_time.strftime("%Y-%m-%dT%H:%M"),
            )
            if not conflicts:
                available.append(equipment)
        return available

    def get_available_smt_equipment(self, start_time, end_time):
        """獲取可用SMT設備"""
        available = []
        for smt_equipment in self.smt_equipments:
            conflicts = check_resource_conflicts(
                smt_equipment_id=smt_equipment["id"],
                start_time=start_time.strftime("%Y-%m-%dT%H:%M"),
                end_time=end_time.strftime("%Y-%m-%dT%H:%M"),
            )
            if not conflicts:
                available.append(smt_equipment)
        return available

    def calculate_setup_time_penalty(self, start_time, end_time):
        """計算設置時間懲罰"""
        penalty = 0
        # 檢查前後任務的設置時間需求
        # 這裡可以根據實際需求調整
        return penalty

    def allocate_resources_for_slot(
        self, process_id, start_time, duration_minutes, is_smt
    ):
        """為時間槽分配資源"""
        end_time = start_time + timedelta(minutes=duration_minutes)

        # 選擇負載最輕的作業員
        available_operators = self.get_available_operators(
            start_time, end_time, process_id
        )
        if not available_operators:
            return None, None, None

        # 選擇工作負載最輕的作業員
        operator = min(
            available_operators, key=lambda op: self.get_operator_workload(op["id"])
        )

        equipment = None
        smt_equipment = None

        if is_smt:
            available_smt = self.get_available_smt_equipment(start_time, end_time)
            if available_smt:
                smt_equipment = min(
                    available_smt,
                    key=lambda eq: self.get_equipment_workload(eq["id"], "smt"),
                )
        else:
            available_eq = self.get_available_equipment(
                start_time, end_time, process_id
            )
            if available_eq:
                equipment = min(
                    available_eq,
                    key=lambda eq: self.get_equipment_workload(eq["id"], "normal"),
                )

        return operator, equipment, smt_equipment

    def get_operator_workload(self, operator_id):
        """獲取作業員工作負載"""
        # 這裡可以實現更複雜的負載計算邏輯
        return 0

    def get_equipment_workload(self, equipment_id, equipment_type):
        """獲取設備工作負載"""
        # 這裡可以實現更複雜的負載計算邏輯
        return 0

    def schedule_order(self, order, routes, current_time):
        """排程單個訂單"""
        tasks = []
        order_qty = int(order.qty_remain)

        # 計算訂單完成的最晚時間
        max_end_time = current_time + timedelta(days=30)  # 最多排程30天後

        for route in sorted(routes, key=lambda x: x["step_order"]):
            process_id = route["process_name__id"]
            step_order = route["step_order"]

            duration_minutes = calculate_task_duration(order_qty, 0)

            # 尋找最佳時間槽
            start_time, operator, equipment, smt_equipment = (
                self.find_optimal_resource_slot(
                    process_id, duration_minutes, current_time, max_end_time
                )
            )

            if start_time is None:
                return (
                    [],
                    f"無法為工序 {process_id} 找到合適的時間槽",
                    "建議調整訂單優先級或增加資源",
                )

            end_time = start_time + timedelta(minutes=duration_minutes)

            process_name = next(
                (p["name"] for p in self.processes if p["id"] == process_id), "Unknown"
            )
            task = {
                "order_id": order.id,
                "step_order": step_order,
                "process": {"id": process_id, "name": process_name},
                "start_time": start_time.strftime("%Y-%m-%dT%H:%M"),
                "end_time": end_time.strftime("%Y-%m-%dT%H:%M"),
                "selected_operator": operator,
                "selected_equipment": equipment,
                "selected_smt_equipment": smt_equipment,
                "description": f"優化自動排程 - 訂單 {order.id} - 工序 {process_name}",
            }
            tasks.append(task)

            # 更新當前時間為任務結束時間
            current_time = end_time

        return tasks, None, None


def generate_optimized_auto_tasks(
    orders: List[Any],
    processes: List[Dict[str, Any]],
    operators: List[Dict[str, Any]],
    equipments: List[Dict[str, Any]],
    smt_equipments: List[Dict[str, Any]],
    routes_by_order: Dict[int, List[Dict[str, Any]]],
    current_time: datetime,
) -> Tuple[List[Dict[str, Any]], Dict[int, Tuple[str, str]]]:
    """
    生成優化的全自動排程任務

    Args:
        orders: 訂單列表
        processes: 工序列表
        operators: 作業員列表
        equipments: 設備列表
        smt_equipments: SMT設備列表
        routes_by_order: 每個訂單的工序路線
        current_time: 當前時間

    Returns:
        (tasks, failed_orders): 任務列表和失敗的訂單
    """
    scheduler = OptimizedAutoScheduler(processes, operators, equipments, smt_equipments)

    # 計算所有訂單的優先級
    order_priorities = []
    for order in orders:
        priority = scheduler.calculate_order_priority(order, current_time)
        order_priorities.append((order, priority))

    # 按優先級排序訂單
    order_priorities.sort(key=lambda x: x[1], reverse=True)

    all_tasks = []
    failed_orders = {}

    for order, priority in order_priorities:
        routes = routes_by_order.get(order.id, [])
        if not routes:
            failed_orders[order.id] = (
                f"訂單 {order.id} 沒有工序路線",
                "請在工序管理中設定產品工序路線",
            )
            continue

        tasks, reason, suggestion = scheduler.schedule_order(
            order, routes, current_time
        )

        if not tasks and reason:
            failed_orders[order.id] = (reason, suggestion)
            continue

        all_tasks.extend(tasks)

        # 更新當前時間為最後一個任務的結束時間
        if tasks:
            last_task = tasks[-1]
            current_time = datetime.strptime(
                last_task["end_time"], "%Y-%m-%dT%H:%M"
            ).replace(tzinfo=TAIWAN_TZ)

    return all_tasks, failed_orders
