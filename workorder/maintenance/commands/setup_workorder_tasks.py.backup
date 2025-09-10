# 工單管理定時任務設定命令
# 功能：註冊工單管理的自動同步和自動轉換定時任務
# 作者：MES 系統
# 建立時間：2024年

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
from workorder.models import SystemConfig
import logging

workorder_logger = logging.getLogger("workorder")


class Command(BaseCommand):
    help = "設定工單管理的自動同步和自動轉換定時任務"

    def handle(self, *args, **options):
        try:
            workorder_logger.info("=== 開始設定工單管理定時任務 ===")

            # 設定自動同步製令單任務
            self.setup_auto_sync_task()

            # 設定自動轉換工單任務
            self.setup_auto_convert_task()

            workorder_logger.info("工單管理定時任務設定完成")
            self.stdout.write(self.style.SUCCESS("工單管理定時任務設定完成！"))

        except Exception as e:
            workorder_logger.error(f"設定工單管理定時任務失敗：{str(e)}")
            self.stdout.write(self.style.ERROR(f"設定失敗：{str(e)}"))

    def setup_auto_sync_task(self):
        """設定自動同步製令單任務"""
        task_name = "workorder.tasks.auto_sync_company_orders"
        display_name = "自動同步公司製令單"

        # 從 SystemConfig 讀取自動同步間隔設定（預設 1 分鐘）
        auto_sync_interval = 1
        try:
            config = SystemConfig.objects.get(key="auto_sync_companyorder_interval")
            auto_sync_interval = int(config.value)
            workorder_logger.info(f"讀取到自動同步間隔設定：{auto_sync_interval} 分鐘")
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動同步間隔設定，使用預設值 1 分鐘")
            # 自動建立預設設定
            SystemConfig.objects.create(
                key="auto_sync_companyorder_interval", value="1"
            )

        # 建立或更新間隔排程
        interval, created = IntervalSchedule.objects.get_or_create(
            every=auto_sync_interval,
            period=IntervalSchedule.MINUTES,
        )

        if created:
            workorder_logger.info(
                f"建立新的間隔排程：每 {interval.every} {interval.period}"
            )

        # 建立或更新定時任務
        periodic_task, created = PeriodicTask.objects.get_or_create(
            name=display_name,
            defaults={
                "task": task_name,
                "interval": interval,
                "enabled": True,
            },
        )

        if not created:
            # 更新現有任務
            periodic_task.task = task_name
            periodic_task.interval = interval
            periodic_task.enabled = True
            periodic_task.save()
            workorder_logger.info(f"更新定時任務：{display_name}")
        else:
            workorder_logger.info(f"建立定時任務：{display_name}")

        self.stdout.write(
            f"✓ {display_name} 任務已設定（每 {auto_sync_interval} 分鐘執行）"
        )

    def setup_auto_convert_task(self):
        """設定自動轉換工單任務"""
        task_name = "workorder.tasks.auto_convert_orders"
        display_name = "自動轉換工單"

        # 從 SystemConfig 讀取自動轉換間隔設定（預設 3 分鐘）
        auto_convert_interval = 3
        try:
            config = SystemConfig.objects.get(key="auto_convert_interval")
            auto_convert_interval = int(config.value)
            workorder_logger.info(
                f"讀取到自動轉換間隔設定：{auto_convert_interval} 分鐘"
            )
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動轉換間隔設定，使用預設值 3 分鐘")
            # 只有在不存在時才建立預設設定
            SystemConfig.objects.create(key="auto_convert_interval", value="3")
            auto_convert_interval = 3

        # 建立或更新間隔排程
        interval, created = IntervalSchedule.objects.get_or_create(
            every=auto_convert_interval,
            period=IntervalSchedule.MINUTES,
        )

        if created:
            workorder_logger.info(
                f"建立新的間隔排程：每 {interval.every} {interval.period}"
            )

        # 建立或更新定時任務
        periodic_task, created = PeriodicTask.objects.get_or_create(
            name=display_name,
            defaults={
                "task": task_name,
                "interval": interval,
                "enabled": True,
            },
        )

        if not created:
            # 更新現有任務
            periodic_task.task = task_name
            periodic_task.interval = interval
            periodic_task.enabled = True
            periodic_task.save()
            workorder_logger.info(f"更新定時任務：{display_name}")
        else:
            workorder_logger.info(f"建立定時任務：{display_name}")

        self.stdout.write(
            f"✓ {display_name} 任務已設定（每 {auto_convert_interval} 分鐘執行）"
        )
