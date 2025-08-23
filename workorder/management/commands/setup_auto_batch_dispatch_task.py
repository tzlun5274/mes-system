# 自動批次派工定時任務設定命令
# 功能：註冊自動批次派工的定時任務
# 作者：MES 系統
# 建立時間：2025年

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
from workorder.company_order.models import SystemConfig
import logging

workorder_logger = logging.getLogger("workorder")


class Command(BaseCommand):
    help = "設定自動批次派工的定時任務"

    def handle(self, *args, **options):
        try:
            workorder_logger.info("=== 開始設定自動批次派工定時任務 ===")

            # 設定自動批次派工任務
            self.setup_auto_batch_dispatch_task()

            workorder_logger.info("自動批次派工定時任務設定完成")
            self.stdout.write(self.style.SUCCESS("自動批次派工定時任務設定完成！"))

        except Exception as e:
            workorder_logger.error(f"設定自動批次派工定時任務失敗：{str(e)}")
            self.stdout.write(self.style.ERROR(f"設定失敗：{str(e)}"))

    def setup_auto_batch_dispatch_task(self):
        """設定自動批次派工任務"""
        task_name = "workorder.tasks.auto_batch_dispatch_orders"
        display_name = "自動批次派工"

        # 從 SystemConfig 讀取自動批次派工間隔設定（預設 60 分鐘）
        auto_dispatch_interval = 60
        try:
            config = SystemConfig.objects.get(key="auto_batch_dispatch_interval")
            auto_dispatch_interval = int(config.value)
            workorder_logger.info(
                f"讀取到自動批次派工間隔設定：{auto_dispatch_interval} 分鐘"
            )
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動批次派工間隔設定，使用預設值 60 分鐘")
            # 只有在不存在時才建立預設設定
            SystemConfig.objects.create(key="auto_batch_dispatch_interval", value="60")
            auto_dispatch_interval = 60

        # 建立或更新間隔排程
        interval, created = IntervalSchedule.objects.get_or_create(
            every=auto_dispatch_interval,
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
            f"✓ {display_name} 任務已設定（每 {auto_dispatch_interval} 分鐘執行）"
        ) 