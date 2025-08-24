"""
報表模組視圖
提供各種報表的查詢和匯出功能
"""

import logging
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    WorkOrderReportData, ReportSchedule, ReportExecutionLog, CompletedWorkOrderReportData,
    OperatorProcessCapacityScore
)
from .forms import (
    GenerateScoringReportForm, 
    SupervisorScoreForm, OperatorScoreFilterForm
)
from .services import WorkHourReportService, ReportGeneratorService, ReportSchedulerService, CompletedWorkOrderReportService, ScoringService, OperatorCapacityService

logger = logging.getLogger(__name__)


def is_report_user(user):
    """檢查使用者是否有報表權限"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def index(request):
    """報表首頁"""
    try:
        # 統計資料
        total_workorders = WorkOrderReportData.objects.count()
        active_workorders = WorkOrderReportData.objects.filter(status='active').count()
        total_operators = OperatorProcessCapacityScore.objects.count()
        total_equipment = 0  # 暫時設為0，因為OperatorCapacityReport模型不存在
        
        # 報表統計
        total_reports = WorkOrderReportData.objects.count()
        today_reports = WorkOrderReportData.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        # 排程統計
        active_schedules = ReportSchedule.objects.filter(status='active').count()
        completed_executions = ReportExecutionLog.objects.filter(status='success').count()
        
        context = {
            'total_workorders': total_workorders,
            'active_workorders': active_workorders,
            'total_operators': total_operators,
            'total_equipment': total_equipment,
            'total_reports': total_reports,
            'today_reports': today_reports,
            'pending_reports': active_schedules,
            'completed_reports': completed_executions,
        }
    except Exception as e:
        logger.error(f"取得報表首頁統計資料失敗: {str(e)}")
        context = {
            'total_workorders': 0,
            'active_workorders': 0,
            'total_operators': 0,
            'total_equipment': 0,
            'total_reports': 0,
            'today_reports': 0,
            'pending_reports': 0,
            'completed_reports': 0,
        }
    
    return render(request, 'reporting/index.html', context)

def get_date_range(date_range):
    """
    根據日期範圍獲取開始和結束日期
    
    Args:
        date_range: 日期範圍字串
        
    Returns:
        tuple: (開始日期, 結束日期)
    """
    today = timezone.now().date()
    
    if date_range == 'today':
        return today, today
    elif date_range == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif date_range == 'this_week':
        # 週一到週日
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week, end_of_week
    elif date_range == 'last_week':
        # 上週一到上週日
        start_of_week = today - timedelta(days=today.weekday())
        start_of_last_week = start_of_week - timedelta(days=7)
        end_of_last_week = start_of_last_week + timedelta(days=6)
        return start_of_last_week, end_of_last_week
    elif date_range == 'this_month':
        start_of_month = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return start_of_month, end_of_month
    elif date_range == 'last_month':
        if today.month == 1:
            start_of_last_month = today.replace(year=today.year - 1, month=12, day=1)
        else:
            start_of_last_month = today.replace(month=today.month - 1, day=1)
        end_of_last_month = today.replace(day=1) - timedelta(days=1)
        return start_of_last_month, end_of_last_month
    else:
        # 預設為今天
        return today, today

def get_report_types():
    """
    獲取報表類型選項
    """
    return [
        ('daily_work', '日工作報表'),
        ('weekly_work', '週工作報表'),
        ('monthly_work', '月工作報表'),
        ('daily_work_hour_operator', '日工時報表 (作業員)'),
        ('weekly_work_hour_operator', '週工時報表 (作業員)'),
        ('monthly_work_hour_operator', '月工時報表 (作業員)'),
        ('daily_work_hour_smt', '日工時報表 (SMT設備)'),
        ('weekly_work_hour_smt', '週工時報表 (SMT設備)'),
        ('monthly_work_hour_smt', '月工時報表 (SMT設備)'),
        ('operator_performance', '作業員績效報表'),
        ('smt_equipment', 'SMT設備效率報表'),
        ('abnormal_report', '異常報工報表'),
        ('efficiency_analysis', '效率分析報表'),
    ]

def get_date_ranges():
    """
    獲取日期範圍選項
    """
    return [
        ('today', '今天'),
        ('yesterday', '昨天'),
        ('this_week', '本週'),
        ('last_week', '上週'),
        ('this_month', '本月'),
        ('last_month', '上月'),
        ('custom', '自訂範圍'),
    ]

def get_daily_work_report_data(start_date, end_date):
    """
    獲取日工作報表資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 從填報記錄中獲取資料
    fill_work_reports = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).select_related('process')
    
    for report in fill_work_reports:
        data.append({
            'operator': report.operator,
            'work_date': report.work_date.strftime('%Y-%m-%d'),
            'workorder': report.workorder,
            'product_id': report.product_id,
            'start_time': report.start_time,
            'end_time': report.end_time,
            'process': report.process.name if report.process else '',
            'work_quantity': report.work_quantity,
            'defect_quantity': report.defect_quantity,
        })
    
    return data

def get_weekly_work_report_data(start_date, end_date):
    """
    獲取週工作報表資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 按作業員分組統計
    operator_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).values('operator').annotate(
        total_work_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    for stat in operator_stats:
        data.append({
            'operator': stat['operator'],
            'total_work_quantity': stat['total_work_quantity'] or 0,
            'total_defect_quantity': stat['total_defect_quantity'] or 0,
        })
    
    return data

def get_monthly_work_report_data(start_date, end_date):
    """
    獲取月工作報表資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 按作業員分組統計
    operator_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).values('operator').annotate(
        total_work_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    for stat in operator_stats:
        data.append({
            'operator': stat['operator'],
            'total_work_quantity': stat['total_work_quantity'] or 0,
            'total_defect_quantity': stat['total_defect_quantity'] or 0,
        })
    
    return data

def get_daily_work_hour_operator_report_data(start_date, end_date):
    """
    獲取日工時報表 (作業員) 資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 從填報記錄中獲取作業員工時資料
    operator_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).exclude(
        Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
    ).values('operator', 'work_date').annotate(
        total_work_hours=Sum('work_hours_calculated'),
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    for stat in operator_stats:
        data.append({
            'operator': stat['operator'],
            'work_date': stat['work_date'].strftime('%Y-%m-%d'),
            'work_hours': round(stat['total_work_hours'] or 0, 2),
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
        })
    
    return data

def get_weekly_work_hour_operator_report_data(start_date, end_date):
    """
    獲取週工時報表 (作業員) 資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 按作業員分組統計週工時
    operator_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).exclude(
        Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
    ).values('operator').annotate(
        total_work_hours=Sum('work_hours_calculated'),
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    for stat in operator_stats:
        data.append({
            'operator': stat['operator'],
            'work_hours': round(stat['total_work_hours'] or 0, 2),
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
        })
    
    return data

def get_monthly_work_hour_operator_report_data(start_date, end_date):
    """
    獲取月工時報表 (作業員) 資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 按作業員分組統計月工時
    operator_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).exclude(
        Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
    ).values('operator').annotate(
        total_work_hours=Sum('work_hours_calculated'),
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    for stat in operator_stats:
        data.append({
            'operator': stat['operator'],
            'work_hours': round(stat['total_work_hours'] or 0, 2),
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
        })
    
    return data

def get_daily_work_hour_smt_report_data(start_date, end_date):
    """
    獲取日工時報表 (SMT設備) 資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 從填報記錄中獲取SMT設備工時資料
    smt_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).filter(
        Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
    ).values('equipment__name', 'work_date').annotate(
        total_work_hours=Sum('work_hours_calculated'),
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    for stat in smt_stats:
        data.append({
            'equipment': stat['equipment__name'] or 'SMT設備',
            'work_date': stat['work_date'].strftime('%Y-%m-%d'),
            'work_hours': round(stat['total_work_hours'] or 0, 2),
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
        })
    
    return data

def get_weekly_work_hour_smt_report_data(start_date, end_date):
    """
    獲取週工時報表 (SMT設備) 資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 按SMT設備分組統計週工時
    smt_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).filter(
        Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
    ).values('equipment__name').annotate(
        total_work_hours=Sum('work_hours_calculated'),
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    for stat in smt_stats:
        data.append({
            'equipment': stat['equipment__name'] or 'SMT設備',
            'work_hours': round(stat['total_work_hours'] or 0, 2),
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
        })
    
    return data

def get_monthly_work_hour_smt_report_data(start_date, end_date):
    """
    獲取月工時報表 (SMT設備) 資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 按SMT設備分組統計月工時
    smt_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).filter(
        Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
    ).values('equipment__name').annotate(
        total_work_hours=Sum('work_hours_calculated'),
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    for stat in smt_stats:
        data.append({
            'equipment': stat['equipment__name'] or 'SMT設備',
            'work_hours': round(stat['total_work_hours'] or 0, 2),
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
        })
    
    return data

def get_operator_performance_report_data(start_date, end_date):
    """
    獲取作業員績效報表資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 從填報記錄中獲取作業員績效資料
    operator_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).exclude(
        Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
    ).values('operator').annotate(
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity'),
        total_work_hours=Sum('work_hours_calculated')
    )
    
    for stat in operator_stats:
        total_quantity = (stat['total_good_quantity'] or 0) + (stat['total_defect_quantity'] or 0)
        defect_rate = 0
        if total_quantity > 0:
            defect_rate = round((stat['total_defect_quantity'] or 0) / total_quantity * 100, 2)
        
        efficiency = 0
        if stat['total_work_hours'] and stat['total_work_hours'] > 0:
            efficiency = round((stat['total_good_quantity'] or 0) / stat['total_work_hours'], 2)
        
        data.append({
            'operator': stat['operator'],
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
            'defect_rate': defect_rate,
            'efficiency': efficiency,
        })
    
    return data

def get_smt_equipment_report_data(start_date, end_date):
    """
    獲取SMT設備效率報表資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 從填報記錄中獲取SMT設備效率資料
    smt_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).filter(
        Q(operator__icontains='SMT') | Q(process__name__icontains='SMT')
    ).values('equipment__name').annotate(
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity'),
        total_work_hours=Sum('work_hours_calculated')
    )
    
    for stat in smt_stats:
        total_quantity = (stat['total_good_quantity'] or 0) + (stat['total_defect_quantity'] or 0)
        defect_rate = 0
        if total_quantity > 0:
            defect_rate = round((stat['total_defect_quantity'] or 0) / total_quantity * 100, 2)
        
        efficiency = 0
        if stat['total_work_hours'] and stat['total_work_hours'] > 0:
            efficiency = round((stat['total_good_quantity'] or 0) / stat['total_work_hours'], 2)
        
        data.append({
            'equipment': stat['equipment__name'] or 'SMT設備',
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
            'defect_rate': defect_rate,
            'efficiency': efficiency,
        })
    
    return data

def get_abnormal_report_data(start_date, end_date):
    """
    獲取異常報工報表資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 從填報記錄中獲取異常報工資料
    abnormal_reports = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).exclude(
        abnormal_notes__isnull=True
    ).exclude(
        abnormal_notes__exact=''
    )
    
    for report in abnormal_reports:
        data.append({
            'operator': report.operator,
            'work_date': report.work_date.strftime('%Y-%m-%d'),
            'workorder': report.workorder,
            'process': report.process.name if report.process else '',
            'abnormal_notes': report.abnormal_notes,
            'good_quantity': report.work_quantity,
            'defect_quantity': report.defect_quantity,
        })
    
    return data

def get_efficiency_analysis_report_data(start_date, end_date):
    """
    獲取效率分析報表資料
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        list: 報表資料
    """
    data = []
    
    # 從填報記錄中獲取效率分析資料
    efficiency_stats = FillWork.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status='approved'
    ).values('operator', 'process__name').annotate(
        total_good_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity'),
        total_work_hours=Sum('work_hours_calculated')
    )
    
    for stat in efficiency_stats:
        total_quantity = (stat['total_good_quantity'] or 0) + (stat['total_defect_quantity'] or 0)
        defect_rate = 0
        if total_quantity > 0:
            defect_rate = round((stat['total_defect_quantity'] or 0) / total_quantity * 100, 2)
        
        efficiency = 0
        if stat['total_work_hours'] and stat['total_work_hours'] > 0:
            efficiency = round((stat['total_good_quantity'] or 0) / stat['total_work_hours'], 2)
        
        data.append({
            'operator': stat['operator'],
            'process': stat['process__name'] or '',
            'good_quantity': stat['total_good_quantity'] or 0,
            'defect_quantity': stat['total_defect_quantity'] or 0,
            'defect_rate': defect_rate,
            'efficiency': efficiency,
        })
    
    return data

def get_report_title(report_type):
    """
    獲取報表標題
    """
    titles = {
        'daily_work': '日工作報表',
        'weekly_work': '週工作報表',
        'monthly_work': '月工作報表',
        'daily_work_hour_operator': '日工時報表 (作業員)',
        'weekly_work_hour_operator': '週工時報表 (作業員)',
        'monthly_work_hour_operator': '月工時報表 (作業員)',
        'daily_work_hour_smt': '日工時報表 (SMT設備)',
        'weekly_work_hour_smt': '週工時報表 (SMT設備)',
        'monthly_work_hour_smt': '月工時報表 (SMT設備)',
        'operator_performance': '作業員績效報表',
        'smt_equipment': 'SMT設備效率報表',
        'abnormal_report': '異常報工報表',
        'efficiency_analysis': '效率分析報表',
    }
    return titles.get(report_type, '未知報表')

def get_report_headers(report_type):
    """
    獲取報表表頭
    """
    headers = {
        'daily_work': ['作業員', '報工日期', '工單號', '產品編號', '開始時間', '結束時間', '工序', '工作數量', '不良品數量'],
        'weekly_work': ['作業員', '週工作數量', '週不良品數量'],
        'monthly_work': ['作業員', '月工作數量', '月不良品數量'],
        'daily_work_hour_operator': ['作業員', '報工日期', '工時(小時)', '良品數量', '不良品數量'],
        'weekly_work_hour_operator': ['作業員', '週工時(小時)', '週良品數量', '週不良品數量'],
        'monthly_work_hour_operator': ['作業員', '月工時(小時)', '月良品數量', '月不良品數量'],
        'daily_work_hour_smt': ['設備', '報工日期', '運行時間(小時)', '良品數量', '不良品數量'],
        'weekly_work_hour_smt': ['設備', '週運行時間(小時)', '週良品數量', '週不良品數量'],
        'monthly_work_hour_smt': ['設備', '月運行時間(小時)', '月良品數量', '月不良品數量'],
        'operator_performance': ['作業員', '良品數量', '不良品數量', '不良率(%)', '平均效率(%)'],
        'smt_equipment': ['設備', '良品數量', '不良品數量', '不良率(%)', '平均效率(%)'],
        'abnormal_report': ['作業員', '報工日期', '工單號', '工序', '異常紀錄', '良品數量', '不良品數量'],
        'efficiency_analysis': ['作業員', '工序', '良品數量', '不良品數量', '不良率(%)', '平均效率(%)'],
    }
    return headers.get(report_type, [])

def get_report_filename(report_type, start_date, end_date):
    """
    獲取報表檔案名稱
    """
    title = get_report_title(report_type)
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    if start_date == end_date:
        return f"{title}_{start_str}.xlsx"
    else:
        return f"{title}_{start_str}_{end_str}.xlsx"

def export_to_excel(data, headers, filename):
    """
    匯出Excel檔案
    
    Args:
        data: 報表資料
        headers: 表頭
        filename: 檔案名稱
        
    Returns:
        HttpResponse: Excel檔案回應
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill
        
        # 建立工作簿
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "報表"
        
        # 設定表頭樣式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # 寫入表頭
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # 寫入資料
        for row, record in enumerate(data, 2):
            for col, header in enumerate(headers, 1):
                value = record.get(header, '')
                ws.cell(row=row, column=col, value=value)
        
        # 調整欄寬
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
        
        # 建立回應
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # 儲存檔案
        wb.save(response)
        return response
        
    except ImportError:
        # 如果沒有 openpyxl，回退到 CSV
        return export_to_csv(data, headers, filename.replace('.xlsx', '.csv'))

def export_to_csv(data, headers, filename):
    """
    匯出CSV檔案
    
    Args:
        data: 報表資料
        headers: 表頭
        filename: 檔案名稱
        
    Returns:
        HttpResponse: CSV檔案回應
    """
    import csv
    from io import StringIO
    
    # 建立CSV檔案
    output = StringIO()
    writer = csv.writer(output)
    
    # 寫入表頭
    writer.writerow(headers)
    
    # 寫入資料
    for record in data:
        row = [record.get(header, '') for header in headers]
        writer.writerow(row)
    
    # 建立回應
    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def report_export(request):
    """
    報表匯出頁面
    """
    context = {
        'report_types': get_report_types(),
        'date_ranges': get_date_ranges(),
    }
    return render(request, 'reporting/report_export.html', context)

@login_required
def execute_report_export(request):
    """
    執行報表匯出
    """
    if request.method != 'POST':
        return JsonResponse({'error': '只支援 POST 請求'}, status=405)
    
    try:
        # 取得參數
        report_type = request.POST.get('report_type')
        date_range = request.POST.get('date_range')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        export_format = request.POST.get('export_format', 'excel')
        
        # 驗證參數
        if not report_type:
            return JsonResponse({'error': '請選擇報表類型'}, status=400)
        
        # 取得日期範圍
        if date_range == 'custom':
            if not start_date_str or not end_date_str:
                return JsonResponse({'error': '請選擇自訂日期範圍'}, status=400)
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            start_date, end_date = get_date_range(date_range)
        
        # 驗證日期範圍（最多4個月）
        date_diff = (end_date - start_date).days
        if date_diff > 120:  # 4個月 = 120天
            return JsonResponse({'error': '查詢期間不能超過4個月'}, status=400)
        
        # 根據報表類型獲取資料
        data = []
        if report_type == 'daily_work':
            data = get_daily_work_report_data(start_date, end_date)
        elif report_type == 'weekly_work':
            data = get_weekly_work_report_data(start_date, end_date)
        elif report_type == 'monthly_work':
            data = get_monthly_work_report_data(start_date, end_date)
        elif report_type == 'daily_work_hour_operator':
            data = get_daily_work_hour_operator_report_data(start_date, end_date)
        elif report_type == 'weekly_work_hour_operator':
            data = get_weekly_work_hour_operator_report_data(start_date, end_date)
        elif report_type == 'monthly_work_hour_operator':
            data = get_monthly_work_hour_operator_report_data(start_date, end_date)
        elif report_type == 'daily_work_hour_smt':
            data = get_daily_work_hour_smt_report_data(start_date, end_date)
        elif report_type == 'weekly_work_hour_smt':
            data = get_weekly_work_hour_smt_report_data(start_date, end_date)
        elif report_type == 'monthly_work_hour_smt':
            data = get_monthly_work_hour_smt_report_data(start_date, end_date)
        elif report_type == 'operator_performance':
            data = get_operator_performance_report_data(start_date, end_date)
        elif report_type == 'smt_equipment':
            data = get_smt_equipment_report_data(start_date, end_date)
        elif report_type == 'abnormal_report':
            data = get_abnormal_report_data(start_date, end_date)
        elif report_type == 'efficiency_analysis':
            data = get_efficiency_analysis_report_data(start_date, end_date)
        else:
            return JsonResponse({'error': '不支援的報表類型'}, status=400)
        
        # 獲取表頭和檔案名稱
        headers = get_report_headers(report_type)
        filename = get_report_filename(report_type, start_date, end_date)
        
        # 根據格式匯出
        if export_format == 'csv':
            filename = filename.replace('.xlsx', '.csv')
            return export_to_csv(data, headers, filename)
        else:
            return export_to_excel(data, headers, filename)
        
    except Exception as e:
        logger.error(f"匯出報表時發生錯誤: {str(e)}")
        return JsonResponse({'error': f'匯出失敗: {str(e)}'}, status=500) 

def placeholder_view(request, function_name):
    """
    通用佔位符視圖 - 用於所有未實現的功能
    """
    context = {
        'function_name': function_name,
        'message': f'功能 "{function_name}" 正在開發中，敬請期待！'
    }
    return render(request, 'reporting/placeholder.html', context) 


@login_required
def work_hour_report_index(request):
    """工作時數報表首頁"""
    return render(request, 'reporting/work_hour_report.html')

@login_required
def daily_report(request):
    """日報表"""
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

@login_required
def chart_data(request):
    """提供圖表資料的 API"""
    from django.http import JsonResponse
    from datetime import datetime, timedelta
    
    chart_type = request.GET.get('chart_type')
    
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
    try:
        from workorder.models import CompletedWorkOrder
        
        # 取得所有已完工工單
        completed_workorders = CompletedWorkOrder.objects.all()
        
        synced_count = 0
        for completed_workorder in completed_workorders:
            try:
                CompletedWorkOrderReportData.create_from_completed_workorder(completed_workorder)
                synced_count += 1
            except Exception as e:
                logger.error(f"同步已完工工單資料失敗: {completed_workorder.id} - {str(e)}")
        
        messages.success(request, f'已完工工單資料同步完成，共處理 {synced_count} 筆記錄')
        
    except Exception as e:
        messages.error(request, f'同步已完工工單資料失敗: {str(e)}')
    
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