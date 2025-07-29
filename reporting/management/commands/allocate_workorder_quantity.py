# -*- coding: utf-8 -*-
"""
工單數量分擔管理命令
在工單完工後，將工單的明細數量分擔，並將分擔後的資料回寫到作業員的資料表

使用方法:
python manage.py allocate_workorder_quantity 123
python manage.py allocate_workorder_quantity 123 --force
"""

from django.core.management.base import BaseCommand, CommandError
from reporting.services.sync_service import ReportDataSyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "工單完工後的數量分擔處理"

    def add_arguments(self, parser):
        parser.add_argument(
            'workorder_id',
            type=int,
            help='工單ID'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制執行：即使工單未完工也執行分擔'
        )

    def handle(self, *args, **options):
        workorder_id = options['workorder_id']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(f"開始執行工單數量分擔 - 工單ID: {workorder_id}")
        )

        try:
            # 初始化同步服務
            sync_service = ReportDataSyncService()

            # 執行數量分擔
            result = sync_service.sync_workorder_allocation(workorder_id)

            if result['status'] == 'success':
                self.stdout.write(
                    self.style.SUCCESS(
                        f"數量分擔完成！\n"
                        f"工單總完成數量: {result['total_completed']}\n"
                        f"分擔記錄數: {len(result['allocation_results'])}"
                    )
                )

                # 顯示分擔詳情
                for allocation in result['allocation_results']:
                    self.stdout.write(
                        f"  - {allocation['report_type']} (ID: {allocation['report_id']}): "
                        f"分配數量 {allocation['allocated_quantity']} "
                        f"(佔比: {allocation['allocation_ratio']:.2%})"
                    )

            else:
                self.stdout.write(
                    self.style.ERROR(f"數量分擔失敗: {result['message']}")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"數量分擔失敗: {str(e)}")
            )
            logger.error(f"工單數量分擔失敗: {str(e)}")
            raise CommandError(f"數量分擔失敗: {str(e)}") 