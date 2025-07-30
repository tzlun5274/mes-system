"""
工單報表服務類別
提供工單報表的數據生成和處理功能
"""

from typing import Dict, List, Any
from datetime import date
from collections import defaultdict

from .base_report_service import BaseReportService
from ..queries.workorder_query import WorkOrderQuery


class WorkOrderReportService(BaseReportService):
    """工單報表服務"""
    
    def __init__(self):
        super().__init__()
        self.query_handler = WorkOrderQuery()

    def generate_report(self, date_range: Dict[str, date], **kwargs) -> List[Dict[str, Any]]:
        """
        生成工單報表數據。
        包含工單進度、完成情況、效率分析等資訊。
        """
        self.logger.info(f"生成工單報表，日期範圍: {date_range}")
        
        # 獲取工單數據
        workorders = self.query_handler.get_workorders_by_date_range(date_range)
        
        # 格式化報表數據
        return self._format_workorder_report_data(workorders)

    def _format_workorder_report_data(self, workorders: List[Any]) -> List[Dict[str, Any]]:
        """
        格式化工單報表數據
        欄位：工單號、產品編號、產品名稱、總數量、完成數量、不良品數量、開始日期、結束日期、狀態等
        """
        workorder_report_data = []
        
        for workorder in workorders:
            # 計算進度百分比
            completion_rate = 0
            if hasattr(workorder, 'total_quantity') and workorder.total_quantity > 0:
                completed_qty = getattr(workorder, 'completed_quantity', 0)
                completion_rate = round((completed_qty / workorder.total_quantity) * 100, 2)
            
            # 計算實際工期
            actual_duration = None
            if hasattr(workorder, 'start_date') and hasattr(workorder, 'end_date'):
                if workorder.start_date and workorder.end_date:
                    actual_duration = (workorder.end_date - workorder.start_date).days
            
            workorder_report_data.append({
                'work_order_no': workorder.work_order_no if hasattr(workorder, 'work_order_no') else '',
                'product_sn': workorder.product_sn if hasattr(workorder, 'product_sn') else '',
                'product_name': workorder.product_name if hasattr(workorder, 'product_name') else '',
                'total_quantity': workorder.total_quantity if hasattr(workorder, 'total_quantity') else 0,
                'completed_quantity': workorder.completed_quantity if hasattr(workorder, 'completed_quantity') else 0,
                'defect_quantity': workorder.defect_quantity if hasattr(workorder, 'defect_quantity') else 0,
                'completion_rate': completion_rate,
                'start_date': workorder.start_date.strftime('%Y-%m-%d') if hasattr(workorder, 'start_date') and workorder.start_date else '',
                'end_date': workorder.end_date.strftime('%Y-%m-%d') if hasattr(workorder, 'end_date') and workorder.end_date else '',
                'planned_duration': workorder.planned_duration if hasattr(workorder, 'planned_duration') else None,
                'actual_duration': actual_duration,
                'status': workorder.status if hasattr(workorder, 'status') else '',
                'efficiency_rate': self._calculate_workorder_efficiency(workorder),
            })
        
        return workorder_report_data

    def generate_summary_report(self, date_range: Dict[str, date], **kwargs) -> Dict[str, Any]:
        """
        生成工單報表摘要統計
        """
        workorder_data = self.generate_report(date_range, **kwargs)
        
        # 按狀態分組統計
        status_summary = defaultdict(lambda: {
            'count': 0,
            'total_quantity': 0,
            'completed_quantity': 0,
            'defect_quantity': 0
        })
        
        # 總體統計
        total_stats = {
            'total_workorders': len(workorder_data),
            'total_quantity': 0,
            'total_completed': 0,
            'total_defect': 0,
            'avg_completion_rate': 0,
            'avg_efficiency_rate': 0
        }
        
        completion_rates = []
        efficiency_rates = []
        
        for record in workorder_data:
            status = record['status']
            status_summary[status]['count'] += 1
            status_summary[status]['total_quantity'] += record['total_quantity']
            status_summary[status]['completed_quantity'] += record['completed_quantity']
            status_summary[status]['defect_quantity'] += record['defect_quantity']
            
            total_stats['total_quantity'] += record['total_quantity']
            total_stats['total_completed'] += record['completed_quantity']
            total_stats['total_defect'] += record['defect_quantity']
            
            completion_rates.append(record['completion_rate'])
            if record['efficiency_rate'] is not None:
                efficiency_rates.append(record['efficiency_rate'])
        
        # 計算平均值
        if completion_rates:
            total_stats['avg_completion_rate'] = round(sum(completion_rates) / len(completion_rates), 2)
        if efficiency_rates:
            total_stats['avg_efficiency_rate'] = round(sum(efficiency_rates) / len(efficiency_rates), 2)
        
        # 格式化狀態摘要
        status_data = []
        for status, data in status_summary.items():
            status_data.append({
                'status': status,
                'count': data['count'],
                'total_quantity': data['total_quantity'],
                'completed_quantity': data['completed_quantity'],
                'defect_quantity': data['defect_quantity'],
                'completion_rate': self._calculate_completion_rate(data['completed_quantity'], data['total_quantity'])
            })
        
        return {
            'total_stats': total_stats,
            'status_summary': status_data,
            'date_range': date_range
        }

    def _calculate_workorder_efficiency(self, workorder: Any) -> float:
        """計算工單效率率"""
        try:
            if hasattr(workorder, 'total_quantity') and workorder.total_quantity > 0:
                completed_qty = getattr(workorder, 'completed_quantity', 0)
                defect_qty = getattr(workorder, 'defect_quantity', 0)
                total_produced = completed_qty + defect_qty
                
                if total_produced > 0:
                    return round((completed_qty / total_produced) * 100, 2)
        except Exception as e:
            self.logger.error(f"計算工單效率率失敗: {str(e)}")
        
        return 0.0

    def _calculate_completion_rate(self, completed: int, total: int) -> float:
        """計算完成率"""
        if total == 0:
            return 0.0
        return round((completed / total) * 100, 2) 