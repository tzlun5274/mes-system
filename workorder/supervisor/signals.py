"""
主管功能信號處理模組
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from workorder.models import WorkOrder, WorkOrderProcess, WorkOrderProduction, WorkOrderProductionDetail
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTSupplementReport

# 移除主管報工引用，避免混淆
# 主管職責：監督、審核、管理，不代為報工

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OperatorSupplementReport)
def operator_report_saved(sender, instance, created, **kwargs):
    """
    作業員報工記錄保存後的信號處理
    """
    if created:
        logger.info(f"新增作業員報工記錄: {instance.id}")
    else:
        logger.info(f"更新作業員報工記錄: {instance.id}")


@receiver(post_save, sender=SMTSupplementReport)
def smt_report_saved(sender, instance, created, **kwargs):
    """
    SMT補登報工記錄保存後的信號處理
    """
    if created:
        logger.info(f"新增SMT補登報工記錄: {instance.id}")
    else:
        logger.info(f"更新SMT補登報工記錄: {instance.id}")


@receiver(post_delete, sender=OperatorSupplementReport)
def operator_report_deleted(sender, instance, **kwargs):
    """
    作業員報工記錄刪除後的信號處理
    """
    logger.info(f"刪除作業員報工記錄: {instance.id}")


@receiver(post_delete, sender=SMTSupplementReport)
def smt_report_deleted(sender, instance, **kwargs):
    """
    SMT補登報工記錄刪除後的信號處理
    """
    logger.info(f"刪除SMT補登報工記錄: {instance.id}") 