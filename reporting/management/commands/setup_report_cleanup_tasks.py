#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定報表清理定時任務的管理命令
用於在 Celery Beat 中設定報表檔案和日誌清理的排程
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '設定報表清理定時任務的 Celery Beat 排程'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file-cleanup-interval',
            type=int,
            default=24,
            help='報表檔案清理間隔（小時），預設24小時'
        )
        parser.add_argument(
            '--log-cleanup-interval',
            type=int,
            default=168,  # 7天
            help='報表日誌清理間隔（小時），預設168小時（7天）'
        )
        parser.add_argument(
            '--report-interval',
            type=int,
            default=168,  # 7天
            help='系統清理報告間隔（小時），預設168小時（7天）'
        )

    def handle(self, *args, **options):
        try:
            file_cleanup_interval = options['file_cleanup_interval']
            log_cleanup_interval = options['log_cleanup_interval']
            report_interval = options['report_interval']
            
            self.stdout.write('開始設定報表清理定時任務...')
            
            # 1. 設定報表檔案清理任務
            self.setup_file_cleanup_task(file_cleanup_interval)
            
            # 2. 設定報表日誌清理任務
            self.setup_log_cleanup_task(log_cleanup_interval)
            
            # 3. 設定系統清理報告任務
            self.setup_cleanup_report_task(report_interval)
            
            self.stdout.write(
                self.style.SUCCESS('報表清理定時任務設定完成！')
            )
            
        except Exception as e:
            logger.error(f"設定報表清理定時任務失敗: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'設定失敗: {str(e)}')
            )

    def setup_file_cleanup_task(self, interval_hours):
        """設定報表檔案清理任務"""
        task_name = 'reporting.tasks.cleanup_report_files'
        display_name = '報表檔案清理'
        
        # 建立或更新間隔排程
        interval_schedule, created = IntervalSchedule.objects.get_or_create(
            every=interval_hours,
            period=IntervalSchedule.HOURS,
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'建立新的間隔排程：每 {interval_hours} 小時')
            )
        
        # 建立或更新定時任務
        periodic_task, created = PeriodicTask.objects.get_or_create(
            name=display_name,
            defaults={
                'task': task_name,
                'interval': interval_schedule,
                'enabled': True,
                'description': f'每 {interval_hours} 小時清理過期的報表檔案'
            }
        )
        
        if not created:
            # 更新現有任務
            periodic_task.interval = interval_schedule
            periodic_task.description = f'每 {interval_hours} 小時清理過期的報表檔案'
            periodic_task.enabled = True
            periodic_task.save()
            self.stdout.write(
                self.style.WARNING(f'更新定時任務：{display_name}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'建立定時任務：{display_name}')
            )
        
        self.stdout.write(
            f'✓ {display_name} 任務已設定（每 {interval_hours} 小時執行）'
        )

    def setup_log_cleanup_task(self, interval_hours):
        """設定報表日誌清理任務"""
        task_name = 'reporting.tasks.cleanup_report_execution_logs'
        display_name = '報表日誌清理'
        
        # 建立或更新間隔排程
        interval_schedule, created = IntervalSchedule.objects.get_or_create(
            every=interval_hours,
            period=IntervalSchedule.HOURS,
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'建立新的間隔排程：每 {interval_hours} 小時')
            )
        
        # 建立或更新定時任務
        periodic_task, created = PeriodicTask.objects.get_or_create(
            name=display_name,
            defaults={
                'task': task_name,
                'interval': interval_schedule,
                'enabled': True,
                'description': f'每 {interval_hours} 小時清理過期的報表執行日誌'
            }
        )
        
        if not created:
            # 更新現有任務
            periodic_task.interval = interval_schedule
            periodic_task.description = f'每 {interval_hours} 小時清理過期的報表執行日誌'
            periodic_task.enabled = True
            periodic_task.save()
            self.stdout.write(
                self.style.WARNING(f'更新定時任務：{display_name}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'建立定時任務：{display_name}')
            )
        
        self.stdout.write(
            f'✓ {display_name} 任務已設定（每 {interval_hours} 小時執行）'
        )

    def setup_cleanup_report_task(self, interval_hours):
        """設定系統清理報告任務"""
        task_name = 'reporting.tasks.generate_system_cleanup_report'
        display_name = '系統清理報告'
        
        # 建立或更新間隔排程
        interval_schedule, created = IntervalSchedule.objects.get_or_create(
            every=interval_hours,
            period=IntervalSchedule.HOURS,
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'建立新的間隔排程：每 {interval_hours} 小時')
            )
        
        # 建立或更新定時任務
        periodic_task, created = PeriodicTask.objects.get_or_create(
            name=display_name,
            defaults={
                'task': task_name,
                'interval': interval_schedule,
                'enabled': True,
                'description': f'每 {interval_hours} 小時生成系統清理報告'
            }
        )
        
        if not created:
            # 更新現有任務
            periodic_task.interval = interval_schedule
            periodic_task.description = f'每 {interval_hours} 小時生成系統清理報告'
            periodic_task.enabled = True
            periodic_task.save()
            self.stdout.write(
                self.style.WARNING(f'更新定時任務：{display_name}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'建立定時任務：{display_name}')
            )
        
        self.stdout.write(
            f'✓ {display_name} 任務已設定（每 {interval_hours} 小時執行）'
        )
