"""
重新計算工作時數管理命令
用於重新計算現有報工記錄的工作時數和加班時數
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from workorder.models import OperatorSupplementReport, SupervisorProductionReport


class Command(BaseCommand):
    help = '重新計算現有報工記錄的工作時數和加班時數'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date-from',
            type=str,
            help='開始日期 (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--date-to',
            type=str,
            help='結束日期 (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--worker',
            type=str,
            help='特定作業員姓名',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際更新資料庫',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('開始重新計算工作時數...')
        )

        # 解析日期範圍
        date_from = None
        date_to = None
        
        if options['date_from']:
            try:
                date_from = date.fromisoformat(options['date_from'])
            except ValueError:
                raise CommandError('日期格式錯誤，請使用 YYYY-MM-DD 格式')
        
        if options['date_to']:
            try:
                date_to = date.fromisoformat(options['date_to'])
            except ValueError:
                raise CommandError('日期格式錯誤，請使用 YYYY-MM-DD 格式')

        # 如果沒有指定日期範圍，預設為最近30天
        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today()

        # 查詢作業員報工記錄
        operator_reports = OperatorSupplementReport.objects.filter(
            work_date__range=[date_from, date_to]
        )
        
        if options['worker']:
            operator_reports = operator_reports.filter(
                operator__name__icontains=options['worker']
            )

        # 查詢主管報工記錄
        supervisor_reports = SupervisorProductionReport.objects.filter(
            work_date__range=[date_from, date_to]
        )

        total_reports = operator_reports.count() + supervisor_reports.count()
        
        if total_reports == 0:
            self.stdout.write(
                self.style.WARNING('在指定日期範圍內沒有找到報工記錄')
            )
            return

        self.stdout.write(f'找到 {total_reports} 筆報工記錄需要重新計算')
        self.stdout.write(f'日期範圍: {date_from} 到 {date_to}')
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('試運行模式，不會實際更新資料庫')
            )

        updated_count = 0
        error_count = 0

        # 處理作業員報工記錄
        for report in operator_reports:
            try:
                if not options['dry_run']:
                    with transaction.atomic():
                        report.calculate_work_hours()
                        report.save()
                updated_count += 1
                
                if updated_count % 100 == 0:
                    self.stdout.write(f'已處理 {updated_count} 筆記錄...')
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'處理記錄 {report.id} 時發生錯誤: {e}')
                )

        # 處理主管報工記錄
        for report in supervisor_reports:
            try:
                if not options['dry_run']:
                    with transaction.atomic():
                        report.calculate_work_hours()
                        report.save()
                updated_count += 1
                
                if updated_count % 100 == 0:
                    self.stdout.write(f'已處理 {updated_count} 筆記錄...')
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'處理記錄 {report.id} 時發生錯誤: {e}')
                )

        # 輸出結果
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f'試運行完成！共處理 {updated_count} 筆記錄')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'重新計算完成！成功更新 {updated_count} 筆記錄，'
                    f'錯誤 {error_count} 筆'
                )
            )

        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'有 {error_count} 筆記錄處理失敗，請檢查錯誤訊息')
            ) 