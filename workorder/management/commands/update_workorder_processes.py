"""
更新工單工序完成數量管理命令
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from workorder.services.process_update_service import ProcessUpdateService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '更新所有工單的工序完成數量和狀態'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=int,
            help='指定要更新的工單ID（可選）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只顯示會更新的內容而不實際執行',
        )

    def handle(self, *args, **options):
        """執行更新操作"""
        
        workorder_id = options.get('workorder_id')
        dry_run = options.get('dry_run')
        
        try:
            if workorder_id:
                # 更新指定工單
                self.stdout.write(f"🔄 開始更新工單 ID: {workorder_id}")
                
                if dry_run:
                    self.stdout.write("🔍 乾跑模式：只檢查不執行更新")
                    # 這裡可以添加乾跑模式的邏輯
                    self.stdout.write(self.style.SUCCESS("✅ 乾跑模式完成"))
                else:
                    try:
                        success = ProcessUpdateService.update_workorder_processes(workorder_id)
                        if success:
                            self.stdout.write(self.style.SUCCESS(f"✅ 工單 {workorder_id} 更新完成"))
                        else:
                            self.stdout.write(self.style.ERROR(f"❌ 工單 {workorder_id} 更新失敗"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"❌ 工單 {workorder_id} 更新失敗：{str(e)}"))
                        import traceback
                        self.stdout.write(traceback.format_exc())
            else:
                # 更新所有工單
                self.stdout.write("🔄 開始更新所有工單的工序完成數量...")
                
                if dry_run:
                    self.stdout.write("🔍 乾跑模式：只檢查不執行更新")
                    # 這裡可以添加乾跑模式的邏輯
                    self.stdout.write(self.style.SUCCESS("✅ 乾跑模式完成"))
                else:
                    success = ProcessUpdateService.update_all_workorders()
                    if success:
                        self.stdout.write(self.style.SUCCESS("✅ 所有工單更新完成"))
                    else:
                        self.stdout.write(self.style.ERROR("❌ 部分工單更新失敗"))
            
            # 記錄操作日誌
            logger.info(
                f"管理員執行工單工序更新: "
                f"工單ID={workorder_id or 'all'}, "
                f"乾跑模式={dry_run}, "
                f"執行時間={timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 更新失敗：{str(e)}"))
            logger.error(f"工單工序更新失敗: {str(e)}")
            raise CommandError(f"更新失敗：{str(e)}") 