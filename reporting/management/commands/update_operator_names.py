"""
更新報表資料中的作業員姓名
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from reporting.models import WorkOrderReportData
from workorder.fill_work.models import FillWork
from workorder.onsite_reporting.models import OnsiteReport


class Command(BaseCommand):
    help = '更新報表資料中的作業員姓名'

    def handle(self, *args, **options):
        self.stdout.write('開始更新作業員姓名...')
        
        updated_count = 0
        
        with transaction.atomic():
            # 更新來自填報作業的資料
            for report_data in WorkOrderReportData.objects.filter(operator_name__isnull=True):
                # 查找對應的填報作業記錄
                fill_work = FillWork.objects.filter(
                    workorder=report_data.workorder_id,
                    work_date=report_data.work_date
                ).first()
                
                if fill_work and fill_work.operator:
                    report_data.operator_name = fill_work.operator
                    report_data.save()
                    updated_count += 1
                    self.stdout.write(f'更新記錄: {report_data.workorder_id} -> {fill_work.operator}')
                
                # 如果填報作業沒有找到，查找現場報工記錄
                elif not fill_work:
                    onsite_report = OnsiteReport.objects.filter(
                        workorder=report_data.workorder_id,
                        work_date=report_data.work_date
                    ).first()
                    
                    if onsite_report and onsite_report.operator:
                        report_data.operator_name = onsite_report.operator
                        report_data.save()
                        updated_count += 1
                        self.stdout.write(f'更新記錄: {report_data.workorder_id} -> {onsite_report.operator}')
        
        self.stdout.write(
            self.style.SUCCESS(f'更新完成！共更新 {updated_count} 筆記錄')
        )
        
        # 顯示更新後的統計
        total_records = WorkOrderReportData.objects.count()
        records_with_operator = WorkOrderReportData.objects.filter(operator_name__isnull=False).count()
        
        self.stdout.write(f'總記錄數: {total_records}')
        self.stdout.write(f'有作業員姓名的記錄數: {records_with_operator}')
        self.stdout.write(f'缺少作業員姓名的記錄數: {total_records - records_with_operator}')
