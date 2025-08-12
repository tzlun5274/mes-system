"""
MES 系統日期處理工具模組
提供統一的日期格式轉換與驗證功能
支援多種常見日期格式輸入，統一轉換為標準格式
"""

from datetime import datetime, date
import re
from typing import Union, Optional


def normalize_date_string(date_str: str) -> Optional[str]:
    """
    將各種日期字串格式正規化為 YYYY-MM-DD 格式
    
    支援格式：
    - 2025-08-12, 2025/08/12, 2025.08.12
    - 20250812
    - 12/08/2025, 12-08-2025, 12.08.2025
    - 08/12/2025, 08-12-2025, 08.12.2025 (美式)
    
    Args:
        date_str: 輸入的日期字串
        
    Returns:
        正規化後的日期字串 (YYYY-MM-DD) 或 None (無法解析時)
    """
    if not date_str:
        return None
    
    # 移除空白字元
    date_str = str(date_str).strip()
    if not date_str:
        return None
    
    # 嘗試各種格式解析
    formats_to_try = [
        # ISO 標準格式
        ('%Y-%m-%d', r'^\d{4}-\d{1,2}-\d{1,2}$'),
        ('%Y/%m/%d', r'^\d{4}/\d{1,2}/\d{1,2}$'),
        ('%Y.%m.%d', r'^\d{4}\.\d{1,2}\.\d{1,2}$'),
        
        # 緊密格式
        ('%Y%m%d', r'^\d{8}$'),
        
        # 日月年格式
        ('%d/%m/%Y', r'^\d{1,2}/\d{1,2}/\d{4}$'),
        ('%d-%m-%Y', r'^\d{1,2}-\d{1,2}-\d{4}$'),
        ('%d.%m.%Y', r'^\d{1,2}\.\d{1,2}\.\d{4}$'),
        
        # 美式格式 (月日年)
        ('%m/%d/%Y', r'^\d{1,2}/\d{1,2}/\d{4}$'),
        ('%m-%d-%Y', r'^\d{1,2}-\d{1,2}-\d{4}$'),
        ('%m.%d.%Y', r'^\d{1,2}\.\d{1,2}\.\d{4}$'),
    ]
    
    for date_format, pattern in formats_to_try:
        if re.match(pattern, date_str):
            try:
                parsed_date = datetime.strptime(date_str, date_format).date()
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
    
    return None


def normalize_datetime_string(datetime_str: str) -> Optional[str]:
    """
    將各種日期時間字串格式正規化為 YYYY-MM-DD HH:MM:SS 格式
    
    Args:
        datetime_str: 輸入的日期時間字串
        
    Returns:
        正規化後的日期時間字串 (YYYY-MM-DD HH:MM:SS) 或 None
    """
    if not datetime_str:
        return None
    
    datetime_str = str(datetime_str).strip()
    if not datetime_str:
        return None
    
    # 嘗試各種格式解析
    formats_to_try = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y.%m.%d %H:%M:%S',
        '%Y.%m.%d %H:%M',
        '%Y%m%d %H:%M:%S',
        '%Y%m%d %H:%M',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%d-%m-%Y %H:%M:%S',
        '%d-%m-%Y %H:%M',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M',
    ]
    
    for date_format in formats_to_try:
        try:
            parsed_datetime = datetime.strptime(datetime_str, date_format)
            return parsed_datetime.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    
    return None


def normalize_time_string(time_str: str) -> Optional[str]:
    """
    將各種時間字串格式正規化為 HH:MM 格式
    
    支援格式：
    - 14:30:00, 14:30
    - 14.30, 1430
    
    Args:
        time_str: 輸入的時間字串
        
    Returns:
        正規化後的時間字串 (HH:MM) 或 None
    """
    if not time_str:
        return None
    
    time_str = str(time_str).strip()
    if not time_str:
        return None
    
    # 嘗試各種格式解析
    formats_to_try = [
        '%H:%M:%S',
        '%H:%M',
        '%H.%M',
        '%H%M',
    ]
    
    for time_format in formats_to_try:
        try:
            parsed_time = datetime.strptime(time_str, time_format).time()
            return parsed_time.strftime('%H:%M')
        except ValueError:
            continue
    
    return None


def get_today_string() -> str:
    """
    取得今日日期的標準格式字串
    
    Returns:
        今日日期 (YYYY-MM-DD)
    """
    return date.today().strftime('%Y-%m-%d')


def is_valid_date_string(date_str: str) -> bool:
    """
    檢查日期字串是否為有效格式
    
    Args:
        date_str: 要檢查的日期字串
        
    Returns:
        True 如果是有效日期格式，否則 False
    """
    return normalize_date_string(date_str) is not None


def convert_date_for_html_input(date_value: Union[date, str, None]) -> str:
    """
    將日期值轉換為適合 HTML input[type="date"] 的格式
    
    Args:
        date_value: 日期物件、字串或 None
        
    Returns:
        YYYY-MM-DD 格式的字串，失敗時返回空字串
    """
    if not date_value:
        return ''
    
    if isinstance(date_value, date):
        return date_value.strftime('%Y-%m-%d')
    
    if isinstance(date_value, str):
        normalized = normalize_date_string(date_value)
        return normalized if normalized else ''
    
    return '' 