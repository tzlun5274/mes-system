"""
工作時數報表服務
提供工作時數相關的報表功能
"""

from django.db.models import Sum, Avg, Count
from django.utils import timezone
from decimal import Decimal
import logging

from .models import WorkOrderReportData

logger = logging.getLogger(__name__)


class WorkHourReportService:
    """工作時數報表服務"""
    
    def __init__(self, company_code=None):
        self.company_code = company_code
    
    def get_daily_report(self, company_code, date):
        """日報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_date=date
        )
    
    def get_daily_report_by_company_operator(self, company, operator, date):
        """按公司和作業員查詢日報表"""
        queryset = WorkOrderReportData.objects.filter(work_date=date)
        
        if company != 'all':
            queryset = queryset.filter(company=company)
        
        if operator != 'all':
            queryset = queryset.filter(operator_name=operator)
        
        return queryset
    
    def get_daily_summary_by_company_operator(self, company, operator, date):
        """按公司和作業員查詢日報表摘要"""
        data = self.get_daily_report_by_company_operator(company, operator, date)
        
        # 計算總工作時數
        total_work_hours = data.aggregate(total=Sum('daily_work_hours'))['total'] or Decimal('0')
        
        # 計算作業員數量（去重）
        if operator == 'all':
            total_operators = data.exclude(operator_name__isnull=True).values('operator_name').distinct().count()
        else:
            total_operators = 1  # 特定作業員
        
        # 計算總設備使用時數
        total_equipment_hours = data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0')
        
        # 計算工單數量
        workorder_count = data.count()
        
        # 計算平均日工作時數
        avg_daily_hours = data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0')
        
        summary = {
            'total_work_hours': total_work_hours,
            'total_operators': total_operators,
            'total_equipment_hours': total_equipment_hours,
            'workorder_count': workorder_count,
            'avg_daily_hours': avg_daily_hours,
        }
        
        return summary
    
    def get_operator_statistics(self, data):
        """生成作業員統計資料"""
        if not data:
            return []
        
        # 按作業員分組統計
        operator_stats = data.values('operator_name').annotate(
            total_work_hours=Sum('daily_work_hours'),
            total_overtime_hours=Sum('overtime_hours'),
            total_hours=Sum('daily_work_hours') + Sum('overtime_hours')
        ).order_by('-total_hours')
        
        # 格式化統計資料
        stats_list = []
        for i, stat in enumerate(operator_stats, 1):
            stats_list.append({
                'rank': i,
                'operator_name': stat['operator_name'] or '未指定',
                'work_hours': float(stat['total_work_hours'] or 0),
                'overtime_hours': float(stat['total_overtime_hours'] or 0),
                'total_hours': float(stat['total_hours'] or 0),
            })
        
        return stats_list
    
    def get_custom_report_by_company_operator(self, company, operator, start_date, end_date):
        """按公司和作業員查詢自訂報表"""
        queryset = WorkOrderReportData.objects.filter(
            work_date__range=[start_date, end_date]
        )
        
        if company != 'all':
            queryset = queryset.filter(company=company)
        
        if operator != 'all':
            queryset = queryset.filter(operator_name=operator)
        
        return queryset.order_by('work_date', 'operator_name')
    
    def get_custom_summary_by_company_operator(self, company, operator, start_date, end_date):
        """按公司和作業員查詢自訂報表摘要"""
        data = self.get_custom_report_by_company_operator(company, operator, start_date, end_date)
        
        # 計算總工作時數
        total_work_hours = data.aggregate(total=Sum('daily_work_hours'))['total'] or Decimal('0')
        
        # 計算作業員數量（去重）
        if operator == 'all':
            total_operators = data.exclude(operator_name__isnull=True).values('operator_name').distinct().count()
        else:
            total_operators = 1  # 特定作業員
        
        # 計算總設備使用時數
        total_equipment_hours = data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0')
        
        # 計算工單數量
        workorder_count = data.count()
        
        # 計算平均日工作時數
        avg_daily_hours = data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0')
        
        summary = {
            'total_work_hours': total_work_hours,
            'total_operators': total_operators,
            'total_equipment_hours': total_equipment_hours,
            'workorder_count': workorder_count,
            'avg_daily_hours': avg_daily_hours,
        }
        
        return summary
    
    def get_weekly_report(self, company_code, year, week):
        """週報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_year=year,
            work_week=week
        ).order_by('operator_name', 'work_date')
    
    def get_monthly_report(self, company_code, year, month):
        """月報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_year=year,
            work_month=month
        ).order_by('operator_name', 'work_date')
    
    def get_quarterly_report(self, company_code, year, quarter):
        """季報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_year=year,
            work_quarter=quarter
        ).order_by('operator_name', 'work_date')
    
    def get_yearly_report(self, company_code, year):
        """年報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_year=year
        ).order_by('operator_name', 'work_date')
    
    def get_daily_summary(self, company_code, date):
        """日報表摘要"""
        data = self.get_daily_report(company_code, date)
        
        summary = {
            'total_operators': data.values('operator_name').distinct().count(),
            'total_workorders': data.values('workorder_id').distinct().count(),
            'total_work_hours': data.aggregate(Sum('work_hours'))['work_hours__sum'] or 0,
            'total_overtime_hours': data.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or 0,
            'total_hours': data.aggregate(Sum('total_hours'))['total_hours__sum'] or 0,
            'avg_work_hours': data.aggregate(Avg('work_hours'))['work_hours__avg'] or 0,
            'avg_overtime_hours': data.aggregate(Avg('overtime_hours'))['overtime_hours__avg'] or 0
        }
        
        return summary
    
    def get_weekly_summary(self, company_code, year, week):
        """週報表摘要"""
        data = self.get_weekly_report(company_code, year, week)
        
        summary = {
            'total_operators': data.values('operator_name').distinct().count(),
            'total_workorders': data.values('workorder_id').distinct().count(),
            'total_work_hours': data.aggregate(Sum('work_hours'))['work_hours__sum'] or 0,
            'total_overtime_hours': data.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or 0,
            'total_hours': data.aggregate(Sum('total_hours'))['total_hours__sum'] or 0,
            'avg_work_hours': data.aggregate(Avg('work_hours'))['work_hours__avg'] or 0,
            'avg_overtime_hours': data.aggregate(Avg('overtime_hours'))['overtime_hours__avg'] or 0
        }
        
        return summary
    
    def get_monthly_summary(self, company_code, year, month):
        """月報表摘要"""
        data = self.get_monthly_report(company_code, year, month)
        
        summary = {
            'total_operators': data.values('operator_name').distinct().count(),
            'total_workorders': data.values('workorder_id').distinct().count(),
            'total_work_hours': data.aggregate(Sum('work_hours'))['work_hours__sum'] or 0,
            'total_overtime_hours': data.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or 0,
            'total_hours': data.aggregate(Sum('total_hours'))['total_hours__sum'] or 0,
            'avg_work_hours': data.aggregate(Avg('work_hours'))['work_hours__avg'] or 0,
            'avg_overtime_hours': data.aggregate(Avg('overtime_hours'))['overtime_hours__avg'] or 0
        }
        
        return summary
    
    def get_quarterly_summary(self, company_code, year, quarter):
        """季報表摘要"""
        data = self.get_quarterly_report(company_code, year, quarter)
        
        summary = {
            'total_operators': data.values('operator_name').distinct().count(),
            'total_workorders': data.values('workorder_id').distinct().count(),
            'total_work_hours': data.aggregate(Sum('work_hours'))['work_hours__sum'] or 0,
            'total_overtime_hours': data.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or 0,
            'total_hours': data.aggregate(Sum('total_hours'))['total_hours__sum'] or 0,
            'avg_work_hours': data.aggregate(Avg('work_hours'))['work_hours__avg'] or 0,
            'avg_overtime_hours': data.aggregate(Avg('overtime_hours'))['overtime_hours__avg'] or 0
        }
        
        return summary
    
    def get_yearly_summary(self, company_code, year):
        """年報表摘要"""
        data = self.get_yearly_report(company_code, year)
        
        summary = {
            'total_operators': data.values('operator_name').distinct().count(),
            'total_workorders': data.values('workorder_id').distinct().count(),
            'total_work_hours': data.aggregate(Sum('work_hours'))['work_hours__sum'] or 0,
            'total_overtime_hours': data.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or 0,
            'total_hours': data.aggregate(Sum('total_hours'))['total_hours__sum'] or 0,
            'avg_work_hours': data.aggregate(Avg('work_hours'))['work_hours__avg'] or 0,
            'avg_overtime_hours': data.aggregate(Avg('overtime_hours'))['overtime_hours__avg'] or 0
        }
        
        return summary
