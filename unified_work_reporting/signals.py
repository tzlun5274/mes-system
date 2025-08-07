"""
統一補登報工信號處理
處理模型事件的自動化操作
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import UnifiedWorkReport, UnifiedWorkReportLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UnifiedWorkReport)
def unified_work_report_post_save(sender, instance, created, **kwargs):
    """
    統一補登報工儲存後的信號處理
    """
    try:
        if created:
            # 新增記錄時自動建立操作日誌
            UnifiedWorkReportLog.objects.create(
                work_report=instance,
                action='created',
                operator=instance.created_by,
                remarks='系統自動記錄：新增統一補登報工記錄'
            )
            logger.info(f"新增統一補登報工記錄：{instance}")
        else:
            # 更新記錄時自動建立操作日誌
            UnifiedWorkReportLog.objects.create(
                work_report=instance,
                action='updated',
                operator=instance.created_by,
                remarks='系統自動記錄：更新統一補登報工記錄'
            )
            logger.info(f"更新統一補登報工記錄：{instance}")
    
    except Exception as e:
        logger.error(f"統一補登報工信號處理錯誤：{e}")


@receiver(post_delete, sender=UnifiedWorkReport)
def unified_work_report_post_delete(sender, instance, **kwargs):
    """
    統一補登報工刪除後的信號處理
    """
    try:
        logger.info(f"刪除統一補登報工記錄：{instance}")
    except Exception as e:
        logger.error(f"統一補登報工刪除信號處理錯誤：{e}") 