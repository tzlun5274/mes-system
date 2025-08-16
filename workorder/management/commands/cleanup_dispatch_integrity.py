"""
清理派工單完整性管理命令
用於清理派工單和工單之間的不一致問題
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理派工單和工單之間的不一致問題'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='僅檢查問題，不進行修復'
        )
        parser.add_argument(
            '--fix-orphaned-dispatches',
            action='store_true',
            help='修復孤立的派工單記錄'
        )
        parser.add_argument(
            '--fix-completed-workorder-dispatches',
            action='store_true',
            help='修復已完工工單的派工單記錄'
        )
        parser.add_argument(
            '--sync-dispatch-status',
            action='store_true',
            help='同步派工單狀態與工單狀態'
        )

    def handle(self, *args, **options):
        check_only = options['check_only']
        fix_orphaned = options['fix_orphaned_dispatches']
        fix_completed = options['fix_completed_workorder_dispatches']
        sync_status = options['sync_dispatch_status']

        if check_only:
            self.check_integrity_issues()
        elif fix_orphaned:
            self.fix_orphaned_dispatches()
        elif fix_completed:
            self.fix_completed_workorder_dispatches()
        elif sync_status:
            self.sync_dispatch_status()
        else:
            # 預設執行完整檢查
            self.check_integrity_issues()

    def check_integrity_issues(self):
        """檢查完整性問題"""
        self.stdout.write(self.style.SUCCESS('=== 開始檢查派工單完整性 ==='))
        
        # 1. 檢查孤立的派工單記錄
        self.check_orphaned_dispatches()
        
        # 2. 檢查已完工工單的派工單記錄
        self.check_completed_workorder_dispatches()
        
        # 3. 檢查派工單狀態與工單狀態的不一致
        self.check_dispatch_status_inconsistency()
        
        self.stdout.write(self.style.SUCCESS('=== 檢查完成 ==='))

    def check_orphaned_dispatches(self):
        """檢查孤立的派工單記錄"""
        self.stdout.write('\n--- 檢查孤立的派工單記錄 ---')
        
        # 檢查沒有對應工單的派工單記錄
        orphaned_dispatches = WorkOrderDispatch.objects.exclude(
            order_number__in=WorkOrder.objects.values_list('order_number', flat=True)
        )
        
        if orphaned_dispatches.exists():
            self.stdout.write(
                self.style.WARNING(f'發現 {orphaned_dispatches.count()} 筆孤立的派工單記錄')
            )
            for dispatch in orphaned_dispatches[:10]:  # 只顯示前10筆
                self.stdout.write(f'  工單號: {dispatch.order_number}, 產品: {dispatch.product_code}')
        else:
            self.stdout.write(self.style.SUCCESS('沒有發現孤立的派工單記錄'))

    def check_completed_workorder_dispatches(self):
        """檢查已完工工單的派工單記錄"""
        self.stdout.write('\n--- 檢查已完工工單的派工單記錄 ---')
        
        # 檢查已完工工單的派工單記錄
        completed_workorders = WorkOrder.objects.filter(status='completed')
        completed_dispatches = WorkOrderDispatch.objects.filter(
            order_number__in=completed_workorders.values_list('order_number', flat=True)
        )
        
        if completed_dispatches.exists():
            self.stdout.write(
                self.style.WARNING(f'發現 {completed_dispatches.count()} 筆已完工工單的派工單記錄')
            )
            for dispatch in completed_dispatches[:10]:  # 只顯示前10筆
                self.stdout.write(f'  工單號: {dispatch.order_number}, 派工單狀態: {dispatch.status}')
        else:
            self.stdout.write(self.style.SUCCESS('沒有發現已完工工單的派工單記錄'))

    def check_dispatch_status_inconsistency(self):
        """檢查派工單狀態與工單狀態的不一致"""
        self.stdout.write('\n--- 檢查派工單狀態與工單狀態的不一致 ---')
        
        # 檢查派工單狀態為 'pending' 但工單狀態不是 'pending' 的記錄
        pending_dispatches = WorkOrderDispatch.objects.filter(status='pending')
        inconsistent_count = 0
        
        for dispatch in pending_dispatches:
            # 使用公司代號和工單號碼組合查詢，確保唯一性
            workorder = WorkOrder.objects.filter(order_number=dispatch.order_number).first()
            # 注意：這裡需要從派工單中獲取公司代號，暫時保持原有邏輯
            if workorder and workorder.status != 'pending':
                inconsistent_count += 1
                if inconsistent_count <= 10:  # 只顯示前10筆
                    self.stdout.write(
                        f'  工單號: {dispatch.order_number}, '
                        f'派工單狀態: {dispatch.status}, '
                        f'工單狀態: {workorder.status}'
                    )
        
        if inconsistent_count > 0:
            self.stdout.write(
                self.style.WARNING(f'發現 {inconsistent_count} 筆狀態不一致的記錄')
            )
        else:
            self.stdout.write(self.style.SUCCESS('沒有發現狀態不一致的記錄'))

    def fix_orphaned_dispatches(self):
        """修復孤立的派工單記錄"""
        self.stdout.write(self.style.SUCCESS('=== 開始修復孤立的派工單記錄 ==='))
        
        orphaned_dispatches = WorkOrderDispatch.objects.exclude(
            order_number__in=WorkOrder.objects.values_list('order_number', flat=True)
        )
        
        if not orphaned_dispatches.exists():
            self.stdout.write(self.style.SUCCESS('沒有孤立的派工單記錄需要修復'))
            return
        
        self.stdout.write(f'發現 {orphaned_dispatches.count()} 筆孤立的派工單記錄')
        
        # 刪除孤立的派工單記錄
        with transaction.atomic():
            deleted_count = orphaned_dispatches.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f'已刪除 {deleted_count} 筆孤立的派工單記錄')
            )

    def fix_completed_workorder_dispatches(self):
        """修復已完工工單的派工單記錄"""
        self.stdout.write(self.style.SUCCESS('=== 開始修復已完工工單的派工單記錄 ==='))
        
        completed_workorders = WorkOrder.objects.filter(status='completed')
        completed_dispatches = WorkOrderDispatch.objects.filter(
            order_number__in=completed_workorders.values_list('order_number', flat=True)
        )
        
        if not completed_dispatches.exists():
            self.stdout.write(self.style.SUCCESS('沒有已完工工單的派工單記錄需要修復'))
            return
        
        self.stdout.write(f'發現 {completed_dispatches.count()} 筆已完工工單的派工單記錄')
        
        # 刪除已完工工單的派工單記錄
        with transaction.atomic():
            deleted_count = completed_dispatches.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f'已刪除 {deleted_count} 筆已完工工單的派工單記錄')
            )

    def sync_dispatch_status(self):
        """同步派工單狀態與工單狀態"""
        self.stdout.write(self.style.SUCCESS('=== 開始同步派工單狀態與工單狀態 ==='))
        
        # 更新派工單狀態以反映工單狀態
        updated_count = 0
        
        with transaction.atomic():
            for dispatch in WorkOrderDispatch.objects.all():
                # 使用公司代號和工單號碼組合查詢，確保唯一性
                workorder = WorkOrder.objects.filter(order_number=dispatch.order_number).first()
                # 注意：這裡需要從派工單中獲取公司代號，暫時保持原有邏輯
                if workorder:
                    # 根據工單狀態更新派工單狀態
                    if workorder.status == 'completed':
                        if dispatch.status != 'completed':
                            dispatch.status = 'completed'
                            dispatch.save()
                            updated_count += 1
                    elif workorder.status == 'in_progress':
                        if dispatch.status == 'pending':
                            dispatch.status = 'in_production'
                            dispatch.save()
                            updated_count += 1
                    elif workorder.status == 'pending':
                        if dispatch.status not in ['pending', 'dispatched']:
                            dispatch.status = 'pending'
                            dispatch.save()
                            updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'已同步 {updated_count} 筆派工單狀態')
        ) 