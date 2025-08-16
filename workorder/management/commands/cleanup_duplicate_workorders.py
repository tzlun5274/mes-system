"""
清理重複工單記錄管理命令
用於清理系統中重複建立的工單記錄
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder, CompletedWorkOrder
from workorder.fill_work.models import FillWork
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理重複的工單記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder',
            type=str,
            help='指定要清理的工單號碼'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅顯示會刪除的記錄，不實際刪除'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制刪除，不進行安全檢查'
        )

    def handle(self, *args, **options):
        workorder_number = options['workorder']
        dry_run = options['dry_run']
        force = options['force']

        if workorder_number:
            self.cleanup_single_workorder(workorder_number, dry_run, force)
        else:
            self.cleanup_all_duplicates(dry_run, force)

    def cleanup_single_workorder(self, workorder_number, dry_run, force):
        """清理指定工單號的重複記錄"""
        try:
            # 查找所有相同工單號的記錄
            workorders = WorkOrder.objects.filter(order_number=workorder_number).order_by('id')
            
            if workorders.count() <= 1:
                self.stdout.write(
                    self.style.WARNING(f'工單 {workorder_number} 沒有重複記錄')
                )
                return

            self.stdout.write(f'找到 {workorders.count()} 個工單記錄:')
            for wo in workorders:
                completed_record = CompletedWorkOrder.objects.filter(
                    original_workorder_id=wo.id
                ).first()
                self.stdout.write(
                    f'  ID: {wo.id}, 狀態: {wo.status}, '
                    f'建立時間: {wo.created_at}, '
                    f'已完工記錄: {"有" if completed_record else "無"}'
                )

            # 找出應該保留的工單（有已完工記錄的）
            completed_workorders = []
            pending_workorders = []
            
            for wo in workorders:
                if CompletedWorkOrder.objects.filter(original_workorder_id=wo.id).exists():
                    completed_workorders.append(wo)
                else:
                    pending_workorders.append(wo)

            if not completed_workorders:
                self.stdout.write(
                    self.style.WARNING(f'工單 {workorder_number} 沒有已完工記錄，無法確定哪個是正確的')
                )
                if not force:
                    return
                # 強制模式下，保留最新的記錄
                workorders_to_delete = workorders.exclude(id=workorders.last().id)
            else:
                # 保留有已完工記錄的工單，刪除其他重複記錄
                workorders_to_delete = pending_workorders

            if not workorders_to_delete:
                self.stdout.write(
                    self.style.SUCCESS(f'工單 {workorder_number} 沒有需要刪除的重複記錄')
                )
                return

            self.stdout.write(f'\n將要刪除的重複工單記錄:')
            for wo in workorders_to_delete:
                self.stdout.write(f'  ID: {wo.id}, 狀態: {wo.status}')

            if dry_run:
                self.stdout.write(
                    self.style.WARNING('這是乾跑模式，不會實際刪除記錄')
                )
                return

            # 實際刪除重複記錄
            with transaction.atomic():
                for wo in workorders_to_delete:
                    self.cleanup_workorder_data(wo)
                    wo.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'已刪除重複工單記錄 ID: {wo.id}')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'工單 {workorder_number} 重複記錄清理完成')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清理工單 {workorder_number} 時發生錯誤: {str(e)}')
            )

    def cleanup_all_duplicates(self, dry_run, force):
        """清理所有重複的工單記錄"""
        try:
            # 查找所有重複的工單號
            from django.db.models import Count
            duplicate_orders = WorkOrder.objects.values('order_number').annotate(
                count=Count('id')
            ).filter(count__gt=1)

            if not duplicate_orders:
                self.stdout.write(
                    self.style.SUCCESS('沒有發現重複的工單記錄')
                )
                return

            self.stdout.write(f'發現 {len(duplicate_orders)} 個重複的工單號:')
            for item in duplicate_orders:
                self.stdout.write(f'  {item["order_number"]} ({item["count"]} 筆記錄)')

            if dry_run:
                self.stdout.write(
                    self.style.WARNING('這是乾跑模式，不會實際刪除記錄')
                )
                return

            # 逐個清理重複工單
            for item in duplicate_orders:
                self.cleanup_single_workorder(item['order_number'], False, force)

            self.stdout.write(
                self.style.SUCCESS('所有重複工單記錄清理完成')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清理重複工單時發生錯誤: {str(e)}')
            )

    def cleanup_workorder_data(self, workorder):
        """清理工單相關的資料"""
        try:
            # 刪除工序記錄
            workorder.processes.all().delete()
            
            # 刪除生產記錄（如果存在）
            if hasattr(workorder, 'production_record') and workorder.production_record:
                # 先刪除生產記錄的明細資料
                workorder.production_record.production_details.all().delete()
                # 再刪除生產記錄本身
                workorder.production_record.delete()
            
            # 刪除填報記錄（FillWork）
            FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            ).delete()
            
            # 刪除工序日誌記錄
            from workorder.models import WorkOrderProcessLog
            WorkOrderProcessLog.objects.filter(
                workorder_process__workorder=workorder
            ).delete()
            
            # 刪除派工記錄
            from workorder.models import DispatchLog
            DispatchLog.objects.filter(
                workorder=workorder
            ).delete()
            
            # 刪除工單分配記錄
            from workorder.models import WorkOrderAssignment
            WorkOrderAssignment.objects.filter(
                workorder=workorder
            ).delete()
            
            # 刪除工序產能記錄
            from workorder.models import WorkOrderProcessCapacity
            WorkOrderProcessCapacity.objects.filter(
                workorder_process__workorder=workorder
            ).delete()
            
            # 刪除派工單相關記錄
            try:
                from workorder.workorder_dispatch.models import WorkOrderDispatch, WorkOrderDispatchProcess, DispatchHistory
                
                # 刪除派工單歷史記錄
                DispatchHistory.objects.filter(
                    workorder_dispatch__order_number=workorder.order_number
                ).delete()
                
                # 刪除派工單工序明細
                WorkOrderDispatchProcess.objects.filter(
                    workorder_dispatch__order_number=workorder.order_number
                ).delete()
                
                # 刪除派工單主表記錄
                WorkOrderDispatch.objects.filter(
                    order_number=workorder.order_number
                ).delete()
                
            except ImportError:
                logger.warning(f"無法導入派工單模組，跳過派工單記錄清理")
            except Exception as e:
                logger.warning(f"清理派工單記錄時發生錯誤: {str(e)}")
            
            logger.info(f"工單 {workorder.order_number} 相關資料已清理")
            
        except Exception as e:
            logger.error(f"清理工單 {workorder.order_number} 相關資料時發生錯誤: {str(e)}")
            raise 