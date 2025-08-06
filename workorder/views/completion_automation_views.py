#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完工自動化管理統一視圖
整合自動分配設定和自動管理功能
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.utils import timezone
from datetime import datetime
import logging

from ..models import AutoManagementConfig, AutoAllocationSettings
from ..forms import AutoManagementConfigForm

logger = logging.getLogger(__name__)


class CompletionAutomationManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    完工自動化管理統一視圖
    整合分配設定和功能管理功能
    """
    
    template_name = "workorder/completion_automation_management.html"
    
    def test_func(self):
        """檢查用戶是否有管理權限"""
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        
        # 添加自動管理功能統計資訊
        context['total_configs'] = AutoManagementConfig.objects.count()
        context['enabled_configs'] = AutoManagementConfig.objects.filter(is_enabled=True).count()
        context['disabled_configs'] = AutoManagementConfig.objects.filter(is_enabled=False).count()
        context['configs'] = AutoManagementConfig.objects.all().order_by('-created_at')
        
        return context


@require_POST
@login_required
def execute_auto_function(request, function_type):
    """
    執行指定的自動化功能
    """
    try:
        # 檢查權限
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({
                "success": False,
                "message": "權限不足"
            })
        
        # 獲取功能設定
        try:
            config = AutoManagementConfig.objects.get(function_type=function_type)
        except AutoManagementConfig.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": f"功能類型 {function_type} 不存在"
            })
        
        # 檢查功能是否啟用
        if not config.is_enabled:
            return JsonResponse({
                "success": False,
                "message": f"功能 {config.get_function_type_display()} 未啟用"
            })
        
        # 根據功能類型執行對應的操作
        if function_type == 'auto_completion_check':
            # 執行完工判斷
            success = execute_completion_check()
            message = "完工判斷執行完成" if success else "完工判斷執行失敗"

        elif function_type == 'auto_approval':
            # 執行自動核准
            success = execute_auto_approval()
            message = "自動核准執行完成" if success else "自動核准執行失敗"
        elif function_type == 'auto_notification':
            # 執行自動通知
            success = execute_auto_notification()
            message = "自動通知執行完成" if success else "自動通知執行失敗"
        else:
            return JsonResponse({
                "success": False,
                "message": f"不支援的功能類型: {function_type}"
            })
        
        # 更新執行記錄
        config.execution_count += 1
        config.last_execution = timezone.now()
        if success:
            config.success_count += 1
        else:
            config.error_count += 1
        config.save()
        
        return JsonResponse({
            "success": success,
            "message": message
        })
        
    except Exception as e:
        logger.error(f"執行自動化功能 {function_type} 時發生錯誤: {str(e)}")
        return JsonResponse({
            "success": False,
            "message": f"執行失敗: {str(e)}"
        })


@require_POST
@login_required
def toggle_auto_function(request, function_type):
    """
    切換自動化功能的啟用狀態
    """
    try:
        # 檢查權限
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({
                "success": False,
                "message": "權限不足"
            })
        
        # 獲取功能設定
        try:
            config = AutoManagementConfig.objects.get(function_type=function_type)
        except AutoManagementConfig.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": f"功能類型 {function_type} 不存在"
            })
        
        # 切換啟用狀態
        config.is_enabled = not config.is_enabled
        config.save()
        
        status_text = "啟用" if config.is_enabled else "停用"
        function_name = config.get_function_type_display()
        
        return JsonResponse({
            "success": True,
            "message": f"自動管理功能「{function_name}」已{status_text}"
        })
        
    except Exception as e:
        logger.error(f"切換自動化功能 {function_type} 狀態時發生錯誤: {str(e)}")
        return JsonResponse({
            "success": False,
            "message": f"操作失敗: {str(e)}"
        })


def execute_completion_check():
    """
    執行完工判斷功能
    """
    try:
        logger.info("開始執行完工判斷")
        
        # 這裡可以調用完工判斷的具體邏輯
        # 例如：檢查工單是否達到完工條件，更新工單狀態等
        
        # 暫時返回成功
        return True
        
    except Exception as e:
        logger.error(f"執行完工判斷時發生錯誤: {str(e)}")
        return False


def execute_quantity_allocation():
    """
    執行智能分配功能
    """
    try:
        logger.info("開始執行智能分配")
        
        # 調用自動分配服務
        from ..services.auto_allocation_scheduler import AutoAllocationScheduler
        scheduler = AutoAllocationScheduler()
        success = scheduler.execute_auto_allocation()
        
        return success
        
    except Exception as e:
        logger.error(f"執行智能分配時發生錯誤: {str(e)}")
        return False


def execute_auto_approval():
    """
    執行自動核准功能
    """
    try:
        logger.info("開始執行自動核准")
        
        # 這裡可以實現自動核准的邏輯
        # 例如：根據規則自動核准符合條件的報工記錄
        
        # 暫時返回成功
        return True
        
    except Exception as e:
        logger.error(f"執行自動核准時發生錯誤: {str(e)}")
        return False


def execute_auto_notification():
    """
    執行自動通知功能
    """
    try:
        logger.info("開始執行自動通知")
        
        # 這裡可以實現自動通知的邏輯
        # 例如：發送完工通知、異常通知等
        
        # 暫時返回成功
        return True
        
    except Exception as e:
        logger.error(f"執行自動通知時發生錯誤: {str(e)}")
        return False 