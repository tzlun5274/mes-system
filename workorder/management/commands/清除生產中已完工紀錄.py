"""
強制清除生產中工單資料表和已完工工單資料表的所有記錄
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from workorder.models import WorkOrderProduction, CompletedWorkOrder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '強制清除生產中工單資料表和已完工工單資料表的所有記錄'

    def handle(self, *args, **options):
        """執行強制清除操作"""

        try:
            # 統計要清除的資料
            all_productions = WorkOrderProduction.objects.all()
            all_productions_count = all_productions.count()
            
            all_completed_workorders = CompletedWorkOrder.objects.all()
            all_completed_workorders_count = all_completed_workorders.count()
            
            total_count = all_productions_count + all_completed_workorders_count
            
            if total_count == 0:
                self.stdout.write(self.style.SUCCESS("✅ 目前沒有任何記錄需要清除"))
                return

            # 顯示要清除的資料統計
            self.stdout.write(
                self.style.SUCCESS(f"📊 找到 {total_count} 筆記錄：")
            )
            self.stdout.write(f"  • WorkOrderProduction（生產中工單資料表）：{all_productions_count} 筆")
            self.stdout.write(f"  • CompletedWorkOrder（已完工工單資料表）：{all_completed_workorders_count} 筆")

            # 執行強制刪除
            self.stdout.write("\n🗑️  開始強制清除所有記錄...")
            
            # 強制刪除生產中工單資料表中的所有記錄
            if all_productions_count > 0:
                self.stdout.write("📝 強制清除 WorkOrderProduction（生產中工單資料表）中的所有記錄...")
                all_productions.delete()
                self.stdout.write(f"✅ 已強制清除 {all_productions_count} 筆生產中工單記錄")
            
            # 強制刪除已完工工單資料表中的所有記錄
            if all_completed_workorders_count > 0:
                self.stdout.write("📝 強制清除 CompletedWorkOrder（已完工工單資料表）中的所有記錄...")
                all_completed_workorders.delete()
                self.stdout.write(f"✅ 已強制清除 {all_completed_workorders_count} 筆已完工工單記錄")

            # 記錄操作日誌
            logger.info(
                f"管理員強制清除所有記錄: 生產中工單 {all_productions_count} 筆, 已完工工單 {all_completed_workorders_count} 筆"
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n🎉 成功強制清除所有記錄！\n"
                    f"📊 WorkOrderProduction（生產中工單資料表）：{all_productions_count} 筆\n"
                    f"📊 CompletedWorkOrder（已完工工單資料表）：{all_completed_workorders_count} 筆\n"
                    f"📊 總計清除：{total_count} 筆記錄\n"
                    f'⏰ 清除時間：{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
                )
            )

            # 顯示清除後的狀態
            remaining_productions = WorkOrderProduction.objects.count()
            remaining_completed = CompletedWorkOrder.objects.count()
            
            self.stdout.write(f"\n📊 清除後剩餘記錄：")
            self.stdout.write(f"  • WorkOrderProduction（生產中工單資料表）：{remaining_productions} 筆")
            self.stdout.write(f"  • CompletedWorkOrder（已完工工單資料表）：{remaining_completed} 筆")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ 強制清除失敗：{str(e)}"))
            logger.error(f"強制清除所有記錄失敗: {str(e)}")
            raise CommandError(f"強制清除失敗：{str(e)}") 