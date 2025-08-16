"""
工單狀態自動更新服務
當有工序記錄或填報核准記錄時，自動將工單狀態更新為生產中
當所有填報記錄都取消核准時，自動將工單狀態轉回待生產
"""

import logging
from django.db import transaction
from django.utils import timezone
from ..models import WorkOrder, WorkOrderProductionDetail
from ..fill_work.models import FillWork
from erp_integration.models import CompanyConfig

logger = logging.getLogger(__name__)


class WorkOrderStatusService:
    """
    工單狀態管理服務
    自動管理工單狀態的轉換
    """
    
    @staticmethod
    def update_workorder_status(workorder_id):
        """
        更新工單狀態
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 是否成功更新狀態
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查當前狀態
            if workorder.status == 'completed':
                logger.debug(f"工單 {workorder.order_number} 已完工，跳過狀態更新")
                return True
            
            # 檢查是否有生產活動
            has_production_activity = WorkOrderStatusService._check_production_activity(workorder)
            
            with transaction.atomic():
                if has_production_activity and workorder.status == 'pending':
                    # 更新為生產中狀態
                    workorder.status = 'in_progress'
                    workorder.updated_at = timezone.now()
                    workorder.save()
                    
                    logger.info(f"工單 {workorder.order_number} 狀態更新：pending → in_progress")
                    return True
                elif not has_production_activity and workorder.status == 'in_progress':
                    # 沒有生產活動但狀態為生產中，轉回待生產
                    workorder.status = 'pending'
                    workorder.updated_at = timezone.now()
                    workorder.save()
                    
                    logger.info(f"工單 {workorder.order_number} 狀態更新：in_progress → pending")
                    return True
            
            return True
            
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"更新工單 {workorder_id} 狀態失敗：{str(e)}")
            return False
    
    @staticmethod
    def _check_production_activity(workorder):
        """
        檢查工單是否有生產活動
        
        Args:
            workorder: 工單物件
            
        Returns:
            bool: 是否有生產活動
        """
        try:
            # 1. 檢查工序記錄
            has_process_records = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=workorder
            ).exists()
            
            if has_process_records:
                logger.debug(f"工單 {workorder.order_number} 有工序記錄")
                return True
            
            # 2. 檢查填報核准記錄
            has_approved_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            ).exists()
            
            if has_approved_reports:
                logger.debug(f"工單 {workorder.order_number} 有已核准填報記錄")
                return True
            
            # 3. 檢查是否有生產記錄
            has_production_record = hasattr(workorder, 'production_record') and workorder.production_record is not None
            
            if has_production_record:
                logger.debug(f"工單 {workorder.order_number} 有生產記錄")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"檢查工單 {workorder.order_number} 生產活動失敗：{str(e)}")
            return False
    
    @staticmethod
    def update_all_pending_workorders():
        """
        更新所有待生產工單的狀態
        
        Returns:
            dict: 更新結果統計
        """
        try:
            pending_workorders = WorkOrder.objects.filter(status='pending')
            
            updated_count = 0
            total_count = 0
            
            for workorder in pending_workorders:
                total_count += 1
                try:
                    if WorkOrderStatusService.update_workorder_status(workorder.id):
                        if workorder.status == 'in_progress':
                            updated_count += 1
                except Exception as e:
                    logger.error(f"更新工單 {workorder.order_number} 狀態失敗：{str(e)}")
            
            logger.info(f"批量更新工單狀態完成：檢查 {total_count} 個工單，更新 {updated_count} 個為生產中")
            
            return {
                'total_count': total_count,
                'updated_count': updated_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"批量更新工單狀態失敗：{str(e)}")
            return {
                'total_count': 0,
                'updated_count': 0,
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_all_in_progress_workorders():
        """
        更新所有生產中工單的狀態
        檢查是否有工單需要轉回待生產
        
        Returns:
            dict: 更新結果統計
        """
        try:
            in_progress_workorders = WorkOrder.objects.filter(status='in_progress')
            
            updated_count = 0
            total_count = 0
            
            for workorder in in_progress_workorders:
                total_count += 1
                try:
                    if WorkOrderStatusService.update_workorder_status(workorder.id):
                        if workorder.status == 'pending':
                            updated_count += 1
                except Exception as e:
                    logger.error(f"更新工單 {workorder.order_number} 狀態失敗：{str(e)}")
            
            logger.info(f"批量更新生產中工單狀態完成：檢查 {total_count} 個工單，更新 {updated_count} 個為待生產")
            
            return {
                'total_count': total_count,
                'updated_count': updated_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"批量更新生產中工單狀態失敗：{str(e)}")
            return {
                'total_count': 0,
                'updated_count': 0,
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_workorder_status_summary(workorder_id):
        """
        取得工單狀態摘要
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 狀態摘要
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查各種生產活動
            process_records_count = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=workorder
            ).count()
            
            approved_reports_count = FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            ).count()
            
            has_production_record = hasattr(workorder, 'production_record') and workorder.production_record is not None
            
            return {
                'workorder_number': workorder.order_number,
                'current_status': workorder.status,
                'planned_quantity': workorder.quantity,
                'completed_quantity': workorder.completed_quantity,
                'process_records_count': process_records_count,
                'approved_reports_count': approved_reports_count,
                'has_production_record': has_production_record,
                'should_be_in_progress': process_records_count > 0 or approved_reports_count > 0 or has_production_record
            }
            
        except WorkOrder.DoesNotExist:
            return {'error': '工單不存在'}
        except Exception as e:
            return {'error': str(e)} 