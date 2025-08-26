"""
Django 管理命令：設定工單分析定時任務
"""
from django.core.management.base import BaseCommand, CommandError
from django_celery_beat.models import PeriodicTask, IntervalSchedule


class Command(BaseCommand):
    help = '設定或移除工單分析定時任務'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--setup',
            action='store_true',
            help='設定定時分析任務'
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='移除定時分析任務'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='執行間隔（分鐘，預設: 60分鐘）'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='列出現有的定時任務'
        )
    
    def handle(self, *args, **options):
        setup = options.get('setup')
        remove = options.get('remove')
        interval = options.get('interval')
        list_tasks = options.get('list')
        
        if list_tasks:
            self.list_tasks()
        elif setup:
            self.setup_tasks(interval)
        elif remove:
            self.remove_tasks()
        else:
            self.stdout.write(
                self.style.WARNING('請指定操作: --setup, --remove, 或 --list')
            )
    
    def setup_tasks(self, interval):
        """設定定時分析任務"""
        try:
            # 建立或取得間隔排程
            interval_schedule, created = IntervalSchedule.objects.get_or_create(
                every=interval,
                period=IntervalSchedule.MINUTES,
            )
            
            if created:
                self.stdout.write(f'建立新的間隔排程: 每{interval}分鐘')
            else:
                self.stdout.write(f'使用現有間隔排程: 每{interval}分鐘')
            
            # 建立或更新定時任務
            task, created = PeriodicTask.objects.get_or_create(
                name='auto_analyze_completed_workorders',
                defaults={
                    'task': 'reporting.tasks.auto_analyze_completed_workorders',
                    'interval': interval_schedule,
                    'enabled': True,
                    'description': f'自動分析已完工工單（每{interval}分鐘執行）'
                }
            )
            
            if not created:
                task.interval = interval_schedule
                task.description = f'自動分析已完工工單（每{interval}分鐘執行）'
                task.save()
                self.stdout.write('更新現有定時任務')
            else:
                self.stdout.write('建立新的定時任務')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'定時分析任務設定成功！每{interval}分鐘執行一次'
                )
            )
            
        except Exception as e:
            raise CommandError(f'設定定時任務失敗: {str(e)}')
    
    def remove_tasks(self):
        """移除定時分析任務"""
        try:
            task = PeriodicTask.objects.filter(
                name='auto_analyze_completed_workorders'
            ).first()
            
            if task:
                task.delete()
                self.stdout.write(
                    self.style.SUCCESS('定時分析任務已移除')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('找不到定時分析任務')
                )
                
        except Exception as e:
            raise CommandError(f'移除定時任務失敗: {str(e)}')
    
    def list_tasks(self):
        """列出現有的定時任務"""
        try:
            tasks = PeriodicTask.objects.filter(
                name__icontains='analyze'
            ).select_related('interval')
            
            if not tasks.exists():
                self.stdout.write('沒有找到分析相關的定時任務')
                return
            
            self.stdout.write('現有的分析相關定時任務:')
            self.stdout.write('-' * 80)
            
            for task in tasks:
                self.stdout.write(f'任務名稱: {task.name}')
                self.stdout.write(f'任務描述: {task.description}')
                self.stdout.write(f'任務函數: {task.task}')
                
                if task.interval:
                    self.stdout.write(f'執行間隔: 每{task.interval.every}分鐘')
                
                self.stdout.write(f'啟用狀態: {"啟用" if task.enabled else "停用"}')
                
                if task.last_run_at:
                    self.stdout.write(f'最後執行: {task.last_run_at}')
                
                if task.next_run_at:
                    self.stdout.write(f'下次執行: {task.next_run_at}')
                
                self.stdout.write('-' * 80)
                
        except Exception as e:
            raise CommandError(f'列出定時任務失敗: {str(e)}')
