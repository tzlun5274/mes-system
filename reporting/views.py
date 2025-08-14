"""
報表模組視圖
提供各種報表的查詢和匯出功能
"""

import logging
from datetime import datetime, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from workorder.fill_work.models import FillWork
from workorder.models import WorkOrder, CompletedWorkOrder
from equip.models import Equipment
from process.models import Operator

logger = logging.getLogger(__name__)

def index(request):
    """報表首頁"""
    return render(request, 'reporting/index.html')

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