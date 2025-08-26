"""
遷移現有的自動審核定時任務到新的 ScheduledTask 模型
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask
from system.models import ScheduledTask
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '遷移現有的自動審核定時任務到新的 ScheduledTask 模型'

    def handle(self, *args, **options):
        try:
            # 檢查是否已經存在自動審核定時任務
            existing_task = ScheduledTask.objects.filter(
                task_type='auto_approve',
                task_function='system.tasks.auto_approve_work_reports'
            ).first()
            
            if existing_task:
                self.stdout.write(
                    self.style.WARNING('自動審核定時任務已存在，跳過遷移')
                )
                return
            
            # 查找現有的 Celery Beat 自動審核定時任務
            celery_task = PeriodicTask.objects.filter(
                name='auto_approve_work_reports'
            ).first()
            
            if celery_task:
                # 創建新的 ScheduledTask
                scheduled_task = ScheduledTask.objects.create(
                    name='自動審核報工記錄',
                    task_type='auto_approve',
                    task_function='system.tasks.auto_approve_work_reports',
                    cron_expression='0 */1 * * *',  # 每小時執行
                    is_enabled=celery_task.enabled,
                    description='自動審核符合條件的報工記錄，每小時執行一次'
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'成功遷移自動審核定時任務: {scheduled_task.name}')
                )
                
                # 刪除舊的 Celery Beat 任務
                celery_task.delete()
                self.stdout.write(
                    self.style.SUCCESS('已刪除舊的 Celery Beat 自動審核定時任務')
                )
            else:
                # 如果沒有現有的任務，創建一個預設的
                scheduled_task = ScheduledTask.objects.create(
                    name='自動審核報工記錄',
                    task_type='auto_approve',
                    task_function='system.tasks.auto_approve_work_reports',
                    cron_expression='0 */1 * * *',  # 每小時執行
                    is_enabled=True,
                    description='自動審核符合條件的報工記錄，每小時執行一次'
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'創建新的自動審核定時任務: {scheduled_task.name}')
                )
            
            # 顯示所有定時任務
            self.stdout.write('\n當前定時任務清單:')
            for task in ScheduledTask.objects.all():
                status = '啟用' if task.is_enabled else '停用'
                self.stdout.write(f'- {task.name} ({status}): {task.cron_expression}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'遷移失敗: {str(e)}')
            )
