"""
填報作業管理子模組 - 自定義欄位
負責填報作業的自定義欄位定義
"""

from django import forms
from django.core.exceptions import ValidationError
import re


class TimeField(forms.Field):
    """
    自定義時間欄位
    支援 HH:MM 格式的24小時制時間輸入
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'HH:MM',
            'pattern': r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$',
            'title': '請輸入24小時制時間格式 (HH:MM)'
        })
        super().__init__(*args, **kwargs)
    
    def clean(self, value):
        """驗證時間格式"""
        if not value:
            return None
        
        # 檢查格式是否正確
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', value):
            raise ValidationError('請輸入正確的24小時制時間格式 (HH:MM)')
        
        # 解析時間
        try:
            hours, minutes = map(int, value.split(':'))
            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                raise ValidationError('時間範圍錯誤')
            
            from datetime import time
            return time(hours, minutes)
        except (ValueError, TypeError):
            raise ValidationError('時間格式錯誤') 