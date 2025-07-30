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

# 新增：從 workorder 模組導入報工模型
from workorder.models import SMTProductionReport, OperatorSupplementReport

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
        
        # 記錄匯出活動
        log_export_activity(
            request, report_type, export_format, date_range_type,
            custom_start_date, custom_end_date, 'success'
        )
        
        # 根據格式匯出
        if export_format == 'EXCEL':
            return export_to_excel(report_data, report_type, date_range)
        elif export_format == 'CSV':
            return export_to_csv(report_data, report_type, date_range)
        elif export_format == 'PDF':
            return export_to_pdf(report_data, report_type, date_range)
        else:
            messages.error(request, '不支援的匯出格式')
            return redirect('reporting:report_export')
            
    except Exception as e:
        logger.error(f'報表匯出失敗: {str(e)}')
        messages.error(request, f'報表匯出失敗: {str(e)}')
        
        # 記錄錯誤
        log_export_activity(
            request, report_type, export_format, date_range_type,
            custom_start_date, custom_end_date, 'error', str(e)
        )
        
        return redirect('reporting:report_export')


def generate_report_data(report_type: str, date_range: Dict[str, date], request) -> Dict[str, Any]:
    """生成報表數據"""
    try:
        if report_type.startswith('WORK_REPORT'):
            service = WorkReportService()
            return service.generate_report(report_type, date_range)
        elif report_type.startswith('WORK_HOUR_REPORT'):
            service = WorkHourReportService()
            return service.generate_report(report_type, date_range)
        elif report_type.startswith('WORKORDER_REPORT'):
            service = WorkOrderReportService()
            return service.generate_report(report_type, date_range)
        else:
            logger.error(f'不支援的報表類型: {report_type}')
            return None
    except Exception as e:
        logger.error(f'生成報表數據失敗: {str(e)}')
        return None


def log_export_activity(request, report_type: str, export_format: str, 
                       date_range_type: str, custom_start_date: str, 
                       custom_end_date: str, status: str, error_message: str = None):
    """記錄匯出活動"""
    try:
        ReportExportLog.objects.create(
            user=request.user,
            report_type=report_type,
            export_format=export_format,
            date_range_type=date_range_type,
            custom_start_date=custom_start_date,
            custom_end_date=custom_end_date,
            status=status,
            error_message=error_message,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    except Exception as e:
        logger.error(f'記錄匯出活動失敗: {str(e)}')


@login_required
@user_passes_test(reporting_user_required, login_url='/login/')
def export_log_list(request):
    """匯出日誌列表"""
    logs = ReportExportLog.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(request, 'reporting/export_log_list.html', {'logs': logs})


@login_required
@user_passes_test(reporting_user_required, login_url='/login/')
def report_preview(request):
    """報表預覽 (AJAX)"""
    try:
        report_type = request.GET.get('report_type')
        date_range_type = request.GET.get('date_range')
        
        if not report_type or not date_range_type:
            return JsonResponse({'error': '缺少必要參數'}, status=400)
        
        # 獲取日期範圍
        service = WorkReportService()
        date_range = service.get_date_range(date_range_type)
        
        # 生成預覽數據
        preview_data = generate_report_data(report_type, date_range, request)
        
        if preview_data:
            return JsonResponse({
                'success': True,
                'data': preview_data[:10],  # 只返回前10筆作為預覽
                'total_count': len(preview_data)
            })
        else:
            return JsonResponse({'error': '無法生成預覽數據'}, status=500)
            
    except Exception as e:
        logger.error(f'報表預覽失敗: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


# ==================== 從 workorder 模組移過來的報表匯出功能 ====================

@login_required
def smt_supplement_export(request):
    """
    SMT補登報工匯出功能 - Excel格式
    按照圖片格式：設備、公司別、報工日期、開始時間、完成時間、製令號碼、機種名稱、工序、工作數量、不良品數量、備註
    """
    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from datetime import datetime
    
    # 建立工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "SMT補登報工記錄"
    
    # 設定標題樣式
    header_font = Font(name='微軟正黑體', size=12, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')
    
    # 設定資料樣式
    data_font = Font(name='微軟正黑體', size=11)
    data_alignment = Alignment(horizontal='center', vertical='center')
    
    # 設定邊框
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # 標題行 - 按照圖片格式，增加異常紀錄欄位
    headers = [
        '設備', '公司別', '報工日期', '開始時間', '完成時間', '製令號碼', 
        '機種名稱', '工序', '工作數量', '不良品數量', '備註', '異常紀錄'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # 查詢資料
    reports = SMTProductionReport.objects.all().order_by('-work_date', '-start_time')
    
    # 寫入資料行
    for row, report in enumerate(reports, 2):
        # 取得公司別（使用公司代號）
        company_code = 'COMP001'  # 預設值
        if report.workorder and report.workorder.company_code:
            company_code = report.workorder.company_code
        elif hasattr(report, 'company_config') and report.company_config:
            company_code = report.company_config.company_code
        
        # 取得機種名稱（產品編號）
        product_name = ''
        if report.workorder and report.workorder.product_code:
            product_name = report.workorder.product_code
        elif report.rd_product_code:
            product_name = report.rd_product_code
        
        # 取得製令號碼（工單號）
        workorder_number = ''
        if report.workorder and report.workorder.order_number:
            workorder_number = report.workorder.order_number
        elif report.rd_workorder_number:
            workorder_number = report.rd_workorder_number
        
        # 取得不良品數量（預設為0）
        defect_quantity = getattr(report, 'defect_quantity', 0) or 0
        
        ws.cell(row=row, column=1, value=report.equipment.name if report.equipment else '')
        ws.cell(row=row, column=2, value=company_code)
        ws.cell(row=row, column=3, value=report.work_date.strftime('%Y-%m-%d') if report.work_date else '')
        # 格式化時間為12小時制
        def format_time_12h(time_obj):
            """將時間格式化為12小時制格式"""
            if not time_obj:
                return ''
            return time_obj.strftime('%I:%M:%S %p')
        
        ws.cell(row=row, column=4, value=format_time_12h(report.start_time))
        ws.cell(row=row, column=5, value=format_time_12h(report.end_time))
        ws.cell(row=row, column=6, value=workorder_number)
        ws.cell(row=row, column=7, value=product_name)
        ws.cell(row=row, column=8, value=report.operation if report.operation else '')
        ws.cell(row=row, column=9, value=report.work_quantity)
        ws.cell(row=row, column=10, value=defect_quantity)
        ws.cell(row=row, column=11, value=report.remarks or '')
        ws.cell(row=row, column=12, value=getattr(report, 'abnormal_notes', '') or '')
        
        # 套用樣式
        for col in range(1, 13):
            cell = ws.cell(row=row, column=col)
            cell.font = data_font
            cell.alignment = data_alignment
            cell.border = thin_border
    
    # 自動調整欄寬
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 15
    
    # 建立回應
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="smt_supplement_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    # 儲存檔案
    wb.save(response)
    return response


@login_required
def operator_supplement_export(request):
    """
    作業員補登報工匯出功能 - Excel格式
    """
    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from datetime import datetime
    
    # 建立工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "作業員補登報工記錄"
    
    # 設定標題樣式
    header_font = Font(name='微軟正黑體', size=12, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')
    
    # 設定資料樣式
    data_font = Font(name='微軟正黑體', size=11)
    data_alignment = Alignment(horizontal='center', vertical='center')
    
    # 設定邊框
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # 標題行 - 增加異常紀錄欄位
    headers = [
        '報工日期', '開始時間', '結束時間', '作業員', '工單號', '工序', 
        '報工數量', '不良品數量', '工時', '審核狀態', '備註', '異常紀錄', '建立時間'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # 查詢資料
    reports = OperatorSupplementReport.objects.all().order_by('-work_date', '-start_time')
    
    # 寫入資料行
    for row, report in enumerate(reports, 2):
        # 格式化時間為12小時制
        def format_time_12h(time_obj):
            """將時間格式化為12小時制格式"""
            if not time_obj:
                return ''
            return time_obj.strftime('%I:%M:%S %p')
        
        ws.cell(row=row, column=1, value=report.work_date.strftime('%Y-%m-%d') if report.work_date else '')
        ws.cell(row=row, column=2, value=format_time_12h(report.start_time))
        ws.cell(row=row, column=3, value=format_time_12h(report.end_time))
        ws.cell(row=row, column=4, value=report.operator.name if report.operator else '')
        ws.cell(row=row, column=5, value=report.workorder.order_number if report.workorder else '')
        ws.cell(row=row, column=6, value=report.process.name if report.process else '')
        ws.cell(row=row, column=7, value=report.work_quantity)
        ws.cell(row=row, column=8, value=report.defect_quantity)
        ws.cell(row=row, column=9, value=f"{report.work_hours:.2f}" if report.work_hours else '')
        ws.cell(row=row, column=10, value=report.get_approval_status_display())
        ws.cell(row=row, column=11, value=report.remarks or '')
        ws.cell(row=row, column=12, value=report.abnormal_notes or '')  # 異常紀錄欄位
        ws.cell(row=row, column=13, value=report.created_at.strftime('%Y-%m-%d %H:%M') if report.created_at else '')
        
        # 套用樣式
        for col in range(1, 14):
            cell = ws.cell(row=row, column=col)
            cell.font = data_font
            cell.alignment = data_alignment
            cell.border = thin_border
    
    # 自動調整欄寬
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 15
    
    # 建立回應
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="operator_supplement_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    # 儲存檔案
    wb.save(response)
    return response


@login_required
def pending_approval_list(request):
    """待審核報工列表"""
    from django.db.models import Q
    
    # 查詢待審核的作業員報工
    operator_pending = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(approval_status='pending').order_by('-created_at')
    
    # 查詢待審核的SMT報工
    smt_pending = SMTProductionReport.objects.select_related(
        'equipment', 'workorder'
    ).filter(approval_status='pending').order_by('-created_at')
    
    # 合併數據
    pending_reports = []
    
    for report in operator_pending:
        pending_reports.append({
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
            'remarks': report.remarks,
        })
    
    for report in smt_pending:
        pending_reports.append({
            'id': report.id,
            'report_type': 'smt',
            'operator': report.equipment.name if report.equipment else '-',
            'workorder': report.workorder.order_number if report.workorder else '-',
            'process': report.operation,
            'quantity': report.work_quantity,
            'defect_quantity': getattr(report, 'defect_quantity', 0),
            'work_date': report.work_date,
            'start_time': report.start_time,
            'end_time': report.end_time,
            'created_at': report.created_at,
            'remarks': getattr(report, 'remarks', ''),
        })
    
    # 按建立時間排序
    pending_reports.sort(key=lambda x: x['created_at'], reverse=True)
    
    context = {
        'pending_reports': pending_reports,
        'operator_count': operator_pending.count(),
        'smt_count': smt_pending.count(),
        'total_count': len(pending_reports),
    }
    
    return render(request, "reporting/pending_approval_list.html", context)


@login_required
def approved_reports_list(request):
    """已審核報工列表"""
    from django.db.models import Q
    
    # 查詢已審核的作業員報工
    operator_approved = OperatorSupplementReport.objects.select_related(
        'operator', 'workorder', 'process'
    ).filter(approval_status='approved').order_by('-approved_at')
    
    # 查詢已審核的SMT報工
    smt_approved = SMTProductionReport.objects.select_related(
        'equipment', 'workorder'
    ).filter(approval_status='approved').order_by('-approved_at')
    
    # 合併數據
    approved_reports = []
    
    for report in operator_approved:
        approved_reports.append({
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
        approved_reports.append({
            'id': report.id,
            'report_type': 'smt',
            'operator': report.equipment.name if report.equipment else '-',
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
    
    # 按審核時間排序
    approved_reports.sort(key=lambda x: x['approved_at'], reverse=True)
    
    context = {
        'approved_reports': approved_reports,
        'operator_count': operator_approved.count(),
        'smt_count': smt_approved.count(),
        'total_count': len(approved_reports),
    }
    
    return render(request, "reporting/approved_reports_list.html", context)


def export_to_excel(data, report_type, date_range):
    """匯出為Excel格式"""
    # 實作Excel匯出邏輯
    pass


def export_to_csv(data, report_type, date_range):
    """匯出為CSV格式"""
    # 實作CSV匯出邏輯
    pass


def export_to_pdf(data, report_type, date_range):
    """匯出為PDF格式"""
    # 實作PDF匯出邏輯
    pass 