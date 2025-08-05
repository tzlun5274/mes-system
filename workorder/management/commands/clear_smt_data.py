"""
SMT 報工統計管理命令
用於查看 SMT 現場報工即時模式資料統計
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from datetime import date, timedelta
from workorder.models import SMTProductionReport
from equip.models import Equipment
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "查看 SMT 現場報工即時模式資料統計"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="統計所有 SMT 報工記錄（不限制日期）",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="統計最近幾天的資料（預設：7天）",
        )
        parser.add_argument(
            "--detailed",
            action="store_true",
            help="顯示詳細的統計資訊",
        )

    def handle(self, *args, **options):
        """執行統計操作"""

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

        # 查詢資料
        queryset = SMTProductionReport.objects.all()

        if start_date and end_date:
            queryset = queryset.filter(work_date__range=[start_date, end_date])

        # 統計資料
        total_count = queryset.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS(f"✅ 沒有找到符合條件的 SMT 報工記錄 ({date_filter})"))
            return

        # 顯示統計資訊
        self.stdout.write(
            self.style.SUCCESS(f"📊 找到 {total_count} 筆 SMT 報工記錄 ({date_filter})")
        )

        # 按設備分組統計
        equipment_stats = {}
        for report in queryset:
            equipment_name = report.equipment.name if report.equipment else "未知設備"
            if equipment_name not in equipment_stats:
                equipment_stats[equipment_name] = {
                    "count": 0,
                    "total_quantity": 0,
                    "latest_report": None,
                }

            equipment_stats[equipment_name]["count"] += 1
            equipment_stats[equipment_name]["total_quantity"] += report.work_quantity or 0

            if (
                equipment_stats[equipment_name]["latest_report"] is None
                or report.work_date > equipment_stats[equipment_name]["latest_report"]
            ):
                equipment_stats[equipment_name]["latest_report"] = report.work_date

        # 顯示設備統計
        self.stdout.write(f"\n🔧 按設備統計：")
        for equipment_name, stats in sorted(equipment_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            latest_time = stats["latest_report"].strftime("%Y-%m-%d %H:%M") if stats["latest_report"] else "無"
            self.stdout.write(
                f"  • {equipment_name}: {stats['count']} 筆, "
                f"總數量: {stats['total_quantity']}, "
                f"最新報工: {latest_time}"
            )

        if options["detailed"]:
            # 顯示詳細統計
            self.stdout.write(f"\n📋 詳細統計資訊：")
            
            # 按報工類型統計（已移除 report_type 欄位）
            self.stdout.write(f"\n📊 按報工類型統計：")
            self.stdout.write(f"  • SMT報工: {total_count} 筆")

            # 按日期統計
            date_stats = queryset.values('work_date').annotate(count=Count('id')).order_by('-work_date')[:10]
            self.stdout.write(f"\n📅 最近10天報工統計：")
            for stat in date_stats:
                report_date = stat['work_date']
                self.stdout.write(f"  • {report_date}: {stat['count']} 筆")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ SMT 報工統計完成！\n"
                f"📊 共計 {total_count} 筆記錄 ({date_filter})\n"
                f"💡 使用 --detailed 參數可查看詳細統計"
            )
        )
