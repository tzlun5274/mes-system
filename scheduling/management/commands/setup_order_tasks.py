"""
管理命令：設定訂單同步定時任務
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django.utils import timezone


class Command(BaseCommand):
    help = '設定訂單同步相關的定時任務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync-interval',
            type=int,
            default=30,
            help='訂單同步間隔（分鐘，預設30分鐘）'
        )
        parser.add_argument(
            '--cleanup-interval',
            type=int,
            default=1440,  # 24小時
            help='訂單清理間隔（分鐘，預設1440分鐘=24小時）'
        )
        parser.add_argument(
            '--status-update-interval',
            type=int,
            default=60,
            help='訂單狀態更新間隔（分鐘，預設60分鐘）'
        )

    def handle(self, *args, **options):
        self.stdout.write('開始設定訂單同步定時任務...')
        
        sync_interval = options['sync_interval']
        cleanup_interval = options['cleanup_interval']
        status_update_interval = options['status_update_interval']
        
        # 1. 設定訂單同步任務
        self.setup_sync_task(sync_interval)
        
        # 2. 設定訂單清理任務
        self.setup_cleanup_task(cleanup_interval)
        
        # 3. 設定訂單狀態更新任務
        self.setup_status_update_task(status_update_interval)
        
        self.stdout.write(
            self.style.SUCCESS('✅ 訂單同步定時任務設定完成！')
        )

    def setup_sync_task(self, interval_minutes):
        """設定訂單同步任務"""
        task_name = 'scheduling.tasks.sync_orders_task'
        
        # 刪除現有任務
        PeriodicTask.objects.filter(name__contains='訂單同步').delete()
        
        # 創建間隔排程
        interval, created = IntervalSchedule.objects.get_or_create(
            every=interval_minutes,
            period=IntervalSchedule.MINUTES,
        )
        
        if created:
            self.stdout.write(f'創建新的間隔排程：每 {interval_minutes} 分鐘')
        
        # 創建定時任務
        task, created = PeriodicTask.objects.get_or_create(
            name=f'訂單同步任務（每{interval_minutes}分鐘）',
            defaults={
                'task': task_name,
                'interval': interval,
                'enabled': True,
                'description': f'每 {interval_minutes} 分鐘同步訂單資料從 ERP 到 MES'
            }
        )
        
        if created:
            self.stdout.write(f'✅ 創建訂單同步任務：每 {interval_minutes} 分鐘執行')
        else:
            task.interval = interval
            task.description = f'每 {interval_minutes} 分鐘同步訂單資料從 ERP 到 MES'
            task.save()
            self.stdout.write(f'✅ 更新訂單同步任務：每 {interval_minutes} 分鐘執行')

    def setup_cleanup_task(self, interval_minutes):
        """設定訂單清理任務"""
        task_name = 'scheduling.tasks.cleanup_old_orders_task'
        
        # 刪除現有任務
        PeriodicTask.objects.filter(name__contains='訂單清理').delete()
        
        # 創建間隔排程
        interval, created = IntervalSchedule.objects.get_or_create(
            every=interval_minutes,
            period=IntervalSchedule.MINUTES,
        )
        
        if created:
            self.stdout.write(f'創建新的間隔排程：每 {interval_minutes} 分鐘')
        
        # 創建定時任務
        task, created = PeriodicTask.objects.get_or_create(
            name=f'訂單清理任務（每{interval_minutes}分鐘）',
            defaults={
                'task': task_name,
                'interval': interval,
                'enabled': True,
                'description': f'每 {interval_minutes} 分鐘清理過期的訂單資料'
            }
        )
        
        if created:
            self.stdout.write(f'✅ 創建訂單清理任務：每 {interval_minutes} 分鐘執行')
        else:
            task.interval = interval
            task.description = f'每 {interval_minutes} 分鐘清理過期的訂單資料'
            task.save()
            self.stdout.write(f'✅ 更新訂單清理任務：每 {interval_minutes} 分鐘執行')

    def setup_status_update_task(self, interval_minutes):
        """設定訂單狀態更新任務"""
        task_name = 'scheduling.tasks.update_order_status_task'
        
        # 刪除現有任務
        PeriodicTask.objects.filter(name__contains='訂單狀態更新').delete()
        
        # 創建間隔排程
        interval, created = IntervalSchedule.objects.get_or_create(
            every=interval_minutes,
            period=IntervalSchedule.MINUTES,
        )
        
        if created:
            self.stdout.write(f'創建新的間隔排程：每 {interval_minutes} 分鐘')
        
        # 創建定時任務
        task, created = PeriodicTask.objects.get_or_create(
            name=f'訂單狀態更新任務（每{interval_minutes}分鐘）',
            defaults={
                'task': task_name,
                'interval': interval,
                'enabled': True,
                'description': f'每 {interval_minutes} 分鐘更新訂單狀態（逾期、緊急等）'
            }
        )
        
        if created:
            self.stdout.write(f'✅ 創建訂單狀態更新任務：每 {interval_minutes} 分鐘執行')
        else:
            task.interval = interval
            task.description = f'每 {interval_minutes} 分鐘更新訂單狀態（逾期、緊急等）'
            task.save()
            self.stdout.write(f'✅ 更新訂單狀態更新任務：每 {interval_minutes} 分鐘執行')
