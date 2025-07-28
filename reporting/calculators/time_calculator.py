# 時間計算器模組
# 本檔案負責計算工作時間、效率時間、加班時間等相關指標

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal
from .base_calculator import BaseCalculator


class TimeCalculator(BaseCalculator):
    """時間計算器 - 負責計算各種時間相關指標"""
    
    def __init__(self):
        """初始化時間計算器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def calculate_work_hours(self, start_time: datetime, end_time: datetime) -> float:
        """
        計算工作時數
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            float: 工作時數（小時）
        """
        try:
            if not self.validate_input(start_time=start_time, end_time=end_time):
                return 0.0
            
            if start_time >= end_time:
                self.logger.warning("開始時間不能大於或等於結束時間")
                return 0.0
            
            time_diff = end_time - start_time
            hours = time_diff.total_seconds() / 3600
            return self.round_decimal(hours, 2)
        except Exception as e:
            self.logger.error(f"計算工作時數失敗: {str(e)}")
            return 0.0
    
    def calculate_overtime_hours(self, start_time: datetime, end_time: datetime, 
                               regular_hours: float = 8.0) -> float:
        """
        計算加班時數
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            regular_hours: 正常工時（預設8小時）
            
        Returns:
            float: 加班時數
        """
        try:
            total_hours = self.calculate_work_hours(start_time, end_time)
            overtime = max(0, total_hours - regular_hours)
            return self.round_decimal(overtime, 2)
        except Exception as e:
            self.logger.error(f"計算加班時數失敗: {str(e)}")
            return 0.0
    
    def calculate_break_time(self, start_time: datetime, end_time: datetime, 
                           break_duration: float = 1.0) -> float:
        """
        計算休息時間
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            break_duration: 休息時間（小時）
            
        Returns:
            float: 實際休息時間
        """
        try:
            total_hours = self.calculate_work_hours(start_time, end_time)
            # 如果工作時間超過8小時，給予1小時休息時間
            if total_hours >= 8:
                return break_duration
            # 如果工作時間超過4小時，給予0.5小時休息時間
            elif total_hours >= 4:
                return 0.5
            else:
                return 0.0
        except Exception as e:
            self.logger.error(f"計算休息時間失敗: {str(e)}")
            return 0.0
    
    def calculate_effective_work_hours(self, start_time: datetime, end_time: datetime, 
                                     break_duration: float = 1.0) -> float:
        """
        計算有效工作時數（扣除休息時間）
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            break_duration: 休息時間（小時）
            
        Returns:
            float: 有效工作時數
        """
        try:
            total_hours = self.calculate_work_hours(start_time, end_time)
            break_time = self.calculate_break_time(start_time, end_time, break_duration)
            effective_hours = total_hours - break_time
            return self.round_decimal(max(0, effective_hours), 2)
        except Exception as e:
            self.logger.error(f"計算有效工作時數失敗: {str(e)}")
            return 0.0
    
    def calculate_operator_work_time(self, reports: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算作業員工作時間
        
        Args:
            reports: 報工記錄列表
            
        Returns:
            Dict[str, float]: 作業員工作時間字典
        """
        try:
            operator_times = {}
            
            for report in reports:
                operator_id = report.get('operator_id')
                start_time = report.get('start_time')
                end_time = report.get('end_time')
                
                if not all([operator_id, start_time, end_time]):
                    continue
                
                work_hours = self.calculate_work_hours(start_time, end_time)
                
                if operator_id in operator_times:
                    operator_times[operator_id] += work_hours
                else:
                    operator_times[operator_id] = work_hours
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in operator_times.items()}
        except Exception as e:
            self.logger.error(f"計算作業員工作時間失敗: {str(e)}")
            return {}
    
    def calculate_daily_work_hours(self, work_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每日工作時數
        
        Args:
            work_records: 工作記錄列表
            
        Returns:
            Dict[str, float]: 每日工作時數字典
        """
        try:
            daily_hours = {}
            
            for record in work_records:
                date = record.get('date')
                start_time = record.get('start_time')
                end_time = record.get('end_time')
                
                if not all([date, start_time, end_time]):
                    continue
                
                work_hours = self.calculate_work_hours(start_time, end_time)
                
                if date in daily_hours:
                    daily_hours[date] += work_hours
                else:
                    daily_hours[date] = work_hours
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in daily_hours.items()}
        except Exception as e:
            self.logger.error(f"計算每日工作時數失敗: {str(e)}")
            return {}
    
    def calculate_weekly_work_hours(self, work_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每週工作時數
        
        Args:
            work_records: 工作記錄列表
            
        Returns:
            Dict[str, float]: 每週工作時數字典
        """
        try:
            weekly_hours = {}
            
            for record in work_records:
                date = record.get('date')
                start_time = record.get('start_time')
                end_time = record.get('end_time')
                
                if not all([date, start_time, end_time]):
                    continue
                
                # 計算週數
                week_number = date.isocalendar()[1]
                week_key = f"{date.year}-W{week_number:02d}"
                
                work_hours = self.calculate_work_hours(start_time, end_time)
                
                if week_key in weekly_hours:
                    weekly_hours[week_key] += work_hours
                else:
                    weekly_hours[week_key] = work_hours
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in weekly_hours.items()}
        except Exception as e:
            self.logger.error(f"計算每週工作時數失敗: {str(e)}")
            return {}
    
    def calculate_monthly_work_hours(self, work_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每月工作時數
        
        Args:
            work_records: 工作記錄列表
            
        Returns:
            Dict[str, float]: 每月工作時數字典
        """
        try:
            monthly_hours = {}
            
            for record in work_records:
                date = record.get('date')
                start_time = record.get('start_time')
                end_time = record.get('end_time')
                
                if not all([date, start_time, end_time]):
                    continue
                
                # 計算月份
                month_key = f"{date.year}-{date.month:02d}"
                
                work_hours = self.calculate_work_hours(start_time, end_time)
                
                if month_key in monthly_hours:
                    monthly_hours[month_key] += work_hours
                else:
                    monthly_hours[month_key] = work_hours
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in monthly_hours.items()}
        except Exception as e:
            self.logger.error(f"計算每月工作時數失敗: {str(e)}")
            return {}
    
    def calculate_work_efficiency(self, actual_hours: float, standard_hours: float) -> float:
        """
        計算工作效率
        
        Args:
            actual_hours: 實際工作時數
            standard_hours: 標準工作時數
            
        Returns:
            float: 工作效率百分比
        """
        try:
            if standard_hours <= 0:
                return 0.0
            
            efficiency = (standard_hours / actual_hours) * 100
            return self.round_decimal(efficiency, 2)
        except Exception as e:
            self.logger.error(f"計算工作效率失敗: {str(e)}")
            return 0.0
    
    def calculate_idle_time(self, total_hours: float, productive_hours: float) -> float:
        """
        計算閒置時間
        
        Args:
            total_hours: 總工作時數
            productive_hours: 生產性工作時數
            
        Returns:
            float: 閒置時間
        """
        try:
            idle_time = max(0, total_hours - productive_hours)
            return self.round_decimal(idle_time, 2)
        except Exception as e:
            self.logger.error(f"計算閒置時間失敗: {str(e)}")
            return 0.0
    
    def calculate_utilization_rate(self, productive_hours: float, total_hours: float) -> float:
        """
        計算利用率
        
        Args:
            productive_hours: 生產性工作時數
            total_hours: 總工作時數
            
        Returns:
            float: 利用率百分比
        """
        try:
            return self.calculate_percentage(productive_hours, total_hours)
        except Exception as e:
            self.logger.error(f"計算利用率失敗: {str(e)}")
            return 0.0 