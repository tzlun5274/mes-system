"""
設定預設的自動審核定時任務
"""

from django.core.management.base import BaseCommand
from system.models import AutoApprovalTask
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '建立預設的自動審核定時任務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除所有現有的自動審核定時任務'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_existing_tasks()
        
        self.create_default_tasks()
        
    def clear_existing_tasks(self):
        """清除所有現有的自動審核定時任務"""
        count = AutoApprovalTask.objects.count()
        AutoApprovalTask.objects.all().delete()
        self.stdout.write(
            self.style.WARNING(f'已清除 {count} 個現有的自動審核定時任務')
        )
    
    def create_default_tasks(self):
        """建立預設的自動審核定時任務"""
        default_tasks = [
            {
                'name': '每30分鐘自動審核',
                'interval_minutes': 30,
                'description': '每30分鐘執行一次自動審核，適合一般工作時段使用',
                'is_enabled': True
            },
            {
                'name': '每60分鐘自動審核',
                'interval_minutes': 60,
                'description': '每小時執行一次自動審核，適合非繁忙時段使用',
                'is_enabled': False
            },
            {
                'name': '每15分鐘快速審核',
                'interval_minutes': 15,
                'description': '每15分鐘執行一次自動審核，適合繁忙時段快速處理',
                'is_enabled': False
            }
        ]
        
        created_count = 0
        for task_data in default_tasks:
            task, created = AutoApprovalTask.objects.get_or_create(
                name=task_data['name'],
                defaults={
                    'interval_minutes': task_data['interval_minutes'],
                    'description': task_data['description'],
                    'is_enabled': task_data['is_enabled']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 建立定時任務：{task.name} (每{task.interval_minutes}分鐘)')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ 定時任務已存在：{task.name}')
                )
        
        total_tasks = AutoApprovalTask.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'\n完成！總共有 {total_tasks} 個自動審核定時任務')
        )
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'本次新增了 {created_count} 個定時任務')
            )
