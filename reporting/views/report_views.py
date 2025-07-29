# -*- coding: utf-8 -*-
"""
報表查看視圖
提供報表列表、詳情、匯出等功能
"""

from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import models
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import datetime, timedelta, date
from reporting.models import WorkTimeReport, WorkOrderProductReport
import json
import logging

logger = logging.getLogger(__name__)


# 權限檢查函數
def reporting_user_required(user):
    """檢查用戶是否為超級用戶或屬於「報表使用者」群組"""
    return user.is_superuser or user.groups.filter(name="報表使用者").exists()


# 用戶操作日誌函數
def log_user_operation(username, module, action):
    """記錄用戶操作"""
    logger.info(f"用戶操作 - 用戶: {username}, 模組: {module}, 動作: {action}")


class ReportDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """報表儀表板視圖"""
    template_name = 'reporting/dashboard.html'
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_authenticated
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        dashboard_data = self.get_dashboard_data()
        context.update(dashboard_data)
        return context
    
    def get_dashboard_data(self):
        """取得儀表板資料"""
        # 今日報表統計
        today = timezone.now().date()
        today_work_time = WorkTimeReport.objects.filter(report_date=today)
        today_work_order = WorkOrderProductReport.objects.filter(report_date=today)
        
        # 本週報表統計
        week_start = today - timedelta(days=today.weekday())
        week_work_time = WorkTimeReport.objects.filter(report_date__gte=week_start)
        week_work_order = WorkOrderProductReport.objects.filter(report_date__gte=week_start)
        
        # 本月報表統計
        month_start = today.replace(day=1)
        month_work_time = WorkTimeReport.objects.filter(report_date__gte=month_start)
        month_work_order = WorkOrderProductReport.objects.filter(report_date__gte=month_start)
        
        # 計算總計數據
        total_production = WorkTimeReport.objects.count()
        today_production = today_work_time.count()
        total_operator = WorkTimeReport.objects.values('worker_name').distinct().count()
        active_operators = WorkTimeReport.objects.filter(report_date__gte=today - timedelta(days=7)).values('worker_name').distinct().count()
        total_smt = WorkOrderProductReport.objects.count()
        running_equipment = WorkOrderProductReport.objects.filter(report_date=today).count()
        
        # 計算平均效率（這裡使用一個簡單的計算方式）
        total_completed = WorkTimeReport.objects.aggregate(total=models.Sum('completed_quantity'))['total'] or 0
        total_defects = WorkTimeReport.objects.aggregate(total=models.Sum('defect_quantity'))['total'] or 0
        total_quantity = total_completed + total_defects
        avg_efficiency = round((total_completed / total_quantity * 100) if total_quantity > 0 else 0, 1)
        
        return {
            'total_production': total_production,
            'today_production': today_production,
            'total_operator': total_operator,
            'active_operators': active_operators,
            'total_smt': total_smt,
            'running_equipment': running_equipment,
            'avg_efficiency': avg_efficiency,
            'now': timezone.now(),
            'today_stats': {
                'work_time_count': today_work_time.count(),
                'work_order_count': today_work_order.count(),
                'total_completed': today_work_time.aggregate(total=models.Sum('completed_quantity'))['total'] or 0,
                'total_defects': today_work_time.aggregate(total=models.Sum('defect_quantity'))['total'] or 0,
            },
            'week_stats': {
                'work_time_count': week_work_time.count(),
                'work_order_count': week_work_order.count(),
                'total_completed': week_work_time.aggregate(total=models.Sum('completed_quantity'))['total'] or 0,
                'total_defects': week_work_time.aggregate(total=models.Sum('defect_quantity'))['total'] or 0,
            },
            'month_stats': {
                'work_time_count': month_work_time.count(),
                'work_order_count': month_work_order.count(),
                'total_completed': month_work_time.aggregate(total=models.Sum('completed_quantity'))['total'] or 0,
                'total_defects': month_work_time.aggregate(total=models.Sum('defect_quantity'))['total'] or 0,
            },
            'recent_work_time': WorkTimeReport.objects.order_by('-report_date', '-created_at')[:10],
            'recent_work_order': WorkOrderProductReport.objects.order_by('-report_date', '-created_at')[:10],
        }


class WorkTimeReportListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """工作時間報表列表視圖"""
    model = WorkTimeReport
    template_name = 'reporting/work_time_list.html'
    context_object_name = 'work_time_reports'
    paginate_by = 20
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_authenticated
    
    def get_queryset(self):
        """取得查詢集"""
        queryset = super().get_queryset()
        
        # 取得報表類型
        report_type = self.request.GET.get('type', 'daily')
        
        # 搜尋功能
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(worker_name__icontains=search) |
                models.Q(workorder_number__icontains=search) |
                models.Q(process_name__icontains=search)
            )
        
        # 日期篩選
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(report_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(report_date__lte=date_to)
        
        # 根據報表類型進行不同的處理
        if report_type == 'weekly':
            # 週報表：按週分組統計
            from django.db.models import Sum, Avg, Count
            from django.db.models.functions import TruncWeek
            
            queryset = queryset.annotate(
                week_start=TruncWeek('report_date')
            ).values(
                'week_start', 'worker_name', 'workorder_number', 
                'product_code', 'process_name'
            ).annotate(
                total_work_hours=Sum('total_work_hours'),
                completed_quantity=Sum('completed_quantity'),
                defect_quantity=Sum('defect_quantity'),
                report_count=Count('id')
            ).order_by('-week_start', 'worker_name')
            
        elif report_type == 'monthly':
            # 月報表：按月分組統計
            from django.db.models import Sum, Avg, Count
            from django.db.models.functions import TruncMonth
            
            queryset = queryset.annotate(
                month_start=TruncMonth('report_date')
            ).values(
                'month_start', 'worker_name', 'workorder_number', 
                'product_code', 'process_name'
            ).annotate(
                total_work_hours=Sum('total_work_hours'),
                completed_quantity=Sum('completed_quantity'),
                defect_quantity=Sum('defect_quantity'),
                report_count=Count('id')
            ).order_by('-month_start', 'worker_name')
            
        else:
            # 日報表：保持原有邏輯
            order_by = self.request.GET.get('order_by', '-report_date')
            queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 報表類型參數
        context['report_type'] = self.request.GET.get('type', 'daily')
        
        # 搜尋和篩選參數
        context['search'] = self.request.GET.get('search', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['order_by'] = self.request.GET.get('order_by', '-report_date')
        
        # 統計資料
        queryset = self.get_queryset()
        context['total_completed'] = queryset.aggregate(
            total=models.Sum('completed_quantity')
        )['total'] or 0
        context['total_defects'] = queryset.aggregate(
            total=models.Sum('defect_quantity')
        )['total'] or 0
        
        # 計算平均效率
        total_quantity = context['total_completed'] + context['total_defects']
        if total_quantity > 0:
            context['avg_efficiency'] = round(
                (context['total_completed'] / total_quantity * 100), 1
            )
        else:
            context['avg_efficiency'] = 0
        
        # 作業員和工序選項
        context['workers'] = WorkTimeReport.objects.values_list(
            'worker_name', flat=True
        ).distinct().order_by('worker_name')
        
        context['processes'] = WorkTimeReport.objects.values_list(
            'process_name', flat=True
        ).distinct().order_by('process_name')
        
        return context


class WorkTimeReportDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """工作時間報表詳情視圖"""
    model = WorkTimeReport
    template_name = 'reporting/work_time_detail.html'
    context_object_name = 'work_time_report'
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_authenticated


class WorkTimeReportExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """工作時間報表匯出視圖"""
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_authenticated
    
    def get(self, request, *args, **kwargs):
        """匯出工作時間報表"""
        try:
            format_type = request.GET.get('format', 'excel')
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')
            
            # 查詢資料
            queryset = WorkTimeReport.objects.all()
            
            if date_from:
                queryset = queryset.filter(report_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(report_date__lte=date_to)
            
            # 準備資料
            data = []
            for report in queryset:
                data.append({
                    '報表日期': report.report_date.strftime('%Y-%m-%d'),
                    '作業員': report.worker_name,
                    '工單號': report.work_order_no,
                    '產品編號': getattr(report, 'product_code', ''),
                    '工序': report.process_name,
                    '開始時間': report.start_time.strftime('%H:%M') if report.start_time else '',
                    '結束時間': report.end_time.strftime('%H:%M') if report.end_time else '',
                    '工作時數': report.work_hours or 0,
                    '完成數量': report.completed_quantity or 0,
                    '不良品': report.defect_quantity or 0,
                })
            
            # 匯出檔案
            if format_type == 'csv':
                return self.export_to_csv(data, 'work_time_report.csv')
            else:
                return self.export_to_excel(data, 'work_time_report.xlsx')
                
        except Exception as e:
            logger.error(f"匯出工作時間報表失敗：{str(e)}")
            messages.error(request, f"匯出失敗：{str(e)}")
            return redirect('reporting:work_time_list')
    
    def export_to_excel(self, data, filename):
        """匯出為Excel檔案"""
        import openpyxl
        from openpyxl.utils import get_column_letter
        
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "工作時間報表"
        
        # 寫入表頭
        if data:
            headers = list(data[0].keys())
            for col, header in enumerate(headers, 1):
                worksheet.cell(row=1, column=col, value=header)
            
            # 寫入資料
            for row, record in enumerate(data, 2):
                for col, value in enumerate(record.values(), 1):
                    worksheet.cell(row=row, column=col, value=value)
            
            # 調整欄寬
            for col in range(1, len(headers) + 1):
                worksheet.column_dimensions[get_column_letter(col)].width = 15
        
        # 建立回應
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        workbook.save(response)
        return response
    
    def export_to_csv(self, data, filename):
        """匯出為CSV檔案"""
        import csv
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # 寫入BOM以支援中文
        response.write('\ufeff')
        
        if data:
            writer = csv.DictWriter(response, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        return response


class WorkOrderProductReportListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """工單機種報表列表視圖"""
    model = WorkOrderProductReport
    template_name = 'reporting/work_order_list.html'
    context_object_name = 'work_order_reports'
    paginate_by = 20
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_authenticated
    
    def get_queryset(self):
        """取得查詢集"""
        queryset = super().get_queryset()
        
        # 搜尋功能
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(work_order_no__icontains=search) |
                models.Q(product_name__icontains=search) |
                models.Q(process_name__icontains=search)
            )
        
        # 日期篩選
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(report_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(report_date__lte=date_to)
        
        # 排序
        order_by = self.request.GET.get('order_by', '-report_date')
        queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 搜尋和篩選參數
        context['search'] = self.request.GET.get('search', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['order_by'] = self.request.GET.get('order_by', '-report_date')
        
        # 統計資料
        queryset = self.get_queryset()
        context['total_production'] = queryset.aggregate(
            total=models.Sum('actual_quantity')
        )['total'] or 0
        
        # 計算完成率
        total_planned = queryset.aggregate(
            total=models.Sum('planned_quantity')
        )['total'] or 0
        if total_planned > 0:
            context['completion_rate'] = round(
                (context['total_production'] / total_planned * 100), 1
            )
        else:
            context['completion_rate'] = 0
        
        # 計算平均效率
        efficiency_sum = queryset.aggregate(
            total=models.Sum('efficiency')
        )['total'] or 0
        efficiency_count = queryset.count()
        if efficiency_count > 0:
            context['avg_efficiency'] = round(efficiency_sum / efficiency_count, 1)
        else:
            context['avg_efficiency'] = 0
        
        # 機種選項
        context['products'] = WorkOrderProductReport.objects.values_list(
            'product_name', flat=True
        ).distinct().order_by('product_name')
        
        return context


class WorkOrderProductReportDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """工單機種報表詳情視圖"""
    model = WorkOrderProductReport
    template_name = 'reporting/work_order_detail.html'
    context_object_name = 'work_order_report'
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_authenticated


class WorkOrderProductReportExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """工單機種報表匯出視圖"""
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_authenticated
    
    def get(self, request, *args, **kwargs):
        """匯出工單機種報表"""
        try:
            format_type = request.GET.get('format', 'excel')
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')
            
            # 查詢資料
            queryset = WorkOrderProductReport.objects.all()
            
            if date_from:
                queryset = queryset.filter(report_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(report_date__lte=date_to)
            
            # 準備資料
            data = []
            for report in queryset:
                data.append({
                    '報表日期': report.report_date.strftime('%Y-%m-%d'),
                    '作業員': getattr(report, 'worker_name', ''),
                    '工單號': report.work_order_no,
                    '產品編號': report.product_name,
                    '工序': getattr(report, 'process_name', ''),
                    '開始時間': report.start_date.strftime('%Y-%m-%d') if report.start_date else '',
                    '結束時間': report.completion_date.strftime('%Y-%m-%d') if report.completion_date else '',
                    '工作時數': getattr(report, 'work_hours', 0) or 0,
                    '完成數量': report.actual_quantity or 0,
                    '不良品': report.defect_quantity or 0,
                })
            
            # 匯出檔案
            if format_type == 'csv':
                return self.export_to_csv(data, 'work_order_report.csv')
            else:
                return self.export_to_excel(data, 'work_order_report.xlsx')
                
        except Exception as e:
            logger.error(f"匯出工單機種報表失敗：{str(e)}")
            messages.error(request, f"匯出失敗：{str(e)}")
            return redirect('reporting:work_order_list')
    
    def export_to_excel(self, data, filename):
        """匯出為Excel檔案"""
        import openpyxl
        from openpyxl.utils import get_column_letter
        
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "工單機種報表"
        
        # 寫入表頭
        if data:
            headers = list(data[0].keys())
            for col, header in enumerate(headers, 1):
                worksheet.cell(row=1, column=col, value=header)
            
            # 寫入資料
            for row, record in enumerate(data, 2):
                for col, value in enumerate(record.values(), 1):
                    worksheet.cell(row=row, column=col, value=value)
            
            # 調整欄寬
            for col in range(1, len(headers) + 1):
                worksheet.column_dimensions[get_column_letter(col)].width = 15
        
        # 建立回應
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        workbook.save(response)
        return response
    
    def export_to_csv(self, data, filename):
        """匯出為CSV檔案"""
        import csv
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # 寫入BOM以支援中文
        response.write('\ufeff')
        
        if data:
            writer = csv.DictWriter(response, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        return response


class ReportExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """報表匯出視圖"""
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_authenticated
    
    def get(self, request, *args, **kwargs):
        """顯示報表匯出頁面"""
        return render(request, 'reporting/report_export.html')
    
    def post(self, request, *args, **kwargs):
        """執行報表匯出"""
        try:
            report_type = request.POST.get('report_type')
            date_from = request.POST.get('date_from')
            date_to = request.POST.get('date_to')
            format_type = request.POST.get('format', 'excel')
            
            if report_type == 'work_time':
                return redirect(f"{reverse('reporting:work_time_export')}?date_from={date_from}&date_to={date_to}&format={format_type}")
            elif report_type == 'work_order':
                return redirect(f"{reverse('reporting:work_order_export')}?date_from={date_from}&date_to={date_to}&format={format_type}")
            else:
                messages.error(request, "不支援的報表類型")
                return redirect('reporting:export')
                
        except Exception as e:
            logger.error(f"報表匯出失敗：{str(e)}")
            messages.error(request, f"匯出失敗：{str(e)}")
            return redirect('reporting:export')


# 報表匯出函數
@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def report_export(request):
    """
    報表匯出頁面 - 統一管理所有報表匯出功能
    匯出各種報工報表，支援Excel、CSV、PDF等多種格式
    """
    from django.db.models import Q
    from workorder.models import OperatorSupplementReport, SMTProductionReport
    
    # 記錄用戶操作
    log_user_operation(request.user.username, "reporting", "訪問報表匯出頁面")
    
    today = date.today()
    month_start = today.replace(day=1)
    
    # 可匯出的報表類型
    report_types = [
        {'id': 'daily', 'name': '日報表', 'description': '每日報工統計報表', 'icon': 'fas fa-calendar-day'},
        {'id': 'weekly', 'name': '週報表', 'description': '每週報工統計報表', 'icon': 'fas fa-calendar-week'},
        {'id': 'monthly', 'name': '月報表', 'description': '每月報工統計報表', 'icon': 'fas fa-calendar-alt'},
        {'id': 'operator', 'name': '作業員報工報表', 'description': '作業員報工詳細記錄', 'icon': 'fas fa-user'},
        {'id': 'smt', 'name': 'SMT報工報表', 'description': 'SMT設備報工詳細記錄', 'icon': 'fas fa-microchip'},
        {'id': 'abnormal', 'name': '異常報工報表', 'description': '異常報工記錄分析', 'icon': 'fas fa-exclamation-triangle'},
        {'id': 'efficiency', 'name': '效率分析報表', 'description': '產能效率分析報表', 'icon': 'fas fa-tachometer-alt'},
        {'id': 'production_daily', 'name': '生產日報表', 'description': '生產日報表統計', 'icon': 'fas fa-chart-line'},
        {'id': 'operator_performance', 'name': '作業員績效報表', 'description': '作業員績效分析', 'icon': 'fas fa-user-chart'},
    ]
    
    # 匯出格式
    export_formats = [
        {'id': 'excel', 'name': 'Excel (.xlsx)', 'icon': 'fas fa-file-excel'},
        {'id': 'csv', 'name': 'CSV (.csv)', 'icon': 'fas fa-file-csv'},
        {'id': 'pdf', 'name': 'PDF (.pdf)', 'icon': 'fas fa-file-pdf'},
    ]
    
    # 日期範圍選項
    date_ranges = [
        {'id': 'today', 'name': '今日', 'start': today, 'end': today},
        {'id': 'yesterday', 'name': '昨日', 'start': today - timedelta(days=1), 'end': today - timedelta(days=1)},
        {'id': 'week', 'name': '本週', 'start': today - timedelta(days=today.weekday()), 'end': today},
        {'id': 'month', 'name': '本月', 'start': month_start, 'end': today},
        {'id': 'custom', 'name': '自訂日期範圍', 'start': None, 'end': None},
    ]
    
    context = {
        'report_types': report_types,
        'export_formats': export_formats,
        'date_ranges': date_ranges,
    }
    return render(request, 'reporting/report_export.html', context)


@login_required
@user_passes_test(reporting_user_required, login_url="/accounts/login/")
def execute_report_export(request):
    """
    執行報表匯出功能
    """
    from django.http import HttpResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from datetime import datetime
    import csv
    from io import StringIO
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '只支援POST請求'})
    
    try:
        report_type = request.POST.get('report_type')
        export_format = request.POST.get('export_format')
        date_range = request.POST.get('date_range')
        custom_start = request.POST.get('custom_start')
        custom_end = request.POST.get('custom_end')
        
        # 記錄用戶操作
        log_user_operation(
            request.user.username, 
            "reporting", 
            f"匯出報表：{report_type}，格式：{export_format}，日期範圍：{date_range}"
        )
        
        # 根據報表類型取得資料
        if report_type == 'operator':
            data = get_operator_report_data(date_range, custom_start, custom_end)
            filename = f'作業員報工報表_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        elif report_type == 'smt':
            data = get_smt_report_data(date_range, custom_start, custom_end)
            filename = f'SMT報工報表_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        elif report_type == 'abnormal':
            data = get_abnormal_report_data(date_range, custom_start, custom_end)
            filename = f'異常報工報表_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        elif report_type == 'production_daily':
            data = get_production_daily_report_data(date_range, custom_start, custom_end)
            filename = f'生產日報表_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        elif report_type == 'operator_performance':
            data = get_operator_performance_report_data(date_range, custom_start, custom_end)
            filename = f'作業員績效報表_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        else:
            return JsonResponse({'success': False, 'error': '不支援的報表類型'})
        
        # 根據格式匯出
        if export_format == 'excel':
            return export_to_excel(data, filename)
        elif export_format == 'csv':
            return export_to_csv(data, filename)
        elif export_format == 'pdf':
            return export_to_pdf(data, filename)
        else:
            return JsonResponse({'success': False, 'error': '不支援的匯出格式'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'匯出失敗：{str(e)}'})


# 資料獲取函數
def get_operator_report_data(date_range, custom_start=None, custom_end=None):
    """取得作業員報工資料"""
    from workorder.models import OperatorSupplementReport
    
    today = date.today()
    
    # 設定日期範圍
    if date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif date_range == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # 查詢資料
    reports = OperatorSupplementReport.objects.filter(
        work_date__gte=start_date,
        work_date__lte=end_date
    ).order_by('work_date', 'worker_name')
    
    # 準備資料
    data = []
    for report in reports:
        data.append({
            '報工日期': report.work_date.strftime('%Y-%m-%d'),
            '作業員': report.worker_name,
            '工單號': report.work_order_no,
            '工序': report.process_name,
            '完成數量': report.completed_quantity or 0,
            '不良數量': report.defect_quantity or 0,
            '開始時間': report.start_time.strftime('%H:%M') if report.start_time else '',
            '結束時間': report.end_time.strftime('%H:%M') if report.end_time else '',
            '異常紀錄': report.abnormal_notes or '',
        })
    
    return data


def get_smt_report_data(date_range, custom_start=None, custom_end=None):
    """取得SMT報工資料"""
    from workorder.models import SMTProductionReport
    
    today = date.today()
    
    # 設定日期範圍
    if date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif date_range == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # 查詢資料
    reports = SMTProductionReport.objects.filter(
        work_date__gte=start_date,
        work_date__lte=end_date
    ).order_by('work_date', 'equipment_name')
    
    # 準備資料
    data = []
    for report in reports:
        data.append({
            '報工日期': report.work_date.strftime('%Y-%m-%d'),
            '設備名稱': report.equipment_name,
            '製令號碼': report.work_order_no,
            '機種名稱': report.product_name,
            '完成數量': report.completed_quantity or 0,
            '不良數量': report.defect_quantity or 0,
            '異常紀錄': report.abnormal_notes or '',
        })
    
    return data


def get_abnormal_report_data(date_range, custom_start=None, custom_end=None):
    """取得異常報工資料"""
    from workorder.models import OperatorSupplementReport, SMTProductionReport
    
    today = date.today()
    
    # 設定日期範圍
    if date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif date_range == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # 查詢作業員異常報工
    operator_reports = OperatorSupplementReport.objects.filter(
        work_date__gte=start_date,
        work_date__lte=end_date,
        abnormal_notes__isnull=False
    ).exclude(abnormal_notes='')
    
    # 查詢SMT異常報工
    smt_reports = SMTProductionReport.objects.filter(
        work_date__gte=start_date,
        work_date__lte=end_date,
        abnormal_notes__isnull=False
    ).exclude(abnormal_notes='')
    
    # 準備資料
    data = []
    
    # 作業員異常報工
    for report in operator_reports:
        data.append({
            '報工日期': report.work_date.strftime('%Y-%m-%d'),
            '報工類型': '作業員報工',
            '作業員/設備': report.worker_name,
            '工單號': report.work_order_no,
            '工序/機種': report.process_name,
            '異常紀錄': report.abnormal_notes,
        })
    
    # SMT異常報工
    for report in smt_reports:
        data.append({
            '報工日期': report.work_date.strftime('%Y-%m-%d'),
            '報工類型': 'SMT報工',
            '作業員/設備': report.equipment_name,
            '工單號': report.work_order_no,
            '工序/機種': report.product_name,
            '異常紀錄': report.abnormal_notes,
        })
    
    # 按日期排序
    data.sort(key=lambda x: x['報工日期'])
    
    return data


def get_production_daily_report_data(date_range, custom_start=None, custom_end=None):
    """取得生產日報表資料"""
    from workorder.models import OperatorSupplementReport, SMTProductionReport
    
    today = date.today()
    
    # 設定日期範圍
    if date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif date_range == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # 查詢資料
    operator_reports = OperatorSupplementReport.objects.filter(
        work_date__gte=start_date,
        work_date__lte=end_date
    )
    
    smt_reports = SMTProductionReport.objects.filter(
        work_date__gte=start_date,
        work_date__lte=end_date
    )
    
    # 按日期分組統計
    daily_stats = {}
    
    # 統計作業員報工
    for report in operator_reports:
        date_str = report.work_date.strftime('%Y-%m-%d')
        if date_str not in daily_stats:
            daily_stats[date_str] = {
                '日期': date_str,
                '作業員報工數': 0,
                '作業員完成數量': 0,
                '作業員不良數量': 0,
                'SMT報工數': 0,
                'SMT完成數量': 0,
                'SMT不良數量': 0,
            }
        
        daily_stats[date_str]['作業員報工數'] += 1
        daily_stats[date_str]['作業員完成數量'] += report.completed_quantity or 0
        daily_stats[date_str]['作業員不良數量'] += report.defect_quantity or 0
    
    # 統計SMT報工
    for report in smt_reports:
        date_str = report.work_date.strftime('%Y-%m-%d')
        if date_str not in daily_stats:
            daily_stats[date_str] = {
                '日期': date_str,
                '作業員報工數': 0,
                '作業員完成數量': 0,
                '作業員不良數量': 0,
                'SMT報工數': 0,
                'SMT完成數量': 0,
                'SMT不良數量': 0,
            }
        
        daily_stats[date_str]['SMT報工數'] += 1
        daily_stats[date_str]['SMT完成數量'] += report.completed_quantity or 0
        daily_stats[date_str]['SMT不良數量'] += report.defect_quantity or 0
    
    # 轉換為列表並排序
    data = list(daily_stats.values())
    data.sort(key=lambda x: x['日期'])
    
    return data


def get_operator_performance_report_data(date_range, custom_start=None, custom_end=None):
    """取得作業員績效報表資料"""
    from workorder.models import OperatorSupplementReport
    
    today = date.today()
    
    # 設定日期範圍
    if date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif date_range == 'custom' and custom_start and custom_end:
        start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # 查詢資料
    reports = OperatorSupplementReport.objects.filter(
        work_date__gte=start_date,
        work_date__lte=end_date
    ).order_by('worker_name', 'work_date')
    
    # 按作業員分組統計
    operator_stats = {}
    
    for report in reports:
        worker_name = report.worker_name
        if worker_name not in operator_stats:
            operator_stats[worker_name] = {
                '作業員': worker_name,
                '報工次數': 0,
                '總完成數量': 0,
                '總不良數量': 0,
                '總工作時間': 0,
                '平均效率': 0,
            }
        
        operator_stats[worker_name]['報工次數'] += 1
        operator_stats[worker_name]['總完成數量'] += report.completed_quantity or 0
        operator_stats[worker_name]['總不良數量'] += report.defect_quantity or 0
        
        # 計算工作時間（如果有開始和結束時間）
        if report.start_time and report.end_time:
            duration = report.end_time - report.start_time
            operator_stats[worker_name]['總工作時間'] += duration.total_seconds() / 3600  # 轉換為小時
    
    # 計算平均效率
    for stats in operator_stats.values():
        total_quantity = stats['總完成數量'] + stats['總不良數量']
        if total_quantity > 0:
            stats['平均效率'] = round((stats['總完成數量'] / total_quantity) * 100, 2)
    
    # 轉換為列表並排序
    data = list(operator_stats.values())
    data.sort(key=lambda x: x['作業員'])
    
    return data


# 匯出函數
def export_to_excel(data, filename):
    """匯出為Excel檔案"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "報表資料"
    
    # 寫入表頭
    if data:
        headers = list(data[0].keys())
        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        # 寫入資料
        for row, record in enumerate(data, 2):
            for col, value in enumerate(record.values(), 1):
                worksheet.cell(row=row, column=col, value=value)
        
        # 調整欄寬
        for col in range(1, len(headers) + 1):
            worksheet.column_dimensions[get_column_letter(col)].width = 15
    
    # 建立回應
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    workbook.save(response)
    return response


def export_to_csv(data, filename):
    """匯出為CSV檔案"""
    import csv
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    # 寫入BOM以支援中文
    response.write('\ufeff')
    
    if data:
        writer = csv.DictWriter(response, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    return response


def export_to_pdf(data, filename):
    """匯出為PDF檔案（暫時重定向到Excel）"""
    # 暫時使用Excel格式，未來實作真正的PDF匯出
    return export_to_excel(data, filename) 