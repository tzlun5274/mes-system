"""
MES 系統自訂表單欄位
完全取代 Django 原生的限制性日期欄位設計
支援任何常見日期格式輸入，對使用者友好
"""

from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime, date
import re
from .date_utils import normalize_date_string, normalize_datetime_string, normalize_time_string


class FlexibleDateField(forms.Field):
    """
    靈活的日期欄位 - 接受任何常見日期格式
    完全取代 Django 原生 DateField 的限制性設計
    """
    
    def __init__(self, *args, **kwargs):
        # 預設使用 text input，避免瀏覽器的格式限制
        kwargs.setdefault('widget', forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '支援格式：2025-08-12, 2025/08/12, 20250812, 12/08/2025 等',
            'title': '支援多種日期格式：YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD, DD/MM/YYYY 等'
        }))
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """將輸入值轉換為 Python date 物件"""
        if value in self.empty_values:
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        # 嘗試正規化日期字串
        normalized = normalize_date_string(str(value))
        if normalized:
            try:
                return datetime.strptime(normalized, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # 如果無法解析，拋出友好的錯誤訊息
        raise ValidationError(
            f'無法識別的日期格式："{value}"。'
            f'支援格式包括：2025-08-12, 2025/08/12, 20250812, 12/08/2025 等。',
            code='invalid'
        )
    
    def prepare_value(self, value):
        """準備顯示在表單中的值"""
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        return value


class FlexibleDateTimeField(forms.Field):
    """
    靈活的日期時間欄位 - 接受任何常見日期時間格式
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '支援格式：2025-08-12 14:30, 2025/08/12 14:30 等',
            'title': '支援多種日期時間格式'
        }))
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """將輸入值轉換為 Python datetime 物件"""
        if value in self.empty_values:
            return None
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        
        # 嘗試正規化日期時間字串
        normalized = normalize_datetime_string(str(value))
        if normalized:
            try:
                return datetime.strptime(normalized, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        raise ValidationError(
            f'無法識別的日期時間格式："{value}"。'
            f'支援格式包括：2025-08-12 14:30, 2025/08/12 14:30:00 等。',
            code='invalid'
        )
    
    def prepare_value(self, value):
        """準備顯示在表單中的值"""
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return value


class FlexibleTimeField(forms.Field):
    """
    靈活的時間欄位 - 接受任何常見時間格式
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '支援格式：14:30, 1430, 14.30 等',
            'title': '支援多種時間格式：HH:MM, HHMM, HH.MM 等'
        }))
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        """將輸入值轉換為 Python time 物件"""
        if value in self.empty_values:
            return None
        
        if hasattr(value, 'time'):  # datetime object
            return value.time()
        
        # 嘗試正規化時間字串
        normalized = normalize_time_string(str(value))
        if normalized:
            try:
                return datetime.strptime(normalized, '%H:%M').time()
            except ValueError:
                pass
        
        raise ValidationError(
            f'無法識別的時間格式："{value}"。'
            f'支援格式包括：14:30, 1430, 14.30 等。',
            code='invalid'
        )
    
    def prepare_value(self, value):
        """準備顯示在表單中的值"""
        if hasattr(value, 'strftime'):
            return value.strftime('%H:%M')
        return value


class SmartDateWidget(forms.TextInput):
    """
    智慧日期輸入小工具
    提供即時格式轉換和友好的使用者介面
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control smart-date-input',
            'placeholder': '任意日期格式，如：2025/08/12',
            'title': '支援多種日期格式，會自動轉換為標準格式',
            'autocomplete': 'off',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    class Media:
        js = ('js/smart_date_widget.js',)
        css = {
            'all': ('css/smart_date_widget.css',)
        }


# 便利函數：建立帶有智慧輸入的日期欄位
def smart_date_field(**kwargs):
    """建立一個智慧日期欄位，支援任何常見格式"""
    kwargs.setdefault('widget', SmartDateWidget())
    return FlexibleDateField(**kwargs)


def smart_datetime_field(**kwargs):
    """建立一個智慧日期時間欄位"""
    return FlexibleDateTimeField(**kwargs)


def smart_time_field(**kwargs):
    """建立一個智慧時間欄位"""
    return FlexibleTimeField(**kwargs) 