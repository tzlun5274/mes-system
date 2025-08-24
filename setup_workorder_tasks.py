#!/usr/bin/env python3
"""
設定工單管理定時任務
"""

import os
import sys
import django

# 設定 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_workorder_tasks():
    """
    設定工單管理定時任務
    """
    print("=== 設定工單管理定時任務 ===")
    
    try:
        # 1. 設定全部工單轉生產中任務（每小時執行一次）
        interval_schedule, created = IntervalSchedule.objects.get_or_create(
            every=1,
            period=IntervalSchedule.HOURS,
        )
        
        if created:
            print(f"✓ 建立新的間隔排程：每 {interval_schedule.every} {interval_schedule.period}")
        
        # 檢查是否已存在任務
        task_name = "workorder.tasks.convert_all_workorders_to_production"
        existing_task = PeriodicTask.objects.filter(name="全部工單轉生產中").first()
        
        if existing_task:
            print("✓ 任務「全部工單轉生產中」已存在")
            # 更新任務設定
            existing_task.task = task_name
            existing_task.interval = interval_schedule
            existing_task.enabled = True
            existing_task.save()
            print("✓ 已更新任務設定")
        else:
            # 建立新任務
            periodic_task = PeriodicTask.objects.create(
                name="全部工單轉生產中",
                task=task_name,
                interval=interval_schedule,
                enabled=True,
                description="每小時自動將所有待生產工單轉換為生產中狀態"
            )
            print(f"✓ 建立新任務：{periodic_task.name}")
        
        # 2. 設定自動批次派工任務（每30分鐘執行一次）
        interval_schedule_30min, created = IntervalSchedule.objects.get_or_create(
            every=30,
            period=IntervalSchedule.MINUTES,
        )
        
        if created:
            print(f"✓ 建立新的間隔排程：每 {interval_schedule_30min.every} {interval_schedule_30min.period}")
        
        # 檢查是否已存在任務
        task_name_auto_dispatch = "workorder.tasks.auto_dispatch_workorders"
        existing_task_auto_dispatch = PeriodicTask.objects.filter(name="自動批次派工").first()
        
        if existing_task_auto_dispatch:
            print("✓ 任務「自動批次派工」已存在")
            # 更新任務設定
            existing_task_auto_dispatch.task = task_name_auto_dispatch
            existing_task_auto_dispatch.interval = interval_schedule_30min
            existing_task_auto_dispatch.enabled = True
            existing_task_auto_dispatch.save()
            print("✓ 已更新任務設定")
        else:
            # 建立新任務
            periodic_task_auto_dispatch = PeriodicTask.objects.create(
                name="自動批次派工",
                task=task_name_auto_dispatch,
                interval=interval_schedule_30min,
                enabled=True,
                description="每30分鐘自動為未派工工單建立派工單"
            )
            print(f"✓ 建立新任務：{periodic_task_auto_dispatch.name}")
        
        print("\n=== 定時任務設定完成 ===")
        print("已設定的任務：")
        print("1. 全部工單轉生產中 - 每小時執行一次")
        print("2. 自動批次派工 - 每30分鐘執行一次")
        
        return True
        
    except Exception as e:
        logger.error(f"設定定時任務失敗: {str(e)}")
        print(f"❌ 設定失敗: {str(e)}")
        return False

def list_workorder_tasks():
    """
    列出所有工單相關的定時任務
    """
    print("\n=== 工單管理定時任務列表 ===")
    
    tasks = PeriodicTask.objects.filter(
        name__in=["全部工單轉生產中", "自動批次派工"]
    )
    
    if not tasks.exists():
        print("沒有找到工單相關的定時任務")
        return
    
    for task in tasks:
        status = "啟用" if task.enabled else "停用"
        interval = f"每 {task.interval.every} {task.interval.period}"
        print(f"任務名稱: {task.name}")
        print(f"狀態: {status}")
        print(f"執行間隔: {interval}")
        print(f"任務函數: {task.task}")
        print(f"描述: {task.description}")
        print("-" * 50)

def enable_workorder_tasks():
    """
    啟用所有工單相關的定時任務
    """
    print("\n=== 啟用工單管理定時任務 ===")
    
    tasks = PeriodicTask.objects.filter(
        name__in=["全部工單轉生產中", "自動批次派工"]
    )
    
    enabled_count = 0
    for task in tasks:
        if not task.enabled:
            task.enabled = True
            task.save()
            print(f"✓ 已啟用任務：{task.name}")
            enabled_count += 1
        else:
            print(f"- 任務 {task.name} 已經是啟用狀態")
    
    print(f"總共啟用了 {enabled_count} 個任務")

def disable_workorder_tasks():
    """
    停用所有工單相關的定時任務
    """
    print("\n=== 停用工單管理定時任務 ===")
    
    tasks = PeriodicTask.objects.filter(
        name__in=["全部工單轉生產中", "自動批次派工"]
    )
    
    disabled_count = 0
    for task in tasks:
        if task.enabled:
            task.enabled = False
            task.save()
            print(f"✓ 已停用任務：{task.name}")
            disabled_count += 1
        else:
            print(f"- 任務 {task.name} 已經是停用狀態")
    
    print(f"總共停用了 {disabled_count} 個任務")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='工單管理定時任務管理工具')
    parser.add_argument('action', choices=['setup', 'list', 'enable', 'disable'], 
                       help='執行動作：setup(設定), list(列出), enable(啟用), disable(停用)')
    
    args = parser.parse_args()
    
    if args.action == 'setup':
        setup_workorder_tasks()
    elif args.action == 'list':
        list_workorder_tasks()
    elif args.action == 'enable':
        enable_workorder_tasks()
    elif args.action == 'disable':
        disable_workorder_tasks()
