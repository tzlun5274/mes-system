"""
更新派工單統計資料的管理命令
"""

from django.core.management.base import BaseCommand, CommandError
from workorder.workorder_dispatch.services import WorkOrderDispatchService


class Command(BaseCommand):
    help = '更新派工單統計資料'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dispatch-id',
            type=int,
            help='指定派工單ID進行更新',
        )
        parser.add_argument(
            '--order-number',
            type=str,
            help='根據工單號碼更新相關派工單',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='更新所有派工單',
        )

    def handle(self, *args, **options):
        """執行命令"""
        dispatch_id = options.get('dispatch_id')
        order_number = options.get('order_number')
        update_all = options.get('all')

        if dispatch_id:
            # 更新指定派工單
            self.stdout.write(f'正在更新派工單 ID {dispatch_id}...')
            result = WorkOrderDispatchService.update_dispatch_statistics(dispatch_id)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {result['message']}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ {result['message']}")
                )

        elif order_number:
            # 根據工單號碼更新
            self.stdout.write(f'正在更新工單 {order_number} 相關派工單...')
            result = WorkOrderDispatchService.update_dispatches_by_order_number(order_number)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {result['message']}")
                )
                self.stdout.write(f"   成功: {result['success_count']} 筆")
                self.stdout.write(f"   失敗: {result['error_count']} 筆")
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ {result['message']}")
                )

        elif update_all:
            # 更新所有派工單
            self.stdout.write('正在更新所有派工單...')
            result = WorkOrderDispatchService.update_all_dispatches_statistics()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {result['message']}")
                )
                self.stdout.write(f"   成功: {result['success_count']} 筆")
                self.stdout.write(f"   失敗: {result['error_count']} 筆")
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ {result['message']}")
                )

        else:
            # 顯示使用說明
            self.stdout.write(self.style.WARNING('請指定更新方式:'))
            self.stdout.write('  --dispatch-id <ID>    更新指定派工單')
            self.stdout.write('  --order-number <工單號碼>  更新指定工單的相關派工單')
            self.stdout.write('  --all                 更新所有派工單')
            raise CommandError('未指定更新方式') 