# 計算引擎基礎類別
# 本檔案定義了所有計算引擎的基礎類別和共用方法

import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal


class BaseCalculator:
    """計算引擎基礎類別 - 所有計算引擎的基礎類別"""
    
    def __init__(self):
        """初始化計算引擎"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_input(self, **kwargs) -> bool:
        """
        驗證輸入參數
        
        Args:
            **kwargs: 輸入參數
            
        Returns:
            bool: 驗證結果
        """
        try:
            # 基本驗證邏輯
            return True
        except Exception as e:
            self.logger.error(f"輸入驗證失敗: {str(e)}")
            return False
    
    def round_decimal(self, value: Union[float, Decimal], places: int = 2) -> float:
        """
        四捨五入到指定小數位數
        
        Args:
            value: 要四捨五入的值
            places: 小數位數
            
        Returns:
            float: 四捨五入後的值
        """
        try:
            if value is None:
                return 0.0
            return round(float(value), places)
        except Exception as e:
            self.logger.error(f"四捨五入計算失敗: {str(e)}")
            return 0.0
    
    def safe_division(self, numerator: Union[float, int], denominator: Union[float, int], default: float = 0.0) -> float:
        """
        安全的除法運算（避免除零錯誤）
        
        Args:
            numerator: 分子
            denominator: 分母
            default: 除零時的預設值
            
        Returns:
            float: 除法結果
        """
        try:
            if denominator == 0 or denominator is None:
                return default
            return float(numerator) / float(denominator)
        except Exception as e:
            self.logger.error(f"除法運算失敗: {str(e)}")
            return default
    
    def calculate_percentage(self, part: Union[float, int], total: Union[float, int], default: float = 0.0) -> float:
        """
        計算百分比
        
        Args:
            part: 部分值
            total: 總值
            default: 除零時的預設值
            
        Returns:
            float: 百分比值
        """
        try:
            result = self.safe_division(part, total, default)
            return self.round_decimal(result * 100, 2)
        except Exception as e:
            self.logger.error(f"百分比計算失敗: {str(e)}")
            return default
    
    def calculate_average(self, values: List[Union[float, int]], default: float = 0.0) -> float:
        """
        計算平均值
        
        Args:
            values: 數值列表
            default: 空列表時的預設值
            
        Returns:
            float: 平均值
        """
        try:
            if not values:
                return default
            
            # 過濾掉 None 值
            valid_values = [v for v in values if v is not None]
            if not valid_values:
                return default
            
            return self.round_decimal(sum(valid_values) / len(valid_values), 2)
        except Exception as e:
            self.logger.error(f"平均值計算失敗: {str(e)}")
            return default
    
    def calculate_sum(self, values: List[Union[float, int]], default: float = 0.0) -> float:
        """
        計算總和
        
        Args:
            values: 數值列表
            default: 空列表時的預設值
            
        Returns:
            float: 總和
        """
        try:
            if not values:
                return default
            
            # 過濾掉 None 值
            valid_values = [v for v in values if v is not None]
            if not valid_values:
                return default
            
            return self.round_decimal(sum(valid_values), 2)
        except Exception as e:
            self.logger.error(f"總和計算失敗: {str(e)}")
            return default
    
    def calculate_min_max(self, values: List[Union[float, int]]) -> Dict[str, float]:
        """
        計算最小值和最大值
        
        Args:
            values: 數值列表
            
        Returns:
            Dict[str, float]: 包含最小值和最大值的字典
        """
        try:
            if not values:
                return {'min': 0.0, 'max': 0.0}
            
            # 過濾掉 None 值
            valid_values = [v for v in values if v is not None]
            if not valid_values:
                return {'min': 0.0, 'max': 0.0}
            
            return {
                'min': self.round_decimal(min(valid_values), 2),
                'max': self.round_decimal(max(valid_values), 2)
            }
        except Exception as e:
            self.logger.error(f"最小最大值計算失敗: {str(e)}")
            return {'min': 0.0, 'max': 0.0}
    
    def calculate_median(self, values: List[Union[float, int]], default: float = 0.0) -> float:
        """
        計算中位數
        
        Args:
            values: 數值列表
            default: 空列表時的預設值
            
        Returns:
            float: 中位數
        """
        try:
            if not values:
                return default
            
            # 過濾掉 None 值
            valid_values = [v for v in values if v is not None]
            if not valid_values:
                return default
            
            # 排序
            sorted_values = sorted(valid_values)
            n = len(sorted_values)
            
            if n % 2 == 0:
                # 偶數個數，取中間兩個數的平均值
                median = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            else:
                # 奇數個數，取中間的數
                median = sorted_values[n//2]
            
            return self.round_decimal(median, 2)
        except Exception as e:
            self.logger.error(f"中位數計算失敗: {str(e)}")
            return default
    
    def calculate_standard_deviation(self, values: List[Union[float, int]], default: float = 0.0) -> float:
        """
        計算標準差
        
        Args:
            values: 數值列表
            default: 空列表時的預設值
            
        Returns:
            float: 標準差
        """
        try:
            if not values:
                return default
            
            # 過濾掉 None 值
            valid_values = [v for v in values if v is not None]
            if len(valid_values) < 2:
                return default
            
            # 計算平均值
            mean = sum(valid_values) / len(valid_values)
            
            # 計算方差
            variance = sum((x - mean) ** 2 for x in valid_values) / len(valid_values)
            
            # 計算標準差
            std_dev = variance ** 0.5
            
            return self.round_decimal(std_dev, 2)
        except Exception as e:
            self.logger.error(f"標準差計算失敗: {str(e)}")
            return default
    
    def calculate_trend(self, values: List[Union[float, int]], periods: int = 1) -> Dict[str, float]:
        """
        計算趨勢
        
        Args:
            values: 數值列表
            periods: 期間數
            
        Returns:
            Dict[str, float]: 趨勢數據
        """
        try:
            if len(values) < periods + 1:
                return {
                    'trend': 0.0,
                    'growth_rate': 0.0,
                    'direction': 'stable'
                }
            
            # 計算趨勢（簡單線性回歸）
            recent_values = values[-periods-1:]
            if len(recent_values) < 2:
                return {
                    'trend': 0.0,
                    'growth_rate': 0.0,
                    'direction': 'stable'
                }
            
            # 計算增長率
            current = recent_values[-1]
            previous = recent_values[-2]
            
            if previous == 0:
                growth_rate = 0.0
            else:
                growth_rate = ((current - previous) / previous) * 100
            
            # 判斷趨勢方向
            if growth_rate > 5:
                direction = 'increasing'
            elif growth_rate < -5:
                direction = 'decreasing'
            else:
                direction = 'stable'
            
            return {
                'trend': self.round_decimal(growth_rate, 2),
                'growth_rate': self.round_decimal(growth_rate, 2),
                'direction': direction
            }
        except Exception as e:
            self.logger.error(f"趨勢計算失敗: {str(e)}")
            return {
                'trend': 0.0,
                'growth_rate': 0.0,
                'direction': 'stable'
            }
    
    def format_number(self, value: Union[float, int], format_type: str = 'decimal') -> str:
        """
        格式化數字
        
        Args:
            value: 數值
            format_type: 格式化類型 (decimal, percentage, currency)
            
        Returns:
            str: 格式化後的字符串
        """
        try:
            if value is None:
                return '0'
            
            if format_type == 'decimal':
                return f"{self.round_decimal(value, 2):.2f}"
            elif format_type == 'percentage':
                return f"{self.round_decimal(value, 2):.2f}%"
            elif format_type == 'currency':
                return f"${self.round_decimal(value, 2):.2f}"
            elif format_type == 'integer':
                return f"{int(value)}"
            else:
                return str(value)
        except Exception as e:
            self.logger.error(f"數字格式化失敗: {str(e)}")
            return '0'
    
    def log_calculation(self, calculation_type: str, inputs: Dict[str, Any], result: Any) -> None:
        """
        記錄計算過程
        
        Args:
            calculation_type: 計算類型
            inputs: 輸入參數
            result: 計算結果
        """
        try:
            log_message = f"計算類型: {calculation_type}, 輸入: {inputs}, 結果: {result}"
            self.logger.debug(log_message)
        except Exception as e:
            self.logger.error(f"記錄計算過程失敗: {str(e)}") 