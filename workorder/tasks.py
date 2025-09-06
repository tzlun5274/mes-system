#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工單管理 Celery 任務
提供各種自動化功能
"""

import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch

logger = logging.getLogger(__name__)

@shared_task
def convert_all_workorders_to_production():
    """
    定時任務：將所有待生產工單轉換為生產中狀態
    """
    try:
        with transaction.atomic():
            # 取得所有待生產的工單
            pending_workorders = WorkOrder.objects.filter(status='pending')
            total_count = pending_workorders.count()
            
            if total_count == 0:
                logger.info("沒有待生產的工單需要轉換")
                return {
                    'success': True,
                    'message': '沒有待生產的工單需要轉換',
                    'updated_count': 0
                }
            
            updated_count = 0
            for workorder in pending_workorders:
                # 更新工單狀態為生產中
                workorder.status = 'in_progress'
                workorder.updated_at = timezone.now()
                workorder.save()
                updated_count += 1
                
                # 記錄操作日誌
                logger.info(f"定時任務：工單 {workorder.order_number} 狀態更新為生產中")
                
                # 同時更新對應的派工單狀態（如果存在）
                try:
                    dispatch = WorkOrderDispatch.objects.filter(
                        order_number=workorder.order_number,
                        product_code=workorder.product_code,
                        company_code=workorder.company_code
                    ).first()
                    
                    if dispatch and dispatch.status != 'in_production':
                        dispatch.status = 'in_production'
                        dispatch.save()
                        logger.info(f"定時任務：派工單 {dispatch.order_number} 狀態更新為生產中")
                except Exception as e:
                    logger.warning(f"定時任務：更新派工單狀態失敗: {str(e)}")
            
            logger.info(f"定時任務完成：成功將 {updated_count} 個工單轉換為生產中狀態")
            
            return {
                'success': True,
                'message': f'定時任務完成：成功將 {updated_count} 個工單轉換為生產中狀態',
                'updated_count': updated_count
            }
            
    except Exception as e:
        logger.error(f"定時任務失敗：全部工單轉生產中失敗: {str(e)}")
        return {
            'success': False,
            'error': f'定時任務失敗：{str(e)}',
            'updated_count': 0
        }

@shared_task
def auto_allocation_task():
    """
    定時任務：自動為數量為0的報工記錄分配數量
    """
    try:
        from workorder.services.auto_allocation_service import AutoAllocationService
        
        service = AutoAllocationService()
        result = service.allocate_all_pending_workorders()
        
        if result.get('success', False):
            logger.info(f"自動分配任務完成：{result.get('message', '分配完成')}")
            return {
                'success': True,
                'message': result.get('message', '自動分配完成'),
                'allocated_count': result.get('total_allocated_reports', 0),
                'total_quantity': result.get('total_allocated_quantity', 0)
            }
        else:
            logger.error(f"自動分配任務失敗：{result.get('message', '未知錯誤')}")
            return {
                'success': False,
                'error': result.get('message', '自動分配失敗'),
                'allocated_count': 0,
                'total_quantity': 0
            }
            
    except Exception as e:
        logger.error(f"自動分配任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'自動分配任務執行失敗: {str(e)}',
            'allocated_count': 0,
            'total_quantity': 0
        }

@shared_task
def completion_check_task():
    """
    定時任務：自動完工檢查
    """
    try:
        from workorder.services.completion_service import FillWorkCompletionService
        
        # 獲取所有進行中的工單
        from workorder.models import WorkOrder
        active_workorders = WorkOrder.objects.filter(status='in_progress')
        
        completed_count = 0
        for workorder in active_workorders:
            try:
                if FillWorkCompletionService.check_and_complete_workorder(workorder.id):
                    completed_count += 1
            except Exception as e:
                logger.error(f"檢查工單 {workorder.id} 完工狀態失敗: {str(e)}")
        
        logger.info(f"完工檢查任務完成，共檢查 {active_workorders.count()} 個工單，完工 {completed_count} 個")
        return {
            'success': True,
            'message': f'完工檢查完成，共完工 {completed_count} 個工單',
            'checked_count': active_workorders.count(),
            'completed_count': completed_count
        }
        
    except Exception as e:
        logger.error(f"完工檢查任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'完工檢查任務執行失敗: {str(e)}',
            'checked_count': 0,
            'completed_count': 0
        }

@shared_task
def data_transfer_task():
    """
    定時任務：資料轉移
    """
    try:
        from workorder.models import CompletedWorkOrder
        from workorder.services.completion_service import FillWorkCompletionService
        
        # 獲取所有已完工但未轉移的工單
        completed_workorders = CompletedWorkOrder.objects.filter(is_transferred=False)
        
        transferred_count = 0
        for completed_workorder in completed_workorders:
            try:
                # 執行資料轉移
                if FillWorkCompletionService.transfer_completed_workorder(completed_workorder.id):
                    transferred_count += 1
            except Exception as e:
                logger.error(f"轉移工單 {completed_workorder.id} 失敗: {str(e)}")
        
        logger.info(f"資料轉移任務完成，共轉移 {transferred_count} 個工單")
        return {
            'success': True,
            'message': f'資料轉移完成，共轉移 {transferred_count} 個工單',
            'transferred_count': transferred_count
        }
        
    except Exception as e:
        logger.error(f"資料轉移任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'資料轉移任務執行失敗: {str(e)}',
            'transferred_count': 0
        }

@shared_task
def auto_dispatch_workorders():
    """
    定時任務：自動批次派工
    """
    try:
        with transaction.atomic():
            # 取得所有未派工的工單
            undispatched_orders = WorkOrder.objects.all()
            
            # 檢查每個工單是否已有對應的派工單
            truly_undispatched = []
            for wo in undispatched_orders:
                dispatch_exists = WorkOrderDispatch.objects.filter(
                    order_number=wo.order_number,
                    product_code=wo.product_code
                ).exists()
                if not dispatch_exists:
                    truly_undispatched.append(wo)
            
            created = 0
            for wo in truly_undispatched:
                # 建立派工單，直接設定為生產中狀態
                dispatch = WorkOrderDispatch.objects.create(
                    company_code=getattr(wo, "company_code", None),
                    order_number=wo.order_number,
                    product_code=wo.product_code,
                    planned_quantity=wo.quantity,
                    status="in_production",  # 直接設定為生產中
                    dispatch_date=timezone.now().date(),  # 設定派工日期為今天
                    created_by="system_auto_dispatch",
                )
                created += 1
                
                # 記錄操作日誌
                logger.info(f"定時任務：自動批次派工 - 工單 {wo.order_number} 轉派為生產中狀態")
            
            logger.info(f"定時任務完成：自動批次派工完成，共建立 {created} 筆派工單")
            
            return {
                'success': True,
                'message': f'定時任務完成：自動批次派工完成，共建立 {created} 筆派工單',
                'created_count': created
            }
            
    except Exception as e:
        logger.error(f"定時任務失敗：自動批次派工失敗: {str(e)}")
        return {
            'success': False,
            'error': f'定時任務失敗：{str(e)}',
            'created_count': 0
        }
