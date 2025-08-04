"""
報工紀錄統計管理命令
用於查看作業員補登報工、SMT補登報工、SMT現場報工等報工紀錄統計
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from workorder.models import OperatorSupplementReport, SMTProductionReport
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "查看報工紀錄統計資訊（作業員補登報工、SMT補登報工、SMT現場報工）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--detailed",
            action="store_true",
            help="顯示詳細的報工紀錄統計資訊",
        )

    def handle(self, *args, **options):
        """執行統計操作"""

        try:
            # 統計報工紀錄
            operator_reports_count = OperatorSupplementReport.objects.count()
                    smt_supplement_count = SMTProductionReport.objects.count()
        smt_on_site_count = 0  # 已移除 report_type 欄位
            
            total_count = operator_reports_count + smt_supplement_count + smt_on_site_count
            
            # 顯示統計資訊
            self.stdout.write(
                self.style.SUCCESS(f"📊 報工紀錄統計：")
            )
            self.stdout.write(f"  • 作業員補登報工：{operator_reports_count} 筆")
            self.stdout.write(f"  • SMT補登報工：{smt_supplement_count} 筆")
            self.stdout.write(f"  • SMT現場報工：{smt_on_site_count} 筆")
            self.stdout.write(f"  • 總計：{total_count} 筆")

            if options["detailed"] and total_count > 0:
                self.stdout.write("\n📋 詳細統計資訊：")
                
                # 作業員報工詳細統計
                if operator_reports_count > 0:
                    self.stdout.write(f"\n👥 作業員補登報工詳細：")
                    operator_stats = OperatorSupplementReport.objects.values('operator__name').annotate(
                        count=Count('id')
                    ).order_by('-count')[:10]
                    
                    for stat in operator_stats:
                        username = stat['operator__name'] or '未知作業員'
                        self.stdout.write(f"  • {username}: {stat['count']} 筆")

                # SMT報工詳細統計
                if smt_supplement_count > 0 or smt_on_site_count > 0:
                    self.stdout.write(f"\n🔧 SMT報工詳細：")
                    smt_stats = SMTProductionReport.objects.values('equipment__name').annotate(
                        count=Count('id')
                    ).order_by('-count')[:10]
                    
                    for stat in smt_stats:
                        equipment_name = stat['equipment__name'] or '未知設備'
                                        self.stdout.write(f"  • {equipment_name}: {stat['count']} 筆")

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ 報工紀錄統計完成！\n"
                    f"📊 共計 {total_count} 筆報工紀錄\n"
                    f"💡 使用 --detailed 參數可查看詳細統計"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ 統計失敗：{str(e)}"))
            logger.error(f"報工紀錄統計失敗: {str(e)}")
            raise CommandError(f"統計失敗：{str(e)}") 