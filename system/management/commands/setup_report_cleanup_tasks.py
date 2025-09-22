# 報表清理定時任務設定命令
# 功能：註冊報表清理的定時任務
# 作者：MES 系統
# 建立時間：2025年

from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone
from workorder.models import SystemConfig
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "設定報表清理的定時任務"

    def handle(self, *args, **options):
        try:
            logger.info("=== 開始設定報表清理定時任務 ===")

            # 設定報表檔案清理任務
            self.setup_file_cleanup_task()
            
            # 設定報表日誌清理任務
            self.setup_log_cleanup_task()

            logger.info("報表清理定時任務設定完成")
            self.stdout.write(self.style.SUCCESS("報表清理定時任務設定完成！"))

        except Exception as e:
            logger.error(f"設定報表清理定時任務失敗：{str(e)}")
            self.stdout.write(self.style.ERROR(f"設定失敗：{str(e)}"))

    def setup_file_cleanup_task(self):
        """設定報表檔案清理任務"""
        task_name = "reporting.tasks.cleanup_report_files"
        display_name = "報表檔案清理"

        # 從 SystemConfig 讀取啟用狀態（預設啟用）
        auto_cleanup_enabled = True
        try:
            config = SystemConfig.objects.get(key="auto_cleanup_enabled")
            auto_cleanup_enabled = config.value.lower() == 'true'
            logger.info(
                f"讀取到自動清理啟用狀態：{'啟用' if auto_cleanup_enabled else '停用'}"
            )
        except SystemConfig.DoesNotExist:
            logger.warning("未找到自動清理啟用狀態設定，使用預設值啟用")
            # 只有在不存在時才建立預設設定
            SystemConfig.objects.create(key="auto_cleanup_enabled", value="true")
            auto_cleanup_enabled = True

        # 建立或更新間隔排程（每24小時執行一次）
        interval, created = IntervalSchedule.objects.get_or_create(
            every=24,
            period=IntervalSchedule.HOURS,
        )

        if created:
            logger.info(
                f"建立新的間隔排程：每 {interval.every} {interval.period}"
            )

        # 建立或更新定時任務
        periodic_task, created = PeriodicTask.objects.get_or_create(
            name=display_name,
            defaults={
                "task": task_name,
                "interval": interval,
                "enabled": auto_cleanup_enabled,
            },
        )

        if not created:
            # 更新現有任務
            periodic_task.task = task_name
            periodic_task.interval = interval
            periodic_task.enabled = auto_cleanup_enabled
            periodic_task.save()
            logger.info(f"更新定時任務：{display_name}，狀態：{'啟用' if auto_cleanup_enabled else '停用'}")
        else:
            logger.info(f"建立定時任務：{display_name}，狀態：{'啟用' if auto_cleanup_enabled else '停用'}")

        status_text = "啟用" if auto_cleanup_enabled else "停用"
        self.stdout.write(
            f"✓ {display_name} 任務已設定（每 24 小時執行，狀態：{status_text}）"
        )

    def setup_log_cleanup_task(self):
        """設定報表日誌清理任務"""
        task_name = "reporting.tasks.cleanup_report_execution_logs"
        display_name = "報表日誌清理"

        # 從 SystemConfig 讀取啟用狀態（預設啟用）
        auto_cleanup_enabled = True
        try:
            config = SystemConfig.objects.get(key="auto_cleanup_enabled")
            auto_cleanup_enabled = config.value.lower() == 'true'
            logger.info(
                f"讀取到自動清理啟用狀態：{'啟用' if auto_cleanup_enabled else '停用'}"
            )
        except SystemConfig.DoesNotExist:
            logger.warning("未找到自動清理啟用狀態設定，使用預設值啟用")
            # 只有在不存在時才建立預設設定
            SystemConfig.objects.create(key="auto_cleanup_enabled", value="true")
            auto_cleanup_enabled = True

        # 建立或更新間隔排程（每7天執行一次）
        interval, created = IntervalSchedule.objects.get_or_create(
            every=7,
            period=IntervalSchedule.DAYS,
        )

        if created:
            logger.info(
                f"建立新的間隔排程：每 {interval.every} {interval.period}"
            )

        # 建立或更新定時任務
        periodic_task, created = PeriodicTask.objects.get_or_create(
            name=display_name,
            defaults={
                "task": task_name,
                "interval": interval,
                "enabled": auto_cleanup_enabled,
            },
        )

        if not created:
            # 更新現有任務
            periodic_task.task = task_name
            periodic_task.interval = interval
            periodic_task.enabled = auto_cleanup_enabled
            periodic_task.save()
            logger.info(f"更新定時任務：{display_name}，狀態：{'啟用' if auto_cleanup_enabled else '停用'}")
        else:
            logger.info(f"建立定時任務：{display_name}，狀態：{'啟用' if auto_cleanup_enabled else '停用'}")

        status_text = "啟用" if auto_cleanup_enabled else "停用"
        self.stdout.write(
            f"✓ {display_name} 任務已設定（每 7 天執行，狀態：{status_text}）"
        )
