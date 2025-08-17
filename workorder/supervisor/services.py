"""
主管服務模組
提供主管相關的業務邏輯服務
注意：舊的報工系統已棄用，相關功能已移至新的填報系統
"""

import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from workorder.models import WorkOrder, WorkOrderProcess, WorkOrderProduction, WorkOrderProductionDetail

logger = logging.getLogger(__name__)

class SupervisorStatisticsService:
    """主管統計數據服務 (Supervisor Statistics Service)"""
    
    @staticmethod
    def get_supervisor_statistics():
        """
        統一的主管功能統計數據生成函數 (Supervisor Statistics Generator)
        返回所有主管功能頁面需要的統計數據
        """
        today = datetime.now().date()
        month_start = today.replace(day=1)
        week_start = today - timedelta(days=today.weekday())
        year_start = today.replace(month=1, day=1)
        
        # 基礎統計數據（主管不報工，只審核）
        stats = {
            # 今日統計 (Today Statistics)
            'total_reports_today': 0,
            'operator_reports_today': 0,
            'smt_reports_today': 0,
            
            # 本週統計 (Week Statistics)
            'total_reports_week': 0,
            'operator_reports_week': 0,
            'smt_reports_week': 0,
            
            # 本月統計 (Month Statistics)
            'total_reports_month': 0,
            'operator_reports_month': 0,
            'smt_reports_month': 0,
            
            # 今年統計 (Year Statistics)
            'total_reports_year': 0,
            'operator_reports_year': 0,
            'smt_reports_year': 0,
            
            # 待審核統計 (Pending Approval Statistics)
            'pending_reports': 0,
            'pending_operator': 0,
            'pending_smt': 0,
            
            # 異常統計 (Abnormal Statistics)
            'abnormal_reports': 0,
            'abnormal_operator': 0,
            'abnormal_smt': 0,
            
            # 審核狀態統計 (Approval Status Statistics)
            'approved_operator': 0,
            'approved_smt': 0,
            'rejected_operator': 0,
            'rejected_smt': 0,
        }
        
        # 計算總計
        stats['total_reports_today'] = stats['operator_reports_today'] + stats['smt_reports_today']
        stats['total_reports_week'] = stats['operator_reports_week'] + stats['smt_reports_week']
        stats['total_reports_month'] = stats['operator_reports_month'] + stats['smt_reports_month']
        stats['total_reports_year'] = stats['operator_reports_year'] + stats['smt_reports_week']
        stats['pending_reports'] = stats['pending_operator'] + stats['pending_smt']
        stats['abnormal_reports'] = stats['abnormal_operator'] + stats['abnormal_smt']
        
        # 計算平均值
        days_in_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - today.replace(day=1)
        days_in_month = days_in_month.days
        
        if days_in_month > 0:
            stats['avg_daily_reports'] = round(stats['total_reports_month'] / days_in_month, 1)
        else:
            stats['avg_daily_reports'] = 0
            
        stats['avg_weekly_reports'] = round(stats['total_reports_month'] / 4, 1)  # 假設每月4週
        stats['avg_monthly_reports'] = stats['total_reports_month']
        
        # 異常統計詳細數據
        abnormal_stats = {
            'total_abnormal': stats['abnormal_reports'],
            'critical': 0,
            'pending': stats['pending_reports'],
            'resolved': stats['approved_operator'] + stats['approved_smt'],
            'operator_abnormal': stats['abnormal_operator'],
            'smt_abnormal': stats['abnormal_smt'],
        }
        
        # 系統狀態（模擬數據，實際應從系統獲取）
        system_status = {
            'database_size': '2.5 GB',
            'last_backup': '2025-01-01 06:00',
            'backup_status': 'success',
            'optimization_status': 'success',
            'disk_usage': '75%',
        }
        
        return {
            'stats': stats,
            'abnormal_stats': abnormal_stats,
            'system_status': system_status,
        }

class SupervisorAbnormalService:
    """主管異常處理服務 (Supervisor Abnormal Service)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_abnormal_data(self):
        """
        獲取異常數據
        """
        return {
            'total_abnormal': 0,
            'critical': 0,
            'pending': 0,
            'resolved': 0,
            'operator_abnormal': [],
            'smt_abnormal': [],
        }
    
    def get_abnormal_detail(self, abnormal_type, abnormal_id):
        """
        獲取異常詳情
        """
        return {
            'id': abnormal_id,
            'type': abnormal_type,
            'details': '異常詳情資料',
        }
    
    def batch_resolve_abnormal(self, abnormal_ids, resolve_type):
        """
        批量解決異常
        """
        try:
            # 這裡可以添加實際的異常解決邏輯
            resolved_count = len(abnormal_ids)
            
            return {
                'success': True,
                'message': f'成功解決 {resolved_count} 個異常',
                'resolved_count': resolved_count
            }
        except Exception as e:
            self.logger.error(f"批量解決異常失敗: {str(e)}")
            return {
                'success': False,
                'message': f'批量解決異常失敗: {str(e)}'
            } 