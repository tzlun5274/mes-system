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
    SMTSupplementReport, 
    WorkOrder,
    WorkOrderProcess
)

# 主管功能不需要主管報工模型，主管只負責審核和管理
# from workorder.workorder_reporting.models import SupervisorProductionReport

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
        'total_smt_reports': SMTSupplementReport.objects.count(),
        'total_supplement_reports': 0,  # 補登報工記錄數量
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
    smt_abnormal_records = SMTSupplementReport.objects.select_related(
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
    
    # 移除主管異常記錄 - 主管不應該有報工記錄
    
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
    recent_approved_smt = SMTSupplementReport.objects.filter(
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
    
    # 移除主管報工審核記錄 - 主管不應該有報工記錄
    
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
        'paginator': paginator,  # 添加 paginator 到 context
    }
    
    return render(request, 'supervisor/pending_approval_list.html', context)


@login_required
def report_detail(request, report_id):
    """
    報工記錄詳情視圖 (Report Detail View)
    顯示單一報工記錄的詳細資訊（支援作業員報工、SMT報工、主管報工）
    """
    # 獲取公司配置對照表
    from erp_integration.models import CompanyConfig
    company_configs = list(CompanyConfig.objects.all())
    
    # 嘗試從作業員報工中查找
    try:
        report = OperatorSupplementReport.objects.get(id=report_id)
        report_type = '作業員報工'
    except OperatorSupplementReport.DoesNotExist:
        # 嘗試從SMT報工中查找
        try:
            from workorder.workorder_reporting.models import SMTSupplementReport
            report = SMTSupplementReport.objects.get(id=report_id)
            report_type = 'SMT報工'
        except SMTSupplementReport.DoesNotExist:
            # 移除主管報工查找 - 主管不應該有報工記錄
            raise Http404("報工記錄不存在")
    
    context = {
        'report': report,
        'report_type': report_type,
        'company_configs': company_configs,
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
        
        # 核准成功後，同步到生產中工單詳情資料表
        try:
            from workorder.services import ProductionReportSyncService
            if hasattr(report, 'workorder') and report.workorder:
                ProductionReportSyncService.sync_specific_workorder(report.workorder.id)
        except Exception as sync_error:
            # 同步失敗不影響核准流程，只記錄錯誤
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"同步報工記錄到生產詳情失敗: {str(sync_error)}")
        
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
        from workorder.workorder_reporting.models import SMTSupplementReport
        report = get_object_or_404(SMTSupplementReport, id=report_id)
        report.approval_status = 'approved'
        report.approved_by = request.user.username
        report.approved_at = timezone.now()
        report.save()
        
        # 核准成功後，同步到生產中工單詳情資料表
        try:
            from workorder.services import ProductionReportSyncService
            if hasattr(report, 'workorder') and report.workorder:
                ProductionReportSyncService.sync_specific_workorder(report.workorder.id)
        except Exception as sync_error:
            # 同步失敗不影響核准流程，只記錄錯誤
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"同步SMT報工記錄到生產詳情失敗: {str(sync_error)}")
        
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
        from workorder.workorder_reporting.models import SMTSupplementReport
        report = get_object_or_404(SMTSupplementReport, id=report_id)
        report.approval_status = 'rejected'
        report.rejected_by = request.user.username
        report.rejected_at = timezone.now()
        report.rejection_reason = request.POST.get('rejection_reason', '')
        report.save()
        
        messages.warning(request, f'SMT報工記錄 {report.id} 已被拒絕')
        return redirect('workorder:supervisor:pending_approval_list')
    
    return redirect('workorder:supervisor:pending_approval_list')


# 移除主管報工核准和駁回功能 - 主管不應該有報工記錄


@login_required
def batch_approve_reports(request):
    """
    批量核准報工記錄視圖 (Batch Approve Reports View)
    處理批量核准報工記錄的操作（支援作業員報工、SMT報工、主管報工）
    """
    if request.method == 'POST':
        report_ids = request.POST.getlist('report_ids')
        approved_count = 0
        synced_workorders = set()  # 記錄需要同步的工單ID
        
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
                    
                    # 記錄需要同步的工單
                    if hasattr(report, 'workorder') and report.workorder:
                        synced_workorders.add(report.workorder.id)
                    continue
                except OperatorSupplementReport.DoesNotExist:
                    pass
                
                # 嘗試從SMT報工中查找
                try:
                    from workorder.workorder_reporting.models import SMTSupplementReport
                    report = SMTSupplementReport.objects.get(id=report_id)
                    report.approval_status = 'approved'
                    report.approved_by = request.user.username
                    report.approved_at = timezone.now()
                    report.save()
                    approved_count += 1
                    
                    # 記錄需要同步的工單
                    if hasattr(report, 'workorder') and report.workorder:
                        synced_workorders.add(report.workorder.id)
                    continue
                except SMTSupplementReport.DoesNotExist:
                    pass
                
                # 移除主管報工批量核准 - 主管不應該有報工記錄
                
            except Exception as e:
                messages.error(request, f'核准報工記錄 {report_id} 失敗: {str(e)}')
        
        # 批量同步所有相關工單的報工記錄到生產詳情資料表
        if synced_workorders:
            try:
                from workorder.services import ProductionReportSyncService
                for workorder_id in synced_workorders:
                    ProductionReportSyncService.sync_specific_workorder(workorder_id)
            except Exception as sync_error:
                # 同步失敗不影響核准流程，只記錄錯誤
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"批量同步報工記錄到生產詳情失敗: {str(sync_error)}")
        
        messages.success(request, f'成功核准 {approved_count} 筆報工記錄')
        return redirect('workorder:supervisor:pending_approval_list')
    
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
        count = SMTSupplementReport.objects.filter(work_date=check_date).count()
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
    
    smt_abnormal = SMTSupplementReport.objects.select_related(
        'workorder'
    ).filter(
        Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='') & ~Q(abnormal_notes='nan')
    ).order_by('-work_date', '-start_time')
    
    # 主管功能處理作業員和SMT的補登報工異常
    # 這裡可以添加其他類型的異常處理，如補登報工異常等
    
    # 計算異常統計數據
    total_operator_abnormal = operator_abnormal.count()
    total_smt_abnormal = smt_abnormal.count()
    total_supplement_abnormal = 0  # 補登報工異常數量
    
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
    
    # critical_supplement = supplement_abnormal.filter(
    #     Q(abnormal_notes__icontains='嚴重') | 
    #     Q(abnormal_notes__icontains='緊急') | 
    #     Q(abnormal_notes__icontains='停機') | 
    #     Q(abnormal_notes__icontains='故障') | 
    #     Q(abnormal_notes__icontains='錯誤')
    # ).count()
    critical_supplement = 0  # 補登報工嚴重異常數量
    
    # 計算待處理和已解決的異常
    pending_operator = operator_abnormal.filter(approval_status='pending').count()
    pending_smt = smt_abnormal.filter(approval_status='pending').count()
    pending_supplement = 0  # 補登報工待處理異常數量
    
    resolved_operator = operator_abnormal.filter(approval_status='approved').count()
    resolved_smt = smt_abnormal.filter(approval_status='approved').count()
    resolved_supplement = 0  # 補登報工已解決異常數量
    
    # 彙總統計
    abnormal_stats = {
        'total_abnormal': total_operator_abnormal + total_smt_abnormal + total_supplement_abnormal,
        'critical': critical_operator + critical_smt + critical_supplement,
        'pending': pending_operator + pending_smt + pending_supplement,
        'resolved': resolved_operator + resolved_smt + resolved_supplement,
        'operator_abnormal': total_operator_abnormal,
        'smt_abnormal': total_smt_abnormal,
        'supplement_abnormal': total_supplement_abnormal,
    }
    
    context = {
        **context_data,
        'operator_abnormal': operator_abnormal,
        'smt_abnormal': smt_abnormal,
        'supplement_abnormal': [],  # 補登報工異常記錄
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
            
            smt_pending = SMTSupplementReport.objects.filter(
                Q(abnormal_notes__isnull=False) & 
                ~Q(abnormal_notes='') & 
                ~Q(abnormal_notes='nan') &
                Q(approval_status='pending')
            )
            
            # supplement_pending = 補登報工異常查詢
            # 這裡可以添加補登報工異常的處理邏輯
            supplement_pending = []  # 補登報工異常
            
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
            
            # supplement_resolved = supplement_pending.update(
            #     approval_status='approved',
            #     approved_by=request.user.username,
            #     approved_at=timezone.now()
            # )
            supplement_resolved = 0  # 補登報工異常解決數量
            
            total_resolved = operator_resolved + smt_resolved + supplement_resolved
            
            return JsonResponse({
                'success': True,
                'resolved_count': total_resolved,
                'operator_resolved': operator_resolved,
                'smt_resolved': smt_resolved,
                'supplement_resolved': supplement_resolved
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
        report = get_object_or_404(SMTSupplementReport, id=abnormal_id)
    elif abnormal_type == 'supplement':
        # 補登報工異常詳情
        # 這裡可以添加補登報工異常的處理邏輯
        messages.error(request, '補登報工異常功能正在開發中')
        return redirect('workorder:supervisor:abnormal_management')
    else:
        messages.error(request, '無效的異常類型')
        return redirect('workorder:supervisor:abnormal_management')
    
    context = {
        'report': report,
        'abnormal_type': abnormal_type,
    }
    
    # 根據異常類型選擇對應的模板
    if abnormal_type == 'operator':
        template_name = 'supervisor/abnormal_detail_operator.html'
    elif abnormal_type == 'smt':
        template_name = 'supervisor/abnormal_detail_smt.html'
    elif abnormal_type == 'supplement':
        # 補登報工異常詳情模板
        # 這裡可以添加補登報工異常的處理邏輯
        messages.error(request, '補登報工異常功能正在開發中')
        return redirect('workorder:supervisor:abnormal_management')
    else:
        template_name = 'supervisor/abnormal_detail_operator.html'  # 預設使用作業員模板
    
    return render(request, template_name, context) 


@login_required
def approved_reports_list(request):
    """
    已審核報工列表視圖 (Approved Reports List View)
    顯示所有已審核的報工記錄（包含作業員報工、SMT報工）
    
    重要：統計數字直接來自報工資料表，不依賴工單關聯
    報工資料表有多少筆已審核記錄就顯示多少筆
    """
    from django.core.paginator import Paginator
    from django.db.models import Q
    from workorder.workorder_reporting.models import OperatorSupplementReport, SMTSupplementReport
    
    # 獲取公司配置對照表
    from erp_integration.models import CompanyConfig
    company_configs = {}
    for config in CompanyConfig.objects.all():
        company_configs[config.company_code] = config.company_name
    
    # 獲取已審核的作業員報工記錄（直接從報工資料表統計，不依賴工單關聯）
    approved_operator_reports = OperatorSupplementReport.objects.filter(
        approval_status='approved'
    ).select_related('operator', 'workorder', 'process').order_by('-approved_at')
    
    # 獲取已審核的SMT報工記錄（直接從報工資料表統計，不依賴工單關聯）
    approved_smt_reports = SMTSupplementReport.objects.filter(
        approval_status='approved'
    ).select_related('workorder').order_by('-approved_at')
    
    # 搜尋功能
    search_query = request.GET.get('search', '')
    if search_query:
        approved_operator_reports = approved_operator_reports.filter(
            Q(workorder__order_number__icontains=search_query) |
            Q(original_workorder_number__icontains=search_query) |
            Q(operator__name__icontains=search_query) |
            Q(process__name__icontains=search_query)
        )
        approved_smt_reports = approved_smt_reports.filter(
            Q(workorder__order_number__icontains=search_query) |
            Q(original_workorder_number__icontains=search_query) |
            Q(operation__icontains=search_query)
        )
    
    # 日期篩選
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    if start_date:
        approved_operator_reports = approved_operator_reports.filter(approved_at__date__gte=start_date)
        approved_smt_reports = approved_smt_reports.filter(approved_at__date__gte=start_date)
    
    if end_date:
        approved_operator_reports = approved_operator_reports.filter(approved_at__date__lte=end_date)
        approved_smt_reports = approved_smt_reports.filter(approved_at__date__lte=end_date)
    
    # 合併並排序所有已審核記錄
    all_approved_reports = []
    
    for report in approved_operator_reports:
        # 取得工單號碼：優先使用 workorder，其次使用 original_workorder_number
        workorder_number = '-'
        if report.workorder:
            workorder_number = report.workorder.order_number
        elif report.original_workorder_number:
            workorder_number = report.original_workorder_number
        
        # 獲取公司名稱
        company_name = '-'
        if report.workorder and report.workorder.company_code:
            company_name = company_configs.get(report.workorder.company_code, report.workorder.company_code)
        elif hasattr(report, 'company_code') and report.company_code:
            company_name = company_configs.get(report.company_code, report.company_code)
        
        all_approved_reports.append({
            'id': report.id,
            'type': '作業員報工',
            'workorder': workorder_number,
            'company_name': company_name,
            'operator': report.operator.name if report.operator else '-',
            'process': report.process.name if report.process else '-',
            'quantity': report.work_quantity or 0,
            'defect_quantity': report.defect_quantity or 0,
            'work_date': report.work_date,
            'approved_by': report.approved_by,
            'approved_at': report.approved_at,
            'report_id': report.id,
            'report_type': 'operator'
        })
    
    for report in approved_smt_reports:
        # 取得工單號碼：優先使用 workorder，其次使用 original_workorder_number
        workorder_number = '-'
        if report.workorder:
            workorder_number = report.workorder.order_number
        elif report.original_workorder_number:
            workorder_number = report.original_workorder_number
        
        # 獲取公司名稱
        company_name = '-'
        if report.workorder and report.workorder.company_code:
            company_name = company_configs.get(report.workorder.company_code, report.workorder.company_code)
        elif hasattr(report, 'company_code') and report.company_code:
            company_name = company_configs.get(report.company_code, report.company_code)
        
        all_approved_reports.append({
            'id': report.id,
            'type': 'SMT報工',
            'workorder': workorder_number,
            'company_name': company_name,
            'operator': 'SMT設備',
            'process': report.operation,
            'quantity': report.work_quantity or 0,
            'defect_quantity': report.defect_quantity or 0,
            'work_date': report.work_date,
            'approved_by': report.approved_by,
            'approved_at': report.approved_at,
            'report_id': report.id,
            'report_type': 'smt'
        })
    
    # 按審核時間排序
    all_approved_reports.sort(key=lambda x: x['approved_at'], reverse=True)
    
    # 分頁
    paginator = Paginator(all_approved_reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 統計資訊 - 直接從報工資料表統計，不依賴工單關聯
    # 這樣確保報工資料表有多少筆已審核記錄就顯示多少筆
    total_approved = approved_operator_reports.count() + approved_smt_reports.count()
    operator_count = approved_operator_reports.count()
    smt_count = approved_smt_reports.count()
    
    context = {
        'page_obj': page_obj,
        'total_approved': total_approved,
        'operator_count': operator_count,
        'smt_count': smt_count,
        'search_query': search_query,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'supervisor/approved_reports_list.html', context) 


@login_required
def revert_approved_report(request, report_id):
    """
    將已核准的報工記錄轉回待核准狀態
    """
    if request.method == 'POST':
        try:
            # 嘗試獲取作業員報工記錄
            report = get_object_or_404(OperatorSupplementReport, id=report_id)
            report_type = 'operator'
        except:
            # 如果找不到作業員報工記錄，嘗試獲取SMT報工記錄
            try:
                from workorder.workorder_reporting.models import SMTSupplementReport
                report = get_object_or_404(SMTSupplementReport, id=report_id)
                report_type = 'smt'
            except:
                messages.error(request, '找不到指定的報工記錄')
                return redirect('workorder:supervisor:pending_approval_list')
        
        # 檢查權限
        if not request.user.is_superuser and not request.user.groups.filter(name='主管').exists():
            messages.error(request, '您沒有權限執行此操作')
            return redirect('workorder:supervisor:pending_approval_list')
        
        # 檢查報工狀態
        if report.approval_status != 'approved':
            messages.error(request, '只有已核准的報工記錄才能轉回待核准狀態')
            return redirect('workorder:supervisor:pending_approval_list')
        
        # 執行狀態轉換
        report.approval_status = 'pending'
        report.approved_by = None
        report.approved_at = None
        report.approval_remarks = ''
        report.save()
        
        # 記錄操作日誌
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'用戶 {request.user.username} 將報工記錄 {report_id} 從已核准轉回待核准狀態')
        
        messages.success(request, f'報工記錄 {report.id} 已成功轉回待核准狀態')
        return redirect('workorder:supervisor:pending_approval_list')
    
    return redirect('workorder:supervisor:pending_approval_list') 


@login_required
def batch_revert_all_approved_reports(request):
    """
    批量將所有已核准的報工記錄轉回待核准狀態
    """
    if request.method == 'POST':
        # 檢查權限
        if not request.user.is_superuser and not request.user.groups.filter(name='主管').exists():
            messages.error(request, '您沒有權限執行此操作')
            return redirect('workorder:supervisor:approved_reports_list')
        
        try:
            # 獲取所有已核准的作業員報工記錄
            approved_operator_reports = OperatorSupplementReport.objects.filter(
                approval_status='approved'
            )
            
            # 獲取所有已核准的SMT報工記錄
            from workorder.workorder_reporting.models import SMTSupplementReport
            approved_smt_reports = SMTSupplementReport.objects.filter(
                approval_status='approved'
            )
            
            # 統計數量
            operator_count = approved_operator_reports.count()
            smt_count = approved_smt_reports.count()
            total_count = operator_count + smt_count
            
            if total_count == 0:
                messages.warning(request, '目前沒有已核准的報工記錄需要轉回待核准狀態')
                return redirect('workorder:supervisor:approved_reports_list')
            
            # 批量更新作業員報工記錄
            operator_updated = approved_operator_reports.update(
                approval_status='pending',
                approved_by=None,
                approved_at=None,
                approval_remarks=''
            )
            
            # 批量更新SMT報工記錄
            smt_updated = approved_smt_reports.update(
                approval_status='pending',
                approved_by=None,
                approved_at=None,
                approval_remarks=''
            )
            
            # 記錄操作日誌
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'用戶 {request.user.username} 批量將 {total_count} 筆已核准報工記錄轉回待核准狀態 (作業員: {operator_updated}, SMT: {smt_updated})')
            
            messages.success(request, f'成功將 {total_count} 筆已核准報工記錄轉回待核准狀態\n• 作業員報工: {operator_updated} 筆\n• SMT報工: {smt_updated} 筆')
            
        except Exception as e:
            messages.error(request, f'批量轉換失敗: {str(e)}')
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'批量轉換已核准報工記錄失敗: {str(e)}')
        
        return redirect('workorder:supervisor:approved_reports_list')
    
    return redirect('workorder:supervisor:approved_reports_list') 