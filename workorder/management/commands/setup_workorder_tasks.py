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

            # 設定自動同步製造命令任務
            self.setup_auto_sync_task()

            # 設定自動轉換MES工單任務
            self.setup_auto_convert_task()

            workorder_logger.info("工單管理定時任務設定完成")
            self.stdout.write(self.style.SUCCESS("工單管理定時任務設定完成！"))

        except Exception as e:
            workorder_logger.error(f"設定工單管理定時任務失敗：{str(e)}")
            self.stdout.write(self.style.ERROR(f"設定失敗：{str(e)}"))

    def setup_auto_sync_task(self):
        """設定自動同步製造命令任務"""
        task_name = "workorder.tasks.auto_sync_manufacturing_orders"
        display_name = "自動同步公司製造命令"

        # 先刪除舊任務
        try:
            old_task = PeriodicTask.objects.get(name=display_name)
            old_task.delete()
            workorder_logger.info(f"已刪除舊的定時任務：{display_name}")
        except PeriodicTask.DoesNotExist:
            workorder_logger.info(f"沒有找到舊的定時任務：{display_name}")

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

        # 從 SystemConfig 讀取自動同步啟用狀態（預設啟用）
        auto_sync_enabled = True
        try:
            config = SystemConfig.objects.get(key="auto_sync_companyorder_enabled")
            auto_sync_enabled = config.value.lower() == 'true'
            workorder_logger.info(f"讀取到自動同步啟用狀態：{auto_sync_enabled}")
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動同步啟用狀態設定，使用預設值 True")
            # 自動建立預設設定
            SystemConfig.objects.create(
                key="auto_sync_companyorder_enabled", value="True"
            )

        # 建立新的間隔排程
        interval, created = IntervalSchedule.objects.get_or_create(
            every=auto_sync_interval,
            period=IntervalSchedule.MINUTES,
        )

        if created:
            workorder_logger.info(
                f"建立新的間隔排程：每 {interval.every} {interval.period}"
            )

        # 建立新的定時任務
        periodic_task = PeriodicTask.objects.create(
            name=display_name,
            task=task_name,
            interval=interval,
            enabled=auto_sync_enabled,
        )

        workorder_logger.info(f"建立新的定時任務：{display_name}")
        self.stdout.write(
            f"✓ {display_name} 任務已重新建立（每 {auto_sync_interval} 分鐘執行）"
        )

    def setup_auto_convert_task(self):
        """設定自動轉換MES工單任務"""
        task_name = "workorder.tasks.auto_convert_orders"
        display_name = "自動轉換MES工單"

        # 從 SystemConfig 讀取自動轉換間隔設定（預設 1 分鐘）
        auto_convert_interval = 1
        try:
            config = SystemConfig.objects.get(key="auto_convert_interval")
            auto_convert_interval = int(config.value)
            workorder_logger.info(
                f"讀取到自動轉換間隔設定：{auto_convert_interval} 分鐘"
            )
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動轉換間隔設定，使用預設值 1 分鐘")
            # 只有在不存在時才建立預設設定
            SystemConfig.objects.create(key="auto_convert_interval", value="1")
            auto_convert_interval = 1

        # 從 SystemConfig 讀取自動轉換啟用狀態（預設啟用）
        auto_convert_enabled = True
        try:
            config = SystemConfig.objects.get(key="auto_convert_enabled")
            auto_convert_enabled = config.value.lower() == 'true'
            workorder_logger.info(f"讀取到自動轉換啟用狀態：{auto_convert_enabled}")
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動轉換啟用狀態設定，使用預設值 True")
            # 自動建立預設設定
            SystemConfig.objects.create(
                key="auto_convert_enabled", value="True"
            )

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
                "enabled": auto_convert_enabled,
            },
        )

        if not created:
            # 更新現有任務
            periodic_task.task = task_name
            periodic_task.interval = interval
            periodic_task.enabled = auto_convert_enabled
            periodic_task.save()
            workorder_logger.info(f"更新定時任務：{display_name}，啟用狀態：{auto_convert_enabled}")
        else:
            workorder_logger.info(f"建立定時任務：{display_name}，啟用狀態：{auto_convert_enabled}")

        self.stdout.write(
            f"✓ {display_name} 任務已設定（每 {auto_convert_interval} 分鐘執行）"
        )
