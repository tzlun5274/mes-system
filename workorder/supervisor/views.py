"""
主管功能子模組視圖
整合所有主管相關功能，包含審核管理、統計分析、異常處理、資料維護等
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
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
    WorkOrder,
    WorkOrderProcess
)
from workorder.workorder_reporting.models import SupervisorProductionReport

# 導入主管功能服務層
from .services import SupervisorStatisticsService, SupervisorApprovalService, SupervisorAbnormalService

logger = logging.getLogger(__name__)

def get_supervisor_statistics():
    """
    統一的主管功能統計數據生成函數 (Supervisor Statistics Generator)
    返回所有主管功能頁面需要的統計數據
    """
    return SupervisorStatisticsService.get_supervisor_statistics()
    
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
    主管功能首頁視圖 (Supervisor Functions Homepage View)
    提供主管功能的主要入口和統計概覽
    """
    """
    主管功能首頁 - 主管專用功能
    包含報工統計、異常處理、系統設定等功能
    """
    # 使用統一的統計數據生成函數
    context_data = get_supervisor_statistics()
    
    # 取得最近異常記錄 (Recent Abnormal Records)
    recent_abnormal_records = []
    
    # 作業員異常記錄 (Operator Abnormal Records)
    operator_abnormal_records = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')[:5]
    
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
    
    # SMT異常記錄 (SMT Abnormal Records)
    smt_abnormal_records = SMTProductionReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')[:5]
    
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
    
    # 主管異常記錄 (Supervisor Abnormal Records)
    supervisor_abnormal_records = SupervisorProductionReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')[:5]
    
    for report in supervisor_abnormal_records:
        recent_abnormal_records.append({
            'report_type': '主管報工',
            'work_date': report.work_date,
            'operator_name': report.operator_name if report.operator_name else '-',
            'workorder_number': report.workorder.order_number if report.workorder else '-',
            'process_name': report.process_name if report.process_name else '-',
            'abnormal_notes': report.abnormal_notes,
            'approval_status': report.approval_status,
        })
    
    # 按時間排序 (Sort by Date)
    recent_abnormal_records.sort(key=lambda x: x['work_date'], reverse=True)
    recent_abnormal_records = recent_abnormal_records[:10]  # 只取前10筆
    
    context = {
        **context_data,
        'recent_abnormal_records': recent_abnormal_records,
    }
    
    return render(request, 'supervisor/functions.html', context)


@login_required
def supervisor_report_index(request):
    """
    主管報表首頁視圖 (Supervisor Report Index View)
    提供主管報表功能的主要入口
    """
    """
    主管報工管理首頁 - 審核管理總覽
    """
    # 使用統一的統計數據生成函數
    context_data = get_supervisor_statistics()
    
    # 獲取最近的審核記錄
    recent_reviews = []
    
    # 最近已審核的作業員報工
    recent_approved_operator = OperatorSupplementReport.objects.filter(
        approval_status='approved'
    ).select_related('operator', 'workorder', 'process').order_by('-approved_at')[:5]
    
    for report in recent_approved_operator:
        recent_reviews.append({
            'type': '作業員報工',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process.name if report.process else '-',
            'quantity': report.work_quantity,
            'reviewer': report.approved_by,
            'time': report.approved_at,
            'status': '已審核'
        })
    
    # 最近已審核的SMT報工
    recent_approved_smt = SMTProductionReport.objects.filter(
        approval_status='approved'
    ).select_related('workorder').order_by('-approved_at')[:5]
    
    for report in recent_approved_smt:
        recent_reviews.append({
            'type': 'SMT報工',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': 'SMT',
            'quantity': report.work_quantity,
            'reviewer': report.approved_by,
            'time': report.approved_at,
            'status': '已審核'
        })
    
    # 最近已審核的主管報工
    recent_approved_supervisor = SupervisorProductionReport.objects.filter(
        approval_status='approved'
    ).select_related('workorder').order_by('-approved_at')[:5]
    
    for report in recent_approved_supervisor:
        recent_reviews.append({
            'type': '主管報工',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process_name if report.process_name else '-',
            'quantity': report.work_quantity,
            'reviewer': report.approved_by,
            'time': report.approved_at,
            'status': '已審核'
        })
    
    # 最近被拒絕的報工
    recent_rejected = []
    
    recent_rejected_operator = OperatorSupplementReport.objects.filter(
        approval_status='rejected'
    ).select_related('operator', 'workorder', 'process').order_by('-rejected_at')[:3]
    
    for report in recent_rejected_operator:
        recent_rejected.append({
            'type': '作業員報工',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process.name if report.process else '-',
            'quantity': report.work_quantity,
            'reviewer': report.rejected_by,
            'time': report.rejected_at,
            'status': '已拒絕',
            'reason': report.rejection_reason
        })
    
    # 按時間排序
    recent_reviews.sort(key=lambda x: x['time'], reverse=True)
    recent_reviews = recent_reviews[:10]  # 只取前10筆
    
    recent_rejected.sort(key=lambda x: x['time'], reverse=True)
    recent_rejected = recent_rejected[:5]  # 只取前5筆
    
    context = {
        **context_data,
        'recent_reviews': recent_reviews,
        'recent_rejected': recent_rejected,
    }
    
    return render(request, 'supervisor/report_management.html', context)


@login_required
def pending_approval_list(request):
    """
    待審核清單視圖 (Pending Approval List View)
    顯示所有待審核的報工記錄（包含作業員報工、SMT報工、主管報工）
    """
    # 使用 SupervisorApprovalService 獲取所有待審核的報工記錄
    from .services import SupervisorApprovalService
    pending_reports = SupervisorApprovalService.get_pending_approval_reports()
    
    # 分頁
    paginator = Paginator(pending_reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_pending': len(pending_reports),
    }
    
    return render(request, 'supervisor/pending_approval_list.html', context)


@login_required
def report_detail(request, report_id):
    """
    報工記錄詳情視圖 (Report Detail View)
    顯示單一報工記錄的詳細資訊（支援作業員報工、SMT報工、主管報工）
    """
    # 嘗試從作業員報工中查找
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
        report_type = '作業員報工'
    except OperatorSupplementReport.DoesNotExist:
        # 嘗試從SMT報工中查找
        try:
            from workorder.workorder_reporting.models import SMTProductionReport
            report = SMTProductionReport.objects.get(id=report_id)
            report_type = 'SMT報工'
        except SMTProductionReport.DoesNotExist:
            # 嘗試從主管報工中查找
            try:
                from workorder.workorder_reporting.models import SupervisorProductionReport
                report = SupervisorProductionReport.objects.get(id=report_id)
                report_type = '主管報工'
            except SupervisorProductionReport.DoesNotExist:
                raise Http404("報工記錄不存在")
    
    context = {
        'report': report,
        'report_type': report_type,
    }
    
    return render(request, 'supervisor/report_detail.html', context)


@login_required
def approve_report(request, report_id):
    """
    核准報工記錄視圖 (Approve Report View)
    處理報工記錄的核准操作
    """
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
    駁回報工記錄視圖 (Reject Report View)
    處理報工記錄的駁回操作
    """
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
def approve_smt_report(request, report_id):
    """
    核准SMT報工記錄視圖 (Approve SMT Report View)
    處理SMT報工記錄的核准操作
    """
    if request.method == 'POST':
        from workorder.workorder_reporting.models import SMTProductionReport
        report = get_object_or_404(SMTProductionReport, id=report_id)
        report.approval_status = 'approved'
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        
        messages.success(request, f'SMT報工記錄 {report.id} 已審核通過')
        return redirect('workorder:supervisor:pending_approval_list')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def reject_smt_report(request, report_id):
    """
    駁回SMT報工記錄視圖 (Reject SMT Report View)
    處理SMT報工記錄的駁回操作
    """
    if request.method == 'POST':
        from workorder.workorder_reporting.models import SMTProductionReport
        report = get_object_or_404(SMTProductionReport, id=report_id)
        report.approval_status = 'rejected'
        report.rejected_by = request.user.username
        report.rejected_at = timezone.now()
        report.rejection_reason = request.POST.get('rejection_reason', '')
        report.save()
        
        messages.warning(request, f'SMT報工記錄 {report.id} 已被拒絕')
        return redirect('workorder:supervisor:pending_approval_list')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def approve_supervisor_report(request, report_id):
    """
    核准主管報工記錄視圖 (Approve Supervisor Report View)
    處理主管報工記錄的核准操作
    """
    if request.method == 'POST':
        from workorder.workorder_reporting.models import SupervisorProductionReport
        report = get_object_or_404(SupervisorProductionReport, id=report_id)
        report.approval_status = 'approved'
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        
        messages.success(request, f'主管報工記錄 {report.id} 已審核通過')
        return redirect('workorder:supervisor:pending_approval_list')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def reject_supervisor_report(request, report_id):
    """
    駁回主管報工記錄視圖 (Reject Supervisor Report View)
    處理主管報工記錄的駁回操作
    """
    if request.method == 'POST':
        from workorder.workorder_reporting.models import SupervisorProductionReport
        report = get_object_or_404(SupervisorProductionReport, id=report_id)
        report.approval_status = 'rejected'
        report.rejected_by = request.user.username
        report.rejected_at = timezone.now()
        report.rejection_reason = request.POST.get('rejection_reason', '')
        report.save()
        
        messages.warning(request, f'主管報工記錄 {report.id} 已被拒絕')
        return redirect('workorder:supervisor:pending_approval_list')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def batch_approve_reports(request):
    """
    批量核准報工記錄視圖 (Batch Approve Reports View)
    處理批量核准報工記錄的操作（支援作業員報工、SMT報工、主管報工）
    """
    if request.method == 'POST':
        report_ids = request.POST.getlist('report_ids')
        approved_count = 0
        
        for report_id in report_ids:
            try:
                # 嘗試從作業員報工中查找
                try:
                    report = OperatorSupplementReport.objects.get(id=report_id)
                    report.approval_status = 'approved'
                    report.approved_by = request.user.username
                    report.approved_at = timezone.now()
                    report.save()
                    approved_count += 1
                    continue
                except OperatorSupplementReport.DoesNotExist:
                    pass
                
                # 嘗試從SMT報工中查找
                try:
                    from workorder.workorder_reporting.models import SMTProductionReport
                    report = SMTProductionReport.objects.get(id=report_id)
                    report.approval_status = 'approved'
                    report.approved_by = request.user.username
                    report.approved_at = timezone.now()
                    report.save()
                    approved_count += 1
                    continue
                except SMTProductionReport.DoesNotExist:
                    pass
                
                # 嘗試從主管報工中查找
                try:
                    from workorder.workorder_reporting.models import SupervisorProductionReport
                    report = SupervisorProductionReport.objects.get(id=report_id)
                    report.approval_status = 'approved'
                    report.approved_by = request.user.username
                    report.approved_at = timezone.now()
                    report.save()
                    approved_count += 1
                    continue
                except SupervisorProductionReport.DoesNotExist:
                    pass
                
            except Exception as e:
                continue
        
        messages.success(request, f'成功審核 {approved_count} 筆報工記錄')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def batch_delete_reports(request):
    """
    批量刪除報工記錄視圖 (Batch Delete Reports View)
    處理批量刪除報工記錄的操作
    """
    if request.method == 'POST':
        report_ids = request.POST.getlist('report_ids')
        deleted_count = 0
        
        for report_id in report_ids:
            try:
                report = OperatorSupplementReport.objects.get(id=report_id)
                report.delete()
                deleted_count += 1
            except OperatorSupplementReport.DoesNotExist:
                continue
        
        messages.success(request, f'成功刪除 {deleted_count} 筆報工記錄')
    
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
def report_statistics(request):
    """
    報表統計分析視圖 (Report Statistics View)
    提供報工記錄的統計分析功能
    """
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
    異常管理視圖 (Abnormal Management View)
    提供異常報工記錄的管理功能
    """
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
    
    # 計算異常統計數據
    total_operator_abnormal = operator_abnormal.count()
    total_smt_abnormal = smt_abnormal.count()
    total_supervisor_abnormal = supervisor_abnormal.count()
    
    # 計算嚴重異常（包含關鍵字的異常）
    critical_keywords = ['嚴重', '緊急', '停機', '故障', '錯誤']
    critical_operator = operator_abnormal.filter(
        Q(abnormal_notes__icontains='嚴重') | 
        Q(abnormal_notes__icontains='緊急') | 
        Q(abnormal_notes__icontains='停機') | 
        Q(abnormal_notes__icontains='故障') | 
        Q(abnormal_notes__icontains='錯誤')
    ).count()
    
    critical_smt = smt_abnormal.filter(
        Q(abnormal_notes__icontains='嚴重') | 
        Q(abnormal_notes__icontains='緊急') | 
        Q(abnormal_notes__icontains='停機') | 
        Q(abnormal_notes__icontains='故障') | 
        Q(abnormal_notes__icontains='錯誤')
    ).count()
    
    critical_supervisor = supervisor_abnormal.filter(
        Q(abnormal_notes__icontains='嚴重') | 
        Q(abnormal_notes__icontains='緊急') | 
        Q(abnormal_notes__icontains='停機') | 
        Q(abnormal_notes__icontains='故障') | 
        Q(abnormal_notes__icontains='錯誤')
    ).count()
    
    # 計算待處理和已解決的異常
    pending_operator = operator_abnormal.filter(approval_status='pending').count()
    pending_smt = smt_abnormal.filter(approval_status='pending').count()
    pending_supervisor = supervisor_abnormal.filter(approval_status='pending').count()
    
    resolved_operator = operator_abnormal.filter(approval_status='approved').count()
    resolved_smt = smt_abnormal.filter(approval_status='approved').count()
    resolved_supervisor = supervisor_abnormal.filter(approval_status='approved').count()
    
    # 彙總統計
    abnormal_stats = {
        'total_abnormal': total_operator_abnormal + total_smt_abnormal + total_supervisor_abnormal,
        'critical': critical_operator + critical_smt + critical_supervisor,
        'pending': pending_operator + pending_smt + pending_supervisor,
        'resolved': resolved_operator + resolved_smt + resolved_supervisor,
        'operator_abnormal': total_operator_abnormal,
        'smt_abnormal': total_smt_abnormal,
        'supervisor_abnormal': total_supervisor_abnormal,
    }
    
    context = {
        **context_data,
        'operator_abnormal': operator_abnormal,
        'smt_abnormal': smt_abnormal,
        'supervisor_abnormal': supervisor_abnormal,
        'abnormal_stats': abnormal_stats,
    }
    
    return render(request, 'supervisor/abnormal.html', context)


@login_required
def batch_resolve_abnormal(request):
    """
    批次解決異常視圖 (Batch Resolve Abnormal View)
    處理批次解決異常的操作
    """
    if request.method == 'POST':
        try:
            # 獲取所有待處理的異常記錄
            operator_pending = OperatorSupplementReport.objects.filter(
                Q(abnormal_notes__isnull=False) & 
                ~Q(abnormal_notes='') & 
                ~Q(abnormal_notes='nan') &
                Q(approval_status='pending')
            )
            
            smt_pending = SMTProductionReport.objects.filter(
                Q(abnormal_notes__isnull=False) & 
                ~Q(abnormal_notes='') & 
                ~Q(abnormal_notes='nan') &
                Q(approval_status='pending')
            )
            
            supervisor_pending = SupervisorProductionReport.objects.filter(
                Q(abnormal_notes__isnull=False) & 
                ~Q(abnormal_notes='') & 
                ~Q(abnormal_notes='nan') &
                Q(approval_status='pending')
            )
            
            # 批次更新狀態
            operator_resolved = operator_pending.update(
                approval_status='approved',
                approved_by=request.user.username,
                approved_at=timezone.now()
            )
            
            smt_resolved = smt_pending.update(
                approval_status='approved',
                approved_by=request.user.username,
                approved_at=timezone.now()
            )
            
            supervisor_resolved = supervisor_pending.update(
                approval_status='approved',
                approved_by=request.user.username,
                approved_at=timezone.now()
            )
            
            total_resolved = operator_resolved + smt_resolved + supervisor_resolved
            
            return JsonResponse({
                'success': True,
                'resolved_count': total_resolved,
                'operator_resolved': operator_resolved,
                'smt_resolved': smt_resolved,
                'supervisor_resolved': supervisor_resolved
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': '無效的請求方法'
    })


@login_required
def data_maintenance(request):
    """
    資料維護視圖 (Data Maintenance View)
    提供報工記錄的資料維護功能
    """
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
    執行資料維護視圖 (Execute Maintenance View)
    處理資料維護的執行操作
    """
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
    異常詳情視圖 (Abnormal Detail View)
    顯示異常報工記錄的詳細資訊
    """
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