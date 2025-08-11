"""
填報作業管理子模組 - 信號處理
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import FillWork
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FillWork)
def fill_work_saved(sender, instance, created, **kwargs):
    """
    填報作業儲存後的信號處理
    """
    if created:
        logger.info(f"新增填報作業：{instance.operator} - {instance.work_date} - {instance.operation}")
    else:
        logger.info(f"更新填報作業：{instance.operator} - {instance.work_date} - {instance.operation}")


@receiver(post_delete, sender=FillWork)
def fill_work_deleted(sender, instance, **kwargs):
    """
    填報作業刪除後的信號處理
    """
    logger.info(f"刪除填報作業：{instance.operator} - {instance.work_date} - {instance.operation}") 