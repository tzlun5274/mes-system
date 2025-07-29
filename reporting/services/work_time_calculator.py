# -*- coding: utf-8 -*-
"""
工作時數計算服務
根據產線設定正確計算工作時數、休息時數、加班時數
"""

import logging
from datetime import datetime, time, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from production.models import ProductionLine
from workorder.models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport


class WorkTimeCalculator:
    """工作時數計算器 - 根據產線設定計算正確的工作時數"""
    
    def __init__(self):
        """初始化工作時數計算器"""
        self.logger = logging.getLogger(__name__)
    
    def calculate_work_time_for_report(self, report, production_line=None) -> Dict[str, float]:
        """
        計算報工記錄的工作時數（根據產線設定）
        
        Args:
            report: 報工記錄（OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport）
            production_line: 產線設定（ProductionLine），如果為None會自動查找
            
        Returns:
            Dict[str, float]: 包含各種時數的字典
        """
        try:
            if not report.start_time or not report.end_time:
                return {
                    'total_work_hours': 0.0,
                    'actual_work_hours': 0.0,
                    'break_hours': 0.0,
                    'overtime_hours': 0.0,
                    'regular_hours': 0.0
                }
            
            # 如果沒有提供產線，嘗試根據作業員或設備查找產線
            if not production_line:
                production_line = self._find_production_line_for_report(report)
            
            # 計算工作時數
            start_dt = datetime.combine(report.work_date, report.start_time)
            end_dt = datetime.combine(report.work_date, report.end_time)
            
            # 處理跨日情況
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            # 總工作時數（原始計算）
            total_work_hours = (end_dt - start_dt).total_seconds() / 3600
            
            if not production_line:
                # 如果找不到產線設定，使用原始計算方式
                self.logger.warning(f"找不到產線設定，使用原始計算方式: {report}")
                return {
                    'total_work_hours': round(total_work_hours, 2),
                    'actual_work_hours': round(total_work_hours, 2),
                    'break_hours': 0.0,
                    'overtime_hours': 0.0,
                    'regular_hours': round(total_work_hours, 2)
                }
            
            # 檢查報工記錄類型
            report_type = self._get_report_type(report)
            
            # 根據產線設定計算各種時數
            return self._calculate_by_production_line(
                start_dt, end_dt, production_line, report.work_date, report_type
            )
            
        except Exception as e:
            self.logger.error(f"計算工作時數失敗: {str(e)}")
            return {
                'total_work_hours': 0.0,
                'actual_work_hours': 0.0,
                'break_hours': 0.0,
                'overtime_hours': 0.0,
                'regular_hours': 0.0
            }
    
    def _get_report_type(self, report) -> str:
        """
        識別報工記錄的類型
        
        Args:
            report: 報工記錄
            
        Returns:
            str: 報工記錄類型 ('operator', 'smt', 'supervisor')
        """
        try:
            # 根據模型類型識別
            model_name = report.__class__.__name__
            
            if model_name == 'SMTProductionReport':
                return 'smt'
            elif model_name == 'OperatorSupplementReport':
                return 'operator'
            elif model_name == 'SupervisorProductionReport':
                return 'supervisor'
            else:
                # 預設為作業員類型
                return 'operator'
                
        except Exception as e:
            self.logger.error(f"識別報工記錄類型失敗: {str(e)}")
            return 'operator'
    
    def _find_production_line_for_report(self, report) -> Optional[ProductionLine]:
        """
        根據報工記錄查找對應的產線設定
        
        Args:
            report: 報工記錄
            
        Returns:
            ProductionLine: 產線設定，如果找不到則返回None
        """
        try:
            # 根據作業員名稱或設備名稱查找產線
            worker_name = getattr(report, 'operator_name', None) or getattr(report, 'worker_name', None)
            equipment_name = getattr(report, 'equipment_name', None)
            process_name = getattr(report, 'process_name', None)
            
            # 優先根據作業員名稱查找
            if worker_name:
                # 嘗試根據作業員名稱查找產線
                production_line = ProductionLine.objects.filter(
                    line_name__icontains=worker_name,
                    is_active=True
                ).first()
                if production_line:
                    return production_line
            
            # 根據設備名稱查找
            if equipment_name:
                production_line = ProductionLine.objects.filter(
                    line_name__icontains=equipment_name,
                    is_active=True
                ).first()
                if production_line:
                    return production_line
            
            # 根據工序名稱查找
            if process_name:
                production_line = ProductionLine.objects.filter(
                    line_name__icontains=process_name,
                    is_active=True
                ).first()
                if production_line:
                    return production_line
            
            # 如果都找不到，返回預設產線（第一個啟用的產線）
            return ProductionLine.objects.filter(is_active=True).first()
            
        except Exception as e:
            self.logger.error(f"查找產線設定失敗: {str(e)}")
            return None
    
    def _calculate_by_production_line(self, start_dt: datetime, end_dt: datetime, 
                                    production_line: ProductionLine, work_date: date, report_type: str = 'operator') -> Dict[str, float]:
        """
        根據產線設定計算工作時數
        
        Args:
            start_dt: 開始時間
            end_dt: 結束時間
            production_line: 產線設定
            work_date: 工作日期
            
        Returns:
            Dict[str, float]: 包含各種時數的字典
        """
        try:
            # 檢查是否為工作日
            if not self._is_workday(work_date, production_line):
                # 非工作日，全部算作加班
                total_hours = (end_dt - start_dt).total_seconds() / 3600
                return {
                    'total_work_hours': round(total_hours, 2),
                    'actual_work_hours': round(total_hours, 2),
                    'break_hours': 0.0,
                    'overtime_hours': round(total_hours, 2),
                    'regular_hours': 0.0
                }
            
            # 計算各種時數
            regular_hours = 0.0
            overtime_hours = 0.0
            break_hours = 0.0
            
            # 取得產線的時間設定
            work_start = production_line.work_start_time
            work_end = production_line.work_end_time
            lunch_start = production_line.lunch_start_time
            lunch_end = production_line.lunch_end_time
            overtime_start = production_line.overtime_start_time
            overtime_end = production_line.overtime_end_time
            
            # 建立工作日期
            work_date_dt = datetime.combine(work_date, time(0, 0))
            
            # 計算正常工時（工作時間內的部分，扣除午休時間）
            if work_start and work_end:
                regular_start = datetime.combine(work_date, work_start)
                regular_end = datetime.combine(work_date, work_end)
                
                # 計算與正常工時的重疊部分
                regular_hours = self._calculate_overlap_hours(
                    start_dt, end_dt, regular_start, regular_end
                )
                
                # 如果有午休時間，且不是SMT報工記錄，才扣除午休時間
                if lunch_start and lunch_end and report_type != 'smt':
                    lunch_start_dt = datetime.combine(work_date, lunch_start)
                    lunch_end_dt = datetime.combine(work_date, lunch_end)
                    
                    # 處理跨日午休
                    if lunch_end_dt < lunch_start_dt:
                        lunch_end_dt += timedelta(days=1)
                    
                    # 計算實際工作時間與午休時間的重疊部分
                    lunch_overlap_in_work = self._calculate_overlap_hours(
                        start_dt, end_dt, lunch_start_dt, lunch_end_dt
                    )
                    
                    # 從正常工時中扣除午休時間的重疊部分
                    # 但只扣除在正常工時範圍內的午休時間
                    if lunch_overlap_in_work > 0:
                        # 計算午休時間在正常工時範圍內的部分
                        lunch_in_regular_start = max(regular_start, lunch_start_dt)
                        lunch_in_regular_end = min(regular_end, lunch_end_dt)
                        
                        if lunch_in_regular_start < lunch_in_regular_end:
                            lunch_in_regular_hours = (lunch_in_regular_end - lunch_in_regular_start).total_seconds() / 3600
                            regular_hours = max(0, regular_hours - lunch_in_regular_hours)
            
            # 計算加班時數
            if overtime_start and overtime_end:
                overtime_start_dt = datetime.combine(work_date, overtime_start)
                overtime_end_dt = datetime.combine(work_date, overtime_end)
                
                # 處理跨日加班
                if overtime_end_dt < overtime_start_dt:
                    overtime_end_dt += timedelta(days=1)
                
                overtime_hours = self._calculate_overlap_hours(
                    start_dt, end_dt, overtime_start_dt, overtime_end_dt
                )
            else:
                # 如果沒有設定加班時間，超過正常工時的部分算作加班
                if regular_hours > 0:
                    total_hours = (end_dt - start_dt).total_seconds() / 3600
                    overtime_hours = max(0, total_hours - regular_hours)
                else:
                    # 如果沒有正常工時設定，全部算作正常工時
                    total_hours = (end_dt - start_dt).total_seconds() / 3600
                    regular_hours = total_hours
            
            # 計算休息時數（午休時間）- SMT報工記錄不計算休息時數
            if lunch_start and lunch_end and report_type != 'smt':
                lunch_start_dt = datetime.combine(work_date, lunch_start)
                lunch_end_dt = datetime.combine(work_date, lunch_end)
                
                # 處理跨日午休
                if lunch_end_dt < lunch_start_dt:
                    lunch_end_dt += timedelta(days=1)
                
                break_hours = self._calculate_overlap_hours(
                    start_dt, end_dt, lunch_start_dt, lunch_end_dt
                )
            else:
                break_hours = 0.0
            
            # 計算實際工作時數（總時數減去休息時數）
            total_hours = (end_dt - start_dt).total_seconds() / 3600
            actual_hours = max(0, total_hours - break_hours)
            
            # 記錄計算過程
            self.logger.info(f"工作時數計算結果: 總時數={total_hours:.2f}, 正常工時={regular_hours:.2f}, "
                           f"加班時數={overtime_hours:.2f}, 休息時數={break_hours:.2f}, 實際工作時數={actual_hours:.2f}")
            
            return {
                'total_work_hours': round(total_hours, 2),
                'actual_work_hours': round(actual_hours, 2),
                'break_hours': round(break_hours, 2),
                'overtime_hours': round(overtime_hours, 2),
                'regular_hours': round(regular_hours, 2)
            }
            
        except Exception as e:
            self.logger.error(f"根據產線設定計算工作時數失敗: {str(e)}")
            # 發生錯誤時使用原始計算
            total_hours = (end_dt - start_dt).total_seconds() / 3600
            return {
                'total_work_hours': round(total_hours, 2),
                'actual_work_hours': round(total_hours, 2),
                'break_hours': 0.0,
                'overtime_hours': 0.0,
                'regular_hours': round(total_hours, 2)
            }
    
    def _is_workday(self, work_date: date, production_line: ProductionLine) -> bool:
        """
        檢查是否為工作日
        
        Args:
            work_date: 工作日期
            production_line: 產線設定
            
        Returns:
            bool: 是否為工作日
        """
        try:
            # 取得星期幾（1=週一，7=週日）
            weekday = work_date.isoweekday()
            work_days = production_line.get_work_days_list()
            
            return str(weekday) in work_days
        except Exception as e:
            self.logger.error(f"檢查工作日失敗: {str(e)}")
            return True  # 預設為工作日
    
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
            overlap_seconds = (overlap_end - overlap_start).total_seconds()
            return overlap_seconds / 3600
            
        except Exception as e:
            self.logger.error(f"計算重疊時數失敗: {str(e)}")
            return 0.0
    
    def calculate_daily_summary(self, work_date: date, worker_name: str = None) -> Dict[str, float]:
        """
        計算某日的工作時數摘要
        
        Args:
            work_date: 工作日期
            worker_name: 作業員名稱（可選）
            
        Returns:
            Dict[str, float]: 工作時數摘要
        """
        try:
            # 查詢當日的報工記錄
            operator_reports = OperatorSupplementReport.objects.filter(
                work_date=work_date,
                approval_status='approved'
            )
            
            if worker_name:
                operator_reports = operator_reports.filter(operator__name=worker_name)
            
            smt_reports = SMTProductionReport.objects.filter(
                work_date=work_date,
                approval_status='approved'
            )
            
            supervisor_reports = SupervisorProductionReport.objects.filter(
                work_date=work_date
            )
            
            # 合併所有報工記錄
            all_reports = list(operator_reports) + list(smt_reports) + list(supervisor_reports)
            
            # 計算總計
            total_work_hours = 0.0
            total_actual_hours = 0.0
            total_break_hours = 0.0
            total_overtime_hours = 0.0
            total_regular_hours = 0.0
            
            for report in all_reports:
                work_time = self.calculate_work_time_for_report(report)
                total_work_hours += work_time['total_work_hours']
                total_actual_hours += work_time['actual_work_hours']
                total_break_hours += work_time['break_hours']
                total_overtime_hours += work_time['overtime_hours']
                total_regular_hours += work_time['regular_hours']
            
            return {
                'total_work_hours': round(total_work_hours, 2),
                'actual_work_hours': round(total_actual_hours, 2),
                'break_hours': round(total_break_hours, 2),
                'overtime_hours': round(total_overtime_hours, 2),
                'regular_hours': round(total_regular_hours, 2),
                'report_count': len(all_reports)
            }
            
        except Exception as e:
            self.logger.error(f"計算日工作時數摘要失敗: {str(e)}")
            return {
                'total_work_hours': 0.0,
                'actual_work_hours': 0.0,
                'break_hours': 0.0,
                'overtime_hours': 0.0,
                'regular_hours': 0.0,
                'report_count': 0
            } 