#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定已完工工單數量分配定時任務管理命令
用於設定已完工工單工序紀錄數量自動分配的定時任務
"""

from django.core.management.base import BaseCommand, CommandError
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from workorder.models import AutoAllocationSettings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    設定已完工工單數量分配定時任務命令
    """
    
    help = '設定已完工工單工序紀錄數量自動分配的定時任務'
    
    def add_arguments(self, parser):
        """添加命令參數"""
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='執行間隔（分鐘），預設60分鐘'
        )
        
        parser.add_argument(
            '--enable',
            action='store_true',
            help='啟用定時任務'
        )
        
        parser.add_argument(
            '--disable',
            action='store_true',
            help='停用定時任務'
        )
        
        parser.add_argument(
            '--create',
            action='store_true',
            help='創建新的定時任務'
        )
        
        parser.add_argument(
            '--delete',
            action='store_true',
            help='刪除定時任務'
        )
    
    def handle(self, *args, **options):
        """執行命令"""
        try:
            interval_minutes = options['interval']
            enable = options['enable']
            disable = options['disable']
            create = options['create']
            delete = options['delete']
            
            task_name = '已完工工單數量分配任務'
            
            if delete:
                # 刪除定時任務
                try:
                    task = PeriodicTask.objects.get(name=task_name)
                    task.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'已刪除定時任務：{task_name}')
                    )
                except PeriodicTask.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'定時任務不存在：{task_name}')
                    )
                return
            
            if create:
                # 創建新的定時任務
                try:
                    # 檢查是否已存在
                    existing_task = PeriodicTask.objects.filter(name=task_name).first()
                    if existing_task:
                        self.stdout.write(
                            self.style.WARNING(f'定時任務已存在：{task_name}')
                        )
                        return
                    
                    # 創建間隔排程
                    interval_schedule, _ = IntervalSchedule.objects.get_or_create(
                        every=interval_minutes,
                        period=IntervalSchedule.MINUTES,
                    )
                    
                    # 創建定時任務
                    task = PeriodicTask.objects.create(
                        name=task_name,
                        task='workorder.tasks.auto_allocate_completed_workorder_quantities',
                        interval=interval_schedule,
                        enabled=False,  # 預設停用
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'已創建定時任務：{task_name}')
                    )
                    
                except Exception as e:
                    raise CommandError(f'創建定時任務失敗：{str(e)}')
            
            # 獲取或創建定時任務
            try:
                task = PeriodicTask.objects.get(name=task_name)
            except PeriodicTask.DoesNotExist:
                # 如果任務不存在，先創建
                interval_schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=interval_minutes,
                    period=IntervalSchedule.MINUTES,
                )
                
                task = PeriodicTask.objects.create(
                    name=task_name,
                    task='workorder.tasks.auto_allocate_completed_workorder_quantities',
                    interval=interval_schedule,
                    enabled=False,
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'已創建定時任務：{task_name}')
                )
            
            # 創建或更新自動分配設定
            settings, created = AutoAllocationSettings.objects.get_or_create(
                id=1,
                defaults={
                    'enabled': False,
                    'interval_minutes': 30,
                    'start_time': '08:00',
                    'end_time': '18:00',
                    'max_execution_time': 30,
                    'notification_enabled': True,
                    'completed_workorder_allocation_enabled': False,
                    'completed_workorder_allocation_interval': interval_minutes
                }
            )
            
            if not created:
                # 更新現有設定
                settings.completed_workorder_allocation_interval = interval_minutes
                settings.save()
                self.stdout.write(
                    self.style.WARNING('更新現有已完工工單數量分配設定')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('創建新的已完工工單數量分配設定')
                )
            
            # 處理啟用/停用選項
            if enable:
                settings.completed_workorder_allocation_enabled = True
                settings.save()
                task.enabled = True
                task.save()
                self.stdout.write(
                    self.style.SUCCESS('已啟用已完工工單數量分配功能')
                )
            elif disable:
                settings.completed_workorder_allocation_enabled = False
                settings.save()
                task.enabled = False
                task.save()
                self.stdout.write(
                    self.style.WARNING('已停用已完工工單數量分配功能')
                )
            
            # 顯示當前狀態
            self.stdout.write('\n=== 當前設定狀態 ===')
            self.stdout.write(f'任務名稱：{task.name}')
            self.stdout.write(f'任務狀態：{"啟用" if task.enabled else "停用"}')
            self.stdout.write(f'執行間隔：{interval_minutes} 分鐘')
            self.stdout.write(f'已完工工單數量分配功能：{"啟用" if settings.completed_workorder_allocation_enabled else "停用"}')
            self.stdout.write(f'設定執行間隔：{settings.completed_workorder_allocation_interval} 分鐘')
            
        except Exception as e:
            logger.error(f"設定已完工工單數量分配定時任務失敗: {str(e)}")
            raise CommandError(f"設定失敗: {str(e)}") 