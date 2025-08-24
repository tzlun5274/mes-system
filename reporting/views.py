"""
報表模組視圖
提供各種報表功能的網頁介面
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from datetime import datetime, timedelta
import calendar
from decimal import Decimal
import logging

from .models import WorkTimeReportSummary, WorkTimeReportDetail, ReportSchedule, ReportExecutionLog
from .services import WorkTimeReportService, WorkHourReportService, ReportGeneratorService

logger = logging.getLogger(__name__)


@login_required
def index(request):
    """報表首頁"""
    context = {
        'page_title': '報表管理',
        'current_page': 'reporting',
    }
    return render(request, 'reporting/index.html', context)


@login_required
def work_time_report_index(request):
    """工作時數報表首頁"""
    context = {
        'page_title': '工作時數報表',
        'current_page': 'work_time_report',
    }
    return render(request, 'reporting/work_time_report.html', context)


@login_required
def work_time_daily_report(request):
    """工作時數日報表"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        report_date = request.POST.get('report_date')
        format = request.POST.get('format', 'excel')
        
        try:
            # 解析日期
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
            
            # 生成日報表
            service = WorkTimeReportService()
            summary = service.generate_daily_work_time_report(report_date, company_code)
            
            # 獲取詳細資料
            detail = WorkTimeReportDetail.objects.filter(summary=summary).first()
            
            if format in ['excel', 'csv']:
                # 生成檔案
                generator = ReportGeneratorService()
                result = generator.generate_work_time_report(
                    company_code, report_date, report_date, 'daily', format
                )
                
                # 下載檔案
                with open(result['file_path'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
            else:
                # 顯示網頁報表
                context = {
                    'report_type': '工作時數日報表',
                    'company_code': company_code,
                    'report_date': report_date,
                    'summary': summary,
                    'detail': detail,
                    'generated_at': timezone.now(),
                }
                return render(request, 'reporting/work_time_daily_report.html', context)
                
        except Exception as e:
            messages.error(request, f'生成工作時數日報表失敗: {str(e)}')
            return redirect('reporting:work_time_report_index')
    
    # GET 請求顯示表單
    current_date = timezone.now().date()
    
    context = {
        'current_date': current_date,
        'page_title': '工作時數日報表',
    }
    return render(request, 'reporting/work_time_daily_report_form.html', context)


@login_required
def work_time_weekly_report(request):
    """工作時數週報表"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        week_start = request.POST.get('week_start')
        format = request.POST.get('format', 'excel')
        
        try:
            # 解析日期
            week_start = datetime.strptime(week_start, '%Y-%m-%d').date()
            
            # 生成週報表
            service = WorkTimeReportService()
            summary = service.generate_weekly_work_time_report(week_start, company_code)
            
            # 計算週結束日期
            week_end = week_start + timedelta(days=6)
            
            if format in ['excel', 'csv']:
                # 生成檔案
                generator = ReportGeneratorService()
                result = generator.generate_work_time_report(
                    company_code, week_start, week_end, 'weekly', format
                )
                
                # 下載檔案
                with open(result['file_path'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
            else:
                # 顯示網頁報表
                context = {
                    'report_type': '工作時數週報表',
                    'company_code': company_code,
                    'week_start': week_start,
                    'week_end': week_end,
                    'summary': summary,
                    'generated_at': timezone.now(),
                }
                return render(request, 'reporting/work_time_weekly_report.html', context)
                
        except Exception as e:
            messages.error(request, f'生成工作時數週報表失敗: {str(e)}')
            return redirect('reporting:work_time_report_index')
    
    # GET 請求顯示表單
    current_date = timezone.now().date()
    # 計算本週開始日期（週一）
    week_start = current_date - timedelta(days=current_date.weekday())
    
    context = {
        'current_date': current_date,
        'week_start': week_start,
        'page_title': '工作時數週報表',
    }
    return render(request, 'reporting/work_time_weekly_report_form.html', context)


@login_required
def work_time_monthly_report(request):
    """工作時數月報表"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
        format = request.POST.get('format', 'excel')
        
        try:
            # 生成月報表
            service = WorkTimeReportService()
            summary = service.generate_monthly_work_time_report(year, month, company_code)
            
            # 計算月份開始和結束日期
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            if format in ['excel', 'csv']:
                # 生成檔案
                generator = ReportGeneratorService()
                result = generator.generate_work_time_report(
                    company_code, month_start, month_end, 'monthly', format
                )
                
                # 下載檔案
                with open(result['file_path'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
            else:
                # 顯示網頁報表
                context = {
                    'report_type': '工作時數月報表',
                    'company_code': company_code,
                    'year': year,
                    'month': month,
                    'month_start': month_start,
                    'month_end': month_end,
                    'summary': summary,
                    'generated_at': timezone.now(),
                }
                return render(request, 'reporting/work_time_monthly_report.html', context)
                
        except Exception as e:
            messages.error(request, f'生成工作時數月報表失敗: {str(e)}')
            return redirect('reporting:work_time_report_index')
    
    # GET 請求顯示表單
    current_year = timezone.now().year
    current_month = timezone.now().month
    
    context = {
        'current_year': current_year,
        'current_month': current_month,
        'years': range(current_year - 5, current_year + 1),
        'months': range(1, 13),
        'page_title': '工作時數月報表',
    }
    return render(request, 'reporting/work_time_monthly_report_form.html', context)


@login_required
def work_time_report_list(request):
    """工作時數報表列表"""
    # 獲取查詢參數
    company_code = request.GET.get('company_code', '')
    report_type = request.GET.get('report_type', 'work_time')
    time_dimension = request.GET.get('time_dimension', 'daily')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # 構建查詢條件
    filters = Q(report_type=report_type)
    
    if company_code:
        filters &= Q(company_code=company_code)
    
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            filters &= Q(report_date__range=[start_date, end_date])
        except ValueError:
            pass
    
    # 查詢報表資料
    reports = WorkTimeReportSummary.objects.filter(filters).order_by('-report_date')
    
    # 分頁
    from django.core.paginator import Paginator
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'company_code': company_code,
        'report_type': report_type,
        'time_dimension': time_dimension,
        'start_date': start_date,
        'end_date': end_date,
        'page_title': '工作時數報表列表',
    }
    return render(request, 'reporting/work_time_report_list.html', context)


@login_required
def work_time_report_detail(request, report_id):
    """工作時數報表詳情"""
    report = get_object_or_404(WorkTimeReportSummary, id=report_id)
    detail = WorkTimeReportDetail.objects.filter(summary=report).first()
    
    context = {
        'report': report,
        'detail': detail,
        'page_title': f'工作時數報表詳情 - {report.report_date}',
    }
    return render(request, 'reporting/work_time_report_detail.html', context)


@login_required
def work_time_report_export(request):
    """工作時數報表匯出"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        time_dimension = request.POST.get('time_dimension', 'daily')
        format = request.POST.get('format', 'excel')
        
        try:
            # 解析日期
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # 生成報表
            generator = ReportGeneratorService()
            result = generator.generate_work_time_report(
                company_code, start_date, end_date, time_dimension, format
            )
            
            # 下載檔案
            with open(result['file_path'], 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                return response
                
        except Exception as e:
            messages.error(request, f'匯出工作時數報表失敗: {str(e)}')
            return redirect('reporting:work_time_report_index')
    
    # GET 請求顯示表單
    current_date = timezone.now().date()
    
    context = {
        'current_date': current_date,
        'page_title': '工作時數報表匯出',
    }
    return render(request, 'reporting/work_time_report_export.html', context)


# 保留原有的視圖函數
@login_required
def work_hour_report_index(request):
    """工作時數報表首頁 - 保留原有功能"""
    return render(request, 'reporting/work_hour_report.html')


@login_required
def daily_report(request):
    """日報表 - 保留原有功能"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
        day = int(request.POST.get('day'))
        format = request.POST.get('format', 'excel')
        
        try:
            service = WorkHourReportService()
            generator = ReportGeneratorService()
            
            # 取得報表資料
            data = service.get_daily_report(company_code, year, month, day)
            summary = service.get_daily_summary(company_code, year, month, day)
            
            if format in ['excel', 'csv']:
                # 生成檔案
                result = generator.generate_daily_report(company_code, year, month, day, format)
                
                # 下載檔案
                with open(result['file_path'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
            else:
                # 顯示網頁報表
                context = {
                    'report_type': '日報表',
                    'company_code': company_code,
                    'year': year,
                    'month': month,
                    'day': day,
                    'work_date': datetime(year, month, day).date(),
                    'summary': summary,
                    'data': data,
                    'generated_at': timezone.now(),
                }
                return render(request, 'reporting/daily_report.html', context)
                
        except Exception as e:
            messages.error(request, f'生成日報表失敗: {str(e)}')
            return redirect('reporting:work_hour_report_index')
    
    # GET 請求顯示表單
    current_year = timezone.now().year
    current_month = timezone.now().month
    current_day = timezone.now().day
    
    context = {
        'current_year': current_year,
        'current_month': current_month,
        'current_day': current_day,
        'years': range(current_year - 5, current_year + 1),
        'months': range(1, 13),
        'days': range(1, 32),
    }
    return render(request, 'reporting/daily_report_form.html', context)


@csrf_exempt
def operator_daily_report(request):
    """作業員日工作時數報表"""
    if request.method == 'POST':
        operator = request.POST.get('operator')
        date = request.POST.get('date')
        format = request.POST.get('format', 'excel')
        
        try:
            from workorder.fill_work.models import FillWork
            from workorder.onsite_reporting.models import OnsiteReport
            from django.db.models import Sum, Count, Avg, Q
            from decimal import Decimal
            
            # 解析日期
            report_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            # 查詢該日期的所有作業員工作記錄（填報作業）
            fill_works = FillWork.objects.filter(
                work_date=report_date
            )
            
            # 查詢該日期的所有作業員工作記錄（現場作業）
            onsite_reports = OnsiteReport.objects.filter(
                work_date=report_date
            )
            
            # 如果選擇了特定作業員，則過濾資料
            if operator and operator != 'all':
                fill_works = fill_works.filter(operator=operator)
                onsite_reports = onsite_reports.filter(operator=operator)
            
            # 合併所有作業員
            all_operators = set()
            all_operators.update(fill_works.values_list('operator', flat=True))
            all_operators.update(onsite_reports.values_list('operator', flat=True))
            
            # 按作業員分組統計
            detailed_data = []
            total_work_hours = Decimal('0.00')
            total_overtime_hours = Decimal('0.00')
            total_onsite_hours = Decimal('0.00')
            total_work_quantity = 0
            total_defect_quantity = 0
            total_fill_work_records = 0
            total_onsite_records = 0
            
            for operator in sorted(all_operators):
                # 填報作業統計 - 使用實際的工作時數和加班時數欄位
                operator_fill_works = fill_works.filter(operator=operator)
                fill_work_stats = operator_fill_works.aggregate(
                    total_work_hours=Sum('work_hours_calculated'),
                    total_overtime_hours=Sum('overtime_hours_calculated'),
                    total_work_quantity=Sum('work_quantity'),
                    total_defect_quantity=Sum('defect_quantity'),
                    work_records_count=Count('id')
                )
                
                # 處理None值
                fill_work_stats = {
                    'total_work_hours': fill_work_stats['total_work_hours'] or Decimal('0.00'),
                    'total_overtime_hours': fill_work_stats['total_overtime_hours'] or Decimal('0.00'),
                    'total_work_quantity': fill_work_stats['total_work_quantity'] or 0,
                    'total_defect_quantity': fill_work_stats['total_defect_quantity'] or 0,
                    'work_records_count': fill_work_stats['work_records_count'] or 0
                }
                
                # 現場作業統計 - 使用實際的工作分鐘數欄位
                operator_onsite_reports = onsite_reports.filter(operator=operator)
                onsite_stats = operator_onsite_reports.aggregate(
                    total_work_minutes=Sum('work_minutes'),
                    total_work_quantity=Sum('work_quantity'),
                    total_defect_quantity=Sum('defect_quantity'),
                    work_records_count=Count('id')
                )
                
                # 處理None值
                onsite_stats = {
                    'total_work_minutes': onsite_stats['total_work_minutes'] or 0,
                    'total_work_quantity': onsite_stats['total_work_quantity'] or 0,
                    'total_defect_quantity': onsite_stats['total_defect_quantity'] or 0,
                    'work_records_count': onsite_stats['work_records_count'] or 0
                }
                
                # 轉換現場作業分鐘為小時
                onsite_hours = Decimal(str(onsite_stats['total_work_minutes'] / 60)).quantize(Decimal('0.01'))
                
                # 合計統計
                operator_total_work_hours = fill_work_stats['total_work_hours'] + onsite_hours
                operator_total_overtime_hours = fill_work_stats['total_overtime_hours']
                operator_total_all_hours = operator_total_work_hours + operator_total_overtime_hours
                operator_total_work_quantity = fill_work_stats['total_work_quantity'] + onsite_stats['total_work_quantity']
                operator_total_defect_quantity = fill_work_stats['total_defect_quantity'] + onsite_stats['total_defect_quantity']
                operator_total_records = fill_work_stats['work_records_count'] + onsite_stats['work_records_count']
                
                # 累計總統計
                total_work_hours += fill_work_stats['total_work_hours']
                total_overtime_hours += fill_work_stats['total_overtime_hours']
                total_onsite_hours += onsite_hours
                total_work_quantity += operator_total_work_quantity
                total_defect_quantity += operator_total_defect_quantity
                total_fill_work_records += fill_work_stats['work_records_count']
                total_onsite_records += onsite_stats['work_records_count']
                
                # 獲取該作業員的詳細工作記錄
                work_details = []
                
                # 填報作業詳細記錄
                for work in operator_fill_works:
                    work_details.append({
                        'type': '填報作業',
                        'workorder': work.workorder,
                        'product_id': work.product_id,
                        'process': work.process.name if work.process else '',
                        'start_time': work.start_time,
                        'end_time': work.end_time,
                        'work_hours': work.work_hours_calculated,
                        'overtime_hours': work.overtime_hours_calculated,
                        'work_quantity': work.work_quantity,
                        'defect_quantity': work.defect_quantity,
                        'equipment': work.equipment,
                        'status': work.get_approval_status_display(),
                    })
                
                # 現場作業詳細記錄
                for report in operator_onsite_reports:
                    work_details.append({
                        'type': '現場作業',
                        'workorder': report.workorder,
                        'product_id': report.product_id,
                        'process': report.process,
                        'start_time': report.start_datetime.time(),
                        'end_time': report.end_datetime.time() if report.end_datetime else None,
                        'work_hours': Decimal(str(report.work_minutes / 60)).quantize(Decimal('0.01')),
                        'overtime_hours': Decimal('0.00'),
                        'work_quantity': report.work_quantity,
                        'defect_quantity': report.defect_quantity,
                        'equipment': report.equipment,
                        'status': report.get_status_display(),
                    })
                
                # 按開始時間排序
                work_details.sort(key=lambda x: x['start_time'])
                
                detailed_data.append({
                    'operator': operator,
                    'total_work_hours': operator_total_work_hours,
                    'total_overtime_hours': operator_total_overtime_hours,
                    'total_onsite_hours': onsite_hours,
                    'total_all_hours': operator_total_all_hours,
                    'total_work_quantity': operator_total_work_quantity,
                    'total_defect_quantity': operator_total_defect_quantity,
                    'fill_work_records_count': fill_work_stats['work_records_count'],
                    'onsite_records_count': onsite_stats['work_records_count'],
                    'total_records_count': operator_total_records,
                    'defect_rate': (operator_total_defect_quantity / operator_total_work_quantity * 100) if operator_total_work_quantity > 0 else 0,
                    'work_details': work_details,
                })
            
            # 按總工作時數排序
            detailed_data.sort(key=lambda x: x['total_all_hours'], reverse=True)
            
            summary = {
                'total_work_hours': total_work_hours,
                'total_overtime_hours': total_overtime_hours,
                'total_onsite_hours': total_onsite_hours,
                'total_all_hours': total_work_hours + total_overtime_hours + total_onsite_hours,
                'total_operators': len(all_operators),
                'total_work_quantity': total_work_quantity,
                'total_defect_quantity': total_defect_quantity,
                'total_fill_work_records': total_fill_work_records,
                'total_onsite_records': total_onsite_records,
                'total_records': total_fill_work_records + total_onsite_records,
                'avg_work_hours_per_operator': (total_work_hours + total_overtime_hours + total_onsite_hours) / len(all_operators) if all_operators else 0,
                'defect_rate': (total_defect_quantity / total_work_quantity * 100) if total_work_quantity > 0 else 0,
            }
            
            if format in ['excel', 'csv']:
                # 生成Excel檔案，包含統計和明細兩個工作表
                try:
                    import openpyxl
                    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
                    from openpyxl.utils import get_column_letter
                    
                    # 建立工作簿
                    wb = openpyxl.Workbook()
                    
                    # 設定樣式
                    header_font = Font(bold=True, color="FFFFFF", size=12)
                    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                    header_alignment = Alignment(horizontal="center", vertical="center")
                    border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    
                    # 工作表1：統計摘要
                    ws_summary = wb.active
                    ws_summary.title = "統計摘要"
                    
                    # 寫入標題
                    ws_summary.merge_cells('A1:I1')
                    title_cell = ws_summary['A1']
                    title_cell.value = f"作業員日工作時數報表 - {date}"
                    title_cell.font = Font(bold=True, size=16)
                    title_cell.alignment = Alignment(horizontal="center")
                    
                    # 寫入統計摘要
                    summary_headers = [
                        '總工作時數', '總作業員數', '總工作數量', '總記錄數', 
                        '不良率', '平均時數', '填報作業時數', '現場作業時數', '加班時數'
                    ]
                    summary_values = [
                         f"{float(summary['total_all_hours']):.1f}h",
                         summary['total_operators'],
                         summary['total_work_quantity'],
                         summary['total_records'],
                         f"{float(summary['defect_rate']):.1f}%",
                         f"{float(summary['avg_work_hours_per_operator']):.1f}h",
                         f"{float(summary['total_work_hours']):.1f}h",
                         f"{float(summary['total_onsite_hours']):.1f}h",
                         f"{float(summary['total_overtime_hours']):.1f}h"
                     ]
                    
                    for col, (header, value) in enumerate(zip(summary_headers, summary_values), 1):
                        # 寫入標題
                        header_cell = ws_summary.cell(row=3, column=col, value=header)
                        header_cell.font = header_font
                        header_cell.fill = header_fill
                        header_cell.alignment = header_alignment
                        header_cell.border = border
                        
                        # 寫入數值
                        value_cell = ws_summary.cell(row=4, column=col, value=value)
                        value_cell.font = Font(bold=True, size=14)
                        value_cell.alignment = Alignment(horizontal="center")
                        value_cell.border = border
                    
                    # 工作表2：作業員統計
                    ws_stats = wb.create_sheet("作業員統計")
                    
                    # 寫入標題
                    ws_stats.merge_cells('A1:H1')
                    stats_title_cell = ws_stats['A1']
                    stats_title_cell.value = f"作業員統計 - {date}"
                    stats_title_cell.font = Font(bold=True, size=16)
                    stats_title_cell.alignment = Alignment(horizontal="center")
                    
                    # 統計表頭
                    stats_headers = [
                        '作業員', '總工作時數', '填報作業', '現場作業', 
                        '加班時數', '工作數量', '不良品', '記錄數'
                    ]
                    
                    for col, header in enumerate(stats_headers, 1):
                        cell = ws_stats.cell(row=3, column=col, value=header)
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment
                        cell.border = border
                    
                    # 按作業員排序（英文在前，中文在後）
                    sorted_stats_data = sorted(detailed_data, key=lambda x: (
                         not x['operator'][0].isalpha(),  # 英文在前
                         x['operator']  # 同類型按字母順序
                     ))
                     
                    # 寫入統計資料
                    for row, item in enumerate(sorted_stats_data, 4):
                        ws_stats.cell(row=row, column=1, value=item['operator']).border = border
                        ws_stats.cell(row=row, column=2, value=f"{float(item['total_all_hours']):.1f}h").border = border
                        ws_stats.cell(row=row, column=3, value=f"{float(item['total_work_hours']):.1f}h").border = border
                        ws_stats.cell(row=row, column=4, value=f"{float(item['total_onsite_hours']):.1f}h").border = border
                        ws_stats.cell(row=row, column=5, value=f"{float(item['total_overtime_hours']):.1f}h").border = border
                        ws_stats.cell(row=row, column=6, value=item['total_work_quantity']).border = border
                        ws_stats.cell(row=row, column=7, value=item['total_defect_quantity']).border = border
                        ws_stats.cell(row=row, column=8, value=item['fill_work_records_count'] + item['onsite_records_count']).border = border
                    
                    # 工作表3：明細記錄
                    ws_detail = wb.create_sheet("明細記錄")
                    
                    # 寫入標題
                    ws_detail.merge_cells('A1:K1')
                    detail_title_cell = ws_detail['A1']
                    detail_title_cell.value = f"明細記錄 - {date}"
                    detail_title_cell.font = Font(bold=True, size=16)
                    detail_title_cell.alignment = Alignment(horizontal="center")
                    
                    # 明細表頭
                    detail_headers = [
                        '作業員', '工序', '工作日期', '開始時間', '結束時間',
                        '工作時數', '加班時數', '工作數量', '不良品', '工單號', '產品編號'
                    ]
                    
                    for col, header in enumerate(detail_headers, 1):
                        cell = ws_detail.cell(row=3, column=col, value=header)
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment
                        cell.border = border
                    
                    # 收集所有工作記錄
                    allWorkRecords = []
                    for item in detailed_data:
                        for work in item['work_details']:
                            allWorkRecords.append({
                                'operator': item['operator'],
                                'process': work['process'],
                                'work_date': date,
                                'start_time': work['start_time'],
                                'end_time': work['end_time'],
                                'work_hours': work['work_hours'],
                                'overtime_hours': work['overtime_hours'],
                                'work_quantity': work['work_quantity'],
                                'defect_quantity': work['defect_quantity'],
                                'workorder': work['workorder'],
                                'product_id': work['product_id']
                            })
                    
                    # 按作業員排序（英文在前，中文在後）
                    allWorkRecords.sort(key=lambda x: (
                        not x['operator'][0].isalpha(),  # 英文在前
                        x['operator']  # 同類型按字母順序
                    ))
                    
                    # 寫入明細資料
                    for row, work in enumerate(allWorkRecords, 4):
                         ws_detail.cell(row=row, column=1, value=work['operator']).border = border
                         ws_detail.cell(row=row, column=2, value=work['process']).border = border
                         ws_detail.cell(row=row, column=3, value=work['work_date']).border = border
                         ws_detail.cell(row=row, column=4, value=str(work['start_time'])).border = border
                         ws_detail.cell(row=row, column=5, value=str(work['end_time']) if work['end_time'] else '-').border = border
                         ws_detail.cell(row=row, column=6, value=f"{float(work['work_hours']):.1f}h").border = border
                         ws_detail.cell(row=row, column=7, value=f"{float(work['overtime_hours']):.1f}h").border = border
                         ws_detail.cell(row=row, column=8, value=work['work_quantity']).border = border
                         ws_detail.cell(row=row, column=9, value=work['defect_quantity']).border = border
                         ws_detail.cell(row=row, column=10, value=work['workorder']).border = border
                         ws_detail.cell(row=row, column=11, value=work['product_id']).border = border
                    
                    # 調整欄寬
                    for ws in [ws_summary, ws_stats, ws_detail]:
                        for col in range(1, max(len(summary_headers), len(stats_headers), len(detail_headers)) + 1):
                            ws.column_dimensions[get_column_letter(col)].width = 15
                    
                    # 建立回應
                    response = HttpResponse(
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    filename = f"作業員日工作時數報表_{date}_{operator or 'all'}.xlsx"
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    # 儲存檔案
                    wb.save(response)
                    return response
                    
                except ImportError:
                    messages.error(request, 'Excel匯出功能需要安裝openpyxl套件')
                    return redirect('reporting:work_hour_report_index')
                except Exception as e:
                    messages.error(request, f'Excel匯出失敗: {str(e)}')
                    return redirect('reporting:work_hour_report_index')
            else:
                # 檢查是否為AJAX請求
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # 返回JSON資料
                    return JsonResponse({
                        'success': True,
                        'summary': summary,
                        'data': detailed_data,
                        'generated_at': timezone.now().isoformat(),
                    })
                else:
                    # 顯示網頁報表
                    context = {
                        'report_type': '作業員日工作時數報表',
                        'operator': operator,
                        'date': date,
                        'summary': summary,
                        'data': detailed_data,
                        'generated_at': timezone.now(),
                    }
                    return render(request, 'reporting/daily_report_form.html', context)
                
        except Exception as e:
            error_msg = f'生成日報表失敗: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            else:
                messages.error(request, error_msg)
                return redirect('reporting:work_hour_report_index')
    
    # GET 請求顯示表單
    current_date = timezone.now().date()
    
    # 獲取所有作業員列表
    from workorder.fill_work.models import FillWork
    from workorder.onsite_reporting.models import OnsiteReport
    
    # 從填報作業和現場作業中獲取所有作業員
    fill_work_operators = FillWork.objects.values_list('operator', flat=True).distinct()
    onsite_operators = OnsiteReport.objects.values_list('operator', flat=True).distinct()
    
    # 合併並去重
    all_operators = sorted(set(list(fill_work_operators) + list(onsite_operators)))
    
    context = {
        'current_date': current_date,
        'operators': all_operators,
    }
    return render(request, 'reporting/daily_report_form.html', context)


@login_required
def weekly_report(request):
    """週報表"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        year = int(request.POST.get('year'))
        week = int(request.POST.get('week'))
        format = request.POST.get('format', 'excel')
        
        try:
            service = WorkHourReportService()
            generator = ReportGeneratorService()
            
            # 取得報表資料
            data = service.get_weekly_report(company_code, year, week)
            summary = service.get_weekly_summary(company_code, year, week)
            
            if format in ['excel', 'csv']:
                # 生成檔案
                result = generator.generate_weekly_report(company_code, year, week, format)
                
                # 下載檔案
                with open(result['file_path'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
            else:
                # 顯示網頁報表
                context = {
                    'report_type': '週報表',
                    'company_code': company_code,
                    'year': year,
                    'week': week,
                    'summary': summary,
                    'data': data,
                    'generated_at': timezone.now(),
                }
                return render(request, 'reporting/weekly_report.html', context)
                
        except Exception as e:
            messages.error(request, f'生成週報表失敗: {str(e)}')
            return redirect('reporting:work_hour_report_index')
    
    # GET 請求顯示表單
    current_year = timezone.now().year
    current_week = timezone.now().isocalendar()[1]
    
    context = {
        'current_year': current_year,
        'current_week': current_week,
        'years': range(current_year - 5, current_year + 1),
        'weeks': range(1, 53),
    }
    return render(request, 'reporting/weekly_report_form.html', context)


@login_required
def monthly_report(request):
    """月報表"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
        format = request.POST.get('format', 'excel')
        
        try:
            service = WorkHourReportService()
            generator = ReportGeneratorService()
            
            # 取得報表資料
            data = service.get_monthly_report(company_code, year, month)
            summary = service.get_monthly_summary(company_code, year, month)
            
            if format in ['excel', 'csv']:
                # 生成檔案
                result = generator.generate_monthly_report(company_code, year, month, format)
                
                # 下載檔案
                with open(result['file_path'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
            else:
                # 顯示網頁報表
                context = {
                    'report_type': '月報表',
                    'company_code': company_code,
                    'year': year,
                    'month': month,
                    'summary': summary,
                    'data': data,
                    'generated_at': timezone.now(),
                }
                return render(request, 'reporting/monthly_report.html', context)
                
        except Exception as e:
            messages.error(request, f'生成月報表失敗: {str(e)}')
            return redirect('reporting:work_hour_report_index')
    
    # GET 請求顯示表單
    current_year = timezone.now().year
    current_month = timezone.now().month
    
    context = {
        'current_year': current_year,
        'current_month': current_month,
        'years': range(current_year - 5, current_year + 1),
        'months': range(1, 13),
    }
    return render(request, 'reporting/monthly_report_form.html', context)


@login_required
def quarterly_report(request):
    """季報表"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        year = int(request.POST.get('year'))
        quarter = int(request.POST.get('quarter'))
        format = request.POST.get('format', 'excel')
        
        try:
            service = WorkHourReportService()
            generator = ReportGeneratorService()
            
            # 取得報表資料
            data = service.get_quarterly_report(company_code, year, quarter)
            summary = service.get_quarterly_summary(company_code, year, quarter)
            
            if format in ['excel', 'csv']:
                # 生成檔案
                result = generator.generate_quarterly_report(company_code, year, quarter, format)
                
                # 下載檔案
                with open(result['file_path'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
            else:
                # 顯示網頁報表
                context = {
                    'report_type': '季報表',
                    'company_code': company_code,
                    'year': year,
                    'quarter': quarter,
                    'summary': summary,
                    'data': data,
                    'generated_at': timezone.now(),
                }
                return render(request, 'reporting/quarterly_report.html', context)
                
        except Exception as e:
            messages.error(request, f'生成季報表失敗: {str(e)}')
            return redirect('reporting:work_hour_report_index')
    
    # GET 請求顯示表單
    current_year = timezone.now().year
    current_quarter = (timezone.now().month - 1) // 3 + 1
    
    context = {
        'current_year': current_year,
        'current_quarter': current_quarter,
        'years': range(current_year - 5, current_year + 1),
        'quarters': range(1, 5),
    }
    return render(request, 'reporting/quarterly_report_form.html', context)


@login_required
def yearly_report(request):
    """年報表"""
    if request.method == 'POST':
        company_code = request.POST.get('company_code')
        year = int(request.POST.get('year'))
        format = request.POST.get('format', 'excel')
        
        try:
            service = WorkHourReportService()
            generator = ReportGeneratorService()
            
            # 取得報表資料
            data = service.get_yearly_report(company_code, year)
            summary = service.get_yearly_summary(company_code, year)
            
            if format in ['excel', 'csv']:
                # 生成檔案
                result = generator.generate_yearly_report(company_code, year, format)
                
                # 下載檔案
                with open(result['file_path'], 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
                    return response
            else:
                # 顯示網頁報表
                context = {
                    'report_type': '年報表',
                    'company_code': company_code,
                    'year': year,
                    'summary': summary,
                    'data': data,
                    'generated_at': timezone.now(),
                }
                return render(request, 'reporting/yearly_report.html', context)
                
        except Exception as e:
            messages.error(request, f'生成年報表失敗: {str(e)}')
            return redirect('reporting:work_hour_report_index')
    
    # GET 請求顯示表單
    current_year = timezone.now().year
    
    context = {
        'current_year': current_year,
        'years': range(current_year - 10, current_year + 1),
    }
    return render(request, 'reporting/yearly_report_form.html', context)


@login_required
def report_schedule_list(request):
    """報表排程列表"""
    schedules = ReportSchedule.objects.all().order_by('-created_at')
    
    # 分頁
    paginator = Paginator(schedules, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'schedules': page_obj,
    }
    return render(request, 'reporting/report_schedule_list.html', context)


@login_required
def report_schedule_form(request, schedule_id=None):
    """報表排程表單"""
    if schedule_id:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id)
    else:
        schedule = None
    
    if request.method == 'POST':
        try:
            if schedule:
                # 更新現有排程
                schedule.name = request.POST.get('name')
                schedule.report_type = request.POST.get('report_type')
                schedule.company = request.POST.get('company')
                schedule.schedule_time = request.POST.get('schedule_time')
                schedule.schedule_day = request.POST.get('schedule_day') or None
                schedule.status = request.POST.get('status')
                schedule.email_recipients = request.POST.get('email_recipients', '')
                schedule.save()
                messages.success(request, '報表排程更新成功')
            else:
                # 建立新排程
                schedule = ReportSchedule.objects.create(
                    name=request.POST.get('name'),
                    report_type=request.POST.get('report_type'),
                    company=request.POST.get('company'),
                    schedule_time=request.POST.get('schedule_time'),
                    schedule_day=request.POST.get('schedule_day') or None,
                    status=request.POST.get('status'),
                    email_recipients=request.POST.get('email_recipients', ''),
                )
                messages.success(request, '報表排程建立成功')
            
            return redirect('reporting:report_schedule_list')
            
        except Exception as e:
            messages.error(request, f'儲存報表排程失敗: {str(e)}')
    
    context = {
        'schedule': schedule,
        'report_types': ReportSchedule.REPORT_TYPES,
        'status_choices': ReportSchedule.STATUS_CHOICES,
    }
    return render(request, 'reporting/report_schedule_form.html', context)


@login_required
def report_execution_log(request):
    """報表執行日誌"""
    logs = ReportExecutionLog.objects.all().order_by('-execution_time')
    
    # 計算統計數據
    total_logs = logs.count()
    completed_logs = logs.filter(status='completed').count()
    running_logs = logs.filter(status='running').count()
    failed_logs = logs.filter(status='failed').count()
    
    # 分頁
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'logs': page_obj,
        'total_logs': total_logs,
        'completed_logs': completed_logs,
        'running_logs': running_logs,
        'failed_logs': failed_logs,
    }
    return render(request, 'reporting/report_execution_log.html', context)


@login_required
def execute_report_schedule(request, schedule_id):
    """手動執行報表排程"""
    try:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id)
        scheduler = ReportSchedulerService()
        
        # 手動執行排程
        scheduler._execute_schedule(schedule)
        
        messages.success(request, f'報表排程 {schedule.name} 執行成功')
        
    except Exception as e:
        messages.error(request, f'執行報表排程失敗: {str(e)}')
    
    return redirect('reporting:report_schedule_list')


@login_required
def sync_report_data(request):
    """同步報表資料"""
    try:
        from workorder.fill_work.models import FillWork
        from workorder.onsite_reporting.models import OnsiteReport
        
        # 同步填報資料
        fill_works = FillWork.objects.filter(approval_status='approved')
        fill_works_synced = 0
        for fill_work in fill_works:
            try:
                WorkOrderReportData.create_from_fill_work(fill_work)
                fill_works_synced += 1
            except Exception as e:
                logger.error(f"同步填報資料失敗: {fill_work.id} - {str(e)}")
        
        # 同步現場報工資料
        onsite_reports = OnsiteReport.objects.filter(status='completed')
        onsite_synced = 0
        for onsite_report in onsite_reports:
            try:
                WorkOrderReportData.create_from_onsite_report(onsite_report)
                onsite_synced += 1
            except Exception as e:
                logger.error(f"同步現場報工資料失敗: {onsite_report.id} - {str(e)}")
        
        total_synced = fill_works_synced + onsite_synced
        messages.success(request, f'報表資料同步完成，填報資料 {fill_works_synced} 筆，現場報工 {onsite_synced} 筆，總計 {total_synced} 筆記錄')
        
    except Exception as e:
        messages.error(request, f'同步報表資料失敗: {str(e)}')
    
    return redirect('reporting:work_hour_report_index') 

@csrf_exempt
def chart_data(request):
    """提供圖表資料的 API"""
    from django.http import JsonResponse
    from datetime import datetime, timedelta
    from django.views.decorators.csrf import csrf_exempt
    
    # 從請求參數中獲取圖表類型
    chart_type = request.GET.get('chart_type', '')
    
    if chart_type == 'work_hours_trend':
        # 工作時數趨勢圖資料
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)  # 改為90天
        
        # 取得最近90天的每日工作時數
        daily_data = WorkOrderReportData.objects.filter(
            work_date__range=[start_date, end_date]
        ).values('work_date').annotate(
            total_hours=Sum('daily_work_hours')
        ).order_by('work_date')
        
        labels = []
        values = []
        
        for item in daily_data:
            labels.append(item['work_date'].strftime('%m/%d'))
            values.append(float(item['total_hours'] or 0))
        
        return JsonResponse({
            'labels': labels,
            'values': values
        })
    
    elif chart_type == 'company_distribution':
        # 公司工作時數分布圖資料
        company_data = WorkOrderReportData.objects.values('company').annotate(
            total_hours=Sum('daily_work_hours')
        ).order_by('-total_hours')[:5]
        
        labels = []
        values = []
        
        for item in company_data:
            company_name = item['company'] or '未指定'
            labels.append(company_name)
            values.append(float(item['total_hours'] or 0))
        
        return JsonResponse({
            'labels': labels,
            'values': values
        })
    
    elif chart_type == 'completed_workorder_trend':
        # 已完工工單趨勢圖資料
        trend_data = CompletedWorkOrderReportService.get_completed_workorder_trend()
        return JsonResponse(trend_data)
    
    elif chart_type == 'completed_workorder_distribution':
        # 已完工工單公司分布圖資料
        company_data = CompletedWorkOrderReportService.get_company_completion_distribution()
        return JsonResponse(company_data)
    
    return JsonResponse({'error': '無效的圖表類型'})


@login_required
def report_data_list(request):
    """提供報表資料列表的 API"""
    from django.http import JsonResponse
    from datetime import datetime, timedelta
    
    # 取得所有資料，按日期排序
    report_data = WorkOrderReportData.objects.all().order_by('-work_date')[:20]  # 限制20筆
    
    data = []
    for item in report_data:
        data.append({
            'workorder_id': item.workorder_id,
            'company': item.company or '未指定',
            'work_date': item.work_date.strftime('%Y-%m-%d'),
            'daily_work_hours': float(item.daily_work_hours or 0),
            'weekly_work_hours': float(item.weekly_work_hours or 0),
            'monthly_work_hours': float(item.monthly_work_hours or 0),
            'operator_count': item.operator_count or 0,
        })
    
    return JsonResponse(data, safe=False) 

@login_required
def dashboard_stats(request):
    """提供儀表板統計資料的 API"""
    from django.http import JsonResponse
    
    try:
        # 統計資料
        total_reports = WorkOrderReportData.objects.count()
        today_reports = WorkOrderReportData.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        # 排程統計
        active_schedules = ReportSchedule.objects.filter(status='active').count()
        completed_executions = ReportExecutionLog.objects.filter(status='success').count()
        
        return JsonResponse({
            'total_reports': total_reports,
            'today_reports': today_reports,
            'pending_reports': active_schedules,
            'completed_reports': completed_executions,
        })
    except Exception as e:
        logger.error(f"取得儀表板統計資料失敗: {str(e)}")
        return JsonResponse({
            'total_reports': 0,
            'today_reports': 0,
            'pending_reports': 0,
            'completed_reports': 0,
        }) 

@login_required
def completed_workorder_report_index(request):
    """已完工工單報表首頁"""
    try:
        # 取得統計摘要
        summary = CompletedWorkOrderReportService.get_completed_workorder_summary()
        
        # 取得趨勢資料
        trend_data = CompletedWorkOrderReportService.get_completed_workorder_trend()
        
        # 取得公司分布資料
        company_data = CompletedWorkOrderReportService.get_company_completion_distribution()
        
        context = {
            'summary': summary,
            'trend_data': trend_data,
            'company_data': company_data,
        }
    except Exception as e:
        logger.error(f"取得已完工工單報表資料失敗: {str(e)}")
        context = {
            'summary': {},
            'trend_data': {},
            'company_data': {},
        }
    
    return render(request, 'reporting/completed_workorder_report.html', context)


@login_required
def completed_workorder_report_list(request):
    """已完工工單報表列表"""
    try:
        # 取得查詢參數
        company_code = request.GET.get('company')
        year = request.GET.get('year')
        month = request.GET.get('month')
        quarter = request.GET.get('quarter')
        
        # 建立查詢集
        queryset = CompletedWorkOrderReportData.objects.all()
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        if year:
            queryset = queryset.filter(completion_year=year)
        if month:
            queryset = queryset.filter(completion_month=month)
        if quarter:
            queryset = queryset.filter(completion_quarter=quarter)
        
        # 排序
        queryset = queryset.order_by('-completion_date', '-created_at')
        
        # 分頁
        paginator = Paginator(queryset, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # 取得公司列表
        companies = CompletedWorkOrderReportData.objects.values_list('company_code', 'company_name').distinct()
        
        context = {
            'page_obj': page_obj,
            'companies': companies,
            'selected_company': company_code,
            'selected_year': year,
            'selected_month': month,
            'selected_quarter': quarter,
        }
    except Exception as e:
        logger.error(f"取得已完工工單報表列表失敗: {str(e)}")
        context = {
            'page_obj': None,
            'companies': [],
            'selected_company': None,
            'selected_year': None,
            'selected_month': None,
            'selected_quarter': None,
        }
    
    return render(request, 'reporting/completed_workorder_report_list.html', context)


@login_required
def completed_workorder_report_detail(request, report_id):
    """已完工工單報表詳情"""
    try:
        report_data = get_object_or_404(CompletedWorkOrderReportData, id=report_id)
        
        context = {
            'report_data': report_data,
        }
    except Exception as e:
        logger.error(f"取得已完工工單報表詳情失敗: {str(e)}")
        messages.error(request, '取得報表詳情失敗')
        return redirect('reporting:completed_workorder_report_list')
    
    return render(request, 'reporting/completed_workorder_report_detail.html', context) 

@login_required
def sync_completed_workorder_data(request):
    """同步已完工工單資料"""
    if request.method == 'POST':
        try:
            from .services import CompletedWorkOrderReportService
            
            # 使用服務類別進行同步
            result = CompletedWorkOrderReportService.sync_completed_workorder_data()
            
            if result['success']:
                messages.success(request, result['message'])
            else:
                messages.error(request, result['error'])
            
        except Exception as e:
            messages.error(request, f'同步已完工工單資料失敗: {str(e)}')
        
        return redirect('reporting:completed_workorder_report_index')
    else:
        # GET 請求也重定向到報表首頁
        return redirect('reporting:completed_workorder_report_index') 

# ==================== 評分報表視圖 ====================

@login_required
def scoring_report_list(request):
    """評分報表清單"""
    # 暫時重定向到作業員評分清單
    return redirect('reporting:operator_score_list')

@login_required
def scoring_report_detail(request, report_id):
    """評分報表詳情"""
    # 暫時重定向到作業員評分清單
    return redirect('reporting:operator_score_list')

@login_required
def generate_scoring_report(request):
    """生成評分報表"""
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        report_period = request.POST.get('report_period', 'monthly')
        
        if start_date and end_date:
            try:
                # 取得指定日期範圍內的評分資料
                scores = OperatorProcessCapacityScore.objects.filter(
                    work_date__range=[start_date, end_date]
                ).order_by('-work_date')
                
                if scores.exists():
                    # 計算統計資料
                    total_records = scores.count()
                    avg_capacity_score = scores.aggregate(Avg('capacity_score'))['capacity_score__avg'] or 0
                    avg_supervisor_score = scores.aggregate(Avg('supervisor_score'))['supervisor_score__avg'] or 80
                    avg_total_score = scores.aggregate(Avg('total_score'))['total_score__avg'] or 0
                    
                    # 等級分布
                    excellent_count = scores.filter(overall_grade='優秀').count()
                    good_count = scores.filter(overall_grade='良好').count()
                    pass_count = scores.filter(overall_grade='及格').count()
                    fail_count = scores.filter(overall_grade='不及格').count()
                    
                    # 建立報表記錄
                    report_data = {
                        'start_date': start_date,
                        'end_date': end_date,
                        'report_period': report_period,
                        'total_records': total_records,
                        'capacity_score': avg_capacity_score,
                        'supervisor_score': avg_supervisor_score,
                        'total_score': avg_total_score,
                        'excellent_count': excellent_count,
                        'good_count': good_count,
                        'pass_count': pass_count,
                        'fail_count': fail_count,
                    }
                    
                    messages.success(request, f'成功生成評分報表！共處理 {total_records} 筆資料')
                    return render(request, 'reporting/scoring_dashboard.html', {
                        'latest_report': report_data,
                        'operator_stats': {
                            'total_records': total_records,
                            'avg_capacity_score': avg_capacity_score,
                            'avg_supervisor_score': avg_supervisor_score,
                            'avg_total_score': avg_total_score,
                        },
                        'grade_distribution': [
                            {'overall_grade': '優秀', 'count': excellent_count},
                            {'overall_grade': '良好', 'count': good_count},
                            {'overall_grade': '及格', 'count': pass_count},
                            {'overall_grade': '不及格', 'count': fail_count},
                        ]
                    })
                else:
                    messages.warning(request, '指定日期範圍內沒有評分資料')
            except Exception as e:
                messages.error(request, f'生成評分報表失敗：{str(e)}')
        else:
            messages.error(request, '請選擇開始和結束日期')
    
    # 提供報表週期選項
    report_periods = [
        ('monthly', '月評分'),
        ('quarterly', '季評分'),
        ('yearly', '年評分'),
    ]
    
    context = {
        'report_periods': report_periods,
    }
    
    return render(request, 'reporting/generate_scoring_report.html', context)

@login_required
def operator_score_list(request):
    """作業員評分清單"""
    scores = OperatorProcessCapacityScore.objects.all().order_by('-work_date')
    
    # 篩選
    form = OperatorScoreFilterForm(request.GET)
    if form.is_valid():
        company_code = form.cleaned_data.get('company_code')
        operator_id = form.cleaned_data.get('operator_id')
        process_name = form.cleaned_data.get('process_name')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        has_supervisor_score = form.cleaned_data.get('has_supervisor_score')
        
        if company_code:
            scores = scores.filter(company_code=company_code)
        if operator_id:
            scores = scores.filter(operator_id=operator_id)
        if process_name:
            scores = scores.filter(process_name__icontains=process_name)
        if start_date:
            scores = scores.filter(work_date__gte=start_date)
        if end_date:
            scores = scores.filter(work_date__lte=end_date)
        if has_supervisor_score == 'yes':
            scores = scores.filter(is_supervisor_scored=True)
        elif has_supervisor_score == 'no':
            scores = scores.filter(is_supervisor_scored=False)
    
    # 分頁
    paginator = Paginator(scores, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
    }
    
    return render(request, 'reporting/operator_score_list.html', context)

@login_required
def supervisor_score_form(request, score_id):
    """主管評分表單"""
    score_record = get_object_or_404(OperatorProcessCapacityScore, id=score_id)
    
    if request.method == 'POST':
        form = SupervisorScoreForm(request.POST, instance=score_record)
        if form.is_valid():
            # 更新主管評分資訊
            score_record.supervisor_name = request.user.get_full_name() or request.user.username
            score_record.supervisor_date = timezone.now()
            score_record.is_supervisor_scored = True
            
            # 重新計算總評分
            score_record.total_score = score_record.calculate_total_score()
            score_record.overall_grade = score_record.get_grade(score_record.total_score)
            
            score_record.save()
            
            messages.success(request, '主管評分已成功儲存！')
            return redirect('reporting:operator_score_list')
    else:
        form = SupervisorScoreForm(instance=score_record)
    
    context = {
        'form': form,
        'score_record': score_record,
    }
    
    return render(request, 'reporting/supervisor_score_form.html', context)

@login_required
def operator_score_detail(request, score_id):
    """作業員評分詳情"""
    score_record = get_object_or_404(OperatorProcessCapacityScore, id=score_id)
    
    context = {
        'score_record': score_record,
    }
    
    return render(request, 'reporting/operator_score_detail.html', context)

@login_required
def export_scoring_report(request, report_id):
    """匯出評分報表"""
    # ScoringReport 和 ScoringDetail 模型已移除，此功能不再可用
    messages.warning(request, '評分報表匯出功能已移除，請直接查看詳情。')
    return redirect('reporting:operator_score_list')

@login_required
def scoring_dashboard(request):
    """評分儀表板"""
    # 取得作業員評分統計
    operator_stats = OperatorProcessCapacityScore.objects.aggregate(
        total_records=Count('id'),
        avg_capacity_score=Avg('capacity_score'),
        avg_quality_score=Avg('quality_score'),
        avg_total_score=Avg('total_score'),
        scored_by_supervisor=Count('id', filter=Q(is_supervisor_scored=True))
    )
    
    # 取得各等級分布
    grade_distribution = OperatorProcessCapacityScore.objects.values('overall_grade').annotate(
        count=Count('id')
    ).order_by('overall_grade')
    
    context = {
        'operator_stats': operator_stats,
        'grade_distribution': grade_distribution,
    }
    
    return render(request, 'reporting/scoring_dashboard.html', context)

@login_required
def score_period_management(request):
    """評分週期管理"""
    from .services import ScorePeriodService
    
    if request.method == 'POST':
        action = request.POST.get('action')
        company_code = request.POST.get('company_code')
        period_type = request.POST.get('period_type', 'monthly')
        
        if action == 'create_period':
            try:
                records = ScorePeriodService.create_period_score_records(
                    company_code, period_type, force=True
                )
                messages.success(request, f'成功建立 {len(records)} 筆{period_type}評分記錄')
            except Exception as e:
                messages.error(request, f'建立評分記錄失敗：{str(e)}')
        
        elif action == 'close_period':
            try:
                count = ScorePeriodService.close_period(company_code, period_type)
                messages.success(request, f'成功關閉 {count} 筆{period_type}評分記錄')
            except Exception as e:
                messages.error(request, f'關閉評分週期失敗：{str(e)}')
    
    # 取得各週期的摘要
    company_code = request.GET.get('company_code', '')
    period_summaries = {}
    
    if company_code:
        for period_type in ['monthly', 'quarterly', 'yearly']:
            summary = ScorePeriodService.get_period_summary(company_code, period_type)
            if summary:
                period_summaries[period_type] = summary
    
    context = {
        'company_code': company_code,
        'period_summaries': period_summaries,
    }
    
    return render(request, 'reporting/score_period_management.html', context)

@login_required
def score_period_detail(request, period_type):
    """評分週期詳情"""
    from .services import ScorePeriodService
    
    company_code = request.GET.get('company_code', '')
    if not company_code:
        messages.error(request, '請選擇公司代號')
        return redirect('reporting:score_period_management')
    
    # 取得週期摘要
    summary = ScorePeriodService.get_period_summary(company_code, period_type)
    if not summary:
        messages.error(request, f'找不到{period_type}評分資料')
        return redirect('reporting:score_period_management')
    
    # 取得詳細記錄
    start_date, end_date = ScorePeriodService.get_current_period_dates(period_type)
    records = OperatorProcessCapacityScore.objects.filter(
        company_code=company_code,
        score_period=period_type,
        period_start_date=start_date,
        period_end_date=end_date
    ).order_by('-work_date')
    
    # 分頁
    paginator = Paginator(records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'summary': summary,
        'page_obj': page_obj,
        'period_type': period_type,
        'company_code': company_code,
    }
    
    return render(request, 'reporting/score_period_detail.html', context)


@login_required
def work_hour_stats(request):
    """工作時數統計 API"""
    from django.http import JsonResponse
    from django.db.models import Sum, Avg, Count
    from workorder.fill_work.models import FillWork
    from datetime import datetime, timedelta
    
    try:
        # 取得工作時數統計資料
        stats = WorkOrderReportData.objects.aggregate(
            total_records=Count('id'),
            total_hours=Sum('daily_work_hours'),
            avg_daily_hours=Avg('daily_work_hours')
        )
        
        # 取得真實的獨立作業員數量（從填報資料中統計）
        unique_operators = FillWork.objects.values('operator').distinct().count()
        
        # 計算上周工作時數
        today = datetime.now().date()
        # 計算上周一：今天是週一(0)時，上周一是7天前；今天是週二(1)時，上周一是8天前，以此類推
        days_since_monday = today.weekday()  # 0=週一, 1=週二, ..., 6=週日
        last_week_start = today - timedelta(days=days_since_monday + 7)  # 上周一
        last_week_end = last_week_start + timedelta(days=6)  # 上周日
        
        last_week_stats = WorkOrderReportData.objects.filter(
            work_date__range=[last_week_start, last_week_end]
        ).aggregate(
            last_week_hours=Sum('daily_work_hours')
        )
        
        # 格式化數據
        response_data = {
            'total_records': stats['total_records'] or 0,
            'total_hours': float(stats['total_hours'] or 0),
            'total_operators': unique_operators,
            'avg_daily_hours': float(stats['avg_daily_hours'] or 0),
            'last_week_hours': float(last_week_stats['last_week_hours'] or 0)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"取得工作時數統計失敗: {str(e)}")
        return JsonResponse({
            'total_records': 0,
            'total_hours': 0,
            'total_operators': 0,
            'avg_daily_hours': 0,
            'last_week_hours': 0
        })