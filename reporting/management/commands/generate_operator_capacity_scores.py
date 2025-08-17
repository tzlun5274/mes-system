"""
從現有報工資料生成作業員工序產能評分的管理命令
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import datetime, timedelta
from reporting.services import OperatorCapacityService


class Command(BaseCommand):
    help = '從現有報工資料生成作業員工序產能評分'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=str,
            help='公司代號，不指定則處理所有公司'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='開始日期 (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='結束日期 (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新計算，覆蓋現有資料'
        )

    def handle(self, *args, **options):
        company_code = options.get('company')
        start_date_str = options.get('start_date')
        end_date_str = options.get('end_date')
        force = options.get('force')
        
        # 設定日期範圍
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            # 預設處理最近30天
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
        
        self.stdout.write(f'開始生成作業員工序產能評分...')
        self.stdout.write(f'日期範圍: {start_date} 至 {end_date}')
        
        # 取得公司列表
        if company_code:
            companies = [company_code]
        else:
            from erp_integration.models import CompanyConfig
            companies = list(CompanyConfig.objects.values_list('company_code', flat=True))
        
        total_processed = 0
        total_created = 0
        
        for company in companies:
            self.stdout.write(f'處理公司: {company}')
            
            try:
                # 從填報資料生成評分
                created_count = self.process_fill_work_data(company, start_date, end_date, force)
                total_created += created_count
                
                # 從現場報工資料生成評分
                created_count = self.process_onsite_report_data(company, start_date, end_date, force)
                total_created += created_count
                
                total_processed += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'處理公司 {company} 時發生錯誤: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'完成！處理了 {total_processed} 家公司，'
                f'生成了 {total_created} 筆作業員工序產能評分記錄'
            )
        )
    
    def process_fill_work_data(self, company_code, start_date, end_date, force=False):
        """處理填報資料"""
        from workorder.fill_work.models import FillWork
        
        fill_works = FillWork.objects.filter(
            company_name=company_code,
            work_date__range=[start_date, end_date]
        )
        
        created_count = 0
        
        for fill_work in fill_works:
            try:
                # 檢查是否已存在評分記錄
                if not force:
                    from reporting.models import OperatorProcessCapacityScore
                    existing = OperatorProcessCapacityScore.objects.filter(
                        operator_id=fill_work.operator_id,
                        workorder_id=fill_work.workorder,
                        process_name=fill_work.process_name,
                        work_date=fill_work.work_date
                    ).exists()
                    
                    if existing:
                        continue
                
                # 生成評分
                score_record = OperatorCapacityService.calculate_operator_process_score(
                    operator_id=fill_work.operator_id,
                    workorder_id=fill_work.workorder,
                    process_name=fill_work.process_name,
                    work_date=fill_work.work_date,
                    completed_quantity=fill_work.completed_quantity or 0,
                    work_hours=fill_work.work_hours_calculated or 0,
                    defect_quantity=fill_work.defect_quantity or 0
                )
                
                if score_record:
                    created_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'處理填報資料失敗 (工單: {fill_work.workorder}, '
                        f'作業員: {fill_work.operator_id}): {str(e)}'
                    )
                )
        
        self.stdout.write(f'  填報資料: 生成了 {created_count} 筆評分記錄')
        return created_count
    
    def process_onsite_report_data(self, company_code, start_date, end_date, force=False):
        """處理現場報工資料"""
        from onsite_reporting.models import OnsiteReport
        
        onsite_reports = OnsiteReport.objects.filter(
            company_code=company_code,
            start_datetime__date__range=[start_date, end_date],
            status='completed'
        )
        
        created_count = 0
        
        for report in onsite_reports:
            try:
                # 檢查是否已存在評分記錄
                if not force:
                    from reporting.models import OperatorProcessCapacityScore
                    existing = OperatorProcessCapacityScore.objects.filter(
                        operator_id=report.operator_id,
                        workorder_id=report.order_number,
                        process_name=report.process_name,
                        work_date=report.start_datetime.date()
                    ).exists()
                    
                    if existing:
                        continue
                
                # 計算工作時數（分鐘轉小時）
                work_hours = report.work_minutes / 60 if report.work_minutes else 0
                
                # 生成評分
                score_record = OperatorCapacityService.calculate_operator_process_score(
                    operator_id=report.operator_id,
                    workorder_id=report.order_number,
                    process_name=report.process_name,
                    work_date=report.start_datetime.date(),
                    completed_quantity=report.completed_quantity or 0,
                    work_hours=work_hours,
                    defect_quantity=report.defect_quantity or 0
                )
                
                if score_record:
                    created_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'處理現場報工資料失敗 (工單: {report.order_number}, '
                        f'作業員: {report.operator_id}): {str(e)}'
                    )
                )
        
        self.stdout.write(f'  現場報工資料: 生成了 {created_count} 筆評分記錄')
        return created_count 