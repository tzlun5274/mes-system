#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定自動分配任務的管理命令
用於在 Celery Beat 中設定自動分配任務的排程
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from workorder.models import AutoAllocationSettings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '設定自動分配任務的 Celery Beat 排程'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='執行間隔（分鐘），預設30分鐘'
        )
        parser.add_argument(
            '--enable',
            action='store_true',
            help='立即啟用自動分配功能'
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='停用自動分配功能'
        )

    def handle(self, *args, **options):
        try:
            interval_minutes = options['interval']
            enable = options['enable']
            disable = options['disable']
            
            self.stdout.write(f'開始設定自動分配任務，間隔：{interval_minutes} 分鐘')
            
            # 創建或更新間隔排程
            interval_schedule, created = IntervalSchedule.objects.get_or_create(
                every=interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'創建新的間隔排程：{interval_minutes} 分鐘')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'使用現有間隔排程：{interval_minutes} 分鐘')
                )
            
            # 創建或更新週期任務
            task_name = 'workorder.tasks.auto_allocation_task'
            task, created = PeriodicTask.objects.get_or_create(
                name='自動分配任務',
                defaults={
                    'task': task_name,
                    'interval': interval_schedule,
                    'enabled': True,
                    'description': f'每 {interval_minutes} 分鐘執行一次自動分配功能'
                }
            )
            
            if not created:
                # 更新現有任務
                task.interval = interval_schedule
                task.description = f'每 {interval_minutes} 分鐘執行一次自動分配功能'
                task.save()
                self.stdout.write(
                    self.style.WARNING('更新現有自動分配任務')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('創建新的自動分配任務')
                )
            
            # 創建或更新自動分配設定
            settings, created = AutoAllocationSettings.objects.get_or_create(
                id=1,
                defaults={
                    'enabled': False,
                    'interval_minutes': interval_minutes,
                    'start_time': '08:00',
                    'end_time': '18:00',
                    'max_execution_time': 30,
                    'notification_enabled': True
                }
            )
            
            if not created:
                # 更新現有設定
                settings.interval_minutes = interval_minutes
                settings.save()
                self.stdout.write(
                    self.style.WARNING('更新現有自動分配設定')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('創建新的自動分配設定')
                )
            
            # 處理啟用/停用選項
            if enable:
                settings.enabled = True
                settings.save()
                task.enabled = True
                task.save()
                self.stdout.write(
                    self.style.SUCCESS('已啟用自動分配功能')
                )
            elif disable:
                settings.enabled = False
                settings.save()
                task.enabled = False
                task.save()
                self.stdout.write(
                    self.style.WARNING('已停用自動分配功能')
                )
            
            # 顯示當前狀態
            self.stdout.write('\n=== 當前設定狀態 ===')
            self.stdout.write(f'任務名稱：{task.name}')
            self.stdout.write(f'任務狀態：{"啟用" if task.enabled else "停用"}')
            self.stdout.write(f'執行間隔：{interval_minutes} 分鐘')
            self.stdout.write(f'自動分配功能：{"啟用" if settings.enabled else "停用"}')
            self.stdout.write(f'執行時間範圍：{settings.start_time} - {settings.end_time}')
            self.stdout.write(f'最大執行時間：{settings.max_execution_time} 分鐘')
            
            self.stdout.write(
                self.style.SUCCESS('\n自動分配任務設定完成！')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'設定自動分配任務失敗：{str(e)}')
            )
            logger.error(f'設定自動分配任務失敗：{str(e)}') 