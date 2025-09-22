"""
工作日曆服務
只負責工作日曆相關的邏輯
"""

import logging
from datetime import date, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class WorkdayCalendarService:
    """工作日曆服務 - 只負責工作日曆邏輯"""
    
    def __init__(self):
        pass
    
    def get_previous_workday(self, current_date):
        """
        取得前一個工作日
        
        Args:
            current_date: 當前日期
            
        Returns:
            date: 前一個工作日的日期
        """
        try:
            # 從當前日期往前推，找到前一個工作日
            previous_date = current_date - timedelta(days=1)
            
            # 檢查是否為工作日（非週末且非國定假日）
            while not self.is_workday(previous_date):
                previous_date = previous_date - timedelta(days=1)
            
            return previous_date
            
        except Exception as e:
            logger.error(f"取得前一個工作日失敗: {str(e)}")
            # 如果出錯，返回昨天
            return current_date - timedelta(days=1)
    
    def is_workday(self, check_date):
        """
        檢查指定日期是否為工作日
        
        Args:
            check_date: 要檢查的日期
            
        Returns:
            bool: True 表示是工作日，False 表示不是工作日
        """
        try:
            # 檢查是否為週末
            if check_date.weekday() >= 5:  # 週六(5) 或 週日(6)
                return False
            
            # 檢查是否為國定假日
            if self.is_holiday(check_date):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"檢查工作日失敗: {str(e)}")
            # 如果出錯，預設為工作日
            return True
    
    def is_holiday(self, check_date):
        """
        檢查指定日期是否為國定假日
        
        Args:
            check_date: 要檢查的日期
            
        Returns:
            bool: True 表示是國定假日，False 表示不是國定假日
        """
        try:
            # 這裡可以從資料庫或外部 API 查詢國定假日
            # 暫時使用簡單的邏輯
            
            # 檢查是否為農曆新年（簡化版）
            if self._is_lunar_new_year(check_date):
                return True
            
            # 檢查是否為其他國定假日
            if self._is_other_holiday(check_date):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"檢查國定假日失敗: {str(e)}")
            # 如果出錯，預設為非國定假日
            return False
    
    def _is_lunar_new_year(self, check_date):
        """檢查是否為農曆新年（簡化版）"""
        # 這裡應該使用農曆轉換庫來準確計算
        # 暫時使用固定日期作為範例
        
        # 2024年農曆新年：2月10日-2月17日
        if check_date.year == 2024:
            if check_date.month == 2 and 10 <= check_date.day <= 17:
                return True
        
        # 2025年農曆新年：1月29日-2月4日
        if check_date.year == 2025:
            if check_date.month == 1 and 29 <= check_date.day <= 31:
                return True
            elif check_date.month == 2 and 1 <= check_date.day <= 4:
                return True
        
        return False
    
    def _is_other_holiday(self, check_date):
        """檢查是否為其他國定假日"""
        # 常見的國定假日
        holidays = [
            # 元旦
            (1, 1),
            # 228紀念日
            (2, 28),
            # 清明節（簡化版，實際應該用農曆計算）
            (4, 4),
            # 勞動節
            (5, 1),
            # 端午節（簡化版，實際應該用農曆計算）
            (6, 10),
            # 中秋節（簡化版，實際應該用農曆計算）
            (9, 17),
            # 國慶日
            (10, 10),
        ]
        
        for month, day in holidays:
            if check_date.month == month and check_date.day == day:
                return True
        
        return False
    
    def get_workdays_in_range(self, start_date, end_date):
        """
        取得指定日期範圍內的工作日
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            list: 工作日日期列表
        """
        try:
            workdays = []
            current_date = start_date
            
            while current_date <= end_date:
                if self.is_workday(current_date):
                    workdays.append(current_date)
                current_date += timedelta(days=1)
            
            return workdays
            
        except Exception as e:
            logger.error(f"取得工作日範圍失敗: {str(e)}")
            return []
    
    def get_workdays_count(self, start_date, end_date):
        """
        取得指定日期範圍內的工作日數量
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            int: 工作日數量
        """
        workdays = self.get_workdays_in_range(start_date, end_date)
        return len(workdays)
    
    def get_next_workday(self, current_date):
        """
        取得下一個工作日
        
        Args:
            current_date: 當前日期
            
        Returns:
            date: 下一個工作日的日期
        """
        try:
            next_date = current_date + timedelta(days=1)
            
            # 檢查是否為工作日
            while not self.is_workday(next_date):
                next_date = next_date + timedelta(days=1)
            
            return next_date
            
        except Exception as e:
            logger.error(f"取得下一個工作日失敗: {str(e)}")
            # 如果出錯，返回明天
            return current_date + timedelta(days=1)
