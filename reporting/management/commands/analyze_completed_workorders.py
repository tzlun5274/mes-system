"""
Django 管理命令：分析已完工工單
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, timedelta
from reporting.workorder_analysis_service import WorkOrderAnalysisService


class Command(BaseCommand):
    help = '分析已完工工單，生成詳細的分析資料'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=str,
            help='指定工單編號進行分析'
        )
        parser.add_argument(
            '--company-code',
            type=str,
            help='指定公司代號'
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
            '--days',
            type=int,
            default=7,
            help='分析最近幾天的工單 (預設: 7天)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際執行分析'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新分析，即使已經分析過'
        )
    
    def handle(self, *args, **options):
        workorder_id = options.get('workorder_id')
        company_code = options.get('company_code')
        start_date = options.get('start_date')
        end_date = options.get('end_date')
        days = options.get('days')
        dry_run = options.get('dry_run')
        force = options.get('force')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 不會實際執行分析')
            )
        
        # 單一工單分析
        if workorder_id:
            if not company_code:
                raise CommandError('分析單一工單時必須指定公司代號')
            
            self.stdout.write(f'開始分析工單: {workorder_id}')
            
            if not dry_run:
                result = WorkOrderAnalysisService.analyze_completed_workorder(
                    workorder_id, company_code, force=force
                )
                
                if result['success']:
                    self.stdout.write(
                        self.style.SUCCESS(f'工單分析完成: {result["message"]}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'工單分析失敗: {result["error"]}')
                    )
            else:
                self.stdout.write(f'試運行: 將分析工單 {workorder_id}')
        
        # 批量分析
        else:
            # 設定日期範圍
            if not start_date and not end_date:
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=days)
            elif start_date and not end_date:
                end_date = timezone.now().date()
            elif not start_date and end_date:
                start_date = end_date - timedelta(days=days)
            
            self.stdout.write(
                f'開始批量分析工單 (日期範圍: {start_date} 到 {end_date})'
            )
            
            if company_code:
                self.stdout.write(f'公司代號: {company_code}')
            
            if not dry_run:
                result = WorkOrderAnalysisService.analyze_completed_workorders_batch(
                    start_date=start_date,
                    end_date=end_date,
                    company_code=company_code
                )
                
                if result['success']:
                    self.stdout.write(
                        self.style.SUCCESS(f'批量分析完成: {result["message"]}')
                    )
                    
                    if result.get('errors'):
                        self.stdout.write(
                            self.style.WARNING('分析過程中的錯誤:')
                        )
                        for error in result['errors'][:10]:  # 只顯示前10個錯誤
                            self.stdout.write(f'  - {error}')
                        
                        if len(result['errors']) > 10:
                            self.stdout.write(f'  ... 還有 {len(result["errors"]) - 10} 個錯誤')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'批量分析失敗: {result["error"]}')
                    )
            else:
                self.stdout.write(
                    f'試運行: 將分析 {start_date} 到 {end_date} 期間的工單'
                )
        
        self.stdout.write(
            self.style.SUCCESS('分析任務執行完成')
        )
