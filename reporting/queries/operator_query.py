"""
作業員查詢器
提供作業員報工相關數據的查詢功能
"""

from typing import List, Dict, Any
from datetime import date

from .base_query import BaseQuery


class OperatorReportQuery(BaseQuery):
    """作業員報工查詢器"""
    
    def get_operator_reports_by_date_range(self, date_range: Dict[str, date]) -> List[Any]:
        """
        根據日期範圍獲取作業員報工數據
        
        Args:
            date_range: 包含 start_date 和 end_date 的字典
        
        Returns:
            作業員報工記錄列表
        """
        try:
            # 嘗試從 workorder 模組獲取 OperatorSupplementReport
            from workorder.models import OperatorSupplementReport
            
            start_date = date_range.get('start_date')
            end_date = date_range.get('end_date')
            
            if not start_date or not end_date:
                self.logger.error("日期範圍不完整")
                return []
            
            return self.get_data_by_date_range(
                OperatorSupplementReport,
                'report_date',
                start_date,
                end_date
            )
            
        except ImportError:
            self.logger.warning("無法導入 OperatorSupplementReport 模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取作業員報工數據失敗: {str(e)}")
            return []
    
    def get_operator_reports_by_work_order(self, work_order_no: str) -> List[Any]:
        """
        根據工單號獲取作業員報工數據
        
        Args:
            work_order_no: 工單號
        
        Returns:
            作業員報工記錄列表
        """
        try:
            from workorder.models import OperatorSupplementReport
            
            return self.get_data_by_field(
                OperatorSupplementReport,
                'work_order_no',
                work_order_no
            )
            
        except ImportError:
            self.logger.warning("無法導入 OperatorSupplementReport 模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取作業員報工數據失敗: {str(e)}")
            return []
    
    def get_operator_reports_by_operator(self, operator_id: int, date_range: Dict[str, date] = None) -> List[Any]:
        """
        根據作業員ID獲取報工數據
        
        Args:
            operator_id: 作業員ID
            date_range: 可選的日期範圍
        
        Returns:
            作業員報工記錄列表
        """
        try:
            from workorder.models import OperatorSupplementReport
            
            filters = {'operator_id': operator_id}
            
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                if start_date and end_date:
                    filters.update({
                        'report_date__gte': start_date,
                        'report_date__lte': end_date
                    })
            
            return list(OperatorSupplementReport.objects.filter(**filters))
            
        except ImportError:
            self.logger.warning("無法導入 OperatorSupplementReport 模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取作業員報工數據失敗: {str(e)}")
            return []
    
    def get_operator_summary_by_date_range(self, date_range: Dict[str, date]) -> List[Dict[str, Any]]:
        """
        獲取作業員摘要統計數據
        
        Args:
            date_range: 包含 start_date 和 end_date 的字典
        
        Returns:
            作業員摘要統計列表
        """
        try:
            from workorder.models import OperatorSupplementReport
            from django.db.models import Sum, Count
            
            start_date = date_range.get('start_date')
            end_date = date_range.get('end_date')
            
            if not start_date or not end_date:
                self.logger.error("日期範圍不完整")
                return []
            
            # 按作業員分組統計
            summary_data = OperatorSupplementReport.objects.filter(
                report_date__gte=start_date,
                report_date__lte=end_date
            ).values('operator__username').annotate(
                total_work_quantity=Sum('work_quantity'),
                total_defect_quantity=Sum('defect_quantity'),
                report_count=Count('id')
            )
            
            return list(summary_data)
            
        except ImportError:
            self.logger.warning("無法導入 OperatorSupplementReport 模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取作業員摘要統計失敗: {str(e)}")
            return [] 