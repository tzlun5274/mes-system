# -*- coding: utf-8 -*-
"""
工時計算器模組
負責計算作業員的工作時數、正常工時、加班時數，正確扣除午休時間
"""

import logging
from datetime import datetime, time, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from .base_calculator import BaseCalculator


class TimeCalculator(BaseCalculator):
    """工時計算器 - 負責計算各種工時相關指標，正確扣除午休時間"""
    
    def __init__(self):
        """初始化工時計算器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        # 預設的工時設定
        self.default_work_start = time(8, 0)  # 08:00
        self.default_work_end = time(17, 0)   # 17:00
        self.default_lunch_start = time(12, 0)  # 12:00
        self.default_lunch_end = time(13, 0)    # 13:00
        self.default_daily_normal_hours = 8.0   # 每日正常工時8小時
    
    def calculate_total_work_time(self, reports: List[Any]) -> float:
        """
        根據報工記錄計算總工時 (以小時為單位)
        
        Args:
            reports: ProcessedOperatorReport 對象列表或其他報工記錄
            
        Returns:
            float: 總工時 (小時)
        """
        try:
            total_duration_seconds = 0
            for report in reports:
                if hasattr(report, 'start_time') and hasattr(report, 'end_time'):
                    if report.start_time and report.end_time:
                        duration_seconds = (report.end_time - report.start_time).total_seconds()
                        total_duration_seconds += duration_seconds
                elif hasattr(report, 'work_date') and hasattr(report, 'start_time') and hasattr(report, 'end_time'):
                    # 處理舊格式的報工記錄
                    if report.start_time and report.end_time:
                        start_dt = datetime.combine(report.work_date, report.start_time)
                        end_dt = datetime.combine(report.work_date, report.end_time)
                        # 處理跨日情況
                        if end_dt < start_dt:
                            end_dt += timedelta(days=1)
                        duration_seconds = (end_dt - start_dt).total_seconds()
                        total_duration_seconds += duration_seconds
            
            return round(total_duration_seconds / 3600.0, 2)
        except Exception as e:
            self.logger.error(f"計算總工時失敗: {str(e)}")
            return 0.0
    
    def calculate_operator_work_time_detail(self, reports: List[Any], 
                                          daily_normal_hours_limit: float = 8.0) -> Dict[str, float]:
        """
        計算每個作業員在給定報告集合中的總工時、正常工時和加班工時
        
        Args:
            reports: ProcessedOperatorReport 對象列表
            daily_normal_hours_limit: 每日正常工時上限 (小時)
            
        Returns:
            Dict[str, float]: 包含各種時數的字典
        """
        try:
            total_hours = self.calculate_total_work_time(reports)
            
            # 簡單計算：如果總工時超過每日正常工時上限，超出部分算加班
            normal_hours = min(total_hours, daily_normal_hours_limit)
            overtime_hours = max(0, total_hours - daily_normal_hours_limit)
            
            return {
                'total_hours': total_hours,
                'normal_hours': normal_hours,
                'overtime_hours': overtime_hours
            }
        except Exception as e:
            self.logger.error(f"計算作業員工時詳情失敗: {str(e)}")
            return {
                'total_hours': 0.0,
                'normal_hours': 0.0,
                'overtime_hours': 0.0
            }
    
    def calculate_work_time_with_breaks(self, start_time: datetime, end_time: datetime,
                                      work_date: date = None,
                                      work_start: time = None, work_end: time = None,
                                      lunch_start: time = None, lunch_end: time = None) -> Dict[str, float]:
        """
        計算工作時數，正確扣除午休時間
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            work_date: 工作日期
            work_start: 正常上班時間
            work_end: 正常下班時間
            lunch_start: 午休開始時間
            lunch_end: 午休結束時間
            
        Returns:
            Dict[str, float]: 包含各種時數的字典
        """
        try:
            if not self.validate_input(start_time=start_time, end_time=end_time):
                return {
                    'total_work_hours': 0.0,
                    'actual_work_hours': 0.0,
                    'break_hours': 0.0,
                    'overtime_hours': 0.0,
                    'regular_hours': 0.0
                }
            
            # 使用預設值如果沒有提供
            if work_date is None:
                work_date = start_time.date()
            if work_start is None:
                work_start = self.default_work_start
            if work_end is None:
                work_end = self.default_work_end
            if lunch_start is None:
                lunch_start = self.default_lunch_start
            if lunch_end is None:
                lunch_end = self.default_lunch_end
            
            # 處理跨日情況
            if end_time < start_time:
                end_time += timedelta(days=1)
            
            # 計算總工作時數
            total_hours = (end_time - start_time).total_seconds() / 3600
            
            # 計算午休時間重疊部分
            break_hours = 0.0
            if lunch_start and lunch_end:
                lunch_start_dt = datetime.combine(work_date, lunch_start)
                lunch_end_dt = datetime.combine(work_date, lunch_end)
                
                # 處理跨日午休
                if lunch_end_dt < lunch_start_dt:
                    lunch_end_dt += timedelta(days=1)
                
                # 計算與午休時間的重疊
                break_hours = self._calculate_overlap_hours(
                    start_time, end_time, lunch_start_dt, lunch_end_dt
                )
            
            # 計算實際工作時數（扣除午休時間）
            actual_hours = max(0, total_hours - break_hours)
            
            # 計算正常工時和加班時數
            regular_hours = 0.0
            overtime_hours = 0.0
            
            if work_start and work_end:
                work_start_dt = datetime.combine(work_date, work_start)
                work_end_dt = datetime.combine(work_date, work_end)
                
                # 處理跨日工作
                if work_end_dt < work_start_dt:
                    work_end_dt += timedelta(days=1)
                
                # 計算與正常工時的重疊部分
                regular_hours = self._calculate_overlap_hours(
                    start_time, end_time, work_start_dt, work_end_dt
                )
                
                # 從正常工時中扣除午休時間
                if break_hours > 0:
                    # 計算午休時間在正常工時範圍內的部分
                    lunch_in_work_start = max(work_start_dt, datetime.combine(work_date, lunch_start))
                    lunch_in_work_end = min(work_end_dt, datetime.combine(work_date, lunch_end))
                    
                    if lunch_in_work_start < lunch_in_work_end:
                        lunch_in_work_hours = (lunch_in_work_end - lunch_in_work_start).total_seconds() / 3600
                        regular_hours = max(0, regular_hours - lunch_in_work_hours)
                
                # 超過正常工時的部分算作加班
                overtime_hours = max(0, actual_hours - regular_hours)
            else:
                # 如果沒有設定正常工時，全部算作正常工時
                regular_hours = actual_hours
            
            self.logger.info(f"工時計算結果: 總時數={total_hours:.2f}, 實際工作時數={actual_hours:.2f}, "
                           f"正常工時={regular_hours:.2f}, 加班時數={overtime_hours:.2f}, 休息時數={break_hours:.2f}")
            
            return {
                'total_work_hours': round(total_hours, 2),
                'actual_work_hours': round(actual_hours, 2),
                'break_hours': round(break_hours, 2),
                'overtime_hours': round(overtime_hours, 2),
                'regular_hours': round(regular_hours, 2)
            }
            
        except Exception as e:
            self.logger.error(f"計算工作時數失敗: {str(e)}")
            return {
                'total_work_hours': 0.0,
                'actual_work_hours': 0.0,
                'break_hours': 0.0,
                'overtime_hours': 0.0,
                'regular_hours': 0.0
            }
    
    def calculate_work_time_for_report(self, report) -> Dict[str, float]:
        """
        計算單個報工記錄的工時數據，正確扣除午休時間
        
        Args:
            report: 報工記錄對象（OperatorSupplementReport 或其他報工記錄）
            
        Returns:
            Dict[str, float]: 包含各種時數的字典
        """
        try:
            # 檢查報工記錄是否有時間資訊
            if not hasattr(report, 'start_time') or not hasattr(report, 'end_time'):
                self.logger.warning(f"報工記錄缺少時間資訊: {report}")
                return {
                    'total_work_hours': 0.0,
                    'actual_work_hours': 0.0,
                    'break_hours': 0.0,
                    'overtime_hours': 0.0,
                    'regular_hours': 0.0
                }
            
            if not report.start_time or not report.end_time:
                self.logger.warning(f"報工記錄時間為空: {report}")
                return {
                    'total_work_hours': 0.0,
                    'actual_work_hours': 0.0,
                    'break_hours': 0.0,
                    'overtime_hours': 0.0,
                    'regular_hours': 0.0
                }
            
            # 取得工作日期
            work_date = getattr(report, 'work_date', None)
            if not work_date:
                # 如果沒有work_date，從start_time推斷
                if isinstance(report.start_time, datetime):
                    work_date = report.start_time.date()
                else:
                    work_date = date.today()
            
            # 轉換為datetime對象
            if isinstance(report.start_time, time):
                start_dt = datetime.combine(work_date, report.start_time)
            else:
                start_dt = report.start_time
            
            if isinstance(report.end_time, time):
                end_dt = datetime.combine(work_date, report.end_time)
                # 處理跨日情況
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
            else:
                end_dt = report.end_time
            
            # 計算總工作時數（包含午休）
            total_work_hours = (end_dt - start_dt).total_seconds() / 3600.0
            
            # 計算實際工作時數（扣除午休）
            actual_work_hours = self.calculate_work_time_with_breaks(
                start_dt, end_dt, work_date,
                self.default_work_start, self.default_work_end,
                self.default_lunch_start, self.default_lunch_end
            )
            
            # 計算休息時數
            break_hours = total_work_hours - actual_work_hours['actual_work_hours']
            
            # 計算正常工時和加班時數
            regular_hours = min(actual_work_hours['actual_work_hours'], self.default_daily_normal_hours)
            overtime_hours = max(0, actual_work_hours['actual_work_hours'] - self.default_daily_normal_hours)
            
            return {
                'total_work_hours': round(total_work_hours, 2),
                'actual_work_hours': round(actual_work_hours['actual_work_hours'], 2),
                'break_hours': round(break_hours, 2),
                'overtime_hours': round(overtime_hours, 2),
                'regular_hours': round(regular_hours, 2)
            }
            
        except Exception as e:
            self.logger.error(f"計算報工記錄工時失敗: {str(e)}")
            return {
                'total_work_hours': 0.0,
                'actual_work_hours': 0.0,
                'break_hours': 0.0,
                'overtime_hours': 0.0,
                'regular_hours': 0.0
            }
    
    def _calculate_overlap_hours(self, start1: datetime, end1: datetime, 
                               start2: datetime, end2: datetime) -> float:
        """
        計算兩個時間區間的重疊時數
        
        Args:
            start1, end1: 第一個時間區間
            start2, end2: 第二個時間區間
            
        Returns:
            float: 重疊時數
        """
        try:
            # 找出重疊的開始和結束時間
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            
            # 如果沒有重疊，返回0
            if overlap_start >= overlap_end:
                return 0.0
            
            # 計算重疊時數
            overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
            return round(overlap_hours, 2)
            
        except Exception as e:
            self.logger.error(f"計算重疊時數失敗: {str(e)}")
            return 0.0
    
    def calculate_daily_work_hours(self, work_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每日工作時數統計
        
        Args:
            work_records: 工作記錄列表
            
        Returns:
            Dict[str, float]: 每日工作時數統計
        """
        try:
            total_hours = 0.0
            normal_hours = 0.0
            overtime_hours = 0.0
            break_hours = 0.0
            
            for record in work_records:
                if 'total_work_hours' in record:
                    total_hours += record.get('total_work_hours', 0)
                if 'regular_hours' in record:
                    normal_hours += record.get('regular_hours', 0)
                if 'overtime_hours' in record:
                    overtime_hours += record.get('overtime_hours', 0)
                if 'break_hours' in record:
                    break_hours += record.get('break_hours', 0)
            
            return {
                'total_hours': round(total_hours, 2),
                'normal_hours': round(normal_hours, 2),
                'overtime_hours': round(overtime_hours, 2),
                'break_hours': round(break_hours, 2)
            }
        except Exception as e:
            self.logger.error(f"計算每日工作時數失敗: {str(e)}")
            return {
                'total_hours': 0.0,
                'normal_hours': 0.0,
                'overtime_hours': 0.0,
                'break_hours': 0.0
            }
    
    def calculate_weekly_work_hours(self, work_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每週工作時數統計
        
        Args:
            work_records: 工作記錄列表
            
        Returns:
            Dict[str, float]: 每週工作時數統計
        """
        return self.calculate_daily_work_hours(work_records)
    
    def calculate_monthly_work_hours(self, work_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每月工作時數統計
        
        Args:
            work_records: 工作記錄列表
            
        Returns:
            Dict[str, float]: 每月工作時數統計
        """
        return self.calculate_daily_work_hours(work_records)
    
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
            
            efficiency = (actual_hours / standard_hours) * 100
            return round(efficiency, 2)
        except Exception as e:
            self.logger.error(f"計算工作效率失敗: {str(e)}")
            return 0.0
    
    def calculate_utilization_rate(self, productive_hours: float, total_hours: float) -> float:
        """
        計算利用率
        
        Args:
            productive_hours: 有效工作時數
            total_hours: 總工作時數
            
        Returns:
            float: 利用率百分比
        """
        try:
            if total_hours <= 0:
                return 0.0
            
            utilization = (productive_hours / total_hours) * 100
            return round(utilization, 2)
        except Exception as e:
            self.logger.error(f"計算利用率失敗: {str(e)}")
            return 0.0 