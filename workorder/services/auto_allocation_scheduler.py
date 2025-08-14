"""
自動分配排程器服務
負責自動為工單分配作業員和設備
"""

import logging
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from workorder.models import (
    WorkOrder, WorkOrderProcess, AutoAllocationSettings, AutoAllocationLog
)
from workorder.fill_work.models import FillWork

logger = logging.getLogger(__name__)


class AutoAllocationScheduler:
    """
    自動分配排程器
    負責自動為工單分配作業員和設備
    """
    
    def __init__(self):
        self.settings = None
        self.log_entry = None
    
    def execute_auto_allocation(self):
        """
        執行自動分配功能
        
        Returns:
            bool: 是否執行成功
        """
        try:
            # 獲取設定
            self.settings = AutoAllocationSettings.objects.get(id=1)
            
            # 檢查是否應該執行
            if not self.settings.should_execute():
                logger.info("自動分配不滿足執行條件，跳過執行")
                return False
            
            # 建立執行記錄
            self.log_entry = AutoAllocationLog.objects.create(
                started_at=timezone.now(),
                success=False
            )
            
            # 標記為正在執行
            self.settings.is_running = True
            self.settings.save()
            
            logger.info("開始執行自動分配")
            
            # 執行分配邏輯
            success = self._perform_allocation()
            
            # 更新執行記錄
            self._update_execution_log(success)
            
            # 更新設定
            self._update_settings(success)
            
            return success
            
        except AutoAllocationSettings.DoesNotExist:
            logger.error("未找到自動分配設定")
            return False
        except Exception as e:
            logger.error(f"自動分配執行異常: {str(e)}")
            if self.log_entry:
                self._update_execution_log(False, str(e))
            return False
        finally:
            # 確保標記為非執行狀態
            if self.settings:
                self.settings.is_running = False
                self.settings.save()
    
    def _perform_allocation(self):
        """
        執行實際的分配邏輯
        
        Returns:
            bool: 是否成功
        """
        try:
            # 獲取需要分配的工單
            workorders_to_allocate = self._get_workorders_needing_allocation()
            
            if not workorders_to_allocate:
                logger.info("沒有需要分配的工單")
                return True
            
            logger.info(f"找到 {len(workorders_to_allocate)} 個需要分配的工單")
            
            successful_allocations = 0
            failed_allocations = 0
            
            for workorder in workorders_to_allocate:
                try:
                    if self._allocate_workorder(workorder):
                        successful_allocations += 1
                    else:
                        failed_allocations += 1
                except Exception as e:
                    logger.error(f"分配工單 {workorder.order_number} 時發生錯誤: {str(e)}")
                    failed_allocations += 1
            
            # 更新執行記錄
            self.log_entry.total_workorders = len(workorders_to_allocate)
            self.log_entry.successful_allocations = successful_allocations
            self.log_entry.failed_allocations = failed_allocations
            
            logger.info(f"自動分配完成: 成功 {successful_allocations}, 失敗 {failed_allocations}")
            
            return successful_allocations > 0 or len(workorders_to_allocate) == 0
            
        except Exception as e:
            logger.error(f"執行分配邏輯時發生錯誤: {str(e)}")
            return False
    
    def _get_workorders_needing_allocation(self):
        """
        獲取需要分配的工單
        
        Returns:
            QuerySet: 需要分配的工單
        """
        # 獲取需要分配的工單（包括沒有工序的工單）
        workorders = WorkOrder.objects.filter(
            status__in=['pending', 'in_progress']
        ).distinct()
        
        return workorders
    
    def _allocate_workorder(self, workorder):
        """
        為單一工單分配作業員和設備
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            bool: 是否分配成功
        """
        try:
            with transaction.atomic():
                # 獲取該工單的所有工序
                processes = WorkOrderProcess.objects.filter(
                    workorder=workorder
                )
                
                if not processes.exists():
                    logger.info(f"工單 {workorder.order_number} 沒有工序記錄，跳過分配")
                    return True  # 沒有工序也算成功
                
                allocated_count = 0
                
                for process in processes:
                    # 分配作業員
                    if not process.assigned_operator and self._allocate_operator(process):
                        allocated_count += 1
                    
                    # 分配設備
                    if not process.assigned_equipment and self._allocate_equipment(process):
                        allocated_count += 1
                
                logger.info(f"工單 {workorder.order_number} 分配完成: {allocated_count} 個工序")
                return True  # 即使沒有分配也算成功
                
        except Exception as e:
            logger.error(f"分配工單 {workorder.order_number} 時發生錯誤: {str(e)}")
            return False
    
    def _allocate_operator(self, process):
        """
        為工序分配作業員
        
        Args:
            process: WorkOrderProcess 實例
            
        Returns:
            bool: 是否分配成功
        """
        try:
            # 這裡可以實現複雜的作業員分配邏輯
            # 目前先使用簡單的邏輯：分配給第一個可用的作業員
            
            # 檢查是否有作業員資料
            from system.models import Operator
            
            available_operators = Operator.objects.filter(
                is_active=True
            ).first()
            
            if available_operators:
                process.assigned_operator = available_operators.name
                process.save()
                logger.info(f"為工序 {process.process_name} 分配作業員: {available_operators.name}")
                return True
            else:
                logger.warning(f"沒有可用的作業員可以分配給工序 {process.process_name}")
                return False
                
        except Exception as e:
            logger.error(f"分配作業員時發生錯誤: {str(e)}")
            return False
    
    def _allocate_equipment(self, process):
        """
        為工序分配設備
        
        Args:
            process: WorkOrderProcess 實例
            
        Returns:
            bool: 是否分配成功
        """
        try:
            # 這裡可以實現複雜的設備分配邏輯
            # 目前先使用簡單的邏輯：分配給第一個可用的設備
            
            # 檢查是否有設備資料
            from equip.models import Equipment
            
            available_equipment = Equipment.objects.filter(
                status='available'
            ).first()
            
            if available_equipment:
                process.assigned_equipment = available_equipment.name
                process.save()
                logger.info(f"為工序 {process.process_name} 分配設備: {available_equipment.name}")
                return True
            else:
                logger.warning(f"沒有可用的設備可以分配給工序 {process.process_name}")
                return False
                
        except Exception as e:
            logger.error(f"分配設備時發生錯誤: {str(e)}")
            return False
    
    def _update_execution_log(self, success, error_message=""):
        """
        更新執行記錄
        
        Args:
            success: 是否成功
            error_message: 錯誤訊息
        """
        if self.log_entry:
            self.log_entry.completed_at = timezone.now()
            self.log_entry.success = success
            self.log_entry.error_message = error_message
            
            if self.log_entry.started_at:
                self.log_entry.execution_time = (
                    self.log_entry.completed_at - self.log_entry.started_at
                )
            
            self.log_entry.save()
    
    def _update_settings(self, success):
        """
        更新設定
        
        Args:
            success: 是否成功
        """
        if self.settings:
            self.settings.last_execution = timezone.now()
            self.settings.total_executions += 1
            
            if success:
                self.settings.success_count += 1
            else:
                self.settings.failure_count += 1
            
            # 計算下次執行時間
            self.settings.next_execution = (
                self.settings.last_execution + 
                timedelta(minutes=self.settings.interval_minutes)
            )
            
            self.settings.save()


# 全域實例
scheduler = AutoAllocationScheduler() 