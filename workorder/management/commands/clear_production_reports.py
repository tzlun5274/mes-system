"""
清除所有報工紀錄的管理命令
用於清除作業員補登報工、SMT補登報工、SMT現場報工等所有報工紀錄
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from workorder.models import OperatorSupplementReport, SMTProductionReport
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "清除所有報工紀錄（作業員補登報工、SMT補登報工、SMT現場報工）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="確認執行清除操作（避免誤操作）",
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
                    "⚠️  警告：此操作將永久刪除所有報工紀錄！\n"
                    "請使用 --confirm 參數確認操作，或使用 --dry-run 預覽要刪除的資料。\n\n"
                    "範例：\n"
                    "  python manage.py clear_production_reports --dry-run\n"
                    "  python manage.py clear_production_reports --confirm"
                )
            )
            return

        try:
            # 統計要清除的資料
            operator_reports_count = OperatorSupplementReport.objects.count()
            smt_supplement_count = SMTProductionReport.objects.filter(report_type__in=['normal', 'rd_sample']).count()
            smt_on_site_count = SMTProductionReport.objects.filter(report_type='on_site').count()
            
            total_count = operator_reports_count + smt_supplement_count + smt_on_site_count
            
            if total_count == 0:
                self.stdout.write(self.style.SUCCESS("✅ 目前沒有任何報工紀錄需要清除"))
                return

            # 顯示要清除的資料統計
            self.stdout.write(
                self.style.SUCCESS(f"📊 找到 {total_count} 筆報工紀錄：")
            )
            self.stdout.write(f"  • 作業員補登報工：{operator_reports_count} 筆")
            self.stdout.write(f"  • SMT補登報工：{smt_supplement_count} 筆")
            self.stdout.write(f"  • SMT現場報工：{smt_on_site_count} 筆")

            # 如果是預覽模式，只顯示統計不執行刪除
            if options["dry_run"]:
                self.stdout.write(
                    self.style.WARNING(
                        "\n🔍 預覽模式：以上資料將被刪除，但不會實際執行刪除操作"
                    )
                )
                return

            # 執行刪除
            self.stdout.write("\n🗑️  開始清除報工紀錄...")
            
            # 清除作業員補登報工
            if operator_reports_count > 0:
                OperatorSupplementReport.objects.all().delete()
                self.stdout.write(f"✅ 已清除 {operator_reports_count} 筆作業員補登報工")
            
            # 清除SMT補登報工
            if smt_supplement_count > 0:
                SMTProductionReport.objects.filter(report_type__in=['normal', 'rd_sample']).delete()
                self.stdout.write(f"✅ 已清除 {smt_supplement_count} 筆SMT補登報工")
            
            # 清除SMT現場報工
            if smt_on_site_count > 0:
                SMTProductionReport.objects.filter(report_type='on_site').delete()
                self.stdout.write(f"✅ 已清除 {smt_on_site_count} 筆SMT現場報工")

            # 記錄操作日誌
            logger.info(
                f"管理員清除所有報工紀錄: {total_count} 筆記錄 "
                f"（作業員：{operator_reports_count}，SMT補登：{smt_supplement_count}，SMT現場：{smt_on_site_count}）"
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n🎉 成功清除所有報工紀錄！\n"
                    f"📊 共清除 {total_count} 筆記錄\n"
                    f'⏰ 清除時間：{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
                )
            )

            # 顯示清除後的狀態
            remaining_operator = OperatorSupplementReport.objects.count()
            remaining_smt = SMTProductionReport.objects.count()
            
            self.stdout.write(f"\n📊 清除後剩餘報工紀錄：")
            self.stdout.write(f"  • 作業員補登報工：{remaining_operator} 筆")
            self.stdout.write(f"  • SMT報工：{remaining_smt} 筆")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ 清除失敗：{str(e)}"))
            logger.error(f"清除報工紀錄失敗: {str(e)}")
            raise CommandError(f"清除失敗：{str(e)}") 