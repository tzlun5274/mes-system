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

@login_required
def supervisor_functions(request):
    """
    主管功能首頁 - 主管專用功能
    包含報工統計、異常處理、系統設定等功能
    """
    today = date.today()
    month_start = today.replace(day=1)
    
    # 統計資訊
    stats = {
        # 報工統計
        'total_reports_today': 0,
        'total_reports_month': 0,
        'pending_reports': 0,
        'abnormal_reports': 0,
        
        # 各類型統計
        'operator_reports_today': OperatorSupplementReport.objects.filter(work_date=today).count(),
        'smt_reports_today': SMTProductionReport.objects.filter(work_date=today).count(),
        'supervisor_reports_today': SupervisorProductionReport.objects.filter(work_date=today).count(),
        
        'operator_reports_month': OperatorSupplementReport.objects.filter(work_date__gte=month_start).count(),
        'smt_reports_month': SMTProductionReport.objects.filter(work_date__gte=month_start).count(),
        'supervisor_reports_month': SupervisorProductionReport.objects.filter(work_date__gte=month_start).count(),
        
        # 待審核統計
        'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
        'pending_supervisor': SupervisorProductionReport.objects.filter(approval_status='pending').count(),
        
        # 異常統計
        'abnormal_operator': OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_smt': SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_supervisor': SupervisorProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
    }
    
    # 計算總計
    stats['total_reports_today'] = stats['operator_reports_today'] + stats['smt_reports_today'] + stats['supervisor_reports_today']
    stats['total_reports_month'] = stats['operator_reports_month'] + stats['smt_reports_month'] + stats['supervisor_reports_month']
    stats['pending_reports'] = stats['pending_operator'] + stats['pending_smt'] + stats['pending_supervisor']
    stats['abnormal_reports'] = stats['abnormal_operator'] + stats['abnormal_smt'] + stats['abnormal_supervisor']
    
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
        'stats': stats,
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
    today = date.today()
    month_start = today.replace(day=1)
    
    # 統計資訊
    stats = {
        'total_reports_today': 0,
        'total_reports_month': 0,
        'pending_reports': 0,
        'abnormal_reports': 0,
        
        'operator_reports_today': OperatorSupplementReport.objects.filter(work_date=today).count(),
        'smt_reports_today': SMTProductionReport.objects.filter(work_date=today).count(),
        'supervisor_reports_today': SupervisorProductionReport.objects.filter(work_date=today).count(),
        
        'operator_reports_month': OperatorSupplementReport.objects.filter(work_date__gte=month_start).count(),
        'smt_reports_month': SMTProductionReport.objects.filter(work_date__gte=month_start).count(),
        'supervisor_reports_month': SupervisorProductionReport.objects.filter(work_date__gte=month_start).count(),
        
        'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
        'pending_supervisor': SupervisorProductionReport.objects.filter(approval_status='pending').count(),
        
        'abnormal_operator': OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_smt': SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_supervisor': SupervisorProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
    }
    
    # 計算總計
    stats['total_reports_today'] = stats['operator_reports_today'] + stats['smt_reports_today'] + stats['supervisor_reports_today']
    stats['total_reports_month'] = stats['operator_reports_month'] + stats['smt_reports_month'] + stats['supervisor_reports_month']
    stats['pending_reports'] = stats['pending_operator'] + stats['pending_smt'] + stats['pending_supervisor']
    stats['abnormal_reports'] = stats['abnormal_operator'] + stats['abnormal_smt'] + stats['abnormal_supervisor']
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'supervisor/statistics.html', context)


@login_required
def abnormal_management(request):
    """
    異常處理管理
    """
    today = date.today()
    month_start = today.replace(day=1)
    
    # 統計資訊
    stats = {
        'total_reports_today': 0,
        'total_reports_month': 0,
        'pending_reports': 0,
        'abnormal_reports': 0,
        
        'operator_reports_today': OperatorSupplementReport.objects.filter(work_date=today).count(),
        'smt_reports_today': SMTProductionReport.objects.filter(work_date=today).count(),
        'supervisor_reports_today': SupervisorProductionReport.objects.filter(work_date=today).count(),
        
        'operator_reports_month': OperatorSupplementReport.objects.filter(work_date__gte=month_start).count(),
        'smt_reports_month': SMTProductionReport.objects.filter(work_date__gte=month_start).count(),
        'supervisor_reports_month': SupervisorProductionReport.objects.filter(work_date__gte=month_start).count(),
        
        'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
        'pending_supervisor': SupervisorProductionReport.objects.filter(approval_status='pending').count(),
        
        'abnormal_operator': OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_smt': SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_supervisor': SupervisorProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
    }
    
    # 計算總計
    stats['total_reports_today'] = stats['operator_reports_today'] + stats['smt_reports_today'] + stats['supervisor_reports_today']
    stats['total_reports_month'] = stats['operator_reports_month'] + stats['smt_reports_month'] + stats['supervisor_reports_month']
    stats['pending_reports'] = stats['pending_operator'] + stats['pending_smt'] + stats['pending_supervisor']
    stats['abnormal_reports'] = stats['abnormal_operator'] + stats['abnormal_smt'] + stats['abnormal_supervisor']
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'supervisor/abnormal.html', context)


@login_required
def data_maintenance(request):
    """
    資料維護管理
    """
    today = date.today()
    month_start = today.replace(day=1)
    
    # 統計資訊
    stats = {
        'total_reports_today': 0,
        'total_reports_month': 0,
        'pending_reports': 0,
        'abnormal_reports': 0,
        
        'operator_reports_today': OperatorSupplementReport.objects.filter(work_date=today).count(),
        'smt_reports_today': SMTProductionReport.objects.filter(work_date=today).count(),
        'supervisor_reports_today': SupervisorProductionReport.objects.filter(work_date=today).count(),
        
        'operator_reports_month': OperatorSupplementReport.objects.filter(work_date__gte=month_start).count(),
        'smt_reports_month': SMTProductionReport.objects.filter(work_date__gte=month_start).count(),
        'supervisor_reports_month': SupervisorProductionReport.objects.filter(work_date__gte=month_start).count(),
        
        'pending_operator': OperatorSupplementReport.objects.filter(approval_status='pending').count(),
        'pending_smt': SMTProductionReport.objects.filter(approval_status='pending').count(),
        'pending_supervisor': SupervisorProductionReport.objects.filter(approval_status='pending').count(),
        
        'abnormal_operator': OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_smt': SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
        'abnormal_supervisor': SupervisorProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
        ).count(),
    }
    
    # 計算總計
    stats['total_reports_today'] = stats['operator_reports_today'] + stats['smt_reports_today'] + stats['supervisor_reports_today']
    stats['total_reports_month'] = stats['operator_reports_month'] + stats['smt_reports_month'] + stats['supervisor_reports_month']
    stats['pending_reports'] = stats['pending_operator'] + stats['pending_smt'] + stats['pending_supervisor']
    stats['abnormal_reports'] = stats['abnormal_operator'] + stats['abnormal_smt'] + stats['abnormal_supervisor']
    
    context = {
        'stats': stats,
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