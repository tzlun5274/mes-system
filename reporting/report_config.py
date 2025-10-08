# -*- coding: utf-8 -*-
"""
報表配置管理模組
負責管理報表類型、收件人、檔案格式、公司代號等配置資訊
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ReportConfig:
    """報表配置管理類別"""
    
    # 報表類型定義
    REPORT_TYPES = [
        ('previous_workday', '前一個工作日報表'),
        ('previous_week', '上週報表'),
        ('previous_month', '上月報表'),
        ('previous_quarter', '上季報表'),
        ('previous_year', '去年報表'),
    ]
    
    # 檔案格式定義
    FILE_FORMATS = [
        ('html', 'HTML格式'),
        ('excel', 'Excel格式'),
        ('both', 'HTML + Excel格式'),
    ]
    
    def __init__(self, report_type: str, company_code: str = None, 
                 recipients: List[str] = None, file_format: str = 'both'):
        """
        初始化報表配置
        
        Args:
            report_type: 報表類型
            company_code: 公司代號
            recipients: 收件人列表
            file_format: 檔案格式
        """
        self.report_type = report_type
        self.company_code = company_code
        self.recipients = recipients or []
        self.file_format = file_format
        self._validate_config()
    
    def _validate_config(self):
        """驗證配置參數"""
        valid_types = [t[0] for t in self.REPORT_TYPES]
        if self.report_type not in valid_types:
            raise ValueError(f"無效的報表類型: {self.report_type}")
        
        valid_formats = [f[0] for f in self.FILE_FORMATS]
        if self.file_format not in valid_formats:
            raise ValueError(f"無效的檔案格式: {self.file_format}")
    
    def get_date_range(self, base_date: datetime = None) -> Dict[str, datetime]:
        """
        根據報表類型計算日期範圍
        
        Args:
            base_date: 基準日期，預設為今天
            
        Returns:
            包含 start_date 和 end_date 的字典
        """
        if base_date is None:
            base_date = datetime.now()
        
        if self.report_type == 'previous_workday':
            return self._get_previous_workday_range(base_date)
        elif self.report_type == 'previous_week':
            return self._get_previous_week_range(base_date)
        elif self.report_type == 'previous_month':
            return self._get_previous_month_range(base_date)
        elif self.report_type == 'previous_quarter':
            return self._get_previous_quarter_range(base_date)
        elif self.report_type == 'previous_year':
            return self._get_previous_year_range(base_date)
        else:
            raise ValueError(f"不支援的報表類型: {self.report_type}")
    
    def _get_previous_workday_range(self, base_date: datetime) -> Dict[str, datetime]:
        """計算前一個工作日的日期範圍"""
        # 找到前一個工作日
        previous_workday = base_date - timedelta(days=1)
        while previous_workday.weekday() >= 5:  # 週六是5，週日是6
            previous_workday -= timedelta(days=1)
        
        return {
            'start_date': previous_workday.replace(hour=0, minute=0, second=0, microsecond=0),
            'end_date': previous_workday.replace(hour=23, minute=59, second=59, microsecond=999999)
        }
    
    
    def _get_previous_week_range(self, base_date: datetime) -> Dict[str, datetime]:
        """計算上週的日期範圍"""
        # 找到上週一
        days_since_monday = base_date.weekday()
        last_monday = base_date - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        
        return {
            'start_date': last_monday.replace(hour=0, minute=0, second=0, microsecond=0),
            'end_date': last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
        }
    
    
    def _get_previous_month_range(self, base_date: datetime) -> Dict[str, datetime]:
        """計算上月的日期範圍"""
        # 找到上個月第一天
        if base_date.month == 1:
            prev_month = base_date.replace(year=base_date.year - 1, month=12, day=1)
        else:
            prev_month = base_date.replace(month=base_date.month - 1, day=1)
        
        start_date = prev_month.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 找到上個月最後一天
        current_month_first = base_date.replace(day=1)
        end_date = current_month_first - timedelta(days=1)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return {
            'start_date': start_date,
            'end_date': end_date
        }
    
    
    def _get_previous_quarter_range(self, base_date: datetime) -> Dict[str, datetime]:
        """計算上季的日期範圍"""
        quarter = (base_date.month - 1) // 3 + 1
        
        if quarter == 1:
            # 當前是第一季，上季是去年第四季
            prev_quarter_start = base_date.replace(year=base_date.year - 1, month=10, day=1)
        else:
            # 上季是今年
            prev_quarter_start_month = (quarter - 2) * 3 + 1
            prev_quarter_start = base_date.replace(month=prev_quarter_start_month, day=1)
        
        start_date = prev_quarter_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 計算當前季度的第一天
        current_quarter_start_month = (quarter - 1) * 3 + 1
        current_quarter_start = base_date.replace(month=current_quarter_start_month, day=1)
        
        end_date = current_quarter_start - timedelta(days=1)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return {
            'start_date': start_date,
            'end_date': end_date
        }
    
    
    def _get_previous_year_range(self, base_date: datetime) -> Dict[str, datetime]:
        """計算上年的日期範圍"""
        start_date = base_date.replace(year=base_date.year - 1, month=1, day=1, 
                                     hour=0, minute=0, second=0, microsecond=0)
        end_date = base_date.replace(year=base_date.year - 1, month=12, day=31, 
                                   hour=23, minute=59, second=59, microsecond=999999)
        
        return {
            'start_date': start_date,
            'end_date': end_date
        }
    
    def get_report_title(self) -> str:
        """取得報表標題"""
        type_names = {
            'previous_workday': '前一個工作日報表',
            'previous_week': '上週報表',
            'previous_month': '上月報表',
            'previous_quarter': '上季報表',
            'previous_year': '去年報表',
        }
        
        return type_names.get(self.report_type, '未知報表類型')
    
    def get_filename_prefix(self) -> str:
        """取得檔案名稱前綴"""
        type_prefixes = {
            'previous_workday': '前一個工作日',
            'previous_week': '上週',
            'previous_month': '上月',
            'previous_quarter': '上季',
            'previous_year': '上年',
        }
        
        return type_prefixes.get(self.report_type, '未知')
    
    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            'report_type': self.report_type,
            'company_code': self.company_code,
            'recipients': self.recipients,
            'file_format': self.file_format,
            'report_title': self.get_report_title(),
            'filename_prefix': self.get_filename_prefix()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ReportConfig':
        """從字典創建配置物件"""
        return cls(
            report_type=data.get('report_type'),
            company_code=data.get('company_code'),
            recipients=data.get('recipients', []),
            file_format=data.get('file_format', 'both')
        )
    
    def __str__(self) -> str:
        """字串表示"""
        return f"ReportConfig(type={self.report_type}, company={self.company_code}, format={self.file_format})"
    
    def __repr__(self) -> str:
        """詳細字串表示"""
        return f"ReportConfig(report_type='{self.report_type}', company_code='{self.company_code}', recipients={self.recipients}, file_format='{self.file_format}')"
