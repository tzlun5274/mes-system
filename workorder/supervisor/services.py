"""
主管服務模組
提供主管相關的業務邏輯服務
"""

import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from workorder.models import WorkOrder, WorkOrderProcess, WorkOrderProduction, WorkOrderProductionDetail
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport

# 移除主管報工引用，避免混淆
# 主管職責：監督、審核、管理，不代為報工

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
            'operator_reports_today': OperatorSupplementReport.objects.filter(work_date=today).count(),
            'smt_reports_today': SMTProductionReport.objects.filter(work_date=today).count(),
            'supervisor_reports_today': 0,  # 主管不報工
            
            # 本週統計 (Week Statistics)
            'total_reports_week': 0,
            'operator_reports_week': OperatorSupplementReport.objects.filter(work_date__gte=week_start).count(),
            'smt_reports_week': SMTProductionReport.objects.filter(work_date__gte=week_start).count(),
            'supervisor_reports_week': 0,  # 主管不報工
            
            # 本月統計 (Month Statistics)
            'total_reports_month': 0,
            'operator_reports_month': OperatorSupplementReport.objects.filter(work_date__gte=month_start).count(),
            'smt_reports_month': SMTProductionReport.objects.filter(work_date__gte=month_start).count(),
            'supervisor_reports_month': 0,  # 主管不報工
            
            # 今年統計 (Year Statistics)
            'total_reports_year': 0,
            'operator_reports_year': OperatorSupplementReport.objects.filter(work_date__gte=year_start).count(),
            'smt_reports_year': SMTProductionReport.objects.filter(work_date__gte=year_start).count(),
            'supervisor_reports_year': 0,  # 主管不報工
            
            # 待審核統計 (Pending Approval Statistics)
            'pending_reports': 0,
            'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
            'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
            'pending_supervisor': 0,  # 主管不報工
            
            # 異常統計 (Abnormal Statistics)
            'abnormal_reports': 0,
            'abnormal_operator': OperatorSupplementReport.objects.filter(
                Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
            ).count(),
            'abnormal_smt': SMTProductionReport.objects.filter(
                Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
            ).count(),
            'abnormal_supervisor': 0,  # 主管不報工
            
            # 審核狀態統計 (Approval Status Statistics)
            'approved_operator': OperatorSupplementReport.objects.filter(approval_status='approved').count(),
            'approved_smt': SMTProductionReport.objects.filter(approval_status='approved').count(),
            'approved_supervisor': 0,  # 主管不報工
            
            'rejected_operator': OperatorSupplementReport.objects.filter(approval_status='rejected').count(),
            'rejected_smt': SMTProductionReport.objects.filter(approval_status='rejected').count(),
            'rejected_supervisor': 0,  # 主管不報工
        }
        
        # 計算總計（主管不報工，只審核）
        stats['total_reports_today'] = stats['operator_reports_today'] + stats['smt_reports_today']
        stats['total_reports_week'] = stats['operator_reports_week'] + stats['smt_reports_week']
        stats['total_reports_month'] = stats['operator_reports_month'] + stats['smt_reports_month']
        stats['total_reports_year'] = stats['operator_reports_year'] + stats['smt_reports_year']
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
        # 計算嚴重異常數量（包含「嚴重」、「緊急」、「停機」等關鍵字的異常）
        critical_operator = OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan') &
            (Q(abnormal_notes__icontains='嚴重') | Q(abnormal_notes__icontains='緊急') | Q(abnormal_notes__icontains='停機'))
        ).count()
        
        critical_smt = SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan') &
            (Q(abnormal_notes__icontains='嚴重') | Q(abnormal_notes__icontains='緊急') | Q(abnormal_notes__icontains='停機'))
        ).count()
        
        critical_supervisor = 0  # 主管不報工
        
        abnormal_stats = {
            'total_abnormal': stats['abnormal_reports'],
            'operator_abnormal': stats['abnormal_operator'],
            'smt_abnormal': stats['abnormal_smt'],
            'supervisor_abnormal': stats['abnormal_supervisor'],
            'critical': critical_operator + critical_smt + critical_supervisor,
            'pending': stats['pending_reports'],
            'resolved': stats['approved_operator'] + stats['approved_smt'] + stats['approved_supervisor'],
        }
        
        # 作業員統計詳細數據
        operator_stats = {
            'today': stats['operator_reports_today'],
            'week': stats['operator_reports_week'],
            'month': stats['operator_reports_month'],
            'year': stats['operator_reports_year'],
            'pending': stats['pending_operator'],
            'approved': stats['approved_operator'],
            'rejected': stats['rejected_operator'],
        }
        
        # SMT統計詳細數據
        smt_stats = {
            'today': stats['smt_reports_today'],
            'week': stats['smt_reports_week'],
            'month': stats['smt_reports_month'],
            'year': stats['smt_reports_year'],
            'pending': stats['pending_smt'],
            'approved': stats['approved_smt'],
            'rejected': stats['rejected_smt'],
        }
        
        # 資料維護統計
        data_stats = {
            'total_operator_reports': OperatorSupplementReport.objects.count(),
            'total_smt_reports': SMTProductionReport.objects.count(),
            'total_supervisor_reports': 0,  # 主管不應該有報工記錄
            'old_reports_30d': OperatorSupplementReport.objects.filter(work_date__lt=today - timedelta(days=30)).count(),
            'old_reports_90d': OperatorSupplementReport.objects.filter(work_date__lt=today - timedelta(days=90)).count(),
        }
        
        # 系統狀態（模擬數據，實際應從系統獲取）
        system_status = {
            'database_size': '2.5 GB',
            'last_backup': '2025-01-01 06:00',
            'backup_status': 'success',
            'optimization_status': 'success',
            'disk_usage': '75%',
        }
        
        # 維護選項
        maintenance_options = [
            {
                'id': 'cleanup_old_data',
                'name': '清理舊資料',
                'description': '清理30天前的報工記錄，釋放資料庫空間'
            },
            {
                'id': 'backup_database',
                'name': '資料庫備份',
                'description': '建立完整的資料庫備份檔案'
            },
            {
                'id': 'optimize_database',
                'name': '資料庫優化',
                'description': '優化資料庫索引和查詢效能'
            },
            {
                'id': 'export_reports',
                'name': '匯出報表',
                'description': '匯出所有報工記錄為Excel檔案'
            },
        ]
        
        return {
            'stats': stats,
            'abnormal_stats': abnormal_stats,
            'operator_stats': operator_stats,
            'smt_stats': smt_stats,
            'data_stats': data_stats,
            'system_status': system_status,
            'maintenance_options': maintenance_options,
        }


class SupervisorApprovalService:
    """主管審核服務 (Supervisor Approval Service)"""
    
    @staticmethod
    def get_pending_approval_reports():
        """
        獲取待審核報工記錄 (Get Pending Approval Reports)
        """
        pending_reports = []
        
        # 獲取公司配置對照表
        from erp_integration.models import CompanyConfig
        company_configs = {}
        for config in CompanyConfig.objects.all():
            company_configs[config.company_code] = config.company_name
        
        # 作業員待審核記錄
        operator_pending = OperatorSupplementReport.objects.select_related(
            'operator', 'workorder', 'process'
        ).filter(approval_status='pending').order_by('-work_date', '-start_time')
        
        for report in operator_pending:
            # 獲取公司名稱
            company_name = '-'
            if report.workorder and report.workorder.company_code:
                company_name = company_configs.get(report.workorder.company_code, report.workorder.company_code)
            elif hasattr(report, 'company_code') and report.company_code:
                company_name = company_configs.get(report.company_code, report.company_code)
            
            pending_reports.append({
                'report_id': report.id,
                'report_type': '作業員報工',
                'work_date': report.work_date,
                'company_name': company_name,
                'operator_name': report.operator.name if report.operator else '-',
                'workorder_number': report.workorder.order_number if report.workorder else (report.original_workorder_number if report.original_workorder_number else '-'),
                'process_name': report.process.name if report.process else '-',
                'work_quantity': report.work_quantity,
                'defect_quantity': report.defect_quantity,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'abnormal_notes': report.abnormal_notes,
                'remarks': report.remarks,
            })
        
        # SMT待審核記錄
        smt_pending = SMTProductionReport.objects.select_related(
            'workorder'
        ).filter(approval_status='pending').order_by('-work_date', '-start_time')
        
        for report in smt_pending:
            # 獲取公司名稱
            company_name = '-'
            if report.workorder and report.workorder.company_code:
                company_name = company_configs.get(report.workorder.company_code, report.workorder.company_code)
            elif hasattr(report, 'company_code') and report.company_code:
                company_name = company_configs.get(report.company_code, report.company_code)
            
            pending_reports.append({
                'report_id': report.id,
                'report_type': 'SMT報工',
                'work_date': report.work_date,
                'company_name': company_name,
                'operator_name': report.equipment_name if report.equipment_name else '-',
                'workorder_number': report.workorder.order_number if report.workorder else (report.original_workorder_number if report.original_workorder_number else '-'),
                'process_name': 'SMT',
                'work_quantity': report.work_quantity,
                'defect_quantity': report.defect_quantity,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'abnormal_notes': report.abnormal_notes,
                'remarks': report.remarks,
            })
        
        # 移除主管待審核記錄 - 主管不應該有報工記錄
        
        # 按時間排序
        pending_reports.sort(key=lambda x: (x['work_date'], x['start_time']), reverse=True)
        
        return pending_reports


class SupervisorAbnormalService:
    """主管異常處理服務 (Supervisor Abnormal Service)"""
    
    @staticmethod
    def get_recent_abnormal_records(limit=10):
        """
        獲取最近異常記錄 (Get Recent Abnormal Records)
        """
        recent_abnormal_records = []
        
        # 作業員異常記錄
        operator_abnormal_records = OperatorSupplementReport.objects.select_related(
            'operator', 'workorder', 'process'
        ).filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).order_by('-work_date', '-start_time')[:limit//3]
        
        for report in operator_abnormal_records:
            recent_abnormal_records.append({
                'report_type': '作業員報工',
                'work_date': report.work_date,
                'operator_name': report.operator.name if report.operator else '-',
                'workorder_number': report.workorder.order_number if report.workorder else '-',
                'process_name': report.process.name if report.process else '-',
                'abnormal_notes': report.abnormal_notes,
                'approval_status': report.approval_status,
            })
        
        # SMT異常記錄
        smt_abnormal_records = SMTProductionReport.objects.select_related(
            'workorder'
        ).filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).order_by('-work_date', '-start_time')[:limit//3]
        
        for report in smt_abnormal_records:
            recent_abnormal_records.append({
                'report_type': 'SMT報工',
                'work_date': report.work_date,
                'operator_name': report.equipment_name if report.equipment_name else '-',
                'workorder_number': report.workorder.order_number if report.workorder else '-',
                'process_name': 'SMT',
                'abnormal_notes': report.abnormal_notes,
                'approval_status': report.approval_status,
            })
        
        # 移除主管異常記錄 - 主管不應該有報工記錄
        
        # 按時間排序
        recent_abnormal_records.sort(key=lambda x: x['work_date'], reverse=True)
        recent_abnormal_records = recent_abnormal_records[:limit]
        
        return recent_abnormal_records 