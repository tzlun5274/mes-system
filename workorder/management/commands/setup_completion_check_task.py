"""
設定完工檢查定時任務
自動檢查工單完工狀態的定時任務設定
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '設定完工檢查定時任務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='檢查間隔（分鐘），預設30分鐘'
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
        interval_minutes = options['interval']
        enabled = options['enabled']
        disabled = options['disabled']
        
        self.stdout.write(f"開始設定完工檢查定時任務（間隔：{interval_minutes} 分鐘）...")
        
        try:
            # 建立或取得間隔排程
            interval_schedule, created = IntervalSchedule.objects.get_or_create(
                every=interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"建立新的間隔排程：{interval_minutes} 分鐘")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"使用現有間隔排程：{interval_minutes} 分鐘")
                )
            
            # 建立或更新定時任務
            task_name = 'workorder.tasks.auto_check_workorder_completion'
            task, created = PeriodicTask.objects.get_or_create(
                name='自動檢查工單完工狀態',
                defaults={
                    'task': task_name,
                    'interval': interval_schedule,
                    'enabled': True,
                    'description': f'每 {interval_minutes} 分鐘自動檢查工單完工狀態，支援數量達到和手動勾選兩種完工判斷方式'
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS("建立新的完工檢查定時任務")
                )
            else:
                # 更新現有任務的間隔
                task.interval = interval_schedule
                task.description = f'每 {interval_minutes} 分鐘自動檢查工單完工狀態，支援數量達到和手動勾選兩種完工判斷方式'
                task.save()
                self.stdout.write(
                    self.style.SUCCESS("更新現有完工檢查定時任務")
                )
            
            # 處理啟用/停用選項
            if enabled:
                task.enabled = True
                task.save()
                self.stdout.write(
                    self.style.SUCCESS("啟用完工檢查定時任務")
                )
            elif disabled:
                task.enabled = False
                task.save()
                self.stdout.write(
                    self.style.WARNING("停用完工檢查定時任務")
                )
            
            # 顯示任務資訊
            self.stdout.write("\n完工檢查定時任務資訊：")
            self.stdout.write(f"  任務名稱：{task.name}")
            self.stdout.write(f"  任務函數：{task.task}")
            self.stdout.write(f"  執行間隔：{task.interval.every} {task.interval.period}")
            self.stdout.write(f"  啟用狀態：{'啟用' if task.enabled else '停用'}")
            self.stdout.write(f"  最後執行：{task.last_run_at or '尚未執行'}")
            self.stdout.write(f"  描述：{task.description}")
            
            self.stdout.write(
                self.style.SUCCESS(f"\n完工檢查定時任務設定完成！")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"設定完工檢查定時任務失敗：{str(e)}")
            )
            logger.error(f"設定完工檢查定時任務失敗：{str(e)}") 