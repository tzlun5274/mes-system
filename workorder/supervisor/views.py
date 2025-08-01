"""
主管功能子模組視圖
整合所有主管相關功能，包含審核管理、統計分析、異常處理、資料維護等
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import date, timedelta
import json
import logging

# 導入工單模組的模型
from workorder.models import (
    OperatorSupplementReport, 
    SMTProductionReport, 
    SupervisorProductionReport,
    WorkOrder,
    WorkOrderProcess
)

logger = logging.getLogger(__name__)

def get_supervisor_statistics():
    """
    統一的主管功能統計數據生成函數
    返回所有主管功能頁面需要的統計數據
    """
    today = date.today()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    year_start = today.replace(month=1, day=1)
    
    # 基礎統計數據
    stats = {
        # 今日統計
        'total_reports_today': 0,
        'operator_reports_today': OperatorSupplementReport.objects.filter(work_date=today).count(),
        'smt_reports_today': SMTProductionReport.objects.filter(work_date=today).count(),
        'supervisor_reports_today': SupervisorProductionReport.objects.filter(work_date=today).count(),
        
        # 本週統計
        'total_reports_week': 0,
        'operator_reports_week': OperatorSupplementReport.objects.filter(work_date__gte=week_start).count(),
        'smt_reports_week': SMTProductionReport.objects.filter(work_date__gte=week_start).count(),
        'supervisor_reports_week': SupervisorProductionReport.objects.filter(work_date__gte=week_start).count(),
        
        # 本月統計
        'total_reports_month': 0,
        'operator_reports_month': OperatorSupplementReport.objects.filter(work_date__gte=month_start).count(),
        'smt_reports_month': SMTProductionReport.objects.filter(work_date__gte=month_start).count(),
        'supervisor_reports_month': SupervisorProductionReport.objects.filter(work_date__gte=month_start).count(),
        
        # 今年統計
        'total_reports_year': 0,
        'operator_reports_year': OperatorSupplementReport.objects.filter(work_date__gte=year_start).count(),
        'smt_reports_year': SMTProductionReport.objects.filter(work_date__gte=year_start).count(),
        'supervisor_reports_year': SupervisorProductionReport.objects.filter(work_date__gte=year_start).count(),
        
        # 待審核統計
        'pending_reports': 0,
        'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
        'pending_supervisor': SupervisorProductionReport.objects.filter(approval_status='pending').count(),
        
        # 異常統計
        'abnormal_reports': 0,
        'abnormal_operator': OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_smt': SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_supervisor': SupervisorProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        
        # 審核狀態統計
        'approved_operator': OperatorSupplementReport.objects.filter(approval_status='approved').count(),
        'approved_smt': SMTProductionReport.objects.filter(approval_status='approved').count(),
        'approved_supervisor': SupervisorProductionReport.objects.filter(approval_status='approved').count(),
        
        'rejected_operator': OperatorSupplementReport.objects.filter(approval_status='rejected').count(),
        'rejected_smt': SMTProductionReport.objects.filter(approval_status='rejected').count(),
        'rejected_supervisor': SupervisorProductionReport.objects.filter(approval_status='rejected').count(),
    }
    
    # 計算總計
    stats['total_reports_today'] = stats['operator_reports_today'] + stats['smt_reports_today'] + stats['supervisor_reports_today']
    stats['total_reports_week'] = stats['operator_reports_week'] + stats['smt_reports_week'] + stats['supervisor_reports_week']
    stats['total_reports_month'] = stats['operator_reports_month'] + stats['smt_reports_month'] + stats['supervisor_reports_month']
    stats['total_reports_year'] = stats['operator_reports_year'] + stats['smt_reports_year'] + stats['supervisor_reports_year']
    stats['pending_reports'] = stats['pending_operator'] + stats['pending_smt'] + stats['pending_supervisor']
    stats['abnormal_reports'] = stats['abnormal_operator'] + stats['abnormal_smt'] + stats['abnormal_supervisor']
    
    # 計算平均值
    days_in_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - today.replace(day=1)
    days_in_month = days_in_month.days
    
    stats['avg_daily_reports'] = round(stats['total_reports_month'] / days_in_month, 1) if days_in_month > 0 else 0
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
    
    critical_supervisor = SupervisorProductionReport.objects.filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan') &
        (Q(abnormal_notes__icontains='嚴重') | Q(abnormal_notes__icontains='緊急') | Q(abnormal_notes__icontains='停機'))
    ).count()
    
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
        'total_supervisor_reports': SupervisorProductionReport.objects.count(),
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

@login_required
def supervisor_functions(request):
    """
    主管功能首頁 - 主管專用功能
    包含報工統計、異常處理、系統設定等功能
    """
    # 使用統一的統計數據生成函數
    context_data = get_supervisor_statistics()
    
    # 取得最近異常記錄
    recent_abnormal = []
    
    # 作業員異常
    operator_abnormal = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')[:5]
    
    for report in operator_abnormal:
        recent_abnormal.append({
            'type': '作業員報工',
            'time': report.work_date,
            'operator': report.operator.name if report.operator else '-',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process.name if report.process else '-',
            'remarks': report.abnormal_notes,
            'status': report.approval_status,
        })
    
    # SMT異常
    smt_abnormal = SMTProductionReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')[:5]
    
    for report in smt_abnormal:
        recent_abnormal.append({
            'type': 'SMT報工',
            'time': report.work_date,
            'operator': report.equipment_name if report.equipment_name else '-',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': 'SMT',
            'remarks': report.abnormal_notes,
            'status': report.approval_status,
        })
    
    # 主管異常
    supervisor_abnormal = SupervisorProductionReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')[:5]
    
    for report in supervisor_abnormal:
        recent_abnormal.append({
            'type': '主管報工',
            'time': report.work_date,
            'operator': report.operator_name if report.operator_name else '-',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process_name if report.process_name else '-',
            'remarks': report.abnormal_notes,
            'status': report.approval_status,
        })
    
    # 按時間排序
    recent_abnormal.sort(key=lambda x: x['time'], reverse=True)
    recent_abnormal = recent_abnormal[:10]  # 只取前10筆
    
    context = {
        **context_data,
        'recent_abnormal': recent_abnormal,
    }
    
    return render(request, 'supervisor/index.html', context)


@login_required
def supervisor_report_index(request):
    """
    主管報工管理首頁 - 重定向到待審核清單
    """
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def pending_approval_list(request):
    """
    待審核報工清單
    """
    # 獲取所有待審核的報工記錄
    pending_reports = OperatorSupplementReport.objects.filter(
        approval_status='pending'
    ).select_related('operator', 'workorder', 'process').order_by('-work_date', '-start_time')
    
    # 分頁
    paginator = Paginator(pending_reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_pending': pending_reports.count(),
    }
    
    return render(request, 'supervisor/pending_approval_list.html', context)


@login_required
def approve_report(request, report_id):
    """
    審核通過報工記錄
    """
    if request.method == 'POST':
        report = get_object_or_404(OperatorSupplementReport, id=report_id)
        report.approval_status = 'approved'
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        
        messages.success(request, f'報工記錄 {report.id} 已審核通過')
        return redirect('workorder:supervisor:pending_approval_list')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def reject_report(request, report_id):
    """
    拒絕報工記錄
    """
    if request.method == 'POST':
        report = get_object_or_404(OperatorSupplementReport, id=report_id)
        report.approval_status = 'rejected'
        report.rejected_by = request.user.username
        report.rejected_at = timezone.now()
        report.rejection_reason = request.POST.get('rejection_reason', '')
        report.save()
        
        messages.warning(request, f'報工記錄 {report.id} 已被拒絕')
        return redirect('workorder:supervisor:pending_approval_list')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def batch_approve_reports(request):
    """
    批次審核報工記錄
    """
    if request.method == 'POST':
        report_ids = request.POST.getlist('report_ids')
        approved_count = 0
        
        for report_id in report_ids:
            try:
                report = OperatorSupplementReport.objects.get(id=report_id)
                report.approval_status = 'approved'
                report.approved_by = request.user.username
                report.approved_at = timezone.now()
                report.save()
                approved_count += 1
            except OperatorSupplementReport.DoesNotExist:
                continue
        
        messages.success(request, f'成功審核 {approved_count} 筆報工記錄')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def report_statistics(request):
    """
    報工統計分析
    """
    # 使用統一的統計數據生成函數
    context_data = get_supervisor_statistics()
    
    # 取得詳細統計數據
    today = date.today()
    month_start = today.replace(day=1)
    
    # 作業員報工趨勢（最近7天）
    operator_trend = []
    for i in range(7):
        check_date = today - timedelta(days=i)
        count = OperatorSupplementReport.objects.filter(work_date=check_date).count()
        operator_trend.append({
            'date': check_date.strftime('%m-%d'),
            'count': count
        })
    operator_trend.reverse()
    
    # SMT報工趨勢（最近7天）
    smt_trend = []
    for i in range(7):
        check_date = today - timedelta(days=i)
        count = SMTProductionReport.objects.filter(work_date=check_date).count()
        smt_trend.append({
            'date': check_date.strftime('%m-%d'),
            'count': count
        })
    smt_trend.reverse()
    
    # 審核狀態分布
    approval_distribution = {
        'pending': context_data['stats']['pending_reports'],
        'approved': context_data['stats']['approved_operator'] + context_data['stats']['approved_smt'] + context_data['stats']['approved_supervisor'],
        'rejected': context_data['stats']['rejected_operator'] + context_data['stats']['rejected_smt'] + context_data['stats']['rejected_supervisor'],
    }
    
    context = {
        **context_data,
        'operator_trend': operator_trend,
        'smt_trend': smt_trend,
        'approval_distribution': approval_distribution,
    }
    
    return render(request, 'supervisor/statistics.html', context)


@login_required
def abnormal_management(request):
    """
    異常處理管理
    """
    # 使用統一的統計數據生成函數
    context_data = get_supervisor_statistics()
    
    # 取得異常記錄
    operator_abnormal = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')
    
    smt_abnormal = SMTProductionReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')
    
    supervisor_abnormal = SupervisorProductionReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')
    
    context = {
        **context_data,
        'operator_abnormal': operator_abnormal,
        'smt_abnormal': smt_abnormal,
        'supervisor_abnormal': supervisor_abnormal,
    }
    
    return render(request, 'supervisor/abnormal.html', context)


@login_required
def data_maintenance(request):
    """
    資料維護管理
    """
    # 使用統一的統計數據生成函數
    context_data = get_supervisor_statistics()
    
    # 取得維護日誌（模擬數據）
    maintenance_logs = [
        {
            'timestamp': '2025-01-01 06:00:00',
            'action': '資料庫備份',
            'status': '成功',
            'details': '完成每日自動備份，備份大小：2.5GB'
        },
        {
            'timestamp': '2025-01-01 05:30:00',
            'action': '資料庫優化',
            'status': '成功',
            'details': '完成索引優化，查詢效能提升15%'
        },
        {
            'timestamp': '2024-12-31 23:00:00',
            'action': '清理舊資料',
            'status': '成功',
            'details': '清理90天前資料，釋放空間：500MB'
        },
    ]
    
    context = {
        **context_data,
        'maintenance_logs': maintenance_logs,
    }
    
    return render(request, 'supervisor/maintenance.html', context)


@login_required
def execute_maintenance(request):
    """
    執行資料維護
    """
    if request.method == 'POST':
        maintenance_type = request.POST.get('maintenance_type')
        
        if maintenance_type == 'clean_old_data':
            # 清理舊資料
            cutoff_date = date.today() - timedelta(days=365)  # 一年前的資料
            deleted_count = OperatorSupplementReport.objects.filter(work_date__lt=cutoff_date).delete()[0]
            messages.success(request, f'已清理 {deleted_count} 筆舊報工記錄')
            
        elif maintenance_type == 'fix_approval_status':
            # 修復審核狀態
            fixed_count = 0
            reports = OperatorSupplementReport.objects.filter(approval_status__isnull=True)
            for report in reports:
                report.approval_status = 'pending'
                report.save()
                fixed_count += 1
            messages.success(request, f'已修復 {fixed_count} 筆報工記錄的審核狀態')
            
        elif maintenance_type == 'update_statistics':
            # 更新統計資料
            messages.success(request, '統計資料已更新')
            
        else:
            messages.error(request, '無效的維護類型')
    
    return redirect('workorder:supervisor:data_maintenance')


@login_required
def abnormal_detail(request, abnormal_type, abnormal_id):
    """
    異常詳情查看
    """
    if abnormal_type == 'operator':
        report = get_object_or_404(OperatorSupplementReport, id=abnormal_id)
    elif abnormal_type == 'smt':
        report = get_object_or_404(SMTProductionReport, id=abnormal_id)
    elif abnormal_type == 'supervisor':
        report = get_object_or_404(SupervisorProductionReport, id=abnormal_id)
    else:
        messages.error(request, '無效的異常類型')
        return redirect('workorder:supervisor:abnormal_management')
    
    context = {
        'report': report,
        'abnormal_type': abnormal_type,
    }
    
    return render(request, 'supervisor/abnormal_detail.html', context) 