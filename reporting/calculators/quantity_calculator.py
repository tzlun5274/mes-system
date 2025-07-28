# 數量計算器模組
# 本檔案負責計算產量、庫存、需求等相關指標

import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal
from .base_calculator import BaseCalculator


class QuantityCalculator(BaseCalculator):
    """數量計算器 - 負責計算各種數量相關指標"""
    
    def __init__(self):
        """初始化數量計算器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def calculate_total_quantity(self, quantities: List[Union[float, int]]) -> float:
        """
        計算總數量
        
        Args:
            quantities: 數量列表
            
        Returns:
            float: 總數量
        """
        try:
            if not quantities:
                return 0.0
            
            total = sum(float(q) for q in quantities if q is not None)
            return self.round_decimal(total, 2)
        except Exception as e:
            self.logger.error(f"計算總數量失敗: {str(e)}")
            return 0.0
    
    def calculate_daily_production(self, production_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每日產量
        
        Args:
            production_records: 生產記錄列表
            
        Returns:
            Dict[str, float]: 每日產量字典
        """
        try:
            daily_production = {}
            
            for record in production_records:
                record_date = record.get('date')
                quantity = record.get('quantity', 0)
                
                if not record_date or quantity is None:
                    continue
                
                date_key = record_date.strftime('%Y-%m-%d') if isinstance(record_date, date) else str(record_date)
                
                if date_key in daily_production:
                    daily_production[date_key] += float(quantity)
                else:
                    daily_production[date_key] = float(quantity)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in daily_production.items()}
        except Exception as e:
            self.logger.error(f"計算每日產量失敗: {str(e)}")
            return {}
    
    def calculate_weekly_production(self, production_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每週產量
        
        Args:
            production_records: 生產記錄列表
            
        Returns:
            Dict[str, float]: 每週產量字典
        """
        try:
            weekly_production = {}
            
            for record in production_records:
                record_date = record.get('date')
                quantity = record.get('quantity', 0)
                
                if not record_date or quantity is None:
                    continue
                
                # 計算週數
                if isinstance(record_date, date):
                    week_number = record_date.isocalendar()[1]
                    week_key = f"{record_date.year}-W{week_number:02d}"
                else:
                    # 如果是字串，嘗試轉換
                    try:
                        date_obj = datetime.strptime(str(record_date), '%Y-%m-%d').date()
                        week_number = date_obj.isocalendar()[1]
                        week_key = f"{date_obj.year}-W{week_number:02d}"
                    except:
                        continue
                
                if week_key in weekly_production:
                    weekly_production[week_key] += float(quantity)
                else:
                    weekly_production[week_key] = float(quantity)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in weekly_production.items()}
        except Exception as e:
            self.logger.error(f"計算每週產量失敗: {str(e)}")
            return {}
    
    def calculate_monthly_production(self, production_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算每月產量
        
        Args:
            production_records: 生產記錄列表
            
        Returns:
            Dict[str, float]: 每月產量字典
        """
        try:
            monthly_production = {}
            
            for record in production_records:
                record_date = record.get('date')
                quantity = record.get('quantity', 0)
                
                if not record_date or quantity is None:
                    continue
                
                # 計算月份
                if isinstance(record_date, date):
                    month_key = f"{record_date.year}-{record_date.month:02d}"
                else:
                    # 如果是字串，嘗試轉換
                    try:
                        date_obj = datetime.strptime(str(record_date), '%Y-%m-%d').date()
                        month_key = f"{date_obj.year}-{date_obj.month:02d}"
                    except:
                        continue
                
                if month_key in monthly_production:
                    monthly_production[month_key] += float(quantity)
                else:
                    monthly_production[month_key] = float(quantity)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in monthly_production.items()}
        except Exception as e:
            self.logger.error(f"計算每月產量失敗: {str(e)}")
            return {}
    
    def calculate_operator_production(self, production_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算作業員產量
        
        Args:
            production_records: 生產記錄列表
            
        Returns:
            Dict[str, float]: 作業員產量字典
        """
        try:
            operator_production = {}
            
            for record in production_records:
                operator_id = record.get('operator_id')
                quantity = record.get('quantity', 0)
                
                if not operator_id or quantity is None:
                    continue
                
                if operator_id in operator_production:
                    operator_production[operator_id] += float(quantity)
                else:
                    operator_production[operator_id] = float(quantity)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in operator_production.items()}
        except Exception as e:
            self.logger.error(f"計算作業員產量失敗: {str(e)}")
            return {}
    
    def calculate_workorder_production(self, production_records: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        計算工單產量
        
        Args:
            production_records: 生產記錄列表
            
        Returns:
            Dict[str, float]: 工單產量字典
        """
        try:
            workorder_production = {}
            
            for record in production_records:
                workorder_id = record.get('workorder_id')
                quantity = record.get('quantity', 0)
                
                if not workorder_id or quantity is None:
                    continue
                
                if workorder_id in workorder_production:
                    workorder_production[workorder_id] += float(quantity)
                else:
                    workorder_production[workorder_id] = float(quantity)
            
            # 四捨五入到小數點後2位
            return {k: self.round_decimal(v, 2) for k, v in workorder_production.items()}
        except Exception as e:
            self.logger.error(f"計算工單產量失敗: {str(e)}")
            return {}
    
    def calculate_inventory_level(self, initial_stock: float, production: float, 
                                consumption: float, returns: float = 0.0) -> float:
        """
        計算庫存水平
        
        Args:
            initial_stock: 期初庫存
            production: 生產數量
            consumption: 消耗數量
            returns: 退貨數量
            
        Returns:
            float: 期末庫存
        """
        try:
            final_stock = initial_stock + production - consumption + returns
            return self.round_decimal(max(0, final_stock), 2)
        except Exception as e:
            self.logger.error(f"計算庫存水平失敗: {str(e)}")
            return 0.0
    
    def calculate_safety_stock(self, average_demand: float, lead_time: float, 
                             service_level: float = 0.95) -> float:
        """
        計算安全庫存
        
        Args:
            average_demand: 平均需求
            lead_time: 前置時間
            service_level: 服務水準（預設95%）
            
        Returns:
            float: 安全庫存
        """
        try:
            # 簡化的安全庫存計算公式
            # 實際應用中可能需要更複雜的統計方法
            safety_stock = average_demand * lead_time * (1 - service_level)
            return self.round_decimal(max(0, safety_stock), 2)
        except Exception as e:
            self.logger.error(f"計算安全庫存失敗: {str(e)}")
            return 0.0
    
    def calculate_reorder_point(self, average_demand: float, lead_time: float, 
                              safety_stock: float) -> float:
        """
        計算再訂購點
        
        Args:
            average_demand: 平均需求
            lead_time: 前置時間
            safety_stock: 安全庫存
            
        Returns:
            float: 再訂購點
        """
        try:
            reorder_point = (average_demand * lead_time) + safety_stock
            return self.round_decimal(max(0, reorder_point), 2)
        except Exception as e:
            self.logger.error(f"計算再訂購點失敗: {str(e)}")
            return 0.0
    
    def calculate_economic_order_quantity(self, annual_demand: float, order_cost: float, 
                                        holding_cost: float) -> float:
        """
        計算經濟訂購量
        
        Args:
            annual_demand: 年需求量
            order_cost: 訂購成本
            holding_cost: 持有成本
            
        Returns:
            float: 經濟訂購量
        """
        try:
            if holding_cost <= 0:
                return 0.0
            
            eoq = ((2 * annual_demand * order_cost) / holding_cost) ** 0.5
            return self.round_decimal(eoq, 2)
        except Exception as e:
            self.logger.error(f"計算經濟訂購量失敗: {str(e)}")
            return 0.0
    
    def calculate_production_efficiency(self, actual_quantity: float, 
                                      standard_quantity: float) -> float:
        """
        計算生產效率
        
        Args:
            actual_quantity: 實際產量
            standard_quantity: 標準產量
            
        Returns:
            float: 生產效率百分比
        """
        try:
            return self.calculate_percentage(actual_quantity, standard_quantity)
        except Exception as e:
            self.logger.error(f"計算生產效率失敗: {str(e)}")
            return 0.0
    
    def calculate_yield_rate(self, good_quantity: float, total_quantity: float) -> float:
        """
        計算良率
        
        Args:
            good_quantity: 良品數量
            total_quantity: 總數量
            
        Returns:
            float: 良率百分比
        """
        try:
            return self.calculate_percentage(good_quantity, total_quantity)
        except Exception as e:
            self.logger.error(f"計算良率失敗: {str(e)}")
            return 0.0
    
    def calculate_defect_rate(self, defect_quantity: float, total_quantity: float) -> float:
        """
        計算不良率
        
        Args:
            defect_quantity: 不良品數量
            total_quantity: 總數量
            
        Returns:
            float: 不良率百分比
        """
        try:
            return self.calculate_percentage(defect_quantity, total_quantity)
        except Exception as e:
            self.logger.error(f"計算不良率失敗: {str(e)}")
            return 0.0
    
    def calculate_throughput(self, production_quantity: float, time_period: float) -> float:
        """
        計算產能
        
        Args:
            production_quantity: 生產數量
            time_period: 時間週期（小時）
            
        Returns:
            float: 產能（數量/小時）
        """
        try:
            if time_period <= 0:
                return 0.0
            
            throughput = production_quantity / time_period
            return self.round_decimal(throughput, 2)
        except Exception as e:
            self.logger.error(f"計算產能失敗: {str(e)}")
            return 0.0 