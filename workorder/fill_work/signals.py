"""
填報作業管理子模組 - 信號處理
負責填報作業的信號處理邏輯
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import FillWork
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FillWork)
def fill_work_post_save(sender, instance, created, **kwargs):
    """
    填報作業儲存後的信號處理
    注意：工單狀態更新邏輯已移至 workorder/signals/workorder_status_signals.py
    避免重複處理
    """
    if created:
        # 新增填報作業時的處理
        logger.info(f"新增填報作業: {instance.operator} - {instance.workorder}")
    else:
        # 更新填報作業時的處理
        logger.info(f"更新填報作業: {instance.operator} - {instance.workorder}")


@receiver(pre_save, sender=FillWork)
def fill_work_pre_save(sender, instance, **kwargs):
    """
    填報作業儲存前的信號處理
    """
    # 自動設定工序名稱
    if instance.process and not instance.operation:
        instance.operation = instance.process.name 