"""
清除報表資料的管理命令
用於清除所有報表相關的資料，包括生產日報表、作業員績效、SMT生產報表等
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reporting.models import (
    ProductionDailyReport,
    OperatorPerformance,
    ReportingOperationLog,
    ReportEmailLog,
)
from reporting.models import ReportSyncSettings, ReportEmailSchedule
from workorder.models import SystemConfig


class Command(BaseCommand):
    help = "清除報表模組的所有資料"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="清除所有報表資料（包括設定和日誌）",
        )
        parser.add_argument(
            "--reports-only",
            action="store_true",
            help="只清除報表資料，保留設定和日誌",
        )
        parser.add_argument(
            "--logs-only",
            action="store_true",
            help="只清除日誌資料",
        )
        parser.add_argument(
            "--settings-only",
            action="store_true",
            help="只清除設定資料",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="確認執行清除操作（避免誤操作）",
        )
        parser.add_argument(
            "--date-range",
            type=str,
            help="指定日期範圍清除資料（格式：YYYY-MM-DD,YYYY-MM-DD）",
        )

    def handle(self, *args, **options):
        # 檢查確認參數
        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  警告：此操作將清除報表資料！\n"
                    "請使用 --confirm 參數確認執行。\n"
                    "可用的清除選項：\n"
                    "  --all: 清除所有報表資料\n"
                    "  --reports-only: 只清除報表資料\n"
                    "  --logs-only: 只清除日誌資料\n"
                    "  --settings-only: 只清除設定資料\n"
                    "  --date-range: 指定日期範圍清除"
                )
            )
            return

        try:
            with transaction.atomic():
                cleared_count = 0

                # 處理日期範圍參數
                date_filter = {}
                if options["date_range"]:
                    try:
                        start_date, end_date = options["date_range"].split(",")
                        from datetime import datetime

                        start_date = datetime.strptime(
                            start_date.strip(), "%Y-%m-%d"
                        ).date()
                        end_date = datetime.strptime(
                            end_date.strip(), "%Y-%m-%d"
                        ).date()
                        date_filter = {"date__range": [start_date, end_date]}
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"📅 將清除 {start_date} 到 {end_date} 的資料"
                            )
                        )
                    except ValueError:
                        raise CommandError(
                            "日期格式錯誤，請使用 YYYY-MM-DD,YYYY-MM-DD 格式"
                        )

                # 清除所有資料
                if options["all"]:
                    cleared_count += self._clear_all_data(date_filter)

                # 只清除報表資料
                elif options["reports_only"]:
                    cleared_count += self._clear_reports_only(date_filter)

                # 只清除日誌資料
                elif options["logs_only"]:
                    cleared_count += self._clear_logs_only()

                # 只清除設定資料
                elif options["settings_only"]:
                    cleared_count += self._clear_settings_only()

                # 預設清除所有報表資料
                else:
                    cleared_count += self._clear_reports_only(date_filter)

                # 記錄操作日誌
                self._log_operation(f"清除報表資料，共清除 {cleared_count} 筆記錄")

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ 成功清除報表資料！\n"
                        f"📊 共清除 {cleared_count} 筆記錄\n"
                        f'⏰ 清除時間：{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 清除資料時發生錯誤：{str(e)}"))
            raise CommandError(f"清除資料失敗：{str(e)}")

    def _clear_all_data(self, date_filter):
        """清除所有報表相關資料"""
        count = 0

        # 清除報表資料
        count += self._clear_reports_only(date_filter)

        # 清除日誌資料
        count += self._clear_logs_only()

        # 清除設定資料
        count += self._clear_settings_only()

        return count

    def _clear_reports_only(self, date_filter):
        """只清除報表資料"""
        count = 0

        # 清除生產日報表
        if date_filter:
            deleted_count = ProductionDailyReport.objects.filter(
                **date_filter
            ).delete()[0]
        else:
            deleted_count = ProductionDailyReport.objects.all().delete()[0]
        count += deleted_count
        self.stdout.write(f"📊 清除生產日報表：{deleted_count} 筆")

        # 清除作業員績效報表
        if date_filter:
            deleted_count = OperatorPerformance.objects.filter(**date_filter).delete()[
                0
            ]
        else:
            deleted_count = OperatorPerformance.objects.all().delete()[0]
        count += deleted_count
        self.stdout.write(f"👤 清除作業員績效報表：{deleted_count} 筆")

        return count

    def _clear_logs_only(self):
        """只清除日誌資料"""
        count = 0

        # 清除報表操作日誌
        deleted_count = ReportingOperationLog.objects.all().delete()[0]
        count += deleted_count
        self.stdout.write(f"📝 清除報表操作日誌：{deleted_count} 筆")

        # 清除郵件發送記錄
        deleted_count = ReportEmailLog.objects.all().delete()[0]
        count += deleted_count
        self.stdout.write(f"📧 清除郵件發送記錄：{deleted_count} 筆")

        return count

    def _clear_settings_only(self):
        """只清除設定資料"""
        count = 0

        # 清除同步設定
        deleted_count = ReportSyncSettings.objects.all().delete()[0]
        count += deleted_count
        self.stdout.write(f"⚙️ 清除同步設定：{deleted_count} 筆")

        # 清除郵件發送設定
        deleted_count = ReportEmailSchedule.objects.all().delete()[0]
        count += deleted_count
        self.stdout.write(f"📧 清除郵件發送設定：{deleted_count} 筆")

        return count

    def _log_operation(self, action):
        """記錄操作到日誌"""
        try:
            ReportingOperationLog.objects.create(user="system", action=action)
        except Exception:
            # 如果記錄日誌失敗，不影響主要操作
            pass

        # 檢查並清除 SystemConfig 資料
        try:
            SystemConfig.objects.filter(key="no_distribute_keywords").delete()
            self.stdout.write(f"⚙️ 清除 SystemConfig：1 筆")
        except Exception:
            # 如果清除 SystemConfig 失敗，不影響主要操作
            pass
