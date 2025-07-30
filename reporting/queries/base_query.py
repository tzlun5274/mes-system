"""
基礎查詢器類別
提供所有查詢器的基礎功能和介面
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date
from django.db import models


class BaseQuery:
    """查詢器基礎類別"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_data_by_date_range(self, model_class: models.Model, date_field: str, 
                              start_date: date, end_date: date, **filters) -> List[Any]:
        """
        根據日期範圍獲取數據的通用方法
        
        Args:
            model_class: Django 模型類別
            date_field: 日期欄位名稱
            start_date: 開始日期
            end_date: 結束日期
            **filters: 額外的過濾條件
        
        Returns:
            查詢結果列表
        """
        try:
            date_filter = {
                f"{date_field}__gte": start_date,
                f"{date_field}__lte": end_date
            }
            
            # 合併額外的過濾條件
            query_filters = {**date_filter, **filters}
            
            queryset = model_class.objects.filter(**query_filters)
            return list(queryset)
            
        except Exception as e:
            self.logger.error(f"查詢數據失敗: {str(e)}")
            return []
    
    def get_data_by_id(self, model_class: models.Model, record_id: int) -> Optional[Any]:
        """
        根據ID獲取單筆數據
        
        Args:
            model_class: Django 模型類別
            record_id: 記錄ID
        
        Returns:
            查詢結果或 None
        """
        try:
            return model_class.objects.get(id=record_id)
        except model_class.DoesNotExist:
            self.logger.warning(f"找不到ID為 {record_id} 的記錄")
            return None
        except Exception as e:
            self.logger.error(f"查詢數據失敗: {str(e)}")
            return None
    
    def get_data_by_field(self, model_class: models.Model, field_name: str, 
                         field_value: Any, **filters) -> List[Any]:
        """
        根據欄位值獲取數據
        
        Args:
            model_class: Django 模型類別
            field_name: 欄位名稱
            field_value: 欄位值
            **filters: 額外的過濾條件
        
        Returns:
            查詢結果列表
        """
        try:
            query_filters = {field_name: field_value, **filters}
            queryset = model_class.objects.filter(**query_filters)
            return list(queryset)
            
        except Exception as e:
            self.logger.error(f"查詢數據失敗: {str(e)}")
            return []
    
    def get_aggregated_data(self, model_class: models.Model, 
                          group_by_fields: List[str], 
                          aggregate_fields: Dict[str, str],
                          **filters) -> List[Dict[str, Any]]:
        """
        獲取聚合數據
        
        Args:
            model_class: Django 模型類別
            group_by_fields: 分組欄位列表
            aggregate_fields: 聚合欄位字典，格式為 {'欄位名': '聚合函數'}
            **filters: 過濾條件
        
        Returns:
            聚合結果列表
        """
        try:
            from django.db.models import Count, Sum, Avg, Max, Min
            
            # 建立聚合字典
            aggregation_dict = {}
            for field, agg_func in aggregate_fields.items():
                if agg_func.upper() == 'COUNT':
                    aggregation_dict[field] = Count(field)
                elif agg_func.upper() == 'SUM':
                    aggregation_dict[field] = Sum(field)
                elif agg_func.upper() == 'AVG':
                    aggregation_dict[field] = Avg(field)
                elif agg_func.upper() == 'MAX':
                    aggregation_dict[field] = Max(field)
                elif agg_func.upper() == 'MIN':
                    aggregation_dict[field] = Min(field)
            
            queryset = model_class.objects.filter(**filters)
            if group_by_fields:
                queryset = queryset.values(*group_by_fields).annotate(**aggregation_dict)
            else:
                queryset = queryset.aggregate(**aggregation_dict)
            
            return list(queryset) if group_by_fields else [queryset]
            
        except Exception as e:
            self.logger.error(f"聚合查詢失敗: {str(e)}")
            return [] 