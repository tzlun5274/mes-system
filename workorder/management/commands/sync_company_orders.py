"""
公司製令單同步命令
主要用於定時任務和系統維護，一般使用者請透過網頁介面操作
"""

from django.core.management.base import BaseCommand
from workorder.services.sync_service import CompanyOrderSyncService
from workorder.models import SystemConfig
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import logging

workorder_logger = logging.getLogger("workorder")


class Command(BaseCommand):
    help = "公司製令單同步命令 - 主要用於定時任務，一般使用者請透過網頁介面操作"

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='限制每個公司同步的記錄數量（用於測試）'
        )
        parser.add_argument(
            '--company',
            type=str,
            default=None,
            help='只同步指定公司代號的資料'
        )
        parser.add_argument(
            '--setup-tasks',
            action='store_true',
            help='設定自動同步和轉換的定時任務'
        )
        parser.add_argument(
            '--auto-mode',
            action='store_true',
            help='自動模式：檢查是否已轉換成工單'
        )

    def handle(self, *args, **options):
        # 如果是指定設定任務，則執行任務設定
        if options.get('setup_tasks'):
            self.setup_periodic_tasks()
            return

        # 執行同步邏輯
        self.sync_company_orders(
            limit=options.get('limit'),
            company_filter=options.get('company'),
            auto_mode=options.get('auto_mode')
        )

    def sync_company_orders(self, limit=None, company_filter=None, auto_mode=False):
        """同步公司製令單的核心邏輯"""
        try:
            # 使用同步服務
            sync_service = CompanyOrderSyncService()
            result = sync_service.sync_all_companies(
                company_filter=company_filter,
                limit=limit,
                auto_mode=auto_mode
            )
            
            if result['success']:
                # 顯示同步結果
                for detail in result['sync_details']:
                    if detail['status'] == 'success':
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ {detail['company']}: {detail['message']}")
                        )
                    elif detail['status'] == 'skipped':
                        self.stdout.write(
                            self.style.WARNING(f"⚠ {detail['company']}: {detail['message']}")
                        )
                    elif detail['status'] == 'error':
                        self.stdout.write(
                            self.style.ERROR(f"✗ {detail['company']}: {detail['message']}")
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"所有公司同步完成，共新增 {result['total_synced']} 筆公司製令單記錄"
                    )
                )
                workorder_logger.info(
                    f"所有公司同步製令單完成，共新增 {result['total_synced']} 筆公司製令單記錄。"
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"同步失敗：{result.get('error', '未知錯誤')}")
                )
                workorder_logger.error(
                    f"同步製令單失敗：{result.get('error', '未知錯誤')}"
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"同步失敗：{e}")
            )
            workorder_logger.error(f"同步製令單失敗：{e}")

    def setup_periodic_tasks(self):
        """設定定時任務"""
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