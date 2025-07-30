"""
工時報表服務類別
提供工時報表的數據生成和處理功能
"""

from typing import Dict, List, Any
from datetime import date
from collections import defaultdict

from .base_report_service import BaseReportService
from ..queries.operator_query import OperatorReportQuery
from ..queries.equipment_query import EquipmentQuery
from ..calculators.time_calculator import TimeCalculator


class WorkHourReportService(BaseReportService):
    """工時報表服務"""
    
    def __init__(self):
        super().__init__()
        self.query_handler = OperatorReportQuery()
        self.equipment_query = EquipmentQuery()
        self.time_calculator = TimeCalculator()

    def generate_report(self, date_range: Dict[str, date], report_target: str = 'operator', **kwargs) -> List[Dict[str, Any]]:
        """
        生成工時報表數據。
        精確計算每日、每週、每月正常工時、加班時數，並從中扣除休息時間。
        
        Args:
            date_range: 日期範圍
            report_target: 報表目標 ('operator' 或 'equipment')
        """
        self.logger.info(f"生成工時報表，目標: {report_target}，日期範圍: {date_range}")
        
        if report_target == 'operator':
            return self._generate_operator_work_hour_report(date_range, **kwargs)
        elif report_target == 'equipment':
            return self._generate_equipment_work_hour_report(date_range, **kwargs)
        else:
            raise ValueError(f"不支援的報表目標: {report_target}")

    def _generate_operator_work_hour_report(self, date_range: Dict[str, date], **kwargs) -> List[Dict[str, Any]]:
        """生成作業員工時報表"""
        # 獲取作業員報工數據
        operator_reports = self.query_handler.get_operator_reports_by_date_range(date_range)
        
        # 按作業員和日期分組
        grouped_reports = defaultdict(lambda: defaultdict(list))
        for report in operator_reports:
            operator_id = report.operator.id if hasattr(report, 'operator') else 'unknown'
            report_date = report.report_date.strftime('%Y-%m-%d') if hasattr(report, 'report_date') else ''
            grouped_reports[operator_id][report_date].append(report)
        
        work_hour_data = []
        
        for operator_id, daily_reports in grouped_reports.items():
            for report_date, reports_for_day in daily_reports.items():
                if not reports_for_day:
                    continue
                
                # 獲取作業員資訊
                operator = reports_for_day[0].operator if hasattr(reports_for_day[0], 'operator') else None
                operator_name = operator.username if operator else f'Operator_{operator_id}'
                
                # 計算工時
                calculated_hours = self.time_calculator.calculate_actual_work_and_overtime(
                    reports_for_day, 
                    line_settings=kwargs.get('line_settings')
                )
                
                work_hour_data.append({
                    'report_date': report_date,
                    'operator_id': operator_id,
                    'operator_name': operator_name,
                    'total_hours_raw': calculated_hours['total_hours_raw'],
                    'normal_hours': calculated_hours['normal_hours'],
                    'overtime_hours': calculated_hours['overtime_hours'],
                    'break_deduction_hours': calculated_hours['break_deduction_hours'],
                    'efficiency_rate': self._calculate_operator_efficiency(reports_for_day),
                    'utilization_rate': self._calculate_utilization_rate(calculated_hours),
                    'calculation_details': calculated_hours['details']
                })
        
        return work_hour_data

    def _generate_equipment_work_hour_report(self, date_range: Dict[str, date], **kwargs) -> List[Dict[str, Any]]:
        """生成設備工時報表"""
        # 獲取設備運行數據
        equipment_reports = self.equipment_query.get_equipment_reports_by_date_range(date_range)
        
        # 按設備和日期分組
        grouped_reports = defaultdict(lambda: defaultdict(list))
        for report in equipment_reports:
            equipment_id = report.equipment.id if hasattr(report, 'equipment') else 'unknown'
            report_date = report.report_date.strftime('%Y-%m-%d') if hasattr(report, 'report_date') else ''
            grouped_reports[equipment_id][report_date].append(report)
        
        work_hour_data = []
        
        for equipment_id, daily_reports in grouped_reports.items():
            for report_date, reports_for_day in daily_reports.items():
                if not reports_for_day:
                    continue
                
                # 獲取設備資訊
                equipment = reports_for_day[0].equipment if hasattr(reports_for_day[0], 'equipment') else None
                equipment_name = equipment.name if equipment else f'Equipment_{equipment_id}'
                
                # 計算設備工時
                calculated_hours = self.time_calculator.calculate_smt_equipment_work_hours(
                    reports_for_day, 
                    line_settings=kwargs.get('line_settings')
                )
                
                work_hour_data.append({
                    'report_date': report_date,
                    'equipment_id': equipment_id,
                    'equipment_name': equipment_name,
                    'total_run_hours_raw': calculated_hours['total_run_hours_raw'],
                    'normal_run_hours': calculated_hours['normal_run_hours'],
                    'overtime_run_hours': calculated_hours['overtime_run_hours'],
                    'down_time_hours': calculated_hours['down_time_hours'],
                    'utilization_rate': self._calculate_equipment_utilization(calculated_hours),
                    'efficiency_rate': self._calculate_equipment_efficiency(reports_for_day),
                    'calculation_details': calculated_hours['details']
                })
        
        return work_hour_data

    def generate_summary_report(self, date_range: Dict[str, date], report_target: str = 'operator', **kwargs) -> Dict[str, Any]:
        """生成工時報表摘要統計"""
        work_hour_data = self.generate_report(date_range, report_target, **kwargs)
        
        if not work_hour_data:
            return {
                'summary_data': [],
                'total_stats': {},
                'date_range': date_range
            }
        
        # 按人員/設備分組統計
        target_summary = defaultdict(lambda: {
            'total_normal_hours': 0,
            'total_overtime_hours': 0,
            'total_break_hours': 0,
            'total_work_days': 0,
            'avg_efficiency_rate': 0,
            'avg_utilization_rate': 0
        })
        
        efficiency_rates = defaultdict(list)
        utilization_rates = defaultdict(list)
        
        for record in work_hour_data:
            if report_target == 'operator':
                target_key = record['operator_name']
                target_summary[target_key]['total_normal_hours'] += record['normal_hours']
                target_summary[target_key]['total_overtime_hours'] += record['overtime_hours']
                target_summary[target_key]['total_break_hours'] += record['break_deduction_hours']
            else:
                target_key = record['equipment_name']
                target_summary[target_key]['total_normal_hours'] += record['normal_run_hours']
                target_summary[target_key]['total_overtime_hours'] += record['overtime_run_hours']
                target_summary[target_key]['total_break_hours'] += record['down_time_hours']
            
            target_summary[target_key]['total_work_days'] += 1
            
            if record.get('efficiency_rate') is not None:
                efficiency_rates[target_key].append(record['efficiency_rate'])
            if record.get('utilization_rate') is not None:
                utilization_rates[target_key].append(record['utilization_rate'])
        
        # 計算平均值
        summary_data = []
        for target_key, data in target_summary.items():
            avg_efficiency = 0
            if efficiency_rates[target_key]:
                avg_efficiency = round(sum(efficiency_rates[target_key]) / len(efficiency_rates[target_key]), 2)
            
            avg_utilization = 0
            if utilization_rates[target_key]:
                avg_utilization = round(sum(utilization_rates[target_key]) / len(utilization_rates[target_key]), 2)
            
            summary_data.append({
                'target_name': target_key,
                'total_normal_hours': round(data['total_normal_hours'], 2),
                'total_overtime_hours': round(data['total_overtime_hours'], 2),
                'total_break_hours': round(data['total_break_hours'], 2),
                'total_work_days': data['total_work_days'],
                'avg_efficiency_rate': avg_efficiency,
                'avg_utilization_rate': avg_utilization,
                'total_work_hours': round(data['total_normal_hours'] + data['total_overtime_hours'], 2)
            })
        
        # 總體統計
        total_stats = {
            'total_records': len(work_hour_data),
            'total_targets': len(summary_data),
            'avg_efficiency_rate': 0,
            'avg_utilization_rate': 0
        }
        
        all_efficiency_rates = [rate for rates in efficiency_rates.values() for rate in rates]
        all_utilization_rates = [rate for rates in utilization_rates.values() for rate in rates]
        
        if all_efficiency_rates:
            total_stats['avg_efficiency_rate'] = round(sum(all_efficiency_rates) / len(all_efficiency_rates), 2)
        if all_utilization_rates:
            total_stats['avg_utilization_rate'] = round(sum(all_utilization_rates) / len(all_utilization_rates), 2)
        
        return {
            'summary_data': summary_data,
            'total_stats': total_stats,
            'date_range': date_range
        }

    def _calculate_operator_efficiency(self, reports: List[Any]) -> float:
        """計算作業員效率率"""
        total_work_quantity = 0
        total_defect_quantity = 0
        
        for report in reports:
            total_work_quantity += getattr(report, 'work_quantity', 0)
            total_defect_quantity += getattr(report, 'defect_quantity', 0)
        
        total_quantity = total_work_quantity + total_defect_quantity
        if total_quantity == 0:
            return 0.0
        
        return round((total_work_quantity / total_quantity) * 100, 2)

    def _calculate_equipment_efficiency(self, reports: List[Any]) -> float:
        """計算設備效率率"""
        # 這裡可以根據設備的實際運行情況計算效率
        # 暫時返回一個預設值
        return 85.0

    def _calculate_utilization_rate(self, calculated_hours: Dict[str, float]) -> float:
        """計算利用率"""
        total_hours = calculated_hours.get('normal_hours', 0) + calculated_hours.get('overtime_hours', 0)
        # 假設標準工作時間為8小時
        standard_hours = 8.0
        if standard_hours == 0:
            return 0.0
        
        return round((total_hours / standard_hours) * 100, 2)

    def _calculate_equipment_utilization(self, calculated_hours: Dict[str, float]) -> float:
        """計算設備利用率"""
        total_run_hours = calculated_hours.get('normal_run_hours', 0) + calculated_hours.get('overtime_run_hours', 0)
        # 假設設備標準運行時間為24小時
        standard_hours = 24.0
        if standard_hours == 0:
            return 0.0
        
        return round((total_run_hours / standard_hours) * 100, 2) 