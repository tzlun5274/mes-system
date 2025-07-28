# 基礎轉換器
# 本檔案定義了報表系統的基礎轉換器類別
# 提供統一的數據轉換介面和格式化功能

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import logging
import json

# 設定日誌記錄器
logger = logging.getLogger(__name__)


class BaseTransformer(ABC):
    """報表轉換器基礎類別 - 所有轉換器的基礎類別"""
    
    def __init__(self):
        """初始化轉換器"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def transform(self, data: Any) -> Any:
        """
        轉換數據（抽象方法）
        
        Args:
            data: 要轉換的數據
            
        Returns:
            Any: 轉換後的數據
        """
        raise NotImplementedError
    
    def format_number(self, value: Union[int, float, Decimal, str], 
                     decimal_places: int = 2, 
                     use_thousands_separator: bool = True) -> str:
        """
        格式化數字
        
        Args:
            value: 數值
            decimal_places: 小數位數
            use_thousands_separator: 是否使用千分位分隔符
            
        Returns:
            str: 格式化後的數字字串
        """
        try:
            if value is None:
                return ""
            
            # 轉換為Decimal以確保精度
            if isinstance(value, str):
                value = Decimal(value)
            elif isinstance(value, (int, float)):
                value = Decimal(str(value))
            
            # 四捨五入到指定小數位數
            value = value.quantize(Decimal('0.' + '0' * decimal_places), rounding=ROUND_HALF_UP)
            
            # 格式化字串
            if decimal_places == 0:
                formatted = f"{int(value)}"
            else:
                formatted = f"{value:.{decimal_places}f}"
            
            # 添加千分位分隔符
            if use_thousands_separator:
                parts = formatted.split('.')
                parts[0] = "{:,}".format(int(parts[0]))
                formatted = '.'.join(parts)
            
            return formatted
            
        except Exception as e:
            self.logger.error(f"數字格式化失敗: {e}")
            return str(value) if value is not None else ""
    
    def format_percentage(self, value: Union[int, float, Decimal, str], 
                         decimal_places: int = 2) -> str:
        """
        格式化百分比
        
        Args:
            value: 數值（0-1或0-100）
            decimal_places: 小數位數
            
        Returns:
            str: 格式化後的百分比字串
        """
        try:
            if value is None:
                return ""
            
            # 轉換為float
            if isinstance(value, str):
                value = float(value)
            elif isinstance(value, Decimal):
                value = float(value)
            
            # 如果值大於1，假設是百分比形式（0-100）
            if value > 1:
                value = value / 100
            
            # 格式化為百分比
            formatted = f"{value * 100:.{decimal_places}f}%"
            return formatted
            
        except Exception as e:
            self.logger.error(f"百分比格式化失敗: {e}")
            return str(value) if value is not None else ""
    
    def format_date(self, value: Union[date, datetime, str], 
                   format_str: str = '%Y-%m-%d') -> str:
        """
        格式化日期
        
        Args:
            value: 日期值
            format_str: 日期格式
            
        Returns:
            str: 格式化後的日期字串
        """
        try:
            if value is None:
                return ""
            
            # 處理字串日期
            if isinstance(value, str):
                # 嘗試解析常見的日期格式
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
                    try:
                        value = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    self.logger.warning(f"無法解析日期格式: {value}")
                    return value
            
            # 格式化日期
            if isinstance(value, datetime):
                return value.strftime(format_str)
            elif isinstance(value, date):
                return value.strftime(format_str)
            else:
                return str(value)
                
        except Exception as e:
            self.logger.error(f"日期格式化失敗: {e}")
            return str(value) if value is not None else ""
    
    def format_time(self, value: Union[datetime, str], 
                   format_str: str = '%H:%M:%S') -> str:
        """
        格式化時間
        
        Args:
            value: 時間值
            format_str: 時間格式
            
        Returns:
            str: 格式化後的時間字串
        """
        try:
            if value is None:
                return ""
            
            # 處理字串時間
            if isinstance(value, str):
                # 嘗試解析常見的時間格式
                for fmt in ['%H:%M:%S', '%H:%M', '%Y-%m-%d %H:%M:%S']:
                    try:
                        value = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    self.logger.warning(f"無法解析時間格式: {value}")
                    return value
            
            # 格式化時間
            if isinstance(value, datetime):
                return value.strftime(format_str)
            else:
                return str(value)
                
        except Exception as e:
            self.logger.error(f"時間格式化失敗: {e}")
            return str(value) if value is not None else ""
    
    def format_duration(self, seconds: Union[int, float, str]) -> str:
        """
        格式化持續時間
        
        Args:
            seconds: 秒數
            
        Returns:
            str: 格式化後的持續時間字串
        """
        try:
            if seconds is None:
                return ""
            
            seconds = float(seconds)
            if seconds < 0:
                return "0秒"
            
            # 轉換為小時、分鐘、秒
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            remaining_seconds = int(seconds % 60)
            
            # 格式化輸出
            if hours > 0:
                return f"{hours}小時{minutes}分鐘{remaining_seconds}秒"
            elif minutes > 0:
                return f"{minutes}分鐘{remaining_seconds}秒"
            else:
                return f"{remaining_seconds}秒"
                
        except Exception as e:
            self.logger.error(f"持續時間格式化失敗: {e}")
            return str(seconds) if seconds is not None else ""
    
    def format_currency(self, value: Union[int, float, Decimal, str], 
                       currency_symbol: str = "NT$") -> str:
        """
        格式化貨幣
        
        Args:
            value: 數值
            currency_symbol: 貨幣符號
            
        Returns:
            str: 格式化後的貨幣字串
        """
        try:
            if value is None:
                return ""
            
            formatted_number = self.format_number(value, 2, True)
            return f"{currency_symbol}{formatted_number}"
            
        except Exception as e:
            self.logger.error(f"貨幣格式化失敗: {e}")
            return str(value) if value is not None else ""
    
    def format_file_size(self, bytes_value: Union[int, float, str]) -> str:
        """
        格式化檔案大小
        
        Args:
            bytes_value: 位元組數
            
        Returns:
            str: 格式化後的檔案大小字串
        """
        try:
            if bytes_value is None:
                return ""
            
            bytes_value = float(bytes_value)
            if bytes_value < 0:
                return "0 B"
            
            # 轉換單位
            units = ['B', 'KB', 'MB', 'GB', 'TB']
            unit_index = 0
            
            while bytes_value >= 1024 and unit_index < len(units) - 1:
                bytes_value /= 1024
                unit_index += 1
            
            # 格式化輸出
            if unit_index == 0:
                return f"{int(bytes_value)} {units[unit_index]}"
            else:
                return f"{bytes_value:.2f} {units[unit_index]}"
                
        except Exception as e:
            self.logger.error(f"檔案大小格式化失敗: {e}")
            return str(bytes_value) if bytes_value is not None else ""
    
    def truncate_text(self, text: str, max_length: int = 50, 
                     suffix: str = "...") -> str:
        """
        截斷文字
        
        Args:
            text: 原始文字
            max_length: 最大長度
            suffix: 截斷後綴
            
        Returns:
            str: 截斷後的文字
        """
        try:
            if text is None:
                return ""
            
            if len(text) <= max_length:
                return text
            
            return text[:max_length - len(suffix)] + suffix
            
        except Exception as e:
            self.logger.error(f"文字截斷失敗: {e}")
            return str(text) if text is not None else ""
    
    def convert_to_dict(self, obj: Any) -> Dict[str, Any]:
        """
        將物件轉換為字典
        
        Args:
            obj: 要轉換的物件
            
        Returns:
            Dict[str, Any]: 轉換後的字典
        """
        try:
            if obj is None:
                return {}
            
            if isinstance(obj, dict):
                return obj
            
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            
            # 嘗試JSON序列化
            try:
                return json.loads(json.dumps(obj, default=str))
            except:
                pass
            
            return {'value': str(obj)}
            
        except Exception as e:
            self.logger.error(f"物件轉字典失敗: {e}")
            return {'error': str(e)}
    
    def convert_to_list(self, obj: Any) -> List[Any]:
        """
        將物件轉換為列表
        
        Args:
            obj: 要轉換的物件
            
        Returns:
            List[Any]: 轉換後的列表
        """
        try:
            if obj is None:
                return []
            
            if isinstance(obj, list):
                return obj
            
            if isinstance(obj, tuple):
                return list(obj)
            
            if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
                return list(obj)
            
            return [obj]
            
        except Exception as e:
            self.logger.error(f"物件轉列表失敗: {e}")
            return []
    
    def flatten_dict(self, data: Dict[str, Any], 
                    separator: str = '.', 
                    prefix: str = '') -> Dict[str, Any]:
        """
        扁平化字典
        
        Args:
            data: 原始字典
            separator: 鍵分隔符
            prefix: 鍵前綴
            
        Returns:
            Dict[str, Any]: 扁平化後的字典
        """
        try:
            result = {}
            
            for key, value in data.items():
                new_key = f"{prefix}{separator}{key}" if prefix else key
                
                if isinstance(value, dict):
                    result.update(self.flatten_dict(value, separator, new_key))
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            result.update(self.flatten_dict(item, separator, f"{new_key}[{i}]"))
                        else:
                            result[f"{new_key}[{i}]"] = item
                else:
                    result[new_key] = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"字典扁平化失敗: {e}")
            return data
    
    def group_by_field(self, data: List[Dict[str, Any]], 
                      field: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        按欄位分組
        
        Args:
            data: 數據列表
            field: 分組欄位
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: 分組後的數據
        """
        try:
            result = {}
            
            for item in data:
                if not isinstance(item, dict):
                    continue
                
                key = item.get(field, 'unknown')
                if key not in result:
                    result[key] = []
                
                result[key].append(item)
            
            return result
            
        except Exception as e:
            self.logger.error(f"數據分組失敗: {e}")
            return {}
    
    def sort_by_field(self, data: List[Dict[str, Any]], 
                     field: str, 
                     reverse: bool = False) -> List[Dict[str, Any]]:
        """
        按欄位排序
        
        Args:
            data: 數據列表
            field: 排序欄位
            reverse: 是否反向排序
            
        Returns:
            List[Dict[str, Any]]: 排序後的數據
        """
        try:
            if not data:
                return data
            
            return sorted(data, key=lambda x: x.get(field, ''), reverse=reverse)
            
        except Exception as e:
            self.logger.error(f"數據排序失敗: {e}")
            return data
    
    def filter_by_condition(self, data: List[Dict[str, Any]], 
                          condition: callable) -> List[Dict[str, Any]]:
        """
        按條件篩選
        
        Args:
            data: 數據列表
            condition: 篩選條件函數
            
        Returns:
            List[Dict[str, Any]]: 篩選後的數據
        """
        try:
            return [item for item in data if condition(item)]
            
        except Exception as e:
            self.logger.error(f"數據篩選失敗: {e}")
            return data
    
    def aggregate_data(self, data: List[Dict[str, Any]], 
                      group_by: str, 
                      aggregate_fields: List[str],
                      aggregate_func: str = 'sum') -> List[Dict[str, Any]]:
        """
        聚合數據
        
        Args:
            data: 數據列表
            group_by: 分組欄位
            aggregate_fields: 聚合欄位列表
            aggregate_func: 聚合函數（sum/avg/count/min/max）
            
        Returns:
            List[Dict[str, Any]]: 聚合後的數據
        """
        try:
            grouped_data = self.group_by_field(data, group_by)
            result = []
            
            for group_key, group_items in grouped_data.items():
                aggregated_item = {group_by: group_key}
                
                for field in aggregate_fields:
                    values = [item.get(field, 0) for item in group_items 
                             if isinstance(item.get(field), (int, float))]
                    
                    if aggregate_func == 'sum':
                        aggregated_item[f"{field}_sum"] = sum(values)
                    elif aggregate_func == 'avg':
                        aggregated_item[f"{field}_avg"] = sum(values) / len(values) if values else 0
                    elif aggregate_func == 'count':
                        aggregated_item[f"{field}_count"] = len(values)
                    elif aggregate_func == 'min':
                        aggregated_item[f"{field}_min"] = min(values) if values else 0
                    elif aggregate_func == 'max':
                        aggregated_item[f"{field}_max"] = max(values) if values else 0
                
                result.append(aggregated_item)
            
            return result
            
        except Exception as e:
            self.logger.error(f"數據聚合失敗: {e}")
            return data
    
    def calculate_statistics(self, data: List[Dict[str, Any]], 
                           field: str) -> Dict[str, Any]:
        """
        計算統計資訊
        
        Args:
            data: 數據列表
            field: 統計欄位
            
        Returns:
            Dict[str, Any]: 統計資訊
        """
        try:
            values = [item.get(field, 0) for item in data 
                     if isinstance(item.get(field), (int, float))]
            
            if not values:
                return {
                    'count': 0,
                    'sum': 0,
                    'avg': 0,
                    'min': 0,
                    'max': 0,
                    'std': 0
                }
            
            count = len(values)
            total = sum(values)
            avg = total / count
            min_val = min(values)
            max_val = max(values)
            
            # 計算標準差
            variance = sum((x - avg) ** 2 for x in values) / count
            std = variance ** 0.5
            
            return {
                'count': count,
                'sum': total,
                'avg': avg,
                'min': min_val,
                'max': max_val,
                'std': std
            }
            
        except Exception as e:
            self.logger.error(f"統計計算失敗: {e}")
            return {} 