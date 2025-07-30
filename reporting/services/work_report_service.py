"""
工作報表服務類別
提供工作報表的數據生成和處理功能
"""

from typing import Dict, List, Any
from datetime import date
from collections import defaultdict

from .base_report_service import BaseReportService
from ..queries.operator_query import OperatorReportQuery
from ..calculators.time_calculator import TimeCalculator


class WorkReportService(BaseReportService):
    """工作報表服務"""
    
    def __init__(self):
        super().__init__()
        self.query_handler = OperatorReportQuery()
        self.time_calculator = TimeCalculator()

    def generate_report(self, date_range: Dict[str, date], **kwargs) -> List[Dict[str, Any]]:
        """
        生成工作報表數據。
        此報表只計算原始報工時長，不考慮休息時間，也不區分正常與加班。
        """
        self.logger.info(f"生成工作報表，日期範圍: {date_range}")
        
        # 獲取作業員報工數據
        operator_reports = self.query_handler.get_operator_reports_by_date_range(date_range)
        
        # 格式化報表數據
        return self._format_work_report_data(operator_reports)

    def _format_work_report_data(self, reports: List[Any]) -> List[Dict[str, Any]]:
        """
        格式化工作報表數據
        欄位：作業員、報工日期、工單號、產品編號、開始時間、結束時間、工序、工作數量、不良品數量
        """
        work_report_data = []
        
        for report in reports:
            # 計算工作時長
            work_duration = self.time_calculator.calculate_raw_duration(
                report.start_time, report.end_time
            )
            
            work_report_data.append({
                'operator': report.operator.username if hasattr(report, 'operator') else '',
                'report_date': report.report_date.strftime('%Y-%m-%d') if hasattr(report, 'report_date') else '',
                'work_order_no': report.work_order_no if hasattr(report, 'work_order_no') else '',
                'product_sn': report.product_sn if hasattr(report, 'product_sn') else '',
                'start_time': report.start_time.strftime('%Y-%m-%d %H:%M:%S') if report.start_time else '',
                'end_time': report.end_time.strftime('%Y-%m-%d %H:%M:%S') if report.end_time else '',
                'process': report.process if hasattr(report, 'process') else '',
                'work_quantity': report.work_quantity if hasattr(report, 'work_quantity') else 0,
                'defect_quantity': report.defect_quantity if hasattr(report, 'defect_quantity') else 0,
                'work_duration_hours': round(work_duration / 3600, 2),  # 轉換為小時
                'abnormal_notes': report.abnormal_notes if hasattr(report, 'abnormal_notes') else '',
            })
        
        return work_report_data

    def generate_summary_report(self, date_range: Dict[str, date], **kwargs) -> Dict[str, Any]:
        """
        生成工作報表摘要統計
        """
        work_data = self.generate_report(date_range, **kwargs)
        
        # 按作業員分組統計
        operator_summary = defaultdict(lambda: {
            'total_work_quantity': 0,
            'total_defect_quantity': 0,
            'total_work_hours': 0,
            'work_orders': set(),
            'processes': set()
        })
        
        for record in work_data:
            operator = record['operator']
            operator_summary[operator]['total_work_quantity'] += record['work_quantity']
            operator_summary[operator]['total_defect_quantity'] += record['defect_quantity']
            operator_summary[operator]['total_work_hours'] += record['work_duration_hours']
            operator_summary[operator]['work_orders'].add(record['work_order_no'])
            operator_summary[operator]['processes'].add(record['process'])
        
        # 格式化摘要數據
        summary_data = []
        for operator, data in operator_summary.items():
            summary_data.append({
                'operator': operator,
                'total_work_quantity': data['total_work_quantity'],
                'total_defect_quantity': data['total_defect_quantity'],
                'total_work_hours': round(data['total_work_hours'], 2),
                'work_order_count': len(data['work_orders']),
                'process_count': len(data['processes']),
                'efficiency_rate': self._calculate_efficiency_rate(
                    data['total_work_quantity'], 
                    data['total_defect_quantity']
                )
            })
        
        return {
            'summary_data': summary_data,
            'total_records': len(work_data),
            'date_range': date_range
        }

    def _calculate_efficiency_rate(self, work_quantity: int, defect_quantity: int) -> float:
        """計算效率率"""
        total_quantity = work_quantity + defect_quantity
        if total_quantity == 0:
            return 0.0
        return round((work_quantity / total_quantity) * 100, 2) 