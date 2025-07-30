"""
基礎報表服務類別
提供所有報表服務的基礎功能和介面
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional


class BaseReportService:
    """報表服務基礎類別"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_report(self, date_range: Dict[str, date], **kwargs) -> List[Dict[str, Any]]:
        """
        生成報表數據（抽象方法）。
        返回用於報表的加工數據。
        """
        raise NotImplementedError
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """驗證輸入參數"""
        try:
            # 基本參數驗證
            if not params.get('date_range'):
                self.logger.error("缺少日期範圍參數")
                return False
            
            start_date = params['date_range'].get('start_date')
            end_date = params['date_range'].get('end_date')
            
            if not start_date or not end_date:
                self.logger.error("日期範圍不完整")
                return False
            
            if start_date > end_date:
                self.logger.error("開始日期不能晚於結束日期")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"參數驗證失敗: {str(e)}")
            return False
    
    def calculate_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """計算統計數據（可選）"""
        if not data:
            return {
                'total_records': 0,
                'summary': '無數據'
            }
        
        # 基本統計
        total_records = len(data)
        
        # 根據數據類型計算不同統計
        stats = {
            'total_records': total_records,
            'summary': f'共 {total_records} 筆記錄'
        }
        
        return stats
    
    def format_output(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化輸出（可選）"""
        # 實現數據格式化邏輯，例如為匯出準備列名和數據結構
        return data
    
    def get_date_range(self, date_range_type: str, custom_start: Optional[date] = None, 
                      custom_end: Optional[date] = None) -> Dict[str, date]:
        """
        根據日期範圍類型獲取實際的開始和結束日期
        """
        today = date.today()
        
        if date_range_type == 'TODAY':
            return {'start_date': today, 'end_date': today}
        elif date_range_type == 'YESTERDAY':
            yesterday = today.replace(day=today.day - 1)
            return {'start_date': yesterday, 'end_date': yesterday}
        elif date_range_type == 'THIS_WEEK':
            # 計算本週開始（週一）
            days_since_monday = today.weekday()
            start_of_week = today.replace(day=today.day - days_since_monday)
            return {'start_date': start_of_week, 'end_date': today}
        elif date_range_type == 'LAST_WEEK':
            # 計算上週
            days_since_monday = today.weekday()
            start_of_this_week = today.replace(day=today.day - days_since_monday)
            start_of_last_week = start_of_this_week.replace(day=start_of_this_week.day - 7)
            end_of_last_week = start_of_this_week.replace(day=start_of_this_week.day - 1)
            return {'start_date': start_of_last_week, 'end_date': end_of_last_week}
        elif date_range_type == 'THIS_MONTH':
            start_of_month = today.replace(day=1)
            return {'start_date': start_of_month, 'end_date': today}
        elif date_range_type == 'LAST_MONTH':
            # 計算上月
            if today.month == 1:
                last_month = today.replace(year=today.year - 1, month=12)
            else:
                last_month = today.replace(month=today.month - 1)
            start_of_last_month = last_month.replace(day=1)
            # 計算上月最後一天
            if last_month.month == 12:
                next_month = last_month.replace(year=last_month.year + 1, month=1)
            else:
                next_month = last_month.replace(month=last_month.month + 1)
            end_of_last_month = next_month.replace(day=1).replace(day=next_month.replace(day=1).day - 1)
            return {'start_date': start_of_last_month, 'end_date': end_of_last_month}
        elif date_range_type == 'CUSTOM':
            if custom_start and custom_end:
                return {'start_date': custom_start, 'end_date': custom_end}
            else:
                raise ValueError("自訂日期範圍需要提供開始和結束日期")
        else:
            raise ValueError(f"不支援的日期範圍類型: {date_range_type}") 