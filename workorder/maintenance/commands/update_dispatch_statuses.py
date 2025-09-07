"""
更新派工單狀態管理命令
根據工序分配情況自動更新派工單狀態
"""

from django.core.management.base import BaseCommand
from workorder.services.dispatch_status_service import DispatchStatusService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "根據工序分配情況更新派工單狀態"

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=int,
            help='指定工單ID進行更新'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='更新所有派工單狀態'
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write("=== 開始更新派工單狀態 ===")
            
            if options['workorder_id']:
                # 更新指定工單的派工單狀態
                workorder_id = options['workorder_id']
                success = DispatchStatusService.update_dispatch_status_by_process_allocation(workorder_id)
                
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f"工單 {workorder_id} 的派工單狀態更新成功")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"工單 {workorder_id} 的派工單狀態更新失敗")
                    )
            
            elif options['all']:
                # 更新所有派工單狀態
                updated_count = DispatchStatusService.update_all_dispatch_statuses()
                
                self.stdout.write(
                    self.style.SUCCESS(f"共更新 {updated_count} 筆派工單狀態")
                )
            
            else:
                # 預設更新所有派工單狀態
                updated_count = DispatchStatusService.update_all_dispatch_statuses()
                
                self.stdout.write(
                    self.style.SUCCESS(f"共更新 {updated_count} 筆派工單狀態")
                )
            
            self.stdout.write("=== 派工單狀態更新完成 ===")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"更新派工單狀態失敗：{str(e)}")
            ) 