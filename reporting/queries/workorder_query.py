"""
工單查詢器
提供工單相關數據的查詢功能
"""

from typing import List, Dict, Any
from datetime import date

from .base_query import BaseQuery


class WorkOrderQuery(BaseQuery):
    """工單查詢器"""
    
    def get_workorders_by_date_range(self, date_range: Dict[str, date]) -> List[Any]:
        """
        根據日期範圍獲取工單數據
        
        Args:
            date_range: 包含 start_date 和 end_date 的字典
        
        Returns:
            工單記錄列表
        """
        try:
            # 嘗試從 workorder 模組獲取 WorkOrder
            from workorder.models import WorkOrder
            
            start_date = date_range.get('start_date')
            end_date = date_range.get('end_date')
            
            if not start_date or not end_date:
                self.logger.error("日期範圍不完整")
                return []
            
            return self.get_data_by_date_range(
                WorkOrder,
                'created_at',
                start_date,
                end_date
            )
            
        except ImportError:
            self.logger.warning("無法導入 WorkOrder 模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取工單數據失敗: {str(e)}")
            return []
    
    def get_workorder_by_number(self, work_order_no: str) -> Any:
        """
        根據工單號獲取工單數據
        
        Args:
            work_order_no: 工單號
        
        Returns:
            工單記錄或 None
        """
        try:
            from workorder.models import WorkOrder
            
            return WorkOrder.objects.get(work_order_no=work_order_no)
            
        except ImportError:
            self.logger.warning("無法導入 WorkOrder 模型，返回 None")
            return None
        except WorkOrder.DoesNotExist:
            self.logger.warning(f"找不到工單號為 {work_order_no} 的記錄")
            return None
        except Exception as e:
            self.logger.error(f"獲取工單數據失敗: {str(e)}")
            return None
    
    def get_workorders_by_status(self, status: str, date_range: Dict[str, date] = None) -> List[Any]:
        """
        根據狀態獲取工單數據
        
        Args:
            status: 工單狀態
            date_range: 可選的日期範圍
        
        Returns:
            工單記錄列表
        """
        try:
            from workorder.models import WorkOrder
            
            filters = {'status': status}
            
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                if start_date and end_date:
                    filters.update({
                        'created_at__gte': start_date,
                        'created_at__lte': end_date
                    })
            
            return list(WorkOrder.objects.filter(**filters))
            
        except ImportError:
            self.logger.warning("無法導入 WorkOrder 模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取工單數據失敗: {str(e)}")
            return []
    
    def get_workorder_summary_by_date_range(self, date_range: Dict[str, date]) -> List[Dict[str, Any]]:
        """
        獲取工單摘要統計數據
        
        Args:
            date_range: 包含 start_date 和 end_date 的字典
        
        Returns:
            工單摘要統計列表
        """
        try:
            from workorder.models import WorkOrder
            from django.db.models import Sum, Count, Avg
            
            start_date = date_range.get('start_date')
            end_date = date_range.get('end_date')
            
            if not start_date or not end_date:
                self.logger.error("日期範圍不完整")
                return []
            
            # 按狀態分組統計
            summary_data = WorkOrder.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).values('status').annotate(
                count=Count('id'),
                total_quantity=Sum('total_quantity'),
                completed_quantity=Sum('completed_quantity'),
                defect_quantity=Sum('defect_quantity')
            )
            
            return list(summary_data)
            
        except ImportError:
            self.logger.warning("無法導入 WorkOrder 模型，返回空列表")
            return []
        except Exception as e:
            self.logger.error(f"獲取工單摘要統計失敗: {str(e)}")
            return []
    
    def get_workorder_progress_data(self, work_order_no: str) -> Dict[str, Any]:
        """
        獲取工單進度數據
        
        Args:
            work_order_no: 工單號
        
        Returns:
            工單進度數據字典
        """
        try:
            from workorder.models import WorkOrder, OperatorSupplementReport
            from django.db.models import Sum
            
            # 獲取工單基本資訊
            workorder = self.get_workorder_by_number(work_order_no)
            if not workorder:
                return {}
            
            # 獲取報工統計
            report_stats = OperatorSupplementReport.objects.filter(
                work_order_no=work_order_no
            ).aggregate(
                total_work_quantity=Sum('work_quantity'),
                total_defect_quantity=Sum('defect_quantity'),
                report_count=Sum('id')
            )
            
            # 計算進度
            total_quantity = getattr(workorder, 'total_quantity', 0)
            completed_quantity = report_stats.get('total_work_quantity', 0) or 0
            defect_quantity = report_stats.get('total_defect_quantity', 0) or 0
            
            completion_rate = 0
            if total_quantity > 0:
                completion_rate = round((completed_quantity / total_quantity) * 100, 2)
            
            return {
                'work_order_no': work_order_no,
                'total_quantity': total_quantity,
                'completed_quantity': completed_quantity,
                'defect_quantity': defect_quantity,
                'completion_rate': completion_rate,
                'status': getattr(workorder, 'status', ''),
                'report_count': report_stats.get('report_count', 0) or 0
            }
            
        except ImportError:
            self.logger.warning("無法導入相關模型，返回空字典")
            return {}
        except Exception as e:
            self.logger.error(f"獲取工單進度數據失敗: {str(e)}")
            return {} 