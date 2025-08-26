#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手動清理報表檔案的管理命令
用於手動執行報表檔案和日誌的清理
"""

from django.core.management.base import BaseCommand
from reporting.tasks import cleanup_report_files, cleanup_report_execution_logs, generate_system_cleanup_report
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '手動清理報表檔案和日誌'

    def add_arguments(self, parser):
        parser.add_argument(
            '--files-only',
            action='store_true',
            help='只清理報表檔案'
        )
        parser.add_argument(
            '--logs-only',
            action='store_true',
            help='只清理報表日誌'
        )
        parser.add_argument(
            '--report-only',
            action='store_true',
            help='只生成系統清理報告'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制執行清理（不詢問確認）'
        )

    def handle(self, *args, **options):
        try:
            files_only = options['files_only']
            logs_only = options['logs_only']
            report_only = options['report_only']
            force = options['force']
            
            # 如果沒有指定特定選項，則執行所有清理
            if not any([files_only, logs_only, report_only]):
                files_only = logs_only = report_only = True
            
            self.stdout.write('開始執行報表清理...')
            
            # 如果不是強制執行，詢問確認
            if not force:
                if files_only:
                    self.stdout.write('將清理過期的報表檔案（保留7天）')
                if logs_only:
                    self.stdout.write('將清理過期的報表執行日誌（保留30天）')
                if report_only:
                    self.stdout.write('將生成系統清理報告')
                
                confirm = input('確定要執行清理嗎？(y/N): ')
                if confirm.lower() != 'y':
                    self.stdout.write('已取消清理操作')
                    return
            
            # 執行清理任務
            if files_only:
                self.stdout.write('正在清理報表檔案...')
                cleanup_report_files()
                self.stdout.write(
                    self.style.SUCCESS('報表檔案清理完成')
                )
            
            if logs_only:
                self.stdout.write('正在清理報表日誌...')
                cleanup_report_execution_logs()
                self.stdout.write(
                    self.style.SUCCESS('報表日誌清理完成')
                )
            
            if report_only:
                self.stdout.write('正在生成系統清理報告...')
                generate_system_cleanup_report()
                self.stdout.write(
                    self.style.SUCCESS('系統清理報告生成完成')
                )
            
            self.stdout.write(
                self.style.SUCCESS('所有清理任務執行完成！')
            )
            
        except Exception as e:
            logger.error(f"執行報表清理失敗: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'清理失敗: {str(e)}')
            )
