"""
工單回朔功能視圖
提供已完工工單回朔到生產中狀態的功能
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from ..models import CompletedWorkOrder
from ..services.rollback_service import WorkOrderRollbackService

import logging

logger = logging.getLogger(__name__)


class WorkOrderRollbackConfirmView(LoginRequiredMixin, TemplateView):
    """
    工單回朔確認視圖
    顯示回朔確認頁面，讓使用者確認是否要回朔工單
    """
    template_name = 'workorder/rollback/rollback_confirm.html'
    
    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        completed_workorder_id = self.kwargs.get('pk')
        
        # 獲取已完工工單
        completed_workorder = get_object_or_404(CompletedWorkOrder, id=completed_workorder_id)
        context['completed_workorder'] = completed_workorder
        
        # 檢查是否可以回朔
        rollback_check = WorkOrderRollbackService.can_rollback(completed_workorder_id)
        context['can_rollback'] = rollback_check['can_rollback']
        context['rollback_reason'] = rollback_check['reason']
        
        # 獲取公司名稱
        company_name = completed_workorder.company_name or '-'
        if not company_name or company_name == '-':
            try:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=completed_workorder.company_code
                ).first()
                if company_config:
                    company_name = company_config.company_name
            except Exception:
                pass
        context['company_name'] = company_name
        
        # 計算統計資料
        context['total_processes'] = completed_workorder.total_report_count or 0
        context['total_work_hours'] = completed_workorder.total_work_hours or 0
        context['total_good_quantity'] = completed_workorder.total_good_quantity or 0
        context['total_defect_quantity'] = completed_workorder.total_defect_quantity or 0
        
        return context


@login_required
@require_POST
def rollback_completed_workorder(request, pk):
    """
    執行工單回朔
    
    Args:
        request: HTTP請求
        pk: 已完工工單ID
        
    Returns:
        JsonResponse: 回朔結果
    """
    try:
        # 檢查是否可以回朔
        rollback_check = WorkOrderRollbackService.can_rollback(pk)
        if not rollback_check['can_rollback']:
            return JsonResponse({
                'success': False,
                'error': rollback_check['reason']
            }, status=400)
        
        # 獲取是否保持核准狀態的參數
        keep_approval_status = request.POST.get('keep_approval_status', 'true').lower() == 'true'
        
        # 執行回朔
        result = WorkOrderRollbackService.rollback_completed_workorder(pk, keep_approval_status)
        
        if result['success']:
            # 記錄操作日誌
            logger.info(
                f"工單回朔成功：工單 {result['order_number']} 已回朔到生產中狀態。"
                f"操作者: {request.user}, IP: {request.META.get('REMOTE_ADDR')}"
            )
            
            # 顯示成功訊息
            messages.success(request, result['message'])
            
            return JsonResponse({
                'success': True,
                'message': result['message'],
                'redirect_url': '/workorder/'  # 重定向到工單列表
            })
        else:
            logger.error(f"工單回朔失敗：{result['error']}")
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=500)
            
    except Exception as e:
        logger.error(f"工單回朔異常：{str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'回朔失敗：{str(e)}'
        }, status=500)


@login_required
@require_POST
def batch_rollback_completed_workorders(request):
    """
    批次回朔已完工工單
    
    Args:
        request: HTTP請求
        
    Returns:
        JsonResponse: 批次回朔結果
    """
    try:
        # 獲取要回朔的工單ID列表
        workorder_ids = request.POST.getlist('workorder_ids[]')
        
        if not workorder_ids:
            return JsonResponse({
                'success': False,
                'error': '請選擇要回朔的工單'
            }, status=400)
        
        success_count = 0
        error_count = 0
        error_messages = []
        
        for workorder_id in workorder_ids:
            try:
                # 檢查是否可以回朔
                rollback_check = WorkOrderRollbackService.can_rollback(int(workorder_id))
                if not rollback_check['can_rollback']:
                    error_count += 1
                    error_messages.append(f"工單 {workorder_id}: {rollback_check['reason']}")
                    continue
                
                # 執行回朔
                result = WorkOrderRollbackService.rollback_completed_workorder(int(workorder_id))
                
                if result['success']:
                    success_count += 1
                    logger.info(f"批次回朔成功：工單 {result['order_number']}")
                else:
                    error_count += 1
                    error_messages.append(f"工單 {workorder_id}: {result['error']}")
                    
            except Exception as e:
                error_count += 1
                error_messages.append(f"工單 {workorder_id}: {str(e)}")
                logger.error(f"批次回朔工單 {workorder_id} 失敗：{str(e)}")
        
        # 記錄操作日誌
        logger.info(
            f"批次回朔完成：成功 {success_count} 個，失敗 {error_count} 個。"
            f"操作者: {request.user}, IP: {request.META.get('REMOTE_ADDR')}"
        )
        
        # 顯示結果訊息
        if success_count > 0:
            messages.success(request, f'成功回朔 {success_count} 個工單')
        
        if error_count > 0:
            messages.warning(request, f'有 {error_count} 個工單回朔失敗')
        
        return JsonResponse({
            'success': True,
            'message': f'批次回朔完成：成功 {success_count} 個，失敗 {error_count} 個',
            'success_count': success_count,
            'error_count': error_count,
            'error_messages': error_messages,
            'redirect_url': '/workorder/completed/' if error_count > 0 else '/workorder/'
        })
        
    except Exception as e:
        logger.error(f"批次回朔異常：{str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'批次回朔失敗：{str(e)}'
        }, status=500)


@login_required
def check_rollback_status(request, pk):
    """
    檢查工單回朔狀態
    
    Args:
        request: HTTP請求
        pk: 已完工工單ID
        
    Returns:
        JsonResponse: 回朔狀態檢查結果
    """
    try:
        rollback_check = WorkOrderRollbackService.can_rollback(pk)
        
        return JsonResponse({
            'success': True,
            'can_rollback': rollback_check['can_rollback'],
            'reason': rollback_check['reason']
        })
        
    except Exception as e:
        logger.error(f"檢查回朔狀態失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'檢查失敗：{str(e)}'
        }, status=500)
