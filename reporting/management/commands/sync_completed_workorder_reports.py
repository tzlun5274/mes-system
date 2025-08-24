"""
同步已完工工單報表資料的管理命令
"""

from django.core.management.base import BaseCommand
from reporting.services import CompletedWorkOrderReportService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '同步已完工工單資料到報表資料表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新同步所有資料',
        )

    def handle(self, *args, **options):
        self.stdout.write('開始同步已完工工單報表資料...')
        
        try:
            # 使用服務類別進行同步
            result = CompletedWorkOrderReportService.sync_completed_workorder_data()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(result['message'])
                )
                
                # 顯示詳細統計
                self.stdout.write(f"總工單數: {result['total_workorders']}")
                self.stdout.write(f"成功同步: {result['synced_count']}")
                self.stdout.write(f"錯誤數量: {result['error_count']}")
                
                if result['errors']:
                    self.stdout.write('錯誤詳情:')
                    for error in result['errors']:
                        self.stdout.write(
                            self.style.ERROR(f"  - 工單 {error['order_number']}: {error['error']}")
                        )
            else:
                self.stdout.write(
                    self.style.ERROR(f"同步失敗: {result['error']}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'同步過程中發生錯誤: {str(e)}')
            )
            logger.error(f'同步已完工工單報表資料失敗: {str(e)}')
