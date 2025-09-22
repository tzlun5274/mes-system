"""
排程管理模組的 Celery 任務
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger("scheduling.tasks")


@shared_task
def sync_orders_task():
    """
    定時任務：同步訂單資料從 ERP 到 MES
    """
    try:
        from .customer_order_management import OrderManager
        from system.models import OrderSyncLog
        
        logger.info("開始執行客戶訂單同步定時任務")
        
        # 創建同步日誌
        log = OrderSyncLog.objects.create(
            sync_type='sync',
            status='running',
            message='定時任務執行同步',
            started_at=timezone.now()
        )
        
        # 創建客戶訂單管理器
        order_manager = OrderManager()
        
        # 執行同步
        result = order_manager.sync_orders_from_erp()
        
        if result.get('status') == 'success':
            logger.info(f"客戶訂單同步成功：{result.get('message')}")
            
            # 更新同步狀態
            try:
                from system.models import OrderSyncSettings, OrderSyncLog
                settings_obj, _ = OrderSyncSettings.objects.get_or_create(id=1)
                settings_obj.last_sync_time = timezone.now()
                settings_obj.last_sync_status = "成功"
                settings_obj.last_sync_message = result.get('message')
                settings_obj.save()
                
                # 更新同步日誌
                log = OrderSyncLog.objects.filter(
                    sync_type='sync',
                    status='running'
                ).order_by('-started_at').first()
                
                if log:
                    log.status = 'success'
                    log.completed_at = timezone.now()
                    log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
                    log.message = result.get('message')
                    log.save()
                    
            except Exception as e:
                logger.error(f"更新同步狀態失敗: {str(e)}")
            
            return {
                'success': True,
                'message': result.get('message'),
                'total_orders': result.get('total_orders', 0),
                'executed_at': timezone.now().isoformat()
            }
        else:
            logger.error(f"客戶訂單同步失敗：{result.get('message')}")
            
            # 更新同步狀態
            try:
                from system.models import OrderSyncSettings, OrderSyncLog
                settings_obj, _ = OrderSyncSettings.objects.get_or_create(id=1)
                settings_obj.last_sync_time = timezone.now()
                settings_obj.last_sync_status = "失敗"
                settings_obj.last_sync_message = result.get('message')
                settings_obj.save()
                
                # 更新同步日誌
                log = OrderSyncLog.objects.filter(
                    sync_type='sync',
                    status='running'
                ).order_by('-started_at').first()
                
                if log:
                    log.status = 'failed'
                    log.completed_at = timezone.now()
                    log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
                    log.message = result.get('message')
                    log.save()
                    
            except Exception as e:
                logger.error(f"更新同步狀態失敗: {str(e)}")
            
            return {
                'success': False,
                'error': result.get('message'),
                'total_orders': 0,
                'executed_at': timezone.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"客戶訂單同步定時任務執行失敗: {str(e)}", exc_info=True)
        
        # 更新同步狀態為失敗
        try:
            from system.models import OrderSyncSettings, OrderSyncLog
            settings_obj, _ = OrderSyncSettings.objects.get_or_create(id=1)
            settings_obj.last_sync_time = timezone.now()
            settings_obj.last_sync_status = "失敗"
            settings_obj.last_sync_message = f'任務執行失敗: {str(e)}'
            settings_obj.save()
            
            # 更新同步日誌為失敗
            log = OrderSyncLog.objects.filter(
                sync_type='sync',
                status='running'
            ).order_by('-started_at').first()
            
            if log:
                log.status = 'failed'
                log.completed_at = timezone.now()
                log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
                log.message = f'任務執行失敗: {str(e)}'
                log.save()
                
        except Exception as update_error:
            logger.error(f"更新失敗狀態時發生錯誤: {str(update_error)}")
        
        return {
            'success': False,
            'error': f'客戶訂單同步定時任務執行失敗: {str(e)}',
            'total_orders': 0,
            'executed_at': timezone.now().isoformat()
        }


@shared_task
def cleanup_old_orders_task():
    """
    定時任務：清理過期的訂單資料
    """
    try:
        from .models import OrderMain
        from django.utils import timezone
        
        logger.info("開始執行訂單清理定時任務")
        
        # 設定清理條件：刪除超過 90 天的已完成訂單
        cutoff_date = timezone.now() - timedelta(days=90)
        
        # 找出需要清理的訂單（已交貨完成且超過 90 天）
        old_orders = OrderMain.objects.filter(
            qty_remain=0,  # 已交貨完成
            updated_at__lt=cutoff_date  # 超過 90 天未更新
        )
        
        deleted_count = old_orders.count()
        old_orders.delete()
        
        logger.info(f"訂單清理完成，刪除 {deleted_count} 筆過期訂單")
        
        # 更新清理狀態
        try:
            from system.models import OrderSyncSettings, OrderSyncLog
            settings_obj, _ = OrderSyncSettings.objects.get_or_create(id=1)
            settings_obj.last_cleanup_time = timezone.now()
            settings_obj.last_cleanup_count = deleted_count
            settings_obj.save()
            
            # 更新同步日誌
            log = OrderSyncLog.objects.filter(
                sync_type='cleanup',
                status='running'
            ).order_by('-started_at').first()
            
            if log:
                log.status = 'success'
                log.completed_at = timezone.now()
                log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
                log.message = f'清理完成，刪除 {deleted_count} 筆過期訂單'
                log.save()
                
        except Exception as e:
            logger.error(f"更新清理狀態失敗: {str(e)}")
        
        return {
            'success': True,
            'message': f'清理完成，刪除 {deleted_count} 筆過期訂單',
            'deleted_count': deleted_count,
            'executed_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"訂單清理定時任務執行失敗: {str(e)}", exc_info=True)
        
        # 更新清理日誌為失敗
        try:
            from system.models import OrderSyncLog
            log = OrderSyncLog.objects.filter(
                sync_type='cleanup',
                status='running'
            ).order_by('-started_at').first()
            
            if log:
                log.status = 'failed'
                log.completed_at = timezone.now()
                log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
                log.message = f'任務執行失敗: {str(e)}'
                log.save()
                
        except Exception as update_error:
            logger.error(f"更新失敗狀態時發生錯誤: {str(update_error)}")
        
        return {
            'success': False,
            'error': f'訂單清理定時任務執行失敗: {str(e)}',
            'deleted_count': 0,
            'executed_at': timezone.now().isoformat()
        }


@shared_task
def update_order_status_task():
    """
    定時任務：更新訂單狀態（逾期、緊急等）
    """
    try:
        from .models import OrderMain
        from django.utils import timezone
        from datetime import datetime
        
        logger.info("開始執行訂單狀態更新定時任務")
        
        # 更新所有訂單的狀態
        updated_count = 0
        orders = OrderMain.objects.all()
        
        for order in orders:
            try:
                # 檢查是否需要更新狀態
                delivery_date = datetime.strptime(order.pre_in_date, '%Y-%m-%d').date()
                today = timezone.now().date()
                
                # 如果訂單狀態需要更新，觸發 save 方法來更新 updated_at
                if order.is_overdue or order.is_urgent:
                    order.save(update_fields=['updated_at'])
                    updated_count += 1
                    
            except Exception as e:
                logger.warning(f"更新訂單 {order.id} 狀態時發生錯誤: {str(e)}")
                continue
        
        logger.info(f"訂單狀態更新完成，更新 {updated_count} 筆訂單")
        
        # 更新狀態更新時間
        try:
            from system.models import OrderSyncSettings, OrderSyncLog
            settings_obj, _ = OrderSyncSettings.objects.get_or_create(id=1)
            settings_obj.last_status_update_time = timezone.now()
            settings_obj.save()
            
            # 更新同步日誌
            log = OrderSyncLog.objects.filter(
                sync_type='status_update',
                status='running'
            ).order_by('-started_at').first()
            
            if log:
                log.status = 'success'
                log.completed_at = timezone.now()
                log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
                log.message = f'狀態更新完成，更新 {updated_count} 筆訂單'
                log.save()
                
        except Exception as e:
            logger.error(f"更新狀態更新時間失敗: {str(e)}")
        
        return {
            'success': True,
            'message': f'狀態更新完成，更新 {updated_count} 筆訂單',
            'updated_count': updated_count,
            'executed_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"訂單狀態更新定時任務執行失敗: {str(e)}", exc_info=True)
        
        # 更新狀態更新日誌為失敗
        try:
            from system.models import OrderSyncLog
            log = OrderSyncLog.objects.filter(
                sync_type='status_update',
                status='running'
            ).order_by('-started_at').first()
            
            if log:
                log.status = 'failed'
                log.completed_at = timezone.now()
                log.duration_seconds = (log.completed_at - log.started_at).total_seconds()
                log.message = f'任務執行失敗: {str(e)}'
                log.save()
                
        except Exception as update_error:
            logger.error(f"更新失敗狀態時發生錯誤: {str(update_error)}")
        
        return {
            'success': False,
            'error': f'訂單狀態更新定時任務執行失敗: {str(e)}',
            'updated_count': 0,
            'executed_at': timezone.now().isoformat()
        }
