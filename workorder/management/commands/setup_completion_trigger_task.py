"""
設定完工觸發定時任務
使用新的完工觸發機制，實現雙重累加檢查
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '設定完工觸發定時任務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='檢查間隔（分鐘），預設5分鐘'
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
        
        self.stdout.write(f"開始設定完工觸發定時任務（間隔：{interval_minutes} 分鐘）...")
        
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
            task_name = 'workorder.tasks.completion_trigger_task'
            task, created = PeriodicTask.objects.get_or_create(
                name='完工觸發檢查任務',
                defaults={
                    'task': task_name,
                    'interval': interval_schedule,
                    'enabled': True,
                    'description': f'每 {interval_minutes} 分鐘檢查工單完工觸發條件，支援工序記錄和填報記錄雙重累加機制'
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS("建立新的完工觸發檢查任務")
                )
            else:
                # 更新現有任務的間隔
                task.interval = interval_schedule
                task.description = f'每 {interval_minutes} 分鐘檢查工單完工觸發條件，支援工序記錄和填報記錄雙重累加機制'
                task.save()
                self.stdout.write(
                    self.style.SUCCESS("更新現有完工觸發檢查任務")
                )
            
            # 處理啟用/停用選項
            if enabled:
                task.enabled = True
                task.save()
                self.stdout.write(
                    self.style.SUCCESS("啟用完工觸發檢查任務")
                )
            elif disabled:
                task.enabled = False
                task.save()
                self.stdout.write(
                    self.style.WARNING("停用完工觸發檢查任務")
                )
            
            # 顯示任務資訊
            self.stdout.write("\n完工觸發檢查任務資訊：")
            self.stdout.write(f"  任務名稱：{task.name}")
            self.stdout.write(f"  任務函數：{task.task}")
            self.stdout.write(f"  執行間隔：{task.interval.every} {task.interval.period}")
            self.stdout.write(f"  啟用狀態：{'啟用' if task.enabled else '停用'}")
            self.stdout.write(f"  最後執行：{task.last_run_at or '尚未執行'}")
            self.stdout.write(f"  描述：{task.description}")
            
            self.stdout.write(
                self.style.SUCCESS(f"\n完工觸發檢查任務設定完成！")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"設定完工觸發檢查任務失敗：{str(e)}")
            )
            logger.error(f"設定完工觸發檢查任務失敗：{str(e)}") 