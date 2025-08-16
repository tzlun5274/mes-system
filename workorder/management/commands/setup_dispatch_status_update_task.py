# 自動更新派工單狀態定時任務設定命令
# 功能：註冊自動更新派工單狀態的定時任務
# 作者：MES 系統
# 建立時間：2025年

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
from workorder.workorder_erp.models import SystemConfig
import logging

workorder_logger = logging.getLogger("workorder")


class Command(BaseCommand):
    help = "設定自動更新派工單狀態的定時任務"

    def handle(self, *args, **options):
        try:
            workorder_logger.info("=== 開始設定自動更新派工單狀態定時任務 ===")

            # 設定自動更新派工單狀態任務
            self.setup_auto_update_dispatch_status_task()

            workorder_logger.info("自動更新派工單狀態定時任務設定完成")
            self.stdout.write(self.style.SUCCESS("自動更新派工單狀態定時任務設定完成！"))

        except Exception as e:
            workorder_logger.error(f"設定自動更新派工單狀態定時任務失敗：{str(e)}")
            self.stdout.write(self.style.ERROR(f"設定失敗：{str(e)}"))

    def setup_auto_update_dispatch_status_task(self):
        """設定自動更新派工單狀態任務"""
        task_name = "workorder.tasks.auto_update_dispatch_statuses"
        display_name = "自動更新派工單狀態"

        # 從 SystemConfig 讀取自動更新間隔設定（預設 30 分鐘）
        auto_update_interval = 30
        try:
            config = SystemConfig.objects.get(key="auto_update_dispatch_status_interval")
            auto_update_interval = int(config.value)
            workorder_logger.info(
                f"讀取到自動更新派工單狀態間隔設定：{auto_update_interval} 分鐘"
            )
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動更新派工單狀態間隔設定，使用預設值 30 分鐘")
            # 只有在不存在時才建立預設設定
            SystemConfig.objects.create(key="auto_update_dispatch_status_interval", value="30")
            auto_update_interval = 30

        # 建立或更新間隔排程
        interval, created = IntervalSchedule.objects.get_or_create(
            every=auto_update_interval,
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
            f"✓ {display_name} 任務已設定（每 {auto_update_interval} 分鐘執行）"
        ) 