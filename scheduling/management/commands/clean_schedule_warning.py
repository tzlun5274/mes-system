from django.core.management.base import BaseCommand
from scheduling.scheduling_models import ScheduleWarning

class Command(BaseCommand):
    help = '自動清理排程警告，只保留最近 1 萬筆（繁體中文說明）'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('開始清理 ScheduleWarning，只保留最近 1 萬筆...'))
        count = ScheduleWarning.objects.count()
        batch = 10000
        total_deleted = 0
        while count > batch:
            ids = list(ScheduleWarning.objects.order_by('created_at').values_list('id', flat=True)[:batch])
            deleted, _ = ScheduleWarning.objects.filter(id__in=ids).delete()
            total_deleted += deleted
            count = ScheduleWarning.objects.count()
            self.stdout.write(f'目前剩下 {count} 筆，已刪除 {total_deleted} 筆')
        self.stdout.write(self.style.SUCCESS('清理完成！目前 ScheduleWarning 只剩下最近 1 萬筆。'))

# 這個指令會自動分批刪除最舊的警告資料，避免一次刪除造成資料庫卡住。
# 執行方式：python manage.py clean_schedule_warning
# 適合資料量過大導致系統卡住時使用。 