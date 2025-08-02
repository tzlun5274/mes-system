"""
清理已完工工單管理命令
清理已經轉移到 CompletedWorkOrder 表的生產中工單記錄
"""

from django.core.management.base import BaseCommand
from workorder.models import WorkOrder, CompletedWorkOrder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理已經轉移到 CompletedWorkOrder 表的生產中工單記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只顯示會清理的工單，不實際執行清理',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制清理，即使工單沒有對應的已完工記錄',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        # 獲取所有已完工的工單
        completed_workorders = WorkOrder.objects.filter(status='completed')
        total_count = completed_workorders.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('沒有找到需要清理的已完工工單')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'找到 {total_count} 個需要清理的已完工工單')
        )
        
        # 檢查哪些工單已經轉移到 CompletedWorkOrder 表
        transferred_workorder_numbers = set(
            CompletedWorkOrder.objects.values_list('order_number', flat=True)
        )
        
        # 分類工單
        safe_to_delete = []
        already_transferred = []
        not_transferred = []
        
        for workorder in completed_workorders:
            if workorder.order_number in transferred_workorder_numbers:
                safe_to_delete.append(workorder)
                already_transferred.append(workorder)
            else:
                not_transferred.append(workorder)
        
        self.stdout.write(f'已轉移的工單: {len(already_transferred)} 個')
        self.stdout.write(f'未轉移的工單: {len(not_transferred)} 個')
        
        if dry_run:
            self.stdout.write('=== 乾跑模式 ===')
            if already_transferred:
                self.stdout.write('會清理的已轉移工單:')
                for workorder in already_transferred[:10]:
                    self.stdout.write(f'  {workorder.order_number} - {workorder.product_code}')
                if len(already_transferred) > 10:
                    self.stdout.write(f'  ... 還有 {len(already_transferred) - 10} 個')
            
            if not_transferred and not force:
                self.stdout.write('未轉移的工單（需要 --force 參數才能清理）:')
                for workorder in not_transferred[:10]:
                    self.stdout.write(f'  {workorder.order_number} - {workorder.product_code}')
                if len(not_transferred) > 10:
                    self.stdout.write(f'  ... 還有 {len(not_transferred) - 10} 個')
            return
        
        # 決定要清理的工單
        to_delete = []
        if already_transferred:
            to_delete.extend(already_transferred)
        
        if not_transferred and force:
            to_delete.extend(not_transferred)
            self.stdout.write(
                self.style.WARNING(f'強制清理 {len(not_transferred)} 個未轉移的工單')
            )
        
        if not to_delete:
            self.stdout.write(
                self.style.WARNING('沒有工單需要清理')
            )
            return
        
        # 執行清理
        success_count = 0
        error_count = 0
        
        for workorder in to_delete:
            try:
                workorder_number = workorder.order_number
                workorder.delete()
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'成功清理: {workorder_number}')
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'清理失敗 {workorder.order_number}: {str(e)}')
                )
                logger.error(f'清理工單 {workorder.order_number} 失敗: {str(e)}')
        
        # 顯示結果
        self.stdout.write('=== 清理完成 ===')
        self.stdout.write(
            self.style.SUCCESS(f'成功清理: {success_count} 個工單')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'清理失敗: {error_count} 個工單')
            )
        
        # 檢查最終結果
        remaining_completed = WorkOrder.objects.filter(status='completed').count()
        transferred_count = CompletedWorkOrder.objects.count()
        
        self.stdout.write(f'剩餘已完工工單: {remaining_completed}')
        self.stdout.write(f'已轉移工單總數: {transferred_count}') 