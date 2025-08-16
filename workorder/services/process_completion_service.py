"""
工序紀錄完工判斷服務
專門處理基於工序進度的工單完工判斷邏輯
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import WorkOrder, WorkOrderProcess
from ..fill_work.models import FillWork
import logging

logger = logging.getLogger(__name__)


class ProcessCompletionService:
    """
    工序紀錄完工判斷服務
    基於工序進度判斷工單是否完工
    """
    
    @classmethod
    def check_process_completion(cls, workorder_id):
        """
        檢查工序完工狀態
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 是否完工
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查所有工序是否都已完成
            all_processes_completed = cls._check_all_processes_completed(workorder)
            
            if all_processes_completed:
                logger.info(f"工序完工判斷：工單 {workorder.order_number} 所有工序已完成")
                return True
            else:
                logger.debug(f"工序完工判斷：工單 {workorder.order_number} 尚有未完成工序")
                return False
                
        except WorkOrder.DoesNotExist:
            logger.error(f"工序完工判斷：工單 {workorder_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"工序完工判斷錯誤：{str(e)}")
            return False
    
    @classmethod
    def _check_all_processes_completed(cls, workorder):
        """
        檢查工單的所有工序是否都已完成
        
        Args:
            workorder: 工單物件
            
        Returns:
            bool: 所有工序是否完成
        """
        # 取得工單的所有工序
        processes = WorkOrderProcess.objects.filter(workorder=workorder)
        
        if not processes.exists():
            logger.warning(f"工單 {workorder.order_number} 沒有任何工序")
            return False
        
        # 檢查每個工序的狀態
        for process in processes:
            if process.status != 'completed':
                logger.debug(f"工序 {process.process_name} 尚未完成，狀態：{process.status}")
                return False
        
        logger.info(f"工單 {workorder.order_number} 所有工序已完成")
        return True
    
    @classmethod
    def get_process_completion_progress(cls, workorder_id):
        """
        取得工序完工進度
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 進度資訊
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            processes = WorkOrderProcess.objects.filter(workorder=workorder)
            
            total_processes = processes.count()
            completed_processes = processes.filter(status='completed').count()
            
            progress_percentage = (completed_processes / total_processes * 100) if total_processes > 0 else 0
            
            return {
                'total_processes': total_processes,
                'completed_processes': completed_processes,
                'progress_percentage': round(progress_percentage, 2),
                'is_completed': completed_processes == total_processes
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'total_processes': 0,
                'completed_processes': 0,
                'progress_percentage': 0,
                'is_completed': False
            }
    
    @classmethod
    def mark_process_completed(cls, workorder_id, process_name):
        """
        標記特定工序為已完成
        
        Args:
            workorder_id: 工單ID
            process_name: 工序名稱
            
        Returns:
            bool: 是否成功標記
        """
        try:
            with transaction.atomic():
                process = WorkOrderProcess.objects.get(
                    workorder_id=workorder_id,
                    process_name=process_name
                )
                
                process.status = 'completed'
                process.completed_at = timezone.now()
                process.save()
                
                logger.info(f"工序 {process_name} 已標記為完成，工單：{process.workorder.order_number}")
                
                # 檢查是否所有工序都完成
                if cls.check_process_completion(workorder_id):
                    logger.info(f"工單 {process.workorder.order_number} 所有工序已完成，觸發完工流程")
                    # 這裡可以觸發完工流程
                
                return True
                
        except WorkOrderProcess.DoesNotExist:
            logger.error(f"工序 {process_name} 不存在於工單 {workorder_id}")
            return False
        except Exception as e:
            logger.error(f"標記工序完成時發生錯誤：{str(e)}")
            return False 