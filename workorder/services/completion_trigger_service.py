"""
工單完工觸發服務
實現雙重累加機制：工序記錄累加 + 填報記錄累加
當任一達到目標數量時，立即觸發完工轉移
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from ..models import WorkOrder, CompletedWorkOrder, WorkOrderProductionDetail
from ..fill_work.models import FillWork
from .completion_service import FillWorkCompletionService

logger = logging.getLogger(__name__)


class WorkOrderCompletionTrigger:
    """
    工單完工觸發器
    當工序記錄或填報記錄累加達到目標數量時，自動觸發完工
    """
    
    def __init__(self, workorder):
        self.workorder = workorder
        self.target_quantity = workorder.quantity
    
    def check_completion_trigger(self):
        """
        檢查是否觸發完工條件
        
        Returns:
            bool: 是否觸發完工
        """
        try:
            # 檢查工單是否已經完工
            if self.workorder.status == 'completed':
                logger.debug(f"工單 {self.workorder.order_number} 已經完工，跳過檢查")
                return False
            
            # 檢查是否已經轉移過
            if CompletedWorkOrder.objects.filter(original_workorder_id=self.workorder.id).exists():
                logger.debug(f"工單 {self.workorder.order_number} 已經轉移過，跳過檢查")
                return False
            
            # 1. 檢查工序記錄累加
            process_quantity = self._get_process_accumulation()
            
            # 2. 檢查填報記錄累加
            report_quantity = self._get_report_accumulation()
            
            # 3. 任一達到目標就觸發完工
            if process_quantity >= self.target_quantity or report_quantity >= self.target_quantity:
                logger.info(f"工單 {self.workorder.order_number} 數量達標：工序={process_quantity}, 填報={report_quantity}, 目標={self.target_quantity}")
                return self._trigger_completion(process_quantity, report_quantity)
            
            logger.debug(f"工單 {self.workorder.order_number} 數量未達標：工序={process_quantity}, 填報={report_quantity}, 目標={self.target_quantity}")
            return False
            
        except Exception as e:
            logger.error(f"檢查工單 {self.workorder.order_number} 完工觸發時發生錯誤：{str(e)}")
            return False
    
    def _get_process_accumulation(self):
        """從工序記錄累加數量"""
        try:
            packaging_reports = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=self.workorder,
                process_name="出貨包裝"
            )
            
            # 計算良品數量
            good_quantity = packaging_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            # 計算不良品數量
            defect_quantity = packaging_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 總數量 = 良品 + 不良品
            total_quantity = good_quantity + defect_quantity
            
            logger.info(f"工單 {self.workorder.order_number} 工序記錄出貨包裝累計: 良品={good_quantity}, 不良品={defect_quantity}, 總計={total_quantity}")
            
            return total_quantity
        except Exception as e:
            logger.error(f"獲取工序累加數量失敗：{str(e)}")
            return 0
    
    def _get_report_accumulation(self):
        """從填報記錄累加數量"""
        try:
            return FillWork.objects.filter(
                workorder=self.workorder.order_number,
                process__name__icontains="出貨包裝",
                approval_status="approved"
            ).aggregate(total=Sum('work_quantity'))['total'] or 0
        except Exception as e:
            logger.error(f"獲取填報累加數量失敗：{str(e)}")
            return 0
    
    def _trigger_completion(self, process_quantity, report_quantity):
        """
        觸發完工流程
        
        Args:
            process_quantity: 工序累加數量
            report_quantity: 填報累加數量
            
        Returns:
            bool: 是否成功觸發完工
        """
        try:
            with transaction.atomic():
                # 1. 更新工單狀態
                self.workorder.status = 'completed'
                self.workorder.completed_at = timezone.now()
                self.workorder.save()
                
                # 2. 立即執行轉移
                completed_workorder = FillWorkCompletionService.transfer_workorder_to_completed(self.workorder.id)
                
                # 3. 記錄觸發日誌
                trigger_source = "工序記錄" if process_quantity >= self.target_quantity else "填報記錄"
                logger.info(f"工單 {self.workorder.order_number} 通過{trigger_source}觸發完工轉移成功")
                
                return True
                
        except Exception as e:
            logger.error(f"觸發完工失敗：{str(e)}")
            return False


class CompletionTriggerService:
    """
    完工觸發服務
    提供靜態方法用於外部調用
    """
    
    @staticmethod
    def check_workorder_completion(workorder_id):
        """
        檢查工單完工觸發
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 是否觸發完工
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            trigger = WorkOrderCompletionTrigger(workorder)
            return trigger.check_completion_trigger()
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"檢查工單 {workorder_id} 完工觸發失敗：{str(e)}")
            return False
    
    @staticmethod
    def check_all_pending_workorders():
        """
        檢查所有待完工工單的觸發條件
        
        Returns:
            dict: 檢查結果統計
        """
        try:
            pending_workorders = WorkOrder.objects.filter(
                status__in=['pending', 'in_progress', 'paused']
            )
            
            triggered_count = 0
            checked_count = 0
            
            for workorder in pending_workorders:
                try:
                    checked_count += 1
                    trigger = WorkOrderCompletionTrigger(workorder)
                    if trigger.check_completion_trigger():
                        triggered_count += 1
                except Exception as e:
                    logger.error(f"檢查工單 {workorder.order_number} 時發生錯誤：{str(e)}")
            
            logger.info(f"完工觸發檢查完成：檢查 {checked_count} 個工單，觸發 {triggered_count} 個完工")
            
            return {
                'checked_count': checked_count,
                'triggered_count': triggered_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"批量檢查完工觸發失敗：{str(e)}")
            return {
                'checked_count': 0,
                'triggered_count': 0,
                'success': False,
                'error': str(e)
            } 