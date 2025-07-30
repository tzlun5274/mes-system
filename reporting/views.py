"""
報表模組視圖函數
提供工作報表、工單報表、工時報表的查詢和匯出功能
"""

import logging
from datetime import datetime, date
from typing import Dict, Any

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import (
    REPORT_TYPE_CHOICES, REPORT_FORMAT_CHOICES, DATE_RANGE_CHOICES,
    WorkReport, WorkOrderReport, WorkHourReport, ReportExportLog
)
from .services.work_report_service import WorkReportService
from .services.workorder_report_service import WorkOrderReportService
from .services.work_hour_report_service import WorkHourReportService
from .utils.export_utils import ExportUtils


logger = logging.getLogger(__name__)


def reporting_user_required(user):
    """
    檢查用戶是否為超級用戶或屬於「報表使用者」群組。
    """
    return user.is_superuser or user.groups.filter(name="報表使用者").exists()


@login_required
@user_passes_test(reporting_user_required, login_url='/login/')
def reporting_index(request):
    """報表模組首頁"""
    return render(request, 'reporting/index.html', {
        'report_types': REPORT_TYPE_CHOICES,
        'export_formats': REPORT_FORMAT_CHOICES,
        'date_ranges': DATE_RANGE_CHOICES,
    })


@login_required
@user_passes_test(reporting_user_required, login_url='/login/')
def report_export(request):
    """報表匯出頁面"""
    if request.method == 'GET':
        return render(request, 'reporting/report_export.html', {
            'report_types': REPORT_TYPE_CHOICES,
            'export_formats': REPORT_FORMAT_CHOICES,
            'date_ranges': DATE_RANGE_CHOICES,
        })
    
    elif request.method == 'POST':
        return execute_report_export(request)


@login_required
@user_passes_test(reporting_user_required, login_url='/login/')
def execute_report_export(request):
    """執行報表匯出"""
    try:
        # 獲取表單數據
        report_type = request.POST.get('report_type')
        export_format = request.POST.get('export_format')
        date_range_type = request.POST.get('date_range')
        custom_start_date = request.POST.get('custom_start_date')
        custom_end_date = request.POST.get('custom_end_date')
        
        # 驗證必要參數
        if not all([report_type, export_format, date_range_type]):
            messages.error(request, '請填寫所有必要欄位')
            return redirect('reporting:report_export')
        
        # 獲取日期範圍
        base_service = WorkReportService()
        try:
            if date_range_type == 'CUSTOM':
                if not custom_start_date or not custom_end_date:
                    messages.error(request, '自訂日期範圍需要提供開始和結束日期')
                    return redirect('reporting:report_export')
                
                start_date = datetime.strptime(custom_start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(custom_end_date, '%Y-%m-%d').date()
                date_range = {'start_date': start_date, 'end_date': end_date}
            else:
                date_range = base_service.get_date_range(date_range_type)
        except ValueError as e:
            messages.error(request, f'日期格式錯誤: {str(e)}')
            return redirect('reporting:report_export')
        
        # 生成報表數據
        report_data = generate_report_data(report_type, date_range, request)
        
        if not report_data:
            messages.error(request, '無法生成報表數據')
            return redirect('reporting:report_export')
        
        # 匯出報表
        export_utils = ExportUtils()
        response = export_utils.export_report(
            report_data, report_type, export_format, date_range
        )
        
        # 記錄匯出日誌
        log_export_activity(request, report_type, export_format, date_range_type, 
                          custom_start_date, custom_end_date, 'SUCCESS')
        
        return response
        
    except Exception as e:
        logger.error(f"報表匯出失敗: {str(e)}")
        messages.error(request, f'報表匯出失敗: {str(e)}')
        
        # 記錄錯誤日誌
        log_export_activity(request, report_type, export_format, date_range_type,
                          custom_start_date, custom_end_date, 'ERROR', str(e))
        
        return redirect('reporting:report_export')


def generate_report_data(report_type: str, date_range: Dict[str, date], request) -> Dict[str, Any]:
    """根據報表類型生成報表數據"""
    try:
        if report_type == 'WORK_REPORT':
            service = WorkReportService()
            report_data = service.generate_report(date_range)
            summary_data = service.generate_summary_report(date_range)
            
            return {
                'report_data': report_data,
                'summary_data': summary_data,
                'report_type': '工作報表',
                'date_range': date_range
            }
            
        elif report_type == 'WORKORDER_REPORT':
            service = WorkOrderReportService()
            report_data = service.generate_report(date_range)
            summary_data = service.generate_summary_report(date_range)
            
            return {
                'report_data': report_data,
                'summary_data': summary_data,
                'report_type': '工單報表',
                'date_range': date_range
            }
            
        elif report_type == 'WORK_HOUR_REPORT':
            service = WorkHourReportService()
            report_target = request.POST.get('report_target', 'operator')
            report_data = service.generate_report(date_range, report_target)
            summary_data = service.generate_summary_report(date_range, report_target)
            
            return {
                'report_data': report_data,
                'summary_data': summary_data,
                'report_type': '工時報表',
                'report_target': report_target,
                'date_range': date_range
            }
            
        else:
            raise ValueError(f"不支援的報表類型: {report_type}")
            
    except Exception as e:
        logger.error(f"生成報表數據失敗: {str(e)}")
        return None


def log_export_activity(request, report_type: str, export_format: str, 
                       date_range_type: str, custom_start_date: str, 
                       custom_end_date: str, status: str, error_message: str = None):
    """記錄匯出活動"""
    try:
        ReportExportLog.objects.create(
            report_type=report_type,
            export_format=export_format,
            date_range=date_range_type,
            custom_start_date=datetime.strptime(custom_start_date, '%Y-%m-%d').date() if custom_start_date else None,
            custom_end_date=datetime.strptime(custom_end_date, '%Y-%m-%d').date() if custom_end_date else None,
            export_status=status,
            error_message=error_message,
            created_by=request.user
        )
    except Exception as e:
        logger.error(f"記錄匯出活動失敗: {str(e)}")


@login_required
@user_passes_test(reporting_user_required, login_url='/login/')
def export_log_list(request):
    """匯出日誌列表"""
    logs = ReportExportLog.objects.all().order_by('-created_at')[:100]  # 最近100筆
    
    return render(request, 'reporting/export_log_list.html', {
        'logs': logs
    })


@login_required
@user_passes_test(reporting_user_required, login_url='/login/')
def report_preview(request):
    """報表預覽"""
    if request.method == 'POST':
        try:
            report_type = request.POST.get('report_type')
            date_range_type = request.POST.get('date_range')
            custom_start_date = request.POST.get('custom_start_date')
            custom_end_date = request.POST.get('custom_end_date')
            
            # 獲取日期範圍
            base_service = WorkReportService()
            if date_range_type == 'CUSTOM':
                if not custom_start_date or not custom_end_date:
                    return JsonResponse({'error': '自訂日期範圍需要提供開始和結束日期'}, status=400)
                
                start_date = datetime.strptime(custom_start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(custom_end_date, '%Y-%m-%d').date()
                date_range = {'start_date': start_date, 'end_date': end_date}
            else:
                date_range = base_service.get_date_range(date_range_type)
            
            # 生成預覽數據
            report_data = generate_report_data(report_type, date_range, request)
            
            if not report_data:
                return JsonResponse({'error': '無法生成報表數據'}, status=400)
            
            # 只返回前10筆數據作為預覽
            preview_data = report_data['report_data'][:10] if report_data['report_data'] else []
            
            return JsonResponse({
                'success': True,
                'preview_data': preview_data,
                'total_records': len(report_data['report_data']),
                'summary_data': report_data.get('summary_data', {})
            })
            
        except Exception as e:
            logger.error(f"報表預覽失敗: {str(e)}")
            return JsonResponse({'error': f'報表預覽失敗: {str(e)}'}, status=500)
    
    return JsonResponse({'error': '不支援的請求方法'}, status=405) 