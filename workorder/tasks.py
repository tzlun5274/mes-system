#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工單管理定時任務
"""

import logging
from celery import shared_task
from django.utils import timezone
from workorder.services.completion_service import FillWorkCompletionService
from workorder.services.auto_allocation_service import AutoAllocationService
from workorder.services.auto_allocation_service import AutoAllocationService

logger = logging.getLogger(__name__)

@shared_task
def check_workorder_completion():
    """
    檢查工單完工狀態的定時任務
    """
    try:
        logger.info("開始執行工單完工檢查任務")
        
        # 執行完工檢查
        result = FillWorkCompletionService.check_all_workorders_completion()
        
        logger.info(f"工單完工檢查完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"工單完工檢查任務執行失敗: {str(e)}")
        return {'error': str(e)}

@shared_task
def auto_allocate_workorder_quantities():
    """
    自動分配工單數量的定時任務
    """
    try:
        logger.info("開始執行工單數量自動分配任務")
        
        # 執行自動分配
        service = AutoAllocationService()
        result = service.allocate_all_pending_workorders()
        
        logger.info(f"工單數量自動分配完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"工單數量自動分配任務執行失敗: {str(e)}")
        return {'error': str(e)}

@shared_task
def auto_allocate_completed_workorder_quantities():
    """
    已完工工單工序紀錄數量自動分配的定時任務
    """
    try:
        logger.info("開始執行已完工工單數量自動分配任務")
        
        # 執行已完工工單數量分配
        service = AutoAllocationService()
        result = service.allocate_all_pending_workorders()
        
        logger.info(f"已完工工單數量自動分配完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"已完工工單數量自動分配任務執行失敗: {str(e)}")
        return {'error': str(e)}
