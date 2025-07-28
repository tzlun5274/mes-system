# 基礎查詢器
# 本檔案定義了報表系統的基礎查詢器類別
# 提供統一的數據查詢介面和錯誤處理機制

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import date, datetime, timedelta
from django.db import models
from django.core.cache import cache
import logging

# 設定日誌記錄器
logger = logging.getLogger(__name__)


class BaseQuery(ABC):
    """報表查詢器基礎類別 - 所有查詢器的基礎類別"""
    
    def __init__(self):
        """初始化查詢器"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache_prefix = 'query_'
        self.cache_timeout = 30 * 60  # 30分鐘快取
        
    @abstractmethod
    def get_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        取得查詢數據（抽象方法）
        
        Args:
            **kwargs: 查詢參數
            
        Returns:
            List[Dict[str, Any]]: 查詢結果列表
        """
        raise NotImplementedError
    
    def get_cached_data(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """
        從快取中取得數據
        
        Args:
            cache_key: 快取鍵值
            
        Returns:
            Optional[List[Dict[str, Any]]]: 快取數據或None
        """
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                self.logger.info(f"使用快取數據: {cache_key}")
            return cached_data
        except Exception as e:
            self.logger.error(f"取得快取數據失敗: {e}")
            return None
    
    def set_cached_data(self, cache_key: str, data: List[Dict[str, Any]]) -> None:
        """
        將數據儲存到快取
        
        Args:
            cache_key: 快取鍵值
            data: 要快取的數據
        """
        try:
            cache.set(cache_key, data, self.cache_timeout)
            self.logger.info(f"數據已快取: {cache_key}")
        except Exception as e:
            self.logger.error(f"儲存快取數據失敗: {e}")
    
    def generate_cache_key(self, **kwargs) -> str:
        """
        生成快取鍵值
        
        Args:
            **kwargs: 查詢參數
            
        Returns:
            str: 快取鍵值
        """
        key_parts = [self.cache_prefix, self.__class__.__name__]
        
        # 將參數轉換為字串並加入鍵值
        for key, value in sorted(kwargs.items()):
            if isinstance(value, (date, datetime)):
                key_parts.append(f"{key}_{value.strftime('%Y%m%d')}")
            else:
                key_parts.append(f"{key}_{str(value)}")
        
        return "_".join(key_parts)
    
    def validate_date_range(self, start_date: date, end_date: date) -> bool:
        """
        驗證日期範圍
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            bool: 日期範圍是否有效
        """
        if start_date > end_date:
            self.logger.error(f"開始日期 {start_date} 不能晚於結束日期 {end_date}")
            return False
        
        # 檢查日期範圍是否超過一年
        if (end_date - start_date).days > 365:
            self.logger.warning(f"日期範圍超過一年: {start_date} 到 {end_date}")
        
        return True
    
    def filter_by_date_range(self, queryset: models.QuerySet, 
                           start_date: date, end_date: date,
                           date_field: str = 'created_at') -> models.QuerySet:
        """
        按日期範圍篩選查詢集
        
        Args:
            queryset: Django查詢集
            start_date: 開始日期
            end_date: 結束日期
            date_field: 日期欄位名稱
            
        Returns:
            models.QuerySet: 篩選後的查詢集
        """
        try:
            # 根據日期欄位類型進行篩選
            if hasattr(queryset.model._meta.get_field(date_field), 'date'):
                # 如果是DateTimeField，需要轉換為日期
                return queryset.filter(
                    **{f"{date_field}__date__gte": start_date,
                       f"{date_field}__date__lte": end_date}
                )
            else:
                # 如果是DateField，直接篩選
                return queryset.filter(
                    **{f"{date_field}__gte": start_date,
                       f"{date_field}__lte": end_date}
                )
        except Exception as e:
            self.logger.error(f"日期範圍篩選失敗: {e}")
            return queryset
    
    def paginate_results(self, data: List[Dict[str, Any]], 
                        page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        分頁處理結果
        
        Args:
            data: 原始數據列表
            page: 頁碼（從1開始）
            page_size: 每頁大小
            
        Returns:
            Dict[str, Any]: 包含分頁資訊的結果
        """
        try:
            total_count = len(data)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            paginated_data = data[start_index:end_index]
            
            return {
                'data': paginated_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': (total_count + page_size - 1) // page_size,
                    'has_next': end_index < total_count,
                    'has_previous': page > 1
                }
            }
        except Exception as e:
            self.logger.error(f"分頁處理失敗: {e}")
            return {
                'data': data,
                'pagination': {
                    'page': 1,
                    'page_size': len(data),
                    'total_count': len(data),
                    'total_pages': 1,
                    'has_next': False,
                    'has_previous': False
                }
            }
    
    def sort_results(self, data: List[Dict[str, Any]], 
                    sort_by: str = None, sort_order: str = 'asc') -> List[Dict[str, Any]]:
        """
        排序結果
        
        Args:
            data: 原始數據列表
            sort_by: 排序欄位
            sort_order: 排序順序（asc/desc）
            
        Returns:
            List[Dict[str, Any]]: 排序後的數據列表
        """
        try:
            if not sort_by or not data:
                return data
            
            # 檢查排序欄位是否存在
            if sort_by not in data[0]:
                self.logger.warning(f"排序欄位 {sort_by} 不存在")
                return data
            
            # 執行排序
            reverse = sort_order.lower() == 'desc'
            sorted_data = sorted(data, key=lambda x: x.get(sort_by, ''), reverse=reverse)
            
            self.logger.info(f"數據已按 {sort_by} {sort_order} 排序")
            return sorted_data
            
        except Exception as e:
            self.logger.error(f"排序處理失敗: {e}")
            return data
    
    def aggregate_results(self, data: List[Dict[str, Any]], 
                         group_by: str = None, 
                         aggregate_fields: List[str] = None) -> Dict[str, Any]:
        """
        聚合結果
        
        Args:
            data: 原始數據列表
            group_by: 分組欄位
            aggregate_fields: 聚合欄位列表
            
        Returns:
            Dict[str, Any]: 聚合後的結果
        """
        try:
            if not data:
                return {}
            
            if not group_by:
                # 不分組，直接計算總計
                result = {}
                if aggregate_fields:
                    for field in aggregate_fields:
                        if field in data[0]:
                            # 計算數值欄位的總和
                            total = sum(item.get(field, 0) for item in data 
                                      if isinstance(item.get(field), (int, float)))
                            result[f"{field}_total"] = total
                            result[f"{field}_count"] = len(data)
                            result[f"{field}_average"] = total / len(data) if len(data) > 0 else 0
                return result
            
            # 按欄位分組
            grouped_data = {}
            for item in data:
                group_key = item.get(group_by, 'unknown')
                if group_key not in grouped_data:
                    grouped_data[group_key] = []
                grouped_data[group_key].append(item)
            
            # 計算每組的聚合值
            result = {}
            for group_key, group_items in grouped_data.items():
                group_result = {}
                if aggregate_fields:
                    for field in aggregate_fields:
                        if field in group_items[0]:
                            total = sum(item.get(field, 0) for item in group_items 
                                      if isinstance(item.get(field), (int, float)))
                            group_result[f"{field}_total"] = total
                            group_result[f"{field}_count"] = len(group_items)
                            group_result[f"{field}_average"] = total / len(group_items) if len(group_items) > 0 else 0
                result[group_key] = group_result
            
            return result
            
        except Exception as e:
            self.logger.error(f"聚合處理失敗: {e}")
            return {}
    
    def export_to_format(self, data: List[Dict[str, Any]], 
                        format_type: str = 'json') -> Union[str, bytes]:
        """
        匯出數據到指定格式
        
        Args:
            data: 原始數據列表
            format_type: 匯出格式（json/csv/excel）
            
        Returns:
            Union[str, bytes]: 匯出的數據
        """
        try:
            if format_type.lower() == 'json':
                import json
                return json.dumps(data, ensure_ascii=False, indent=2, default=str)
            
            elif format_type.lower() == 'csv':
                import csv
                import io
                
                if not data:
                    return ""
                
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                
                return output.getvalue()
            
            elif format_type.lower() == 'excel':
                # 這裡可以實作Excel匯出邏輯
                self.logger.warning("Excel匯出功能尚未實作")
                return ""
            
            else:
                self.logger.error(f"不支援的匯出格式: {format_type}")
                return ""
                
        except Exception as e:
            self.logger.error(f"數據匯出失敗: {e}")
            return ""
    
    def log_query_execution(self, query_params: Dict[str, Any], 
                           result_count: int, execution_time: float) -> None:
        """
        記錄查詢執行日誌
        
        Args:
            query_params: 查詢參數
            result_count: 結果數量
            execution_time: 執行時間（秒）
        """
        self.logger.info(
            f"查詢執行完成 - 類別: {self.__class__.__name__}, "
            f"參數: {query_params}, 結果數量: {result_count}, "
            f"執行時間: {execution_time:.2f}秒"
        ) 