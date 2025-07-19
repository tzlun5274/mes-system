import logging
from datetime import datetime
from django.utils import timezone
from zoneinfo import ZoneInfo
import requests
from .models import SchedulingOperationLog

logger = logging.getLogger('scheduling.utils')
TAIWAN_TZ = ZoneInfo("Asia/Taipei")

def log_user_operation(username, module, action, ip_address=None, event_related=None):
    """
    記錄用戶操作到 SchedulingOperationLog 模型。
    Args:
        username (str): 用戶名
        module (str): 模組名稱
        action (str): 操作描述
        ip_address (str, 可選): 用戶的 IP 地址
        event_related (Event, 可選): 關聯的事件對象
    """
    if not username or not module or not action:
        logger.error("記錄操作日誌失敗: 用戶名、模組名稱或操作描述不能為空")
        return
    try:
        SchedulingOperationLog.objects.create(
            user=username,
            action=f"{module}: {action}",
            timestamp=timezone.now(),
            ip_address=ip_address,
            event_related=event_related
        )
        logger.debug(f"成功記錄操作日誌: {username} - {module}: {action}")
    except Exception as e:
        logger.error(f"記錄操作日誌失敗: {str(e)}")

def log_operation(user, action, ip_address, event_related=None):
    """
    記錄操作日誌（舊版相容函數）。
    """
    log_user_operation(user, "scheduling", action, ip_address, event_related)

def check_holiday_conflicts(tasks):
    """
    檢查任務是否與假期衝突。
    Args:
        tasks: 任務列表，每個任務包含 start_time 和 end_time（格式為 'YYYY-MM-DDTHH:MM'）。
    Returns:
        衝突列表，若無衝突則返回空列表。
    """
    conflicts = []
    try:
        holiday_response = requests.get('http://localhost:8000/scheduling/api/holidays/', timeout=10)
        if holiday_response.status_code != 200:
            logger.error(f"無法獲取假期數據，狀態碼: {holiday_response.status_code}")
            return conflicts

        holidays = holiday_response.json().get('holidays', [])
        for task in tasks:
            start_time = task.get('start_time')
            end_time = task.get('end_time')
            if not (start_time and end_time):
                continue

            try:
                start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M').replace(tzinfo=TAIWAN_TZ)
                end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M').replace(tzinfo=TAIWAN_TZ)
            except ValueError as e:
                logger.error(f"任務時間格式無效: {str(e)}")
                continue

            for holiday in holidays:
                holiday_start = datetime.strptime(holiday['start_date'], '%Y-%m-%d').replace(tzinfo=TAIWAN_TZ)
                holiday_end = datetime.strptime(holiday['end_date'], '%Y-%m-%d').replace(tzinfo=TAIWAN_TZ)
                if (start_datetime.date() <= holiday_end.date() and end_datetime.date() >= holiday_start.date()):
                    conflicts.append({
                        'task': task,
                        'holiday': holiday['name'],
                        'holiday_start': holiday['start_date'],
                        'holiday_end': holiday['end_date']
                    })
    except Exception as e:
        logger.error(f"檢查假期衝突失敗: {str(e)}")
    return conflicts
