"""
清除工單狀態命令
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from workorder.workorder_reporting.models import BackupOperatorSupplementReport as OperatorSupplementReport, BackupSMTSupplementReport as SMTSupplementReport

# 移除主管報工相關程式碼，避免混淆
# 主管職責：監督、審核、管理，不代為報工

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '清除工單狀態相關記錄，但保留報工記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只顯示會刪除的記錄數量，不實際執行',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制執行，不需要確認',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        # 統計要刪除的記錄
        completed_workorders = CompletedWorkOrder.objects.count()
        in_progress_workorders = WorkOrder.objects.filter(status='in_progress').count()
        completed_processes = CompletedWorkOrderProcess.objects.count()
        completed_reports = CompletedProductionReport.objects.count()

        # 統計報工記錄數量
        operator_reports = OperatorSupplementReport.objects.count()
        smt_reports = SMTSupplementReport.objects.count()
        
        # 移除主管報工相關程式碼，避免混淆
        # 主管職責：監督、審核、管理，不代為報工
        
        self.stdout.write(f'報工記錄統計:')
        self.stdout.write(f'  - 作業員補登報工: {operator_reports} 筆')
        self.stdout.write(f'  - SMT報工: {smt_reports} 筆')

        self.stdout.write(self.style.WARNING(f'=== 要刪除的記錄 ==='))
        self.stdout.write(f'已完工工單: {completed_workorders} 個')
        self.stdout.write(f'生產中工單: {in_progress_workorders} 個')
        self.stdout.write(f'工序記錄: {completed_processes} 筆')
        self.stdout.write(f'完工報表: {completed_reports} 筆')
        self.stdout.write(f'總計要刪除: {completed_workorders + in_progress_workorders + completed_processes + completed_reports} 筆')

        self.stdout.write(self.style.SUCCESS(f'=== 要保留的記錄（報工記錄）==='))
        self.stdout.write(f'作業員報工記錄: {operator_reports} 筆')
        self.stdout.write(f'SMT報工記錄: {smt_reports} 筆')
        self.stdout.write(f'總計保留: {operator_reports + smt_reports} 筆')

        if dry_run:
            self.stdout.write(self.style.SUCCESS('乾跑模式完成，沒有實際刪除任何記錄'))
            return

        if not force:
            confirm = input('確定要刪除這些工單狀態記錄嗎？(輸入 "yes" 確認): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('操作已取消'))
                return

        try:
            with transaction.atomic():
                # 刪除已完工工單相關記錄
                deleted_completed = CompletedWorkOrder.objects.all().delete()
                self.stdout.write(f'已刪除已完工工單: {deleted_completed[0]} 個')

                # 刪除生產中工單（將狀態改回待生產）
                in_progress_workorders_list = list(WorkOrder.objects.filter(status='in_progress'))
                for workorder in in_progress_workorders_list:
                    workorder.status = 'pending'
                    workorder.save()
                self.stdout.write(f'已將 {len(in_progress_workorders_list)} 個生產中工單改回待生產狀態')

                # 刪除工序記錄
                deleted_processes = CompletedWorkOrderProcess.objects.all().delete()
                self.stdout.write(f'已刪除工序記錄: {deleted_processes[0]} 筆')

                # 刪除完工報表
                deleted_reports = CompletedProductionReport.objects.all().delete()
                self.stdout.write(f'已刪除完工報表: {deleted_reports[0]} 筆')

                self.stdout.write(self.style.SUCCESS('=== 清除完成 ==='))
                self.stdout.write(f'已完工工單: {deleted_completed[0]} 個')
                self.stdout.write(f'生產中工單: {len(in_progress_workorders_list)} 個 (已改回待生產)')
                self.stdout.write(f'工序記錄: {deleted_processes[0]} 筆')
                self.stdout.write(f'完工報表: {deleted_reports[0]} 筆')
                self.stdout.write(f'總計處理: {deleted_completed[0] + len(in_progress_workorders_list) + deleted_processes[0] + deleted_reports[0]} 筆')

                # 確認報工記錄被保留
                remaining_operator = OperatorSupplementReport.objects.count()
                remaining_smt = SMTSupplementReport.objects.count()
                
                self.stdout.write(self.style.SUCCESS('=== 確認報工記錄被保留 ==='))
                self.stdout.write(f'作業員報工記錄: {remaining_operator} 筆')
                self.stdout.write(f'SMT報工記錄: {remaining_smt} 筆')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'清除過程中發生錯誤: {str(e)}'))
            logger.error(f'清除工單狀態記錄時發生錯誤: {str(e)}')
            raise 