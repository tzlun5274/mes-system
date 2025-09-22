from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class ReportingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reporting'
    verbose_name = '報表管理'
    
    def ready(self):
        """
        應用程式準備就緒時自動同步報表排程
        """
        try:
            # 只在主進程中執行，避免在子進程中重複執行
            import os
            if os.environ.get('RUN_MAIN') == 'true':
                from .report_schedule_sync_service import ReportScheduleSyncService
                logger.info("正在同步報表排程到 Celery Beat...")
                result = ReportScheduleSyncService.sync_report_schedules_to_celery()
                if result['success']:
                    logger.info(f"報表排程同步成功: {result['message']}")
                else:
                    logger.error(f"報表排程同步失敗: {result.get('error', '未知錯誤')}")
        except Exception as e:
            logger.error(f"同步報表排程時發生錯誤: {str(e)}") 