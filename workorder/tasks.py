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
from workorder.services.completion_service import FillWorkCompletionService

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
def workorder_archive_task():
    """
    定時任務：自動工單歸檔
    觸發條件：定時執行（可配置執行間隔）
    執行動作：自動處理所有待歸檔的工單（完工判斷+資料轉移+資料清除）
    執行方式：排程自動執行
    """
    try:
        from django.utils import timezone
        
        # 執行完整的工單歸檔流程
        result = FillWorkCompletionService.archive_workorders()
        
        # 更新所有完工判斷定時任務的最後執行時間
        try:
            from system.models import ScheduledTask
            ScheduledTask.objects.filter(
                task_type='completion_check',
                is_enabled=True
            ).update(last_run_at=timezone.now())
            logger.info("已更新所有完工判斷定時任務的最後執行時間")
        except Exception as e:
            logger.error(f"更新定時任務最後執行時間失敗: {str(e)}")
        
        logger.info(f"自動工單歸檔任務完成：{result.get('message', '歸檔完成')}")
        return {
            'success': True,
            'message': result.get('message', '自動工單歸檔完成'),
            'total_checked': result.get('total_checked', 0),
            'archived_count': result.get('archived_count', 0),
            'error_count': result.get('error_count', 0)
        }
        
    except Exception as e:
        logger.error(f"自動工單歸檔任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'自動工單歸檔任務執行失敗: {str(e)}',
            'total_checked': 0,
            'archived_count': 0,
            'error_count': 1
        }


@shared_task
def auto_dispatch_workorders():
    """
    定時任務：自動批次派工
    """
    from workorder.services.auto_dispatch_service import AutoDispatchService
    
    # 使用統一的服務執行批次派工
    result = AutoDispatchService.execute_auto_dispatch(created_by="system")
    
    return result

@shared_task
def auto_sync_manufacturing_orders():
    """
    定時任務：自動同步各公司製造命令到 ManufacturingOrder 表
    """
    try:
        from django.core.management import call_command
        
        logger.info("開始執行自動同步製造命令任務")
        
        # 執行同步命令
        call_command("sync_manufacturing_orders")
        
        logger.info("自動同步製造命令任務完成")
        
        return {
            'success': True,
            'message': '自動同步製造命令任務完成',
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"自動同步製造命令任務失敗: {str(e)}")
        return {
            'success': False,
            'error': f'自動同步製造命令任務失敗: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }

@shared_task
def auto_convert_orders():
    """
    定時任務：自動轉換製造命令為 MES 工單
    """
    try:
        from workorder.manufacturing_order.services import ManufacturingOrderConvertService
        
        logger.info("開始執行自動轉換MES工單任務")
        
        # 執行轉換服務
        result = ManufacturingOrderConvertService.convert_to_workorder()
        
        if result.get('success', False):
            logger.info(f"自動轉換MES工單任務完成：{result.get('message', '轉換完成')}")
            return {
                'success': True,
                'message': result.get('message', '自動轉換MES工單任務完成'),
                'converted_count': result.get('converted_count', 0),
                'timestamp': timezone.now().isoformat()
            }
        else:
            logger.error(f"自動轉換MES工單任務失敗：{result.get('message', '未知錯誤')}")
            return {
                'success': False,
                'error': result.get('message', '自動轉換MES工單任務失敗'),
                'converted_count': 0,
                'timestamp': timezone.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"自動轉換MES工單任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'自動轉換MES工單任務執行失敗: {str(e)}',
            'converted_count': 0,
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def auto_check_workorder_completion():
    """
    自動檢查工單完工狀態
    檢查所有生產中的工單是否達到完工條件
    """
    try:
        logger.info("開始執行自動完工檢查任務")
        
        # 取得所有生產中的工單
        production_workorders = WorkOrder.objects.filter(status='in_progress')
        total_count = production_workorders.count()
        
        if total_count == 0:
            logger.info("沒有生產中的工單需要檢查")
            return {
                'success': True,
                'message': '沒有生產中的工單需要檢查',
                'checked_count': 0,
                'completed_count': 0
            }
        
        completed_count = 0
        error_count = 0
        
        for workorder in production_workorders:
            try:
                # 檢查完工條件
                summary = FillWorkCompletionService.get_completion_summary(workorder.id)
                
                if summary.get('can_complete', False):
                    # 執行自動完工
                    result = FillWorkCompletionService.auto_complete_workorder(workorder.id)
                    
                    if result.get('success', False):
                        completed_count += 1
                        logger.info(f"工單 {workorder.order_number} 自動完工成功")
                    else:
                        error_count += 1
                        logger.warning(f"工單 {workorder.order_number} 自動完工失敗：{result.get('message', '未知錯誤')}")
                else:
                    logger.debug(f"工單 {workorder.order_number} 尚未達到完工條件")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"檢查工單 {workorder.order_number} 完工狀態時發生錯誤：{str(e)}")
        
        logger.info(f"自動完工檢查任務完成：檢查了 {total_count} 個工單，完工 {completed_count} 個，錯誤 {error_count} 個")
        
        return {
            'success': True,
            'message': f'自動完工檢查任務完成，檢查了 {total_count} 個工單',
            'checked_count': total_count,
            'completed_count': completed_count,
            'error_count': error_count
        }
        
    except Exception as e:
        logger.error(f"自動完工檢查任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'自動完工檢查任務執行失敗: {str(e)}',
            'checked_count': 0,
            'completed_count': 0,
            'error_count': 1
        }


@shared_task
def auto_data_transfer_task():
    """
    定時任務：自動轉移已完工工單資料
    根據系統設定執行批次資料轉移
    """
    try:
        from workorder.models import SystemConfig
        
        # 檢查智能自動完工功能是否啟用（資料轉移使用同一個開關）
        try:
            auto_completion_config = SystemConfig.objects.get(key="auto_completion_enabled")
            transfer_enabled = auto_completion_config.value.lower() == 'true'
        except SystemConfig.DoesNotExist:
            transfer_enabled = True  # 預設啟用
        
        if not transfer_enabled:
            logger.info("資料轉移功能已停用，跳過自動轉移任務")
            return {
                'success': True,
                'message': '資料轉移功能已停用',
                'transferred_count': 0,
                'timestamp': timezone.now().isoformat()
            }
        
        # 取得批次轉移數量設定
        try:
            batch_size_config = SystemConfig.objects.get(key="transfer_batch_size")
            batch_size = int(batch_size_config.value)
        except (SystemConfig.DoesNotExist, ValueError):
            batch_size = 50  # 預設批次大小
        
        logger.info(f"開始執行自動資料轉移任務，批次大小：{batch_size}")
        
        # 執行統一資料轉移服務
        from workorder.services.unified_transfer_service import UnifiedTransferService
        
        # 獲取需要轉移的工單
        from workorder.models import WorkOrder, CompletedWorkOrder
        completed_workorders = WorkOrder.objects.filter(
            status='completed'
        ).exclude(
            id__in=CompletedWorkOrder.objects.values_list('original_workorder_id', flat=True)
        )[:batch_size]
        
        transferred_count = 0
        errors = []
        
        for workorder in completed_workorders:
            try:
                transfer_result = UnifiedTransferService.transfer_workorder_to_completed(
                    workorder.id, "定時自動轉移"
                )
                if transfer_result.get('success'):
                    transferred_count += 1
                else:
                    errors.append(f'工單 {workorder.order_number}: {transfer_result.get("error", "轉移失敗")}')
            except Exception as e:
                errors.append(f'工單 {workorder.order_number}: {str(e)}')
        
        result = {
            'success': True,
            'transferred_count': transferred_count,
            'errors': errors
        }
        
        if result.get('success', False):
            transferred_count = result.get('transferred_count', 0)
            logger.info(f"自動資料轉移任務完成：轉移了 {transferred_count} 個工單")
            return {
                'success': True,
                'message': f'自動資料轉移任務完成，轉移了 {transferred_count} 個工單',
                'transferred_count': transferred_count,
                'timestamp': timezone.now().isoformat()
            }
        else:
            error_msg = result.get('error', '資料轉移失敗')
            logger.error(f"自動資料轉移任務失敗：{error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'transferred_count': 0,
                'timestamp': timezone.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"自動資料轉移任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'自動資料轉移任務執行失敗: {str(e)}',
            'transferred_count': 0,
            'timestamp': timezone.now().isoformat()
        }
