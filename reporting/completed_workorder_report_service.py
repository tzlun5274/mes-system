"""
已完工工單報表服務
提供已完工工單報表的資料查詢和統計功能
"""

import logging
from django.utils import timezone
from django.db.models import Count, Sum, Avg

logger = logging.getLogger(__name__)


class CompletedWorkOrderReportService:
    """
    已完工工單報表服務
    提供已完工工單報表的資料查詢和統計功能
    """
    
    @staticmethod
    def get_completed_workorder_summary(company_code=None, year=None, month=None, quarter=None):
        """
        取得已完工工單統計摘要
        
        Args:
            company_code: 公司代號
            year: 年份
            month: 月份
            quarter: 季度
            
        Returns:
            dict: 統計摘要
        """
        from .models import CompletedWorkOrderAnalysis
        
        # 排除 RD樣品工單
        queryset = CompletedWorkOrderAnalysis.objects.exclude(workorder_id__icontains='RD樣品')
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        if year:
            queryset = queryset.filter(completion_year=year)
        if month:
            queryset = queryset.filter(completion_month=month)
        if quarter:
            queryset = queryset.filter(completion_quarter=quarter)
        
        # 計算統計資料
        stats = queryset.aggregate(
            total_workorders=Count('id'),
            total_work_hours=Sum('total_work_hours'),
            total_overtime_hours=Sum('total_overtime_hours'),
            avg_efficiency_rate=Avg('efficiency_rate'),
        )
        
        # 計算平均效率率
        avg_efficiency_rate = stats['avg_efficiency_rate'] or 0
        
        return {
            'total_workorders': stats['total_workorders'] or 0,
            'total_work_hours': float(stats['total_work_hours'] or 0),
            'total_overtime_hours': float(stats['total_overtime_hours'] or 0),
            'avg_efficiency_rate': float(avg_efficiency_rate),
        }
    
    @staticmethod
    def get_completed_workorder_trend(company_code=None, days=30):
        """
        取得已完工工單趨勢資料
        
        Args:
            company_code: 公司代號
            days: 天數
            
        Returns:
            dict: 趨勢資料
        """
        from .models import CompletedWorkOrderAnalysis
        from datetime import datetime, timedelta
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 排除 RD樣品工單
        queryset = CompletedWorkOrderAnalysis.objects.exclude(workorder_id__icontains='RD樣品').filter(
            completion_date__range=[start_date, end_date]
        )
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        # 按日期分組統計
        daily_data = queryset.values('completion_date').annotate(
            workorder_count=Count('id'),
            total_work_hours=Sum('total_work_hours'),
            avg_efficiency_rate=Avg('efficiency_rate'),
        ).order_by('completion_date')
        
        labels = []
        workorder_counts = []
        work_hours = []
        efficiency_rates = []
        
        for item in daily_data:
            labels.append(item['completion_date'].strftime('%m/%d'))
            workorder_counts.append(item['workorder_count'])
            work_hours.append(float(item['total_work_hours'] or 0))
            efficiency_rates.append(float(item['avg_efficiency_rate'] or 0))
        
        return {
            'labels': labels,
            'workorder_counts': workorder_counts,
            'work_hours': work_hours,
            'efficiency_rates': efficiency_rates,
        }
    
    @staticmethod
    def get_company_completion_distribution():
        """
        取得公司完工分布資料
        
        Returns:
            dict: 分布資料
        """
        from .models import CompletedWorkOrderAnalysis
        
        # 排除 RD樣品工單
        company_data = CompletedWorkOrderAnalysis.objects.exclude(workorder_id__icontains='RD樣品').values('company_name').annotate(
            workorder_count=Count('id'),
            total_work_hours=Sum('total_work_hours'),
            avg_efficiency_rate=Avg('efficiency_rate'),
        ).order_by('-workorder_count')
        
        labels = []
        workorder_counts = []
        work_hours = []
        efficiency_rates = []
        
        for item in company_data:
            company_name = item['company_name'] or '未指定'
            labels.append(company_name)
            workorder_counts.append(item['workorder_count'])
            work_hours.append(float(item['total_work_hours'] or 0))
            efficiency_rates.append(float(item['avg_efficiency_rate'] or 0))
        
        return {
            'labels': labels,
            'workorder_counts': workorder_counts,
            'work_hours': work_hours,
            'efficiency_rates': efficiency_rates,
        }
