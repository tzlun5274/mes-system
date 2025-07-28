# 效率計算器模組
# 本檔案負責計算各種效率指標

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal
from .base_calculator import BaseCalculator


class EfficiencyCalculator(BaseCalculator):
    """效率計算器 - 負責計算各種效率指標"""
    
    def __init__(self):
        """初始化效率計算器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def calculate_overall_equipment_effectiveness(self, availability: float, 
                                                performance: float, 
                                                quality: float) -> float:
        """
        計算整體設備效率 (OEE)
        
        Args:
            availability: 可用性
            performance: 性能
            quality: 品質
            
        Returns:
            float: OEE百分比
        """
        try:
            oee = availability * performance * quality
            return self.round_decimal(oee * 100, 2)
        except Exception as e:
            self.logger.error(f"計算OEE失敗: {str(e)}")
            return 0.0
    
    def calculate_availability(self, actual_runtime: float, planned_runtime: float) -> float:
        """
        計算可用性
        
        Args:
            actual_runtime: 實際運行時間
            planned_runtime: 計劃運行時間
            
        Returns:
            float: 可用性百分比
        """
        try:
            return self.calculate_percentage(actual_runtime, planned_runtime)
        except Exception as e:
            self.logger.error(f"計算可用性失敗: {str(e)}")
            return 0.0
    
    def calculate_performance_efficiency(self, actual_cycle_time: float, 
                                       standard_cycle_time: float) -> float:
        """
        計算性能效率
        
        Args:
            actual_cycle_time: 實際週期時間
            standard_cycle_time: 標準週期時間
            
        Returns:
            float: 性能效率百分比
        """
        try:
            if actual_cycle_time <= 0:
                return 0.0
            
            performance = (standard_cycle_time / actual_cycle_time) * 100
            return self.round_decimal(performance, 2)
        except Exception as e:
            self.logger.error(f"計算性能效率失敗: {str(e)}")
            return 0.0
    
    def calculate_quality_rate(self, good_quantity: float, total_quantity: float) -> float:
        """
        計算品質率
        
        Args:
            good_quantity: 良品數量
            total_quantity: 總數量
            
        Returns:
            float: 品質率百分比
        """
        try:
            return self.calculate_percentage(good_quantity, total_quantity)
        except Exception as e:
            self.logger.error(f"計算品質率失敗: {str(e)}")
            return 0.0
    
    def calculate_labor_efficiency(self, standard_hours: float, actual_hours: float) -> float:
        """
        計算人工效率
        
        Args:
            standard_hours: 標準工時
            actual_hours: 實際工時
            
        Returns:
            float: 人工效率百分比
        """
        try:
            if actual_hours <= 0:
                return 0.0
            
            efficiency = (standard_hours / actual_hours) * 100
            return self.round_decimal(efficiency, 2)
        except Exception as e:
            self.logger.error(f"計算人工效率失敗: {str(e)}")
            return 0.0
    
    def calculate_production_efficiency(self, actual_output: float, 
                                      standard_output: float) -> float:
        """
        計算生產效率
        
        Args:
            actual_output: 實際產出
            standard_output: 標準產出
            
        Returns:
            float: 生產效率百分比
        """
        try:
            return self.calculate_percentage(actual_output, standard_output)
        except Exception as e:
            self.logger.error(f"計算生產效率失敗: {str(e)}")
            return 0.0
    
    def calculate_cycle_time_efficiency(self, standard_cycle_time: float, 
                                      actual_cycle_time: float) -> float:
        """
        計算週期時間效率
        
        Args:
            standard_cycle_time: 標準週期時間
            actual_cycle_time: 實際週期時間
            
        Returns:
            float: 週期時間效率百分比
        """
        try:
            if actual_cycle_time <= 0:
                return 0.0
            
            efficiency = (standard_cycle_time / actual_cycle_time) * 100
            return self.round_decimal(efficiency, 2)
        except Exception as e:
            self.logger.error(f"計算週期時間效率失敗: {str(e)}")
            return 0.0
    
    def calculate_setup_efficiency(self, standard_setup_time: float, 
                                 actual_setup_time: float) -> float:
        """
        計算換線效率
        
        Args:
            standard_setup_time: 標準換線時間
            actual_setup_time: 實際換線時間
            
        Returns:
            float: 換線效率百分比
        """
        try:
            if actual_setup_time <= 0:
                return 0.0
            
            efficiency = (standard_setup_time / actual_setup_time) * 100
            return self.round_decimal(efficiency, 2)
        except Exception as e:
            self.logger.error(f"計算換線效率失敗: {str(e)}")
            return 0.0
    
    def calculate_utilization_rate(self, actual_usage: float, 
                                 total_capacity: float) -> float:
        """
        計算利用率
        
        Args:
            actual_usage: 實際使用量
            total_capacity: 總容量
            
        Returns:
            float: 利用率百分比
        """
        try:
            return self.calculate_percentage(actual_usage, total_capacity)
        except Exception as e:
            self.logger.error(f"計算利用率失敗: {str(e)}")
            return 0.0
    
    def calculate_operator_efficiency(self, operator_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算作業員效率
        
        Args:
            operator_records: 作業員記錄列表
            
        Returns:
            Dict[str, float]: 作業員效率字典
        """
        try:
            operator_efficiency = {}
            
            for record in operator_records:
                operator_id = record.get('operator_id')
                standard_hours = record.get('standard_hours', 0)
                actual_hours = record.get('actual_hours', 0)
                
                if not operator_id or actual_hours <= 0:
                    continue
                
                efficiency = self.calculate_labor_efficiency(standard_hours, actual_hours)
                operator_efficiency[operator_id] = efficiency
            
            return operator_efficiency
        except Exception as e:
            self.logger.error(f"計算作業員效率失敗: {str(e)}")
            return {}
    
    def calculate_equipment_efficiency(self, equipment_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算設備效率
        
        Args:
            equipment_records: 設備記錄列表
            
        Returns:
            Dict[str, float]: 設備效率字典
        """
        try:
            equipment_efficiency = {}
            
            for record in equipment_records:
                equipment_id = record.get('equipment_id')
                availability = record.get('availability', 0)
                performance = record.get('performance', 0)
                quality = record.get('quality', 0)
                
                if not equipment_id:
                    continue
                
                oee = self.calculate_overall_equipment_effectiveness(
                    availability / 100, performance / 100, quality / 100
                )
                equipment_efficiency[equipment_id] = oee
            
            return equipment_efficiency
        except Exception as e:
            self.logger.error(f"計算設備效率失敗: {str(e)}")
            return {}
    
    def calculate_line_efficiency(self, line_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算產線效率
        
        Args:
            line_records: 產線記錄列表
            
        Returns:
            Dict[str, float]: 產線效率字典
        """
        try:
            line_efficiency = {}
            
            for record in line_records:
                line_id = record.get('line_id')
                actual_output = record.get('actual_output', 0)
                standard_output = record.get('standard_output', 0)
                
                if not line_id:
                    continue
                
                efficiency = self.calculate_production_efficiency(actual_output, standard_output)
                line_efficiency[line_id] = efficiency
            
            return line_efficiency
        except Exception as e:
            self.logger.error(f"計算產線效率失敗: {str(e)}")
            return {}
    
    def calculate_daily_efficiency(self, daily_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每日效率
        
        Args:
            daily_records: 每日記錄列表
            
        Returns:
            Dict[str, float]: 每日效率字典
        """
        try:
            daily_efficiency = {}
            
            for record in daily_records:
                record_date = record.get('date')
                actual_output = record.get('actual_output', 0)
                standard_output = record.get('standard_output', 0)
                
                if not record_date:
                    continue
                
                date_key = record_date.strftime('%Y-%m-%d') if isinstance(record_date, date) else str(record_date)
                efficiency = self.calculate_production_efficiency(actual_output, standard_output)
                daily_efficiency[date_key] = efficiency
            
            return daily_efficiency
        except Exception as e:
            self.logger.error(f"計算每日效率失敗: {str(e)}")
            return {}
    
    def calculate_weekly_efficiency(self, weekly_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每週效率
        
        Args:
            weekly_records: 每週記錄列表
            
        Returns:
            Dict[str, float]: 每週效率字典
        """
        try:
            weekly_efficiency = {}
            
            for record in weekly_records:
                record_date = record.get('date')
                actual_output = record.get('actual_output', 0)
                standard_output = record.get('standard_output', 0)
                
                if not record_date:
                    continue
                
                # 計算週數
                if isinstance(record_date, date):
                    week_number = record_date.isocalendar()[1]
                    week_key = f"{record_date.year}-W{week_number:02d}"
                else:
                    try:
                        date_obj = datetime.strptime(str(record_date), '%Y-%m-%d').date()
                        week_number = date_obj.isocalendar()[1]
                        week_key = f"{date_obj.year}-W{week_number:02d}"
                    except:
                        continue
                
                efficiency = self.calculate_production_efficiency(actual_output, standard_output)
                weekly_efficiency[week_key] = efficiency
            
            return weekly_efficiency
        except Exception as e:
            self.logger.error(f"計算每週效率失敗: {str(e)}")
            return {}
    
    def calculate_monthly_efficiency(self, monthly_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每月效率
        
        Args:
            monthly_records: 每月記錄列表
            
        Returns:
            Dict[str, float]: 每月效率字典
        """
        try:
            monthly_efficiency = {}
            
            for record in monthly_records:
                record_date = record.get('date')
                actual_output = record.get('actual_output', 0)
                standard_output = record.get('standard_output', 0)
                
                if not record_date:
                    continue
                
                # 計算月份
                if isinstance(record_date, date):
                    month_key = f"{record_date.year}-{record_date.month:02d}"
                else:
                    try:
                        date_obj = datetime.strptime(str(record_date), '%Y-%m-%d').date()
                        month_key = f"{date_obj.year}-{date_obj.month:02d}"
                    except:
                        continue
                
                efficiency = self.calculate_production_efficiency(actual_output, standard_output)
                monthly_efficiency[month_key] = efficiency
            
            return monthly_efficiency
        except Exception as e:
            self.logger.error(f"計算每月效率失敗: {str(e)}")
            return {}
    
    def calculate_trend_efficiency(self, efficiency_data: List[float], 
                                 periods: int = 1) -> Dict[str, float]:
        """
        計算效率趨勢
        
        Args:
            efficiency_data: 效率數據列表
            periods: 趨勢週期
            
        Returns:
            Dict[str, float]: 效率趨勢字典
        """
        try:
            return self.calculate_trend(efficiency_data, periods)
        except Exception as e:
            self.logger.error(f"計算效率趨勢失敗: {str(e)}")
            return {} 