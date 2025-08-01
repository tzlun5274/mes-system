"""
報表模組視圖
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
import logging

# 設定日誌
logger = logging.getLogger(__name__)


def superuser_required(user):
    """
    檢查用戶是否為超級管理員
    只有超級管理員才能執行批次刪除操作
    """
    return user.is_superuser


class ReportingIndexView(LoginRequiredMixin, TemplateView):
    """
    報表管理首頁視圖
    """
    template_name = 'reporting/index.html'


@login_required
def pending_approval_list(request):
    """
    待審核報工列表視圖
    顯示所有待審核的作業員報工和SMT報工記錄
    """
    # 取得待審核的作業員報工記錄
    operator_pending = OperatorSupplementReport.objects.filter(
        approval_status='pending'
    ).select_related('operator', 'workorder', 'process').order_by('-created_at')
    
    # 取得待審核的SMT報工記錄
    smt_pending = SMTProductionReport.objects.filter(
        approval_status='pending'
    ).select_related('workorder', 'equipment').order_by('-created_at')
    
    # 合併所有待審核記錄
    all_pending = []
    
    for report in operator_pending:
        all_pending.append({
            'type': '作業員報工',
            'id': report.id,
            'report_type': 'operator',
            'operator': report.operator.name if report.operator else '-',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process.name if report.process else '-',
            'quantity': report.work_quantity,
            'defect_quantity': report.defect_quantity,
            'work_date': report.work_date,
            'start_time': report.start_time,
            'end_time': report.end_time,
            'created_at': report.created_at,
            'created_by': report.created_by,
            'remarks': report.remarks,
        })
    
    for report in smt_pending:
        all_pending.append({
            'type': 'SMT報工',
            'id': report.id,
            'report_type': 'smt',
            'operator': 'SMT設備',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.operation,
            'quantity': report.work_quantity,
            'defect_quantity': getattr(report, 'defect_quantity', 0),
            'work_date': report.work_date,
            'start_time': report.start_time,
            'end_time': report.end_time,
            'created_at': report.created_at,
            'created_by': report.created_by,
            'remarks': getattr(report, 'remarks', ''),
        })
    
    # 按建立時間排序
    all_pending.sort(key=lambda x: x['created_at'], reverse=True)
    
    # 統計資料
    total_pending = len(all_pending)
    operator_count = len(operator_pending)
    smt_count = len(smt_pending)

    return render(
        request,
        "reporting/pending_approval_list.html",
        {
            "all_pending": all_pending,
            "total_pending": total_pending,
            "operator_count": operator_count,
            "smt_count": smt_count,
        },
    )


@login_required
def approved_reports_list(request):
    """
    已核准報工列表視圖
    顯示所有已核准的作業員報工和SMT報工記錄
    """
    # 取得已核准的作業員報工記錄
    operator_approved = OperatorSupplementReport.objects.filter(
        approval_status='approved'
    ).select_related('operator', 'workorder', 'process').order_by('-approved_at')
    
    # 取得已核准的SMT報工記錄
    smt_approved = SMTProductionReport.objects.filter(
        approval_status='approved'
    ).select_related('workorder', 'equipment').order_by('-approved_at')
    
    # 合併所有已核准記錄
    all_approved = []
    
    for report in operator_approved:
        all_approved.append({
            'type': '作業員報工',
            'id': report.id,
            'report_type': 'operator',
            'operator': report.operator.name if report.operator else '-',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.process.name if report.process else '-',
            'quantity': report.work_quantity,
            'defect_quantity': report.defect_quantity,
            'work_date': report.work_date,
            'start_time': report.start_time,
            'end_time': report.end_time,
            'approved_at': report.approved_at,
            'approved_by': report.approved_by,
            'remarks': report.remarks,
        })
    
    for report in smt_approved:
        all_approved.append({
            'type': 'SMT報工',
            'id': report.id,
            'report_type': 'smt',
            'operator': 'SMT設備',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.operation,
            'quantity': report.work_quantity,
            'defect_quantity': getattr(report, 'defect_quantity', 0),
            'work_date': report.work_date,
            'start_time': report.start_time,
            'end_time': report.end_time,
            'approved_at': report.approved_at,
            'approved_by': report.approved_by,
            'remarks': getattr(report, 'remarks', ''),
        })
    
    # 按核准時間排序
    all_approved.sort(key=lambda x: x['approved_at'], reverse=True)
    
    # 統計資料
    total_approved = len(all_approved)
    operator_count = len(operator_approved)
    smt_count = len(smt_approved)

    return render(
        request,
        "reporting/approved_reports_list.html",
        {
            "all_approved": all_approved,
            "total_approved": total_approved,
            "operator_count": operator_count,
            "smt_count": smt_count,
        },
    )


@login_required
@user_passes_test(superuser_required, login_url='/accounts/login/')
def batch_delete_pending_confirm(request):
    """
    批次刪除待核准報工記錄確認頁面
    只有超級管理員可以訪問
    """
    # 取得待刪除的記錄統計
    operator_pending_count = OperatorSupplementReport.objects.filter(
        approval_status='pending'
    ).count()
    
    smt_pending_count = SMTProductionReport.objects.filter(
        approval_status='pending'
    ).count()
    
    total_pending_count = operator_pending_count + smt_pending_count
    
    context = {
        'operator_pending_count': operator_pending_count,
        'smt_pending_count': smt_pending_count,
        'total_pending_count': total_pending_count,
    }
    
    return render(request, 'reporting/batch_delete_pending_confirm.html', context)


@login_required
@user_passes_test(superuser_required, login_url='/accounts/login/')
@require_POST
def batch_delete_pending_reports(request):
    """
    批次刪除待核准報工記錄
    只有超級管理員可以執行此操作
    """
    try:
        # 記錄操作開始
        logger.warning(
            f"超級管理員 {request.user.username} 開始執行批次刪除待核准報工記錄"
        )
        
        # 取得刪除前的統計資料
        operator_pending = OperatorSupplementReport.objects.filter(
            approval_status='pending'
        )
        smt_pending = SMTProductionReport.objects.filter(
            approval_status='pending'
        )
        
        operator_pending_count = operator_pending.count()
        smt_pending_count = smt_pending.count()
        total_before = operator_pending_count + smt_pending_count
        
        logger.info(f"找到待刪除記錄：作業員報工 {operator_pending_count} 筆，SMT報工 {smt_pending_count} 筆")
        
        if total_before == 0:
            messages.warning(request, "目前沒有待核准的報工記錄")
            return redirect('reporting:pending_approval_list')
        
        # 記錄詳細資訊
        for report in operator_pending[:5]:  # 只記錄前5筆作為範例
            logger.info(f"待刪除作業員報工：ID={report.id}, 作業員={report.operator}, 工單={report.workorder}, 日期={report.work_date}")
        
        # 執行批次刪除 - 使用更安全的方式
        operator_deleted = 0
        smt_deleted = 0
        
        # 方法1：嘗試正常刪除
        try:
            # 逐筆刪除作業員報工記錄，避免外鍵約束問題
            for report in operator_pending:
                try:
                    report_id = report.id
                    report.delete()
                    operator_deleted += 1
                    logger.info(f"成功刪除作業員報工記錄 ID: {report_id}")
                except Exception as e:
                    logger.error(f"刪除作業員報工記錄 ID: {report.id} 失敗：{str(e)}")
            
            # 逐筆刪除SMT報工記錄
            for report in smt_pending:
                try:
                    report_id = report.id
                    report.delete()
                    smt_deleted += 1
                    logger.info(f"成功刪除SMT報工記錄 ID: {report_id}")
                except Exception as e:
                    logger.error(f"刪除SMT報工記錄 ID: {report.id} 失敗：{str(e)}")
        except Exception as e:
            logger.error(f"正常刪除失敗，嘗試使用原始SQL刪除：{str(e)}")
            
            # 方法2：使用原始SQL強制刪除
            from django.db import connection
            
            try:
                with connection.cursor() as cursor:
                    # 強制刪除作業員報工記錄
                    cursor.execute("""
                        DELETE FROM workorder_operator_supplement_report 
                        WHERE approval_status = 'pending'
                    """)
                    operator_deleted = cursor.rowcount
                    logger.info(f"使用SQL成功刪除作業員報工記錄：{operator_deleted} 筆")
                    
                    # 強制刪除SMT報工記錄
                    cursor.execute("""
                        DELETE FROM workorder_smt_production_report 
                        WHERE approval_status = 'pending'
                    """)
                    smt_deleted = cursor.rowcount
                    logger.info(f"使用SQL成功刪除SMT報工記錄：{smt_deleted} 筆")
                    
            except Exception as sql_error:
                logger.error(f"SQL刪除也失敗：{str(sql_error)}")
                messages.error(request, f"批次刪除失敗：{str(sql_error)}")
                return redirect('reporting:pending_approval_list')
        
        total_deleted = operator_deleted + smt_deleted
        
        # 記錄操作完成
        logger.warning(
            f"超級管理員 {request.user.username} 完成批次刪除待核准報工記錄："
            f"作業員報工 {operator_deleted} 筆，SMT報工 {smt_deleted} 筆，"
            f"總計 {total_deleted} 筆"
        )
        
        if total_deleted > 0:
            messages.success(
                request, 
                f"成功批次刪除待核准報工記錄！\n"
                f"作業員報工：{operator_deleted} 筆\n"
                f"SMT報工：{smt_deleted} 筆\n"
                f"總計：{total_deleted} 筆"
            )
        else:
            messages.warning(request, "沒有成功刪除任何記錄，可能是因為外鍵約束或其他限制")
        
        return redirect('reporting:pending_approval_list')
        
    except Exception as e:
        # 記錄錯誤
        logger.error(
            f"超級管理員 {request.user.username} 批次刪除待核准報工記錄失敗：{str(e)}"
        )
        
        messages.error(request, f"批次刪除失敗：{str(e)}")
        return redirect('reporting:pending_approval_list')


@login_required
@user_passes_test(superuser_required, login_url='/accounts/login/')
@require_POST
def batch_delete_selected_pending(request):
    """
    批次刪除選定的待核准報工記錄
    只有超級管理員可以執行此操作
    """
    try:
        # 取得要刪除的記錄 ID 列表
        operator_ids = request.POST.getlist('operator_report_ids')
        smt_ids = request.POST.getlist('smt_report_ids')
        
        if not operator_ids and not smt_ids:
            messages.warning(request, "請選擇要刪除的報工記錄")
            return redirect('reporting:pending_approval_list')
        
        # 記錄操作開始
        logger.warning(
            f"超級管理員 {request.user.username} 開始執行批次刪除選定待核准報工記錄："
            f"作業員報工 {len(operator_ids)} 筆，SMT報工 {len(smt_ids)} 筆"
        )
        
        # 執行批次刪除
        operator_deleted = 0
        smt_deleted = 0
        
        if operator_ids:
            operator_deleted = OperatorSupplementReport.objects.filter(
                id__in=operator_ids,
                approval_status='pending'
            ).delete()[0]
        
        if smt_ids:
            smt_deleted = SMTProductionReport.objects.filter(
                id__in=smt_ids,
                approval_status='pending'
            ).delete()[0]
        
        total_deleted = operator_deleted + smt_deleted
        
        # 記錄操作完成
        logger.warning(
            f"超級管理員 {request.user.username} 成功批次刪除選定待核准報工記錄："
            f"作業員報工 {operator_deleted} 筆，SMT報工 {smt_deleted} 筆，"
            f"總計 {total_deleted} 筆"
        )
        
        messages.success(
            request, 
            f"成功批次刪除選定的待核准報工記錄！\n"
            f"作業員報工：{operator_deleted} 筆\n"
            f"SMT報工：{smt_deleted} 筆\n"
            f"總計：{total_deleted} 筆"
        )
        
        return redirect('reporting:pending_approval_list')
        
    except Exception as e:
        # 記錄錯誤
        logger.error(
            f"超級管理員 {request.user.username} 批次刪除選定待核准報工記錄失敗：{str(e)}"
        )
        
        messages.error(request, f"批次刪除失敗：{str(e)}")
        return redirect('reporting:pending_approval_list')


@login_required
@user_passes_test(superuser_required, login_url='/accounts/login/')
def get_pending_reports_count(request):
    """
    API：取得待核准報工記錄數量
    只有超級管理員可以訪問
    """
    try:
        operator_count = OperatorSupplementReport.objects.filter(
            approval_status='pending'
        ).count()
        
        smt_count = SMTProductionReport.objects.filter(
            approval_status='pending'
        ).count()
        
        total_count = operator_count + smt_count
        
        return JsonResponse({
            'success': True,
            'operator_count': operator_count,
            'smt_count': smt_count,
            'total_count': total_count,
        })
        
    except Exception as e:
        logger.error(f"取得待核准報工記錄數量失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@user_passes_test(superuser_required, login_url='/accounts/login/')
@require_POST
def force_delete_all_reports(request):
    """
    強制刪除所有報工記錄（超級管理員專用）
    此功能會刪除所有狀態的報工記錄，包括已核准和已駁回的記錄
    """
    try:
        # 記錄操作開始
        logger.warning(
            f"超級管理員 {request.user.username} 開始執行強制刪除所有報工記錄"
        )
        
        # 取得所有記錄的統計資料
        operator_all = OperatorSupplementReport.objects.all()
        smt_all = SMTProductionReport.objects.all()
        
        operator_total = operator_all.count()
        smt_total = smt_all.count()
        total_before = operator_total + smt_total
        
        logger.info(f"找到所有記錄：作業員報工 {operator_total} 筆，SMT報工 {smt_total} 筆")
        
        if total_before == 0:
            messages.warning(request, "目前沒有任何報工記錄")
            return redirect('reporting:pending_approval_list')
        
        # 使用原始SQL強制刪除所有記錄
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                # 強制刪除所有作業員報工記錄
                cursor.execute("DELETE FROM workorder_operator_supplement_report")
                operator_deleted = cursor.rowcount
                logger.info(f"使用SQL成功刪除所有作業員報工記錄：{operator_deleted} 筆")
                
                # 強制刪除所有SMT報工記錄
                cursor.execute("DELETE FROM workorder_smt_production_report")
                smt_deleted = cursor.rowcount
                logger.info(f"使用SQL成功刪除所有SMT報工記錄：{smt_deleted} 筆")
                
        except Exception as sql_error:
            logger.error(f"SQL刪除失敗：{str(sql_error)}")
            messages.error(request, f"強制刪除失敗：{str(sql_error)}")
            return redirect('reporting:pending_approval_list')
        
        total_deleted = operator_deleted + smt_deleted
        
        # 記錄操作完成
        logger.warning(
            f"超級管理員 {request.user.username} 完成強制刪除所有報工記錄："
            f"作業員報工 {operator_deleted} 筆，SMT報工 {smt_deleted} 筆，"
            f"總計 {total_deleted} 筆"
        )
        
        messages.success(
            request, 
            f"成功強制刪除所有報工記錄！\n"
            f"作業員報工：{operator_deleted} 筆\n"
            f"SMT報工：{smt_deleted} 筆\n"
            f"總計：{total_deleted} 筆\n\n"
            f"⚠️ 警告：此操作已永久刪除所有報工記錄，無法復原！"
        )
        
        return redirect('reporting:pending_approval_list')
        
    except Exception as e:
        # 記錄錯誤
        logger.error(
            f"超級管理員 {request.user.username} 強制刪除所有報工記錄失敗：{str(e)}"
        )
        
        messages.error(request, f"強制刪除失敗：{str(e)}")
        return redirect('reporting:pending_approval_list')


@login_required
def placeholder_view(request, function_name=None):
    """
    通用佔位符視圖
    """
    return render(request, 'reporting/placeholder.html', {
        'function_name': function_name or '未知功能'
    }) 