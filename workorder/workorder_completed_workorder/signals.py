"""
已完工工單管理子模組 - 信號處理
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import CompletedWorkOrder, CompletedWorkOrderProcess, AutoAllocationLog

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CompletedWorkOrder)
def completed_workorder_saved(sender, instance, created, **kwargs):
    """已完工工單儲存後的信號處理"""
    if created:
        logger.info(f'已完工工單已建立: {instance.company_code}-{instance.order_number}-{instance.product_code}')
    else:
        logger.info(f'已完工工單已更新: {instance.company_code}-{instance.order_number}-{instance.product_code}')


@receiver(post_delete, sender=CompletedWorkOrder)
def completed_workorder_deleted(sender, instance, **kwargs):
    """已完工工單刪除後的信號處理"""
    logger.info(f'已完工工單已刪除: {instance.company_code}-{instance.order_number}-{instance.product_code}')


@receiver(post_save, sender=CompletedWorkOrderProcess)
def completed_workorder_process_saved(sender, instance, created, **kwargs):
    """已完工工單工序儲存後的信號處理"""
    if created:
        logger.info(f'已完工工單工序已建立: {instance.completed_workorder} - {instance.process_name}')
    else:
        logger.info(f'已完工工單工序已更新: {instance.completed_workorder} - {instance.process_name}')


@receiver(post_save, sender=AutoAllocationLog)
def auto_allocation_log_saved(sender, instance, created, **kwargs):
    """自動分配日誌儲存後的信號處理"""
    if created:
        logger.info(f'自動分配日誌已建立: {instance.allocation_settings} - {instance.target_workorder} - {instance.allocation_status}') 