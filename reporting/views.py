"""
報表模組視圖
"""

import csv
import io
import logging
from datetime import datetime, timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import TemplateView, ListView
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from workorder.models import (
    WorkOrder, OperatorSupplementReport, SMTSupplementReport
)
from equip.models import Equipment
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def reporting_user_required(user):
    """
    檢查用戶是否為超級用戶或屬於「報表使用者」群組。
    """
    return user.is_superuser or user.groups.filter(name="報表使用者").exists()


class ReportingIndexView(LoginRequiredMixin, TemplateView):
    """
    報表管理首頁視圖
    """
    template_name = 'reporting/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 獲取基本統計數據
        context['total_workorders'] = WorkOrder.objects.count()
        context['active_workorders'] = WorkOrder.objects.filter(status='active').count()
        context['completed_workorders'] = WorkOrder.objects.filter(status='completed').count()
        context['total_operators'] = User.objects.filter(is_active=True).count()
        context['total_equipment'] = Equipment.objects.count()
        
        return context


@login_required
def pending_approval_list(request):
    """
    待審核報工清單 - 重定向到工單模組的主管功能
    """
    return redirect('workorder:supervisor:pending_approval_list')


@login_required
@user_passes_test(reporting_user_required, login_url='/login/')
def report_export(request):
    """
    報表匯出功能
    """
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        export_format = request.POST.get('export_format')
        date_range = request.POST.get('date_range')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # 處理日期範圍
        if date_range == 'custom':
            if start_date and end_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                messages.error(request, '請選擇自訂日期範圍')
                return redirect('reporting:report_export')
        else:
            start_date, end_date = get_date_range(date_range)
        
        # 根據報表類型和格式匯出
        if export_format == 'excel':
            return export_to_excel(report_type, start_date, end_date)
        elif export_format == 'csv':
            return export_to_csv(report_type, start_date, end_date)
        elif export_format == 'pdf':
            return export_to_pdf(report_type, start_date, end_date)
    
    context = {
        'report_types': get_report_types(),
        'date_ranges': get_date_ranges(),
    }
    
    return render(request, 'reporting/report_export.html', context)


def get_date_range(date_range):
    """
    根據日期範圍類型獲取開始和結束日期
    """
    today = date.today()
    
    if date_range == 'today':
        return today, today
    elif date_range == 'yesterday':
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif date_range == 'this_week':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end
    elif date_range == 'last_week':
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return start, end
    elif date_range == 'this_month':
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return start, end
    elif date_range == 'last_month':
        if today.month == 1:
            start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            start = today.replace(month=today.month - 1, day=1)
        end = today.replace(day=1) - timedelta(days=1)
        return start, end
    
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
        ('today', '今日'),
        ('yesterday', '昨日'),
        ('this_week', '本週'),
        ('last_week', '上週'),
        ('this_month', '本月'),
        ('last_month', '上月'),
        ('custom', '自訂範圍'),
    ]


def export_to_excel(report_type, start_date, end_date):
    """
    匯出 Excel 報表
    """
    # 獲取報表數據
    data = get_report_data(report_type, start_date, end_date)
    
    # 創建 Excel 工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = get_report_title(report_type)
    
    # 設定標題樣式
    title_font = Font(bold=True, size=14)
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # 寫入標題
    ws['A1'] = f'{get_report_title(report_type)} ({start_date} ~ {end_date})'
    ws['A1'].font = title_font
    ws.merge_cells('A1:H1')
    
    # 寫入表頭
    headers = get_report_headers(report_type)
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    # 寫入數據
    for row, row_data in enumerate(data, 4):
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = border
    
    # 調整欄寬
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 15
    
    # 創建回應
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{get_report_filename(report_type, start_date, end_date)}.xlsx"'
    
    wb.save(response)
    return response


def export_to_csv(report_type, start_date, end_date):
    """
    匯出 CSV 報表
    """
    # 獲取報表數據
    data = get_report_data(report_type, start_date, end_date)
    headers = get_report_headers(report_type)
    
    # 創建 CSV 回應
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{get_report_filename(report_type, start_date, end_date)}.csv"'
    
    # 寫入 CSV 數據
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(data)
    
    return response


def export_to_pdf(report_type, start_date, end_date):
    """
    匯出 PDF 報表 (暫時重定向到 Excel)
    """
    # 暫時重定向到 Excel 匯出
    return export_to_excel(report_type, start_date, end_date)


def get_report_data(report_type, start_date, end_date):
    """
    根據報表類型獲取數據
    """
    if report_type == 'daily_work':
        return get_daily_work_report_data(start_date, end_date)
    elif report_type == 'weekly_work':
        return get_weekly_work_report_data(start_date, end_date)
    elif report_type == 'monthly_work':
        return get_monthly_work_report_data(start_date, end_date)
    elif 'work_hour_operator' in report_type:
        return get_work_hour_operator_report_data(report_type, start_date, end_date)
    elif 'work_hour_smt' in report_type:
        return get_work_hour_smt_report_data(report_type, start_date, end_date)
    elif report_type == 'operator_performance':
        return get_operator_performance_report_data(start_date, end_date)
    elif report_type == 'smt_equipment':
        return get_smt_equipment_report_data(start_date, end_date)
    elif report_type == 'abnormal_report':
        return get_abnormal_report_data(start_date, end_date)
    elif report_type == 'efficiency_analysis':
        return get_efficiency_analysis_report_data(start_date, end_date)
    
    return []


def get_daily_work_report_data(start_date, end_date):
    """
    獲取日工作報表數據
    """
    reports = OperatorSupplementReport.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status="approved"
    ).select_related('operator', 'workorder')
    
    data = []
    for report in reports:
        data.append([
            report.operator.name if report.operator else '',
            report.work_date.strftime('%Y-%m-%d'),
            report.workorder.order_number if report.workorder else '',
            report.product_id or '',
            report.start_time.strftime('%H:%M') if report.start_time else '',
            report.end_time.strftime('%H:%M') if report.end_time else '',
            report.process.name if report.process else '',
            report.work_quantity or 0,
            report.defect_quantity or 0,
        ])
    
    return data


def get_weekly_work_report_data(start_date, end_date):
    """
    獲取週工作報表數據
    """
    reports = OperatorSupplementReport.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status="approved"
    ).values('operator__name').annotate(
        total_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    data = []
    for report in reports:
        data.append([
            report['operator__name'] or '',
            report['total_quantity'] or 0,
            report['total_defect_quantity'] or 0,
        ])
    
    return data


def get_monthly_work_report_data(start_date, end_date):
    """
    獲取月工作報表數據
    """
    reports = OperatorSupplementReport.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status="approved"
    ).values('operator__name').annotate(
        total_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    data = []
    for report in reports:
        data.append([
            report['operator__name'] or '',
            report['total_quantity'] or 0,
            report['total_defect_quantity'] or 0,
        ])
    
    return data


def get_work_hour_operator_report_data(report_type, start_date, end_date):
    """
    獲取作業員工時報表數據
    """
    reports = OperatorSupplementReport.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status="approved"
    ).select_related('operator')
    
    data = []
    for report in reports:
        # 計算工時
        if report.start_time and report.end_time:
            duration = report.end_time - report.start_time
            hours = duration.total_seconds() / 3600
        else:
            hours = 0
        
        data.append([
            report.operator.name if report.operator else '',
            report.work_date.strftime('%Y-%m-%d'),
            round(hours, 2),
            report.work_quantity or 0,
            report.defect_quantity or 0,
        ])
    
    return data


def get_work_hour_smt_report_data(report_type, start_date, end_date):
    """
    獲取 SMT 設備工時報表數據
    """
    reports = SMTSupplementReport.objects.filter(
        work_date__range=[start_date, end_date]
    ).select_related('equipment')
    
    data = []
    for report in reports:
        # 計算運行時間
        if report.start_time and report.end_time:
            duration = report.end_time - report.start_time
            hours = duration.total_seconds() / 3600
        else:
            hours = 0
        
        data.append([
            report.equipment.name if report.equipment else '',
            report.work_date.strftime('%Y-%m-%d'),
            round(hours, 2),
            report.work_quantity or 0,
            report.defect_quantity or 0,
        ])
    
    return data


def get_operator_performance_report_data(start_date, end_date):
    """
    獲取作業員績效報表數據
    """
    reports = OperatorSupplementReport.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status="approved"
    ).values('operator__name').annotate(
        total_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    data = []
    for report in reports:
        total_quantity = report['total_quantity'] or 0
        total_defect_quantity = report['total_defect_quantity'] or 0
        total_output = total_quantity + total_defect_quantity
        
        if total_output > 0:
            defect_rate = (total_defect_quantity / total_output) * 100
        else:
            defect_rate = 0
        
        data.append([
            report['operator__name'] or '',
            total_quantity,
            total_defect_quantity,
            round(defect_rate, 2),
            0,  # 效率率暫時設為0，因為模型中没有efficiency欄位
        ])
    
    return data


def get_smt_equipment_report_data(start_date, end_date):
    """
    獲取 SMT 設備效率報表數據
    """
    reports = SMTSupplementReport.objects.filter(
        work_date__range=[start_date, end_date]
    ).values('equipment__name').annotate(
        total_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    data = []
    for report in reports:
        total_quantity = report['total_quantity'] or 0
        total_defect_quantity = report['total_defect_quantity'] or 0
        total_output = total_quantity + total_defect_quantity
        
        if total_output > 0:
            defect_rate = (total_defect_quantity / total_output) * 100
        else:
            defect_rate = 0
        
        data.append([
            report['equipment__name'] or '',
            total_quantity,
            total_defect_quantity,
            round(defect_rate, 2),
            0,  # 效率率暫時設為0，因為模型中没有efficiency欄位
        ])
    
    return data


def get_abnormal_report_data(start_date, end_date):
    """
    獲取異常報工報表數據
    """
    reports = OperatorSupplementReport.objects.filter(
        work_date__range=[start_date, end_date],
        abnormal_notes__isnull=False
    ).exclude(abnormal_notes='').select_related('operator', 'workorder', 'process')
    
    data = []
    for report in reports:
        data.append([
            report.operator.name if report.operator else '',
            report.work_date.strftime('%Y-%m-%d'),
            report.workorder.order_number if report.workorder else '',
            report.process.name if report.process else '',
            report.abnormal_notes,
            report.work_quantity or 0,
            report.defect_quantity or 0,
        ])
    
    return data


def get_efficiency_analysis_report_data(start_date, end_date):
    """
    獲取效率分析報表數據
    """
    reports = OperatorSupplementReport.objects.filter(
        work_date__range=[start_date, end_date],
        approval_status="approved"
    ).values('operator__name', 'process__name').annotate(
        total_quantity=Sum('work_quantity'),
        total_defect_quantity=Sum('defect_quantity')
    )
    
    data = []
    for report in reports:
        total_quantity = report['total_quantity'] or 0
        total_defect_quantity = report['total_defect_quantity'] or 0
        total_output = total_quantity + total_defect_quantity
        
        if total_output > 0:
            defect_rate = (total_defect_quantity / total_output) * 100
        else:
            defect_rate = 0
        
        data.append([
            report['operator__name'] or '',
            report['process__name'] or '',
            total_quantity,
            total_defect_quantity,
            round(defect_rate, 2),
            0,  # 效率率暫時設為0，因為模型中没有efficiency欄位
        ])
    
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
    return f"{title}_{start_date}_{end_date}"


def placeholder_view(request, function_name=None):
    """
    通用佔位符視圖
    用於所有未實現的功能
    """
    return render(request, 'reporting/placeholder.html', {
        'function_name': function_name or '未知功能'
    }) 