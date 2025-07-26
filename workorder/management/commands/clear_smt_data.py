"""
清除 SMT 現場報工即時模式資料的管理命令
用於清除所有 SMT 報工記錄和相關資料
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import date, timedelta
from workorder.models import SMTProductionReport
from equip.models import Equipment
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "清除 SMT 現場報工即時模式的所有資料"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="清除所有 SMT 報工記錄（不限制日期）",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="清除最近幾天的資料（預設：7天）",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="確認清除操作（避免誤刪）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="預覽要清除的資料，但不實際刪除",
        )

    def handle(self, *args, **options):
        """執行清除操作"""

        # 檢查確認參數
        if not options["confirm"] and not options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  警告：此操作將永久刪除 SMT 報工資料！\n"
                    "請使用 --confirm 參數確認操作，或使用 --dry-run 預覽要刪除的資料。"
                )
            )
            return

        # 計算日期範圍
        if options["all"]:
            start_date = None
            end_date = None
            date_filter = "所有時間"
        else:
            days = options["days"]
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            date_filter = f"最近 {days} 天 ({start_date} 到 {end_date})"

        # 查詢要清除的資料
        queryset = SMTProductionReport.objects.all()

        if start_date and end_date:
            queryset = queryset.filter(report_time__date__range=[start_date, end_date])

        # 統計資料
        total_count = queryset.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("✅ 沒有找到符合條件的 SMT 報工記錄"))
            return

        # 顯示要清除的資料統計
        self.stdout.write(
            self.style.SUCCESS(f"📊 找到 {total_count} 筆 SMT 報工記錄 ({date_filter})")
        )

        # 按設備分組統計
        equipment_stats = {}
        for report in queryset:
            equipment_name = report.equipment.name
            if equipment_name not in equipment_stats:
                equipment_stats[equipment_name] = {
                    "count": 0,
                    "total_quantity": 0,
                    "latest_report": None,
                }

            equipment_stats[equipment_name]["count"] += 1
            equipment_stats[equipment_name]["total_quantity"] += report.quantity

            if (
                equipment_stats[equipment_name]["latest_report"] is None
                or report.report_time > equipment_stats[equipment_name]["latest_report"]
            ):
                equipment_stats[equipment_name]["latest_report"] = report.report_time

        # 顯示詳細統計
        self.stdout.write("\n📋 設備統計：")
        for equipment_name, stats in equipment_stats.items():
            self.stdout.write(
                f"  • {equipment_name}: "
                f'{stats["count"]} 筆記錄, '
                f'總產出 {stats["total_quantity"]} 件, '
                f'最新記錄 {stats["latest_report"].strftime("%Y-%m-%d %H:%M")}'
            )

        # 如果是預覽模式，只顯示統計不刪除
        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"\n🔍 預覽模式：以上 {total_count} 筆記錄將被刪除\n"
                    "使用 --confirm 參數實際執行刪除操作"
                )
            )
            return

        # 確認刪除
        if not options["confirm"]:
            self.stdout.write(
                self.style.ERROR("\n❌ 請使用 --confirm 參數確認刪除操作")
            )
            return

        # 執行刪除
        try:
            deleted_count = queryset.delete()[0]

            self.stdout.write(
                self.style.SUCCESS(f"\n✅ 成功清除 {deleted_count} 筆 SMT 報工記錄")
            )

            # 記錄操作日誌
            logger.info(
                f"管理員清除 SMT 報工資料: {deleted_count} 筆記錄 ({date_filter})"
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ 清除失敗：{str(e)}"))
            logger.error(f"清除 SMT 報工資料失敗: {str(e)}")
            raise CommandError(f"清除失敗：{str(e)}")

        # 顯示清除後的狀態
        remaining_count = SMTProductionReport.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"📊 清除後剩餘 SMT 報工記錄：{remaining_count} 筆")
        )

        # 檢查設備狀態
        self.stdout.write("\n🔧 設備狀態檢查：")
        smt_equipment = Equipment.objects.filter(name__icontains="SMT").order_by("name")

        for equipment in smt_equipment:
            today_reports = SMTProductionReport.objects.filter(
                equipment=equipment, report_time__date=date.today()
            ).count()

            status_icon = (
                "🟢"
                if equipment.status == "running"
                else "🟡" if equipment.status == "idle" else "🔴"
            )

            self.stdout.write(
                f"  {status_icon} {equipment.name}: "
                f"{equipment.get_status_display()}, "
                f"今日報工 {today_reports} 筆"
            )

        self.stdout.write(self.style.SUCCESS("\n🎉 SMT 現場報工資料清除完成！"))
