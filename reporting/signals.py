"""
報表模組信號處理器
處理與報表相關的信號事件
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import ReportExportLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ReportExportLog)
def report_export_log_saved(sender, instance, created, **kwargs):
    """當報表匯出日誌被儲存時觸發"""
    if created:
        logger.info(f"新的報表匯出記錄已建立: {instance.report_type} - {instance.export_format} - {instance.created_by.username}")
    else:
        logger.info(f"報表匯出記錄已更新: {instance.report_type} - {instance.export_format} - {instance.created_by.username}")


@receiver(post_delete, sender=ReportExportLog)
def report_export_log_deleted(sender, instance, **kwargs):
    """當報表匯出日誌被刪除時觸發"""
    logger.info(f"報表匯出記錄已刪除: {instance.report_type} - {instance.export_format} - {instance.created_by.username}")


# 可以根據需要添加更多信號處理器
# 例如：當作業員報工數據更新時，自動更新相關報表
# 例如：當工單狀態變更時，觸發報表重新計算 