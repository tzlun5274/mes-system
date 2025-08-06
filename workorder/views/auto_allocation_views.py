#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動分配相關視圖
處理自動分配功能的前端API請求
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render
from workorder.services.auto_allocation_scheduler import scheduler
from workorder.services.auto_allocation_service import AutoAllocationService

logger = logging.getLogger(__name__)


def supervisor_required(user):
    """檢查用戶是否為主管或超級用戶"""
    return user.is_superuser or user.groups.filter(name="主管").exists()


@login_required
@user_passes_test(supervisor_required)
def auto_allocation_status(request):
    """取得自動分配狀態"""
    try:
        status = scheduler.get_status()
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"取得自動分配狀態失敗: {str(e)}")
        # 返回預設狀態而不是錯誤
        return JsonResponse({
            'enabled': False,
            'is_running': False,
            'interval_minutes': 30,
            'start_time': '08:00',
            'end_time': '18:00',
            'max_execution_time': 30,
            'notification_enabled': True,
            'last_execution': None,
            'next_execution': None,
            'today_executions': 0,
            'success_count': 0,
            'failure_count': 0,
            'avg_execution_time': '0秒',
            'error': '取得狀態失敗，使用預設值',
            'message': str(e)
        })


@login_required
@user_passes_test(supervisor_required)
@require_http_methods(["POST"])
def auto_allocation_settings(request):
    """更新自動分配設定"""
    try:
        # 解析表單數據
        enabled = request.POST.get('executionEnabled') == 'on'
        
        # 安全地處理數字欄位，避免空字串轉換錯誤
        interval_minutes_str = request.POST.get('executionInterval', '30')
        try:
            interval_minutes = int(interval_minutes_str) if interval_minutes_str and interval_minutes_str.strip() else 30
        except (ValueError, TypeError):
            interval_minutes = 30
        
        start_time = request.POST.get('startTime', '08:00')
        end_time = request.POST.get('endTime', '18:00')
        
        max_execution_time_str = request.POST.get('maxExecutionTime', '30')
        try:
            max_execution_time = int(max_execution_time_str) if max_execution_time_str and max_execution_time_str.strip() else 30
        except (ValueError, TypeError):
            max_execution_time = 30
        
        notification_enabled = request.POST.get('notificationEnabled') == 'on'
        
        # 驗證數據
        if interval_minutes < 1 or interval_minutes > 1440:
            return JsonResponse({
                'success': False,
                'message': '執行頻率必須在1-1440分鐘之間'
            })
        
        if max_execution_time < 1 or max_execution_time > 120:
            return JsonResponse({
                'success': False,
                'message': '最大執行時間必須在1-120分鐘之間'
            })
        
        # 更新設定
        from datetime import time
        start_time_obj = time.fromisoformat(start_time)
        end_time_obj = time.fromisoformat(end_time)
        
        scheduler.update_settings(
            enabled=enabled,
            interval_minutes=interval_minutes,
            start_time=start_time_obj,
            end_time=end_time_obj,
            max_execution_time=max_execution_time,
            notification_enabled=notification_enabled
        )
        
        return JsonResponse({
            'success': True,
            'message': '設定更新成功'
        })
        
    except Exception as e:
        logger.error(f"更新自動分配設定失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'設定更新失敗: {str(e)}'
        })


@login_required
@user_passes_test(supervisor_required)
@require_http_methods(["POST"])
def auto_allocation_execute(request):
    """立即執行自動分配"""
    try:
        # 檢查是否已在執行
        settings = scheduler.get_settings()
        if settings.is_running:
            return JsonResponse({
                'success': False,
                'message': '自動分配已在執行中，請稍後再試'
            })
        
        # 執行自動分配
        success = scheduler.execute_auto_allocation()
        
        if success:
            # 取得執行結果
            recent_logs = scheduler.get_recent_logs(limit=1)
            if recent_logs:
                latest_log = recent_logs[0]
                return JsonResponse({
                    'success': True,
                    'message': '自動分配執行成功',
                    'total_workorders': latest_log.total_workorders,
                    'successful_allocations': latest_log.successful_allocations,
                    'failed_allocations': latest_log.failed_allocations,
                    'execution_time': latest_log.execution_time_display
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': '自動分配執行成功'
                })
        else:
            return JsonResponse({
                'success': False,
                'message': '自動分配執行失敗'
            })
            
    except Exception as e:
        logger.error(f"執行自動分配失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'執行失敗: {str(e)}'
        })


@login_required
@user_passes_test(supervisor_required)
@require_http_methods(["POST"])
def auto_allocation_stop(request):
    """停止自動執行"""
    try:
        success = scheduler.stop_execution()
        return JsonResponse({
            'success': success,
            'message': '自動執行已停止' if success else '停止失敗'
        })
    except Exception as e:
        logger.error(f"停止自動執行失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'停止失敗: {str(e)}'
        })


@login_required
@user_passes_test(supervisor_required)
def auto_allocation_log(request):
    """查看執行記錄"""
    try:
        logs = scheduler.get_recent_logs(limit=100)
        
        context = {
            'logs': logs,
            'title': '自動分配執行記錄'
        }
        
        return render(request, 'workorder/auto_allocation_log.html', context)
        
    except Exception as e:
        logger.error(f"取得執行記錄失敗: {str(e)}")
        return JsonResponse({
            'error': '取得記錄失敗',
            'message': str(e)
        }, status=500)


@login_required
@user_passes_test(supervisor_required)
def auto_allocation_summary(request):
    """取得自動分配摘要"""
    try:
        # 取得待分配摘要
        allocation_service = AutoAllocationService()
        summary = allocation_service.get_pending_allocation_summary()
        
        # 取得執行狀態
        status = scheduler.get_status()
        
        # 合併資訊
        result = {
            'pending_summary': summary,
            'execution_status': status
        }
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"取得自動分配摘要失敗: {str(e)}")
        return JsonResponse({
            'error': '取得摘要失敗',
            'message': str(e)
        }, status=500) 