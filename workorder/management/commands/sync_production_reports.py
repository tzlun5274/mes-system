"""
同步生產報工記錄管理命令
將所有已核准的報工記錄同步到生產中工單詳情資料表
"""

from django.core.management.base import BaseCommand
from workorder.services import ProductionReportSyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '同步所有已核准的報工記錄到生產中工單詳情資料表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=int,
            help='指定同步特定工單的報工記錄',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新同步所有記錄',
        )

    def handle(self, *args, **options):
        workorder_id = options.get('workorder_id')
        force = options.get('force')
        
        self.stdout.write(
            self.style.SUCCESS('開始同步生產報工記錄...')
        )
        
        try:
            if workorder_id:
                # 同步特定工單
                self.stdout.write(f'同步工單 {workorder_id} 的報工記錄...')
                success = ProductionReportSyncService.sync_specific_workorder(workorder_id)
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f'工單 {workorder_id} 的報工記錄同步完成')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'工單 {workorder_id} 的報工記錄同步失敗')
                    )
            else:
                # 同步所有工單
                self.stdout.write('同步所有已核准的報工記錄...')
                success = ProductionReportSyncService.sync_all_approved_reports()
                if success:
                    self.stdout.write(
                        self.style.SUCCESS('所有已核准報工記錄同步完成')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('同步報工記錄失敗')
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'同步過程中發生錯誤: {str(e)}')
            )
            import traceback
            error_traceback = traceback.format_exc()
            self.stdout.write(
                self.style.ERROR(f'詳細錯誤信息:\n{error_traceback}')
            )
            logger.error(f"同步報工記錄命令執行失敗: {str(e)}")
            logger.error(f"詳細錯誤信息: {error_traceback}")
            # 強制輸出錯誤信息
            print(f"錯誤詳情: {error_traceback}") 