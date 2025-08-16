"""
設定完工檢查定時任務
建立工序完工檢查和填報完工檢查兩個獨立的定時任務
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '設定工序完工檢查和填報完工檢查定時任務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--process-interval',
            type=int,
            default=15,
            help='工序完工檢查間隔（分鐘），預設15分鐘'
        )
        parser.add_argument(
            '--report-interval',
            type=int,
            default=15,
            help='填報完工檢查間隔（分鐘），預設15分鐘'
        )
        parser.add_argument(
            '--enabled',
            action='store_true',
            help='啟用定時任務'
        )
        parser.add_argument(
            '--disabled',
            action='store_true',
            help='停用定時任務'
        )

    def handle(self, *args, **options):
        process_interval = options['process_interval']
        report_interval = options['report_interval']
        enabled = options['enabled']
        disabled = options['disabled']
        
        self.stdout.write(f"開始設定完工檢查定時任務...")
        self.stdout.write(f"工序完工檢查間隔：{process_interval} 分鐘")
        self.stdout.write(f"填報完工檢查間隔：{report_interval} 分鐘")
        
        try:
            # 設定工序完工檢查定時任務
            self._setup_process_completion_task(process_interval, enabled, disabled)
            
            # 設定填報完工檢查定時任務
            self._setup_report_completion_task(report_interval, enabled, disabled)
            
            self.stdout.write(
                self.style.SUCCESS("完工檢查定時任務設定完成！")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"設定定時任務時發生錯誤：{str(e)}")
            )
    
    def _setup_process_completion_task(self, interval_minutes, enabled, disabled):
        """設定工序完工檢查定時任務"""
        try:
            # 建立或取得間隔排程
            interval_schedule, created = IntervalSchedule.objects.get_or_create(
                every=interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            
            if created:
                self.stdout.write(f"建立新的工序完工檢查間隔排程：{interval_minutes} 分鐘")
            else:
                self.stdout.write(f"使用現有工序完工檢查間隔排程：{interval_minutes} 分鐘")
            
            # 建立或更新定時任務
            task_name = 'workorder.tasks.auto_check_process_completion'
            task, created = PeriodicTask.objects.get_or_create(
                name='工序完工檢查定時任務',
                defaults={
                    'task': task_name,
                    'interval': interval_schedule,
                    'enabled': True,
                    'description': f'每 {interval_minutes} 分鐘自動檢查工單工序進度，當所有工序都完成時觸發完工'
                }
            )
            
            if not created:
                # 更新現有任務
                task.interval = interval_schedule
                task.description = f'每 {interval_minutes} 分鐘自動檢查工單工序進度，當所有工序都完成時觸發完工'
            
            # 設定啟用狀態
            if enabled:
                task.enabled = True
            elif disabled:
                task.enabled = False
            
            task.save()
            
            status = "啟用" if task.enabled else "停用"
            self.stdout.write(
                self.style.SUCCESS(f"工序完工檢查定時任務已{status}")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"設定工序完工檢查定時任務時發生錯誤：{str(e)}")
            )
    
    def _setup_report_completion_task(self, interval_minutes, enabled, disabled):
        """設定填報完工檢查定時任務"""
        try:
            # 建立或取得間隔排程
            interval_schedule, created = IntervalSchedule.objects.get_or_create(
                every=interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            
            if created:
                self.stdout.write(f"建立新的填報完工檢查間隔排程：{interval_minutes} 分鐘")
            else:
                self.stdout.write(f"使用現有填報完工檢查間隔排程：{interval_minutes} 分鐘")
            
            # 建立或更新定時任務
            task_name = 'workorder.tasks.auto_check_report_completion'
            task, created = PeriodicTask.objects.get_or_create(
                name='填報完工檢查定時任務',
                defaults={
                    'task': task_name,
                    'interval': interval_schedule,
                    'enabled': True,
                    'description': f'每 {interval_minutes} 分鐘自動檢查出貨包裝報工數量，當達到目標數量時觸發完工'
                }
            )
            
            if not created:
                # 更新現有任務
                task.interval = interval_schedule
                task.description = f'每 {interval_minutes} 分鐘自動檢查出貨包裝報工數量，當達到目標數量時觸發完工'
            
            # 設定啟用狀態
            if enabled:
                task.enabled = True
            elif disabled:
                task.enabled = False
            
            task.save()
            
            status = "啟用" if task.enabled else "停用"
            self.stdout.write(
                self.style.SUCCESS(f"填報完工檢查定時任務已{status}")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"設定填報完工檢查定時任務時發生錯誤：{str(e)}")
            ) 