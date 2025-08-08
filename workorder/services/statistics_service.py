"""
統一統計服務
確保所有地方的統計數據計算邏輯一致
"""

from datetime import date, timedelta
from django.db.models import Q, Count
from workorder.models import BackupOperatorSupplementReport as OperatorSupplementReport, BackupSMTSupplementReport as SMTSupplementReport


class StatisticsService:
    """
    統一統計服務類別
    提供一致的統計數據計算邏輯
    """
    
    @staticmethod
    def get_report_statistics():
        """
        獲取報工統計數據
        返回統一的統計數據字典
        """
        today = date.today()
        month_start = today.replace(day=1)
        
        # 作業員報工統計
        operator_stats = StatisticsService._get_operator_statistics(today, month_start)
        
        # SMT報工統計
        smt_stats = StatisticsService._get_smt_statistics(today, month_start)
        
        # 計算總計（主管不報工，只審核）
        total_stats = {
            'total_today': operator_stats['today'] + smt_stats['today'],
            'total_month': operator_stats['month'] + smt_stats['month'],
            'total_pending': operator_stats['pending'] + smt_stats['pending'],
            'total_abnormal': operator_stats['abnormal'] + smt_stats['abnormal'],
        }
        
        return {
            'operator': operator_stats,
            'smt': smt_stats,
            'total': total_stats,
        }
    
    @staticmethod
    def _get_operator_statistics(today, month_start):
        """
        獲取作業員報工統計
        使用 created_at（登記時間）進行統計，而不是 work_date（工作日期）
        """
        from django.utils import timezone
        from datetime import datetime
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        month_start_datetime = timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
        
        return {
            'today': OperatorSupplementReport.objects.filter(created_at__range=(today_start, today_end)).count(),
            'month': OperatorSupplementReport.objects.filter(created_at__gte=month_start_datetime).count(),
            'pending': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
            'abnormal': OperatorSupplementReport.objects.filter(
                Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
            ).count(),
            'approved': OperatorSupplementReport.objects.filter(approval_status='approved').count(),
        }
    
    @staticmethod
    def _get_smt_statistics(today, month_start):
        """
        獲取SMT報工統計
        使用 created_at（登記時間）進行統計，而不是 work_date（工作日期）
        """
        from django.utils import timezone
        from datetime import datetime
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        month_start_datetime = timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
        
        return {
            'today': SMTSupplementReport.objects.filter(created_at__range=(today_start, today_end)).count(),
            'month': SMTSupplementReport.objects.filter(created_at__gte=month_start_datetime).count(),
            'pending': SMTSupplementReport.objects.filter(approval_status='pending').count(),
            'abnormal': SMTSupplementReport.objects.filter(
                Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
            ).count(),
            'approved': SMTSupplementReport.objects.filter(approval_status='approved').count(),
        }
    
    @staticmethod
    def get_operator_only_statistics():
        """
        獲取僅作業員的統計數據
        用於作業員報工頁面
        """
        today = date.today()
        month_start = today.replace(day=1)
        
        operator_stats = StatisticsService._get_operator_statistics(today, month_start)
        
        return {
            'today_reports': operator_stats['today'],
            'month_reports': operator_stats['month'],
            'pending_reports': operator_stats['pending'],
            'abnormal_reports': operator_stats['abnormal'],
            'stats': {
                'total_pending': operator_stats['pending'],
                'total_today': operator_stats['today'],
                'total_month': operator_stats['month'],
                'total_abnormal': operator_stats['abnormal'],
                'pending_operator': operator_stats['pending'],
                'pending_smt': 0,
                'today_operator': operator_stats['today'],
                'today_smt': 0,
                'month_operator': operator_stats['month'],
                'month_smt': 0,
                'abnormal_operator': operator_stats['abnormal'],
                'abnormal_smt': 0,
            }
        }
    
    @staticmethod
    def get_smt_only_statistics():
        """
        獲取僅SMT的統計數據
        用於SMT報工頁面
        """
        today = date.today()
        month_start = today.replace(day=1)
        
        smt_stats = StatisticsService._get_smt_statistics(today, month_start)
        
        return {
            'today_reports': smt_stats['today'],
            'month_reports': smt_stats['month'],
            'pending_reports': smt_stats['pending'],
            'abnormal_reports': smt_stats['abnormal'],
            'stats': {
                'total_pending': smt_stats['pending'],
                'total_today': smt_stats['today'],
                'total_month': smt_stats['month'],
                'total_abnormal': smt_stats['abnormal'],
                'pending_operator': 0,
                'pending_smt': smt_stats['pending'],
                'today_operator': 0,
                'today_smt': smt_stats['today'],
                'month_operator': 0,
                'month_smt': smt_stats['month'],
                'abnormal_operator': 0,
                'abnormal_smt': smt_stats['abnormal'],
            }
        }
    
    @staticmethod
    def get_supervisor_dashboard_statistics():
        """
        獲取主管儀表板統計數據
        用於主管審核首頁 - 顯示作業員和SMT的統計（主管不報工，只審核）
        """
        stats = StatisticsService.get_report_statistics()
        
        # 格式化為主管儀表板需要的格式
        dashboard_stats = {
            # 待審核統計
            'pending_supervisor': 0,  # 主管不報工
            'pending_operator': stats['operator']['pending'],
            'pending_smt': stats['smt']['pending'],
            'total_pending': stats['total']['total_pending'],
            
            # 今日統計
            'today_supervisor': 0,  # 主管不報工
            'today_operator': stats['operator']['today'],
            'today_smt': stats['smt']['today'],
            'total_today': stats['total']['total_today'],
            
            # 本月統計
            'month_supervisor': 0,  # 主管不報工
            'month_operator': stats['operator']['month'],
            'month_smt': stats['smt']['month'],
            'total_month': stats['total']['total_month'],
            
            # 異常統計
            'abnormal_supervisor': 0,  # 主管不報工
            'abnormal_operator': stats['operator']['abnormal'],
            'abnormal_smt': stats['smt']['abnormal'],
            'total_abnormal': stats['total']['total_abnormal'],
            
            # 已核准統計
            'approved_supervisor': 0,  # 主管不報工
            'approved_operator': stats['operator']['approved'],
            'approved_smt': stats['smt']['approved'],
            'total_approved': stats['operator']['approved'] + stats['smt']['approved'],
        }
        
        return dashboard_stats
    
    @staticmethod
    def get_report_index_statistics():
        """
        獲取報工管理首頁統計數據
        用於報工管理首頁 - 顯示作業員和SMT的統計（主管不報工）
        """
        stats = StatisticsService.get_report_statistics()
        
        return {
            'today_reports': stats['total']['total_today'],
            'month_reports': stats['total']['total_month'],
            'pending_reports': stats['total']['total_pending'],
            'abnormal_reports': stats['total']['total_abnormal'],
            'stats': {
                'total_pending': stats['total']['total_pending'],
                'total_today': stats['total']['total_today'],
                'total_month': stats['total']['total_month'],
                'total_abnormal': stats['total']['total_abnormal'],
                'pending_operator': stats['operator']['pending'],
                'pending_smt': stats['smt']['pending'],
                'today_operator': stats['operator']['today'],
                'today_smt': stats['smt']['today'],
                'month_operator': stats['operator']['month'],
                'month_smt': stats['smt']['month'],
                'abnormal_operator': stats['operator']['abnormal'],
                'abnormal_smt': stats['smt']['abnormal'],
            }
        } 