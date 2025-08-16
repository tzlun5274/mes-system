"""
更新工單狀態管理命令
將有生產活動但狀態仍為待生產的工單更新為生產中
"""

from django.core.management.base import BaseCommand
from workorder.services.workorder_status_service import WorkOrderStatusService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '更新工單狀態 - 將有生產活動的待生產工單更新為生產中'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=int,
            help='指定工單ID進行狀態更新'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只檢查不執行實際更新'
        )

    def handle(self, *args, **options):
        workorder_id = options.get('workorder_id')
        dry_run = options.get('dry_run')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== 乾跑模式 ==='))
        
        if workorder_id:
            self._update_single_workorder(workorder_id, dry_run)
        else:
            self._update_all_pending_workorders(dry_run)

    def _update_single_workorder(self, workorder_id, dry_run):
        """更新單一工單狀態"""
        try:
            from workorder.models import WorkOrder
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            self.stdout.write(f"檢查工單：{workorder.order_number}")
            
            # 取得狀態摘要
            summary = WorkOrderStatusService.get_workorder_status_summary(workorder_id)
            
            if 'error' in summary:
                self.stdout.write(
                    self.style.ERROR(f"取得工單狀態摘要失敗：{summary['error']}")
                )
                return
            
            self.stdout.write(f"當前狀態：{summary['current_status']}")
            self.stdout.write(f"工序記錄數：{summary['process_records_count']}")
            self.stdout.write(f"已核准填報數：{summary['approved_reports_count']}")
            self.stdout.write(f"有生產記錄：{summary['has_production_record']}")
            self.stdout.write(f"應該為生產中：{summary['should_be_in_progress']}")
            
            if summary['should_be_in_progress'] and summary['current_status'] == 'pending':
                if not dry_run:
                    updated = WorkOrderStatusService.update_workorder_status(workorder_id)
                    if updated:
                        self.stdout.write(
                            self.style.SUCCESS(f"工單 {workorder.order_number} 狀態更新成功：pending → in_progress")
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f"工單 {workorder.order_number} 狀態更新失敗")
                        )
                else:
                    self.stdout.write(f"乾跑模式：工單 {workorder.order_number} 將從 pending 更新為 in_progress")
            else:
                self.stdout.write(
                    self.style.WARNING(f"工單 {workorder.order_number} 不需要更新狀態")
                )
                    
        except WorkOrder.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"工單 ID {workorder_id} 不存在")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"更新工單 {workorder_id} 狀態失敗：{str(e)}")
            )

    def _update_all_pending_workorders(self, dry_run):
        """更新所有待生產工單的狀態"""
        self.stdout.write("開始更新所有待生產工單狀態...")
        
        if dry_run:
            # 乾跑模式：只檢查不更新
            from workorder.models import WorkOrder
            pending_workorders = WorkOrder.objects.filter(status='pending')
            
            self.stdout.write(f"找到 {pending_workorders.count()} 個待生產工單")
            
            should_update_count = 0
            for workorder in pending_workorders:
                summary = WorkOrderStatusService.get_workorder_status_summary(workorder.id)
                if 'error' not in summary and summary['should_be_in_progress']:
                    should_update_count += 1
                    self.stdout.write(f"  - {workorder.order_number}: 有生產活動，應更新為生產中")
            
            self.stdout.write(f"乾跑模式：{should_update_count} 個工單需要更新狀態")
            
        else:
            # 實際執行更新
            result = WorkOrderStatusService.update_all_pending_workorders()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f"批量更新完成：檢查 {result['total_count']} 個工單，更新 {result['updated_count']} 個為生產中")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"批量更新失敗：{result.get('error', '未知錯誤')}")
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("注意：此為乾跑模式，未進行實際更新")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("工單狀態更新完成！")
            ) 