"""
派工單狀態自動更新服務
根據工序分配情況自動更新派工單狀態
"""

import logging
from django.db import transaction
from django.utils import timezone
from workorder.workorder_dispatch.models import WorkOrderDispatch
from workorder.models import WorkOrder, WorkOrderProcess

logger = logging.getLogger(__name__)


class DispatchStatusService:
    """
    派工單狀態自動更新服務
    根據工序分配情況自動更新派工單狀態
    """
    
    @staticmethod
    def update_dispatch_status_by_process_allocation(workorder_id):
        """
        根據工序分配情況更新派工單狀態
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 取得對應的派工單
            dispatch = WorkOrderDispatch.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code
            ).first()
            
            if not dispatch:
                logger.warning(f"工單 {workorder.order_number} 沒有對應的派工單")
                return False
            
            # 檢查工序分配情況
            processes = WorkOrderProcess.objects.filter(workorder_id=workorder.id)
            
            if not processes.exists():
                logger.info(f"工單 {workorder.order_number} 沒有工序記錄")
                return True
            
            # 統計分配情況
            total_processes = processes.count()
            allocated_processes = processes.filter(
                assigned_operator__isnull=False
            ).exclude(assigned_operator='').count()
            
            # 檢查是否有設備分配
            equipment_allocated_processes = processes.filter(
                assigned_equipment__isnull=False
            ).exclude(assigned_equipment='').count()
            
            # 根據分配情況決定派工單狀態（作業員或設備任一有分配即可）
            if allocated_processes > 0 or equipment_allocated_processes > 0:
                if dispatch.status != 'dispatched':
                    dispatch.status = 'dispatched'
                    dispatch.dispatch_date = timezone.now().date()
                    dispatch.save()
                    logger.info(f"派工單 {dispatch.order_number} 狀態更新為已派工（作業員分配: {allocated_processes}, 設備分配: {equipment_allocated_processes}）")
            
            return True
            
        except WorkOrder.DoesNotExist:
            logger.error(f"工單不存在: {workorder_id}")
            return False
        except Exception as e:
            logger.error(f"更新派工單狀態失敗: {str(e)}")
            return False
    
    @staticmethod
    def update_all_dispatch_statuses():
        """
        更新所有派工單的狀態
        根據對應工單的工序分配情況
        """
        try:
            updated_count = 0
            
            # 取得所有派工單
            dispatches = WorkOrderDispatch.objects.filter(status='pending')
            
            for dispatch in dispatches:
                # 取得對應的工單
                workorder = WorkOrder.objects.filter(
                    order_number=dispatch.order_number,
                    product_code=dispatch.product_code
                ).first()
                
                if workorder:
                    # 檢查工序分配情況
                    processes = WorkOrderProcess.objects.filter(workorder_id=workorder.id)
                    
                    if processes.exists():
                        # 檢查是否有工序已分配（作業員或設備任一有分配即可）
                        has_operator_allocation = processes.filter(
                            assigned_operator__isnull=False
                        ).exclude(assigned_operator='').exists()
                        
                        has_equipment_allocation = processes.filter(
                            assigned_equipment__isnull=False
                        ).exclude(assigned_equipment='').exists()
                        
                        if has_operator_allocation or has_equipment_allocation:
                            # 更新為已派工
                            dispatch.status = 'dispatched'
                            dispatch.dispatch_date = timezone.now().date()
                            dispatch.save()
                            updated_count += 1
                            logger.info(f"派工單 {dispatch.order_number} 狀態更新為已派工")
            
            logger.info(f"共更新 {updated_count} 筆派工單狀態")
            return updated_count
            
        except Exception as e:
            logger.error(f"批量更新派工單狀態失敗: {str(e)}")
            return 0
    
    @staticmethod
    def sync_dispatch_status_with_workorder(workorder_id):
        """
        同步派工單狀態與工單狀態
        
        Args:
            workorder_id: 工單ID
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 取得對應的派工單
            dispatch = WorkOrderDispatch.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code
            ).first()
            
            if not dispatch:
                return False
            
            # 根據工單狀態更新派工單狀態
            if workorder.status == 'completed':
                if dispatch.status != 'completed':
                    dispatch.status = 'completed'
                    dispatch.save()
                    logger.info(f"派工單 {dispatch.order_number} 狀態同步為已完工")
            elif workorder.status == 'in_progress':
                if dispatch.status == 'pending':
                    dispatch.status = 'in_production'
                    dispatch.save()
                    logger.info(f"派工單 {dispatch.order_number} 狀態同步為生產中")
            elif workorder.status == 'pending':
                # 檢查是否有工序分配
                processes = WorkOrderProcess.objects.filter(workorder_id=workorder.id)
                has_allocation = processes.filter(
                    assigned_operator__isnull=False
                ).exclude(assigned_operator='').exists()
                
                if has_allocation and dispatch.status == 'pending':
                    dispatch.status = 'dispatched'
                    dispatch.dispatch_date = timezone.now().date()
                    dispatch.save()
                    logger.info(f"派工單 {dispatch.order_number} 狀態同步為已派工")
            
            return True
            
        except WorkOrder.DoesNotExist:
            logger.error(f"工單不存在: {workorder_id}")
            return False
        except Exception as e:
            logger.error(f"同步派工單狀態失敗: {str(e)}")
            return False 