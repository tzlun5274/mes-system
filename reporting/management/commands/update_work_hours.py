"""
更新報表資料的工作時數
修復工作時數顯示為0的問題
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.fill_work.models import FillWork
from reporting.models import WorkOrderReportData
from django.db.models import Sum
from datetime import timedelta


class Command(BaseCommand):
    help = '更新報表資料的工作時數'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='指定要更新的日期 (YYYY-MM-DD)',
        )

    def handle(self, *args, **options):
        self.stdout.write('開始更新報表資料的工作時數...')
        
        # 取得要更新的日期範圍
        if options['date']:
            from datetime import datetime
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            report_data_list = WorkOrderReportData.objects.filter(work_date=target_date)
        else:
            report_data_list = WorkOrderReportData.objects.all()
        
        updated_count = 0
        
        with transaction.atomic():
            for report_data in report_data_list:
                # 找到對應的填報資料
                fill_work = FillWork.objects.filter(
                    workorder=report_data.workorder_id,
                    company_name=report_data.company,
                    work_date=report_data.work_date,
                    operator=report_data.operator_name,
                    start_time=report_data.start_time
                ).first()
                
                if fill_work:
                    # 更新工作時數
                    report_data.work_hours = fill_work.work_hours_calculated or 0
                    report_data.overtime_hours = fill_work.overtime_hours_calculated or 0
                    report_data.total_hours = float(fill_work.work_hours_calculated or 0) + float(fill_work.overtime_hours_calculated or 0)
                    report_data.daily_work_hours = fill_work.work_hours_calculated or 0
                    
                    # 計算週工作時數
                    start_of_week = report_data.work_date - timedelta(days=report_data.work_date.weekday())
                    end_of_week = start_of_week + timedelta(days=6)
                    
                    weekly_hours = WorkOrderReportData.objects.filter(
                        work_date__range=[start_of_week, end_of_week],
                        operator_name=report_data.operator_name,
                        company=report_data.company
                    ).aggregate(total=Sum('daily_work_hours'))['total'] or 0
                    
                    # 計算月工作時數
                    start_of_month = report_data.work_date.replace(day=1)
                    if report_data.work_date.month == 12:
                        end_of_month = report_data.work_date.replace(year=report_data.work_date.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        end_of_month = report_data.work_date.replace(month=report_data.work_date.month + 1, day=1) - timedelta(days=1)
                    
                    monthly_hours = WorkOrderReportData.objects.filter(
                        work_date__range=[start_of_month, end_of_month],
                        operator_name=report_data.operator_name,
                        company=report_data.company
                    ).aggregate(total=Sum('daily_work_hours'))['total'] or 0
                    
                    report_data.weekly_work_hours = weekly_hours
                    report_data.monthly_work_hours = monthly_hours
                    report_data.save()
                    
                    updated_count += 1
                    
                    if updated_count % 100 == 0:
                        self.stdout.write(f'已更新 {updated_count} 筆資料...')
        
        self.stdout.write(
            self.style.SUCCESS(f'更新完成！共更新 {updated_count} 筆報表資料')
        )
