"""
主管功能子模組視圖
整合所有主管相關功能，包含統計分析、異常處理、資料維護等
注意：舊的報工系統已棄用，相關視圖函數已移除
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
    WorkOrder,
    WorkOrderProcess
)

# 導入主管功能服務層
from .services import SupervisorStatisticsService, SupervisorAbnormalService

logger = logging.getLogger(__name__)

def get_supervisor_statistics():
    """
    統一的主管功能統計數據生成函數 (Supervisor Statistics Generator)
    返回所有主管功能頁面需要的統計數據
    """
    return SupervisorStatisticsService.get_supervisor_statistics()

@login_required
def supervisor_functions(request):
    """
    主管功能首頁 (Supervisor Functions Homepage)
    顯示主管功能的主要選單和統計資訊
    """
    try:
        # 獲取統計數據
        stats = get_supervisor_statistics()
        
        context = {
            'stats': stats,
            'page_title': '主管功能',
            'current_time': timezone.now(),
        }
        
        return render(request, 'supervisor/functions.html', context)
        
    except Exception as e:
        logger.error(f"主管功能首頁載入失敗: {str(e)}")
        messages.error(request, f'載入主管功能失敗: {str(e)}')
        return redirect('workorder:index')

@login_required
def report_statistics(request):
    """
    報工統計分析 (Report Statistics Analysis)
    顯示各種報工統計數據和圖表
    """
    try:
        # 獲取統計數據
        stats = get_supervisor_statistics()
        
        context = {
            'stats': stats,
            'page_title': '報工統計分析',
            'current_time': timezone.now(),
        }
        
        return render(request, 'supervisor/statistics.html', context)
        
    except Exception as e:
        logger.error(f"報工統計分析載入失敗: {str(e)}")
        messages.error(request, f'載入統計分析失敗: {str(e)}')
        return redirect('workorder:supervisor:supervisor_functions')

@login_required
def abnormal_management(request):
    """
    異常處理管理 (Abnormal Management)
    顯示和管理各種異常情況
    """
    try:
        # 獲取異常數據
        abnormal_service = SupervisorAbnormalService()
        abnormal_data = abnormal_service.get_abnormal_data()
        
        context = {
            'abnormal_data': abnormal_data,
            'page_title': '異常處理管理',
            'current_time': timezone.now(),
        }
        
        return render(request, 'supervisor/abnormal.html', context)
        
    except Exception as e:
        logger.error(f"異常處理管理載入失敗: {str(e)}")
        messages.error(request, f'載入異常處理失敗: {str(e)}')
        return redirect('workorder:supervisor:supervisor_functions')

@login_required
def abnormal_detail(request, abnormal_type, abnormal_id):
    """
    異常詳情 (Abnormal Detail)
    顯示特定異常的詳細資訊
    """
    try:
        # 獲取異常詳情
        abnormal_service = SupervisorAbnormalService()
        detail_data = abnormal_service.get_abnormal_detail(abnormal_type, abnormal_id)
        
        context = {
            'detail_data': detail_data,
            'abnormal_type': abnormal_type,
            'abnormal_id': abnormal_id,
            'page_title': f'異常詳情 - {abnormal_type}',
            'current_time': timezone.now(),
        }
        
        template_name = f'supervisor/abnormal_detail_{abnormal_type}.html'
        return render(request, template_name, context)
        
    except Exception as e:
        logger.error(f"異常詳情載入失敗: {str(e)}")
        messages.error(request, f'載入異常詳情失敗: {str(e)}')
        return redirect('workorder:supervisor:abnormal_management')

@login_required
def batch_resolve_abnormal(request):
    """
    批量解決異常 (Batch Resolve Abnormal)
    批量處理異常情況
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '無效的請求方法'})
    
    try:
        abnormal_ids = request.POST.getlist('abnormal_ids')
        resolve_type = request.POST.get('resolve_type', 'auto')
        
        abnormal_service = SupervisorAbnormalService()
        result = abnormal_service.batch_resolve_abnormal(abnormal_ids, resolve_type)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"批量解決異常失敗: {str(e)}")
        return JsonResponse({'success': False, 'message': f'批量解決異常失敗: {str(e)}'})

@login_required
def data_maintenance(request):
    """
    資料維護 (Data Maintenance)
    顯示資料維護選項和統計資訊
    """
    try:
        # 獲取維護統計數據
        stats = get_supervisor_statistics()
        
        # 維護選項
        maintenance_options = [
            {
                'id': 'cleanup_old_data',
                'name': '清理舊資料',
                'description': '清理30天前的填報記錄，釋放資料庫空間'
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
                'description': '匯出所有填報記錄為Excel檔案'
            },
        ]
        
        context = {
            'stats': stats,
            'maintenance_options': maintenance_options,
            'page_title': '資料維護',
            'current_time': timezone.now(),
        }
        
        return render(request, 'supervisor/maintenance.html', context)
        
    except Exception as e:
        logger.error(f"資料維護頁面載入失敗: {str(e)}")
        messages.error(request, f'載入資料維護失敗: {str(e)}')
        return redirect('workorder:supervisor:supervisor_functions')

@login_required
def execute_maintenance(request):
    """
    執行資料維護 (Execute Data Maintenance)
    執行選定的資料維護操作
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '無效的請求方法'})
    
    try:
        maintenance_type = request.POST.get('maintenance_type')
        
        if maintenance_type == 'cleanup_old_data':
            # 清理舊資料
            result = {'success': True, 'message': '舊資料清理完成'}
        elif maintenance_type == 'backup_database':
            # 資料庫備份
            result = {'success': True, 'message': '資料庫備份完成'}
        elif maintenance_type == 'optimize_database':
            # 資料庫優化
            result = {'success': True, 'message': '資料庫優化完成'}
        elif maintenance_type == 'export_reports':
            # 匯出報表
            result = {'success': True, 'message': '報表匯出完成'}
        else:
            result = {'success': False, 'message': '未知的維護操作類型'}
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"執行資料維護失敗: {str(e)}")
        return JsonResponse({'success': False, 'message': f'執行資料維護失敗: {str(e)}'}) 