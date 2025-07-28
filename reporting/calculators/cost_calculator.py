# 成本計算器模組
# 本檔案負責計算各種成本指標

import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal
from .base_calculator import BaseCalculator


class CostCalculator(BaseCalculator):
    """成本計算器 - 負責計算各種成本指標"""
    
    def __init__(self):
        """初始化成本計算器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def calculate_total_cost(self, costs: List[Union[float, int]]) -> float:
        """
        計算總成本
        
        Args:
            costs: 成本列表
            
        Returns:
            float: 總成本
        """
        try:
            if not costs:
                return 0.0
            
            total = sum(float(c) for c in costs if c is not None)
            return self.round_decimal(total, 2)
        except Exception as e:
            self.logger.error(f"計算總成本失敗: {str(e)}")
            return 0.0
    
    def calculate_labor_cost(self, hours: float, hourly_rate: float) -> float:
        """
        計算人工成本
        
        Args:
            hours: 工作時數
            hourly_rate: 時薪
            
        Returns:
            float: 人工成本
        """
        try:
            labor_cost = hours * hourly_rate
            return self.round_decimal(labor_cost, 2)
        except Exception as e:
            self.logger.error(f"計算人工成本失敗: {str(e)}")
            return 0.0
    
    def calculate_material_cost(self, quantity: float, unit_price: float) -> float:
        """
        計算材料成本
        
        Args:
            quantity: 數量
            unit_price: 單價
            
        Returns:
            float: 材料成本
        """
        try:
            material_cost = quantity * unit_price
            return self.round_decimal(material_cost, 2)
        except Exception as e:
            self.logger.error(f"計算材料成本失敗: {str(e)}")
            return 0.0
    
    def calculate_overhead_cost(self, direct_labor_cost: float, 
                              overhead_rate: float) -> float:
        """
        計算間接成本
        
        Args:
            direct_labor_cost: 直接人工成本
            overhead_rate: 間接成本率
            
        Returns:
            float: 間接成本
        """
        try:
            overhead_cost = direct_labor_cost * overhead_rate
            return self.round_decimal(overhead_cost, 2)
        except Exception as e:
            self.logger.error(f"計算間接成本失敗: {str(e)}")
            return 0.0
    
    def calculate_unit_cost(self, total_cost: float, total_quantity: float) -> float:
        """
        計算單位成本
        
        Args:
            total_cost: 總成本
            total_quantity: 總數量
            
        Returns:
            float: 單位成本
        """
        try:
            if total_quantity <= 0:
                return 0.0
            
            unit_cost = total_cost / total_quantity
            return self.round_decimal(unit_cost, 2)
        except Exception as e:
            self.logger.error(f"計算單位成本失敗: {str(e)}")
            return 0.0
    
    def calculate_cost_variance(self, actual_cost: float, standard_cost: float) -> float:
        """
        計算成本差異
        
        Args:
            actual_cost: 實際成本
            standard_cost: 標準成本
            
        Returns:
            float: 成本差異
        """
        try:
            variance = actual_cost - standard_cost
            return self.round_decimal(variance, 2)
        except Exception as e:
            self.logger.error(f"計算成本差異失敗: {str(e)}")
            return 0.0
    
    def calculate_cost_variance_percentage(self, actual_cost: float, 
                                         standard_cost: float) -> float:
        """
        計算成本差異百分比
        
        Args:
            actual_cost: 實際成本
            standard_cost: 標準成本
            
        Returns:
            float: 成本差異百分比
        """
        try:
            if standard_cost <= 0:
                return 0.0
            
            variance_percentage = ((actual_cost - standard_cost) / standard_cost) * 100
            return self.round_decimal(variance_percentage, 2)
        except Exception as e:
            self.logger.error(f"計算成本差異百分比失敗: {str(e)}")
            return 0.0
    
    def calculate_daily_cost(self, cost_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每日成本
        
        Args:
            cost_records: 成本記錄列表
            
        Returns:
            Dict[str, float]: 每日成本字典
        """
        try:
            daily_cost = {}
            
            for record in cost_records:
                record_date = record.get('date')
                cost = record.get('cost', 0)
                
                if not record_date or cost is None:
                    continue
                
                date_key = record_date.strftime('%Y-%m-%d') if isinstance(record_date, date) else str(record_date)
                
                if date_key in daily_cost:
                    daily_cost[date_key] += float(cost)
                else:
                    daily_cost[date_key] = float(cost)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in daily_cost.items()}
        except Exception as e:
            self.logger.error(f"計算每日成本失敗: {str(e)}")
            return {}
    
    def calculate_weekly_cost(self, cost_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每週成本
        
        Args:
            cost_records: 成本記錄列表
            
        Returns:
            Dict[str, float]: 每週成本字典
        """
        try:
            weekly_cost = {}
            
            for record in cost_records:
                record_date = record.get('date')
                cost = record.get('cost', 0)
                
                if not record_date or cost is None:
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
                
                if week_key in weekly_cost:
                    weekly_cost[week_key] += float(cost)
                else:
                    weekly_cost[week_key] = float(cost)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in weekly_cost.items()}
        except Exception as e:
            self.logger.error(f"計算每週成本失敗: {str(e)}")
            return {}
    
    def calculate_monthly_cost(self, cost_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每月成本
        
        Args:
            cost_records: 成本記錄列表
            
        Returns:
            Dict[str, float]: 每月成本字典
        """
        try:
            monthly_cost = {}
            
            for record in cost_records:
                record_date = record.get('date')
                cost = record.get('cost', 0)
                
                if not record_date or cost is None:
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
                
                if month_key in monthly_cost:
                    monthly_cost[month_key] += float(cost)
                else:
                    monthly_cost[month_key] = float(cost)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in monthly_cost.items()}
        except Exception as e:
            self.logger.error(f"計算每月成本失敗: {str(e)}")
            return {}
    
    def calculate_workorder_cost(self, workorder_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算工單成本
        
        Args:
            workorder_records: 工單記錄列表
            
        Returns:
            Dict[str, float]: 工單成本字典
        """
        try:
            workorder_cost = {}
            
            for record in workorder_records:
                workorder_id = record.get('workorder_id')
                cost = record.get('cost', 0)
                
                if not workorder_id or cost is None:
                    continue
                
                if workorder_id in workorder_cost:
                    workorder_cost[workorder_id] += float(cost)
                else:
                    workorder_cost[workorder_id] = float(cost)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in workorder_cost.items()}
        except Exception as e:
            self.logger.error(f"計算工單成本失敗: {str(e)}")
            return {}
    
    def calculate_operator_cost(self, operator_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算作業員成本
        
        Args:
            operator_records: 作業員記錄列表
            
        Returns:
            Dict[str, float]: 作業員成本字典
        """
        try:
            operator_cost = {}
            
            for record in operator_records:
                operator_id = record.get('operator_id')
                hours = record.get('hours', 0)
                hourly_rate = record.get('hourly_rate', 0)
                
                if not operator_id or hours is None or hourly_rate is None:
                    continue
                
                cost = self.calculate_labor_cost(hours, hourly_rate)
                
                if operator_id in operator_cost:
                    operator_cost[operator_id] += cost
                else:
                    operator_cost[operator_id] = cost
            
            return operator_cost
        except Exception as e:
            self.logger.error(f"計算作業員成本失敗: {str(e)}")
            return {}
    
    def calculate_cost_per_unit(self, total_cost: float, total_units: float) -> float:
        """
        計算每單位成本
        
        Args:
            total_cost: 總成本
            total_units: 總單位數
            
        Returns:
            float: 每單位成本
        """
        try:
            return self.calculate_unit_cost(total_cost, total_units)
        except Exception as e:
            self.logger.error(f"計算每單位成本失敗: {str(e)}")
            return 0.0
    
    def calculate_cost_efficiency(self, actual_cost: float, 
                                standard_cost: float) -> float:
        """
        計算成本效率
        
        Args:
            actual_cost: 實際成本
            standard_cost: 標準成本
            
        Returns:
            float: 成本效率百分比
        """
        try:
            if standard_cost <= 0:
                return 0.0
            
            efficiency = (standard_cost / actual_cost) * 100
            return self.round_decimal(efficiency, 2)
        except Exception as e:
            self.logger.error(f"計算成本效率失敗: {str(e)}")
            return 0.0
    
    def calculate_profit_margin(self, revenue: float, cost: float) -> float:
        """
        計算利潤率
        
        Args:
            revenue: 營收
            cost: 成本
            
        Returns:
            float: 利潤率百分比
        """
        try:
            if revenue <= 0:
                return 0.0
            
            profit = revenue - cost
            margin = (profit / revenue) * 100
            return self.round_decimal(margin, 2)
        except Exception as e:
            self.logger.error(f"計算利潤率失敗: {str(e)}")
            return 0.0
    
    def calculate_break_even_point(self, fixed_cost: float, 
                                 unit_price: float, 
                                 unit_variable_cost: float) -> float:
        """
        計算損益平衡點
        
        Args:
            fixed_cost: 固定成本
            unit_price: 單位售價
            unit_variable_cost: 單位變動成本
            
        Returns:
            float: 損益平衡點數量
        """
        try:
            if unit_price <= unit_variable_cost:
                return 0.0
            
            contribution_margin = unit_price - unit_variable_cost
            break_even = fixed_cost / contribution_margin
            return self.round_decimal(break_even, 2)
        except Exception as e:
            self.logger.error(f"計算損益平衡點失敗: {str(e)}")
            return 0.0 