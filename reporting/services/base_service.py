# 報表服務基礎類別
# 本檔案定義了所有報表服務的基礎類別和共用方法

import logging
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional


class BaseReportService:
    """報表服務基礎類別 - 所有報表服務的基礎類別"""
    
    def __init__(self):
        """初始化服務"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache_prefix = 'report_'
        self.cache_timeout = 24 * 60 * 60  # 24小時
    
    def generate_report(self, report_type: str, date_range: Dict[str, date], **kwargs) -> Dict[str, Any]:
        """
        生成報表（抽象方法）
        
        Args:
            report_type: 報表類型 (daily, weekly, monthly, custom)
            date_range: 日期範圍 {'start': date, 'end': date}
            **kwargs: 其他參數
            
        Returns:
            Dict[str, Any]: 報表數據
        """
        raise NotImplementedError("子類別必須實作此方法")
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        驗證數據
        
        Args:
            data: 要驗證的數據
            
        Returns:
            bool: 驗證結果
        """
        try:
            # 基本驗證邏輯
            required_fields = ['report_type', 'report_date']
            for field in required_fields:
                if field not in data:
                    self.logger.error(f"缺少必要欄位: {field}")
                    return False
            
            # 日期驗證
            if 'report_date' in data:
                if not isinstance(data['report_date'], date):
                    self.logger.error("report_date 必須是 date 類型")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"數據驗證失敗: {str(e)}")
            return False
    
    def calculate_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        計算統計數據
        
        Args:
            data: 原始數據列表
            
        Returns:
            Dict[str, Any]: 統計結果
        """
        try:
            if not data:
                return {}
            
            # 基本統計
            total_count = len(data)
            
            # 數值欄位統計
            numeric_fields = ['completed_quantity', 'work_hours', 'efficiency_rate']
            statistics = {
                'total_count': total_count,
                'sums': {},
                'averages': {},
                'min_values': {},
                'max_values': {}
            }
            
            for field in numeric_fields:
                values = [item.get(field, 0) for item in data if item.get(field) is not None]
                if values:
                    statistics['sums'][field] = sum(values)
                    statistics['averages'][field] = sum(values) / len(values)
                    statistics['min_values'][field] = min(values)
                    statistics['max_values'][field] = max(values)
            
            return statistics
        except Exception as e:
            self.logger.error(f"統計計算失敗: {str(e)}")
            return {}
    
    def format_output(self, data: Dict[str, Any], format_type: str = 'dict') -> Any:
        """
        格式化輸出
        
        Args:
            data: 原始數據
            format_type: 輸出格式 (dict, list, json)
            
        Returns:
            Any: 格式化後的數據
        """
        try:
            if format_type == 'dict':
                return data
            elif format_type == 'list':
                if isinstance(data, dict):
                    return [data]
                elif isinstance(data, list):
                    return data
                else:
                    return [data]
            elif format_type == 'json':
                import json
                return json.dumps(data, ensure_ascii=False, default=str)
            else:
                return data
        except Exception as e:
            self.logger.error(f"格式化輸出失敗: {str(e)}")
            return data
    
    def log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """
        記錄操作日誌
        
        Args:
            operation: 操作名稱
            details: 操作詳情
        """
        try:
            log_message = f"操作: {operation}, 詳情: {details}"
            self.logger.info(log_message)
            
            # 可以選擇將日誌儲存到資料庫
            from reporting.models import ReportingOperationLog
            ReportingOperationLog.objects.create(
                user=details.get('user', 'system'),
                action=log_message
            )
        except Exception as e:
            self.logger.error(f"記錄操作日誌失敗: {str(e)}")
    
    def get_cache_key(self, report_type: str, date: date, **kwargs) -> str:
        """
        生成快取鍵值
        
        Args:
            report_type: 報表類型
            date: 報表日期
            **kwargs: 其他參數
            
        Returns:
            str: 快取鍵值
        """
        key_parts = [self.cache_prefix, report_type, str(date)]
        for k, v in sorted(kwargs.items()):
            key_parts.extend([k, str(v)])
        return '_'.join(key_parts)
    
    def get_cached_report(self, report_type: str, date: date, **kwargs) -> Optional[Dict[str, Any]]:
        """
        取得快取的報表
        
        Args:
            report_type: 報表類型
            date: 報表日期
            **kwargs: 其他參數
            
        Returns:
            Optional[Dict[str, Any]]: 快取的報表數據
        """
        try:
            cache_key = self.get_cache_key(report_type, date, **kwargs)
            return cache.get(cache_key)
        except Exception as e:
            self.logger.error(f"取得快取報表失敗: {str(e)}")
            return None
    
    def set_cached_report(self, report_type: str, date: date, data: Dict[str, Any], **kwargs) -> None:
        """
        設定報表快取
        
        Args:
            report_type: 報表類型
            date: 報表日期
            data: 報表數據
            **kwargs: 其他參數
        """
        try:
            cache_key = self.get_cache_key(report_type, date, **kwargs)
            cache.set(cache_key, data, self.cache_timeout)
            self.logger.info(f"報表已快取: {cache_key}")
        except Exception as e:
            self.logger.error(f"設定報表快取失敗: {str(e)}")
    
    def clear_cache(self, pattern: Optional[str] = None) -> None:
        """
        清理快取
        
        Args:
            pattern: 快取模式，如果為 None 則清理所有報表快取
        """
        try:
            if pattern:
                # 清理特定模式的快取
                # 這裡可以實作更精細的快取清理邏輯
                pass
            else:
                # 清理所有報表快取
                cache.clear()
            self.logger.info("報表快取已清理")
        except Exception as e:
            self.logger.error(f"清理快取失敗: {str(e)}")
    
    def get_date_range(self, report_type: str, base_date: Optional[date] = None) -> Dict[str, date]:
        """
        取得報表日期範圍
        
        Args:
            report_type: 報表類型
            base_date: 基準日期，如果為 None 則使用今天
            
        Returns:
            Dict[str, date]: 日期範圍 {'start': date, 'end': date}
        """
        if base_date is None:
            base_date = timezone.now().date()
        
        if report_type == 'daily':
            return {
                'start': base_date,
                'end': base_date
            }
        elif report_type == 'weekly':
            # 取得該週的開始和結束日期
            start_of_week = base_date - timedelta(days=base_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            return {
                'start': start_of_week,
                'end': end_of_week
            }
        elif report_type == 'monthly':
            # 取得該月的開始和結束日期
            start_of_month = base_date.replace(day=1)
            if base_date.month == 12:
                end_of_month = base_date.replace(year=base_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = base_date.replace(month=base_date.month + 1, day=1) - timedelta(days=1)
            return {
                'start': start_of_month,
                'end': end_of_month
            }
        else:
            # 自訂期間，預設為今天
            return {
                'start': base_date,
                'end': base_date
            }
    
    def validate_date_range(self, date_range: Dict[str, date]) -> bool:
        """
        驗證日期範圍
        
        Args:
            date_range: 日期範圍
            
        Returns:
            bool: 驗證結果
        """
        try:
            if 'start' not in date_range or 'end' not in date_range:
                return False
            
            start_date = date_range['start']
            end_date = date_range['end']
            
            if not isinstance(start_date, date) or not isinstance(end_date, date):
                return False
            
            if start_date > end_date:
                return False
            
            # 檢查日期範圍是否合理（不超過一年）
            if (end_date - start_date).days > 365:
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"日期範圍驗證失敗: {str(e)}")
            return False 