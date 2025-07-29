#!/usr/bin/env python3
"""
報表資料同步管理命令
自動將已核准的報工記錄同步到報表資料表中

使用方法:
python manage.py sync_report_data --type work_time --date-from 2025-01-01 --date-to 2025-01-31
python manage.py sync_report_data --type work_order --date-from 2025-01-01 --date-to 2025-01-31
python manage.py sync_report_data --type all --date-from 2025-01-01 --date-to 2025-01-31
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, timedelta
from reporting.services.sync_service import ReportDataSyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "同步已核准的報工記錄到報表資料表"

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['work_time', 'work_order', 'all'],
            default='all',
            help='同步類型: work_time(工作時間), work_order(工單機種), all(全部)'
        )
        parser.add_argument(
            '--date-from',
            type=str,
            help='開始日期 (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--date-to',
            type=str,
            help='結束日期 (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='自動模式：同步最近7天的資料'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制同步：即使記錄已存在也重新同步'
        )

    def handle(self, *args, **options):
        sync_type = options['type']
        date_from = options['date_from']
        date_to = options['date_to']
        auto_mode = options['auto']
        force_sync = options['force']

        self.stdout.write(
            self.style.SUCCESS(f"開始執行報表資料同步 - 類型: {sync_type}")
        )

        try:
            # 初始化同步服務
            sync_service = ReportDataSyncService()

            # 處理日期參數
            if auto_mode:
                # 自動模式：同步最近7天的資料
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=7)
                date_from = start_date.strftime('%Y-%m-%d')
                date_to = end_date.strftime('%Y-%m-%d')
                self.stdout.write(
                    self.style.WARNING(f"自動模式：同步 {date_from} 到 {date_to} 的資料")
                )
            else:
                # 手動模式：使用指定的日期範圍
                if not date_from:
                    date_from = (timezone.now().date() - timedelta(days=7)).strftime('%Y-%m-%d')
                if not date_to:
                    date_to = timezone.now().date().strftime('%Y-%m-%d')

            # 驗證日期格式
            try:
                datetime.strptime(date_from, '%Y-%m-%d')
                datetime.strptime(date_to, '%Y-%m-%d')
            except ValueError:
                raise CommandError("日期格式錯誤，請使用 YYYY-MM-DD 格式")

            # 執行同步
            result = sync_service.sync_data(
                sync_type=sync_type,
                date_from=date_from,
                date_to=date_to,
                user='system'
            )

            # 顯示結果
            self.stdout.write(
                self.style.SUCCESS(
                    f"同步完成！\n"
                    f"處理記錄數: {result['processed']}\n"
                    f"新增記錄數: {result['created']}\n"
                    f"更新記錄數: {result['updated']}\n"
                    f"執行時間: {result['duration_seconds']} 秒"
                )
            )

            # 顯示詳細統計
            if result['processed'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"同步效率: {result['processed'] / result['duration_seconds']:.2f} 記錄/秒"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"同步失敗: {str(e)}")
            )
            logger.error(f"報表資料同步失敗: {str(e)}")
            raise CommandError(f"同步失敗: {str(e)}")


 