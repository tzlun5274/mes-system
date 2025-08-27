"""
設定自動審核定時任務
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '設定自動審核定時任務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='執行間隔（分鐘），預設30分鐘'
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='移除自動審核定時任務'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        remove = options['remove']

        if remove:
            self.remove_auto_approval_task()
        else:
            self.setup_auto_approval_task(interval)

    def setup_auto_approval_task(self, interval):
        """設定自動審核定時任務"""
        try:
            # 創建或取得間隔排程
            interval_schedule, created = IntervalSchedule.objects.get_or_create(
                every=interval,
                period=IntervalSchedule.MINUTES,
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'創建間隔排程: 每{interval}分鐘')
                )

            # 創建或更新定時任務
            task, created = PeriodicTask.objects.get_or_create(
                name='auto_approve_work_reports',
                defaults={
                    'task': 'system.tasks.auto_approve_work_reports',
                    'interval': interval_schedule,
                    'enabled': True,
                    'description': f'自動審核報工記錄（每{interval}分鐘執行）'
                }
            )

            if not created:
                task.interval = interval_schedule
                task.enabled = True
                task.description = f'自動審核報工記錄（每{interval}分鐘執行）'
                task.save()
                self.stdout.write(
                    self.style.SUCCESS(f'更新自動審核定時任務: 每{interval}分鐘執行')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'創建自動審核定時任務: 每{interval}分鐘執行')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'設定自動審核定時任務失敗: {str(e)}')
            )

    def remove_auto_approval_task(self):
        """移除自動審核定時任務"""
        try:
            task = PeriodicTask.objects.filter(name='auto_approve_work_reports').first()
            if task:
                task.delete()
                self.stdout.write(
                    self.style.SUCCESS('自動審核定時任務已移除')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('自動審核定時任務不存在')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'移除自動審核定時任務失敗: {str(e)}')
            )

