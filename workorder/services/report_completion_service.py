"""
填報紀錄完工判斷服務
專門處理基於填報數量的工單完工判斷邏輯
"""

from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from ..models import WorkOrder
from ..fill_work.models import FillWork
import logging

logger = logging.getLogger(__name__)


class ReportCompletionService:
    """
    填報紀錄完工判斷服務
    基於填報數量判斷工單是否完工
    """
    
    # 出貨包裝工序名稱（用於完工判斷）
    PACKAGING_PROCESS_NAME = "出貨包裝"
    
    @classmethod
    def check_report_completion(cls, workorder_id):
        """
        檢查填報完工狀態
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 是否完工
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查出貨包裝報工數量是否達到目標
            packaging_quantity = cls._get_packaging_quantity(workorder)
            
            if packaging_quantity >= workorder.quantity:
                logger.info(f"填報完工判斷：工單 {workorder.order_number} 出貨包裝數量已達標 ({packaging_quantity}/{workorder.quantity})")
                return True
            else:
                logger.debug(f"填報完工判斷：工單 {workorder.order_number} 出貨包裝數量未達標 ({packaging_quantity}/{workorder.quantity})")
                return False
                
        except WorkOrder.DoesNotExist:
            logger.error(f"填報完工判斷：工單 {workorder_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"填報完工判斷錯誤：{str(e)}")
            return False
    
    @classmethod
    def _get_packaging_quantity(cls, workorder):
        """
        取得出貨包裝工序的已報工數量
        
        Args:
            workorder: 工單物件
            
        Returns:
            int: 出貨包裝報工數量
        """
        try:
            # 統計出貨包裝工序的已核准報工數量
            packaging_quantity = FillWork.objects.filter(
                workorder=workorder.order_number,
                process__name=cls.PACKAGING_PROCESS_NAME,
                approval_status='approved'
            ).aggregate(
                total_quantity=Sum('work_quantity')
            )['total_quantity'] or 0
            
            return packaging_quantity
            
        except Exception as e:
            logger.error(f"取得出貨包裝數量時發生錯誤：{str(e)}")
            return 0
    
    @classmethod
    def get_report_completion_progress(cls, workorder_id):
        """
        取得填報完工進度
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 進度資訊
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 取得出貨包裝報工數量
            packaging_quantity = cls._get_packaging_quantity(workorder)
            
            # 計算進度百分比
            progress_percentage = (packaging_quantity / workorder.quantity * 100) if workorder.quantity > 0 else 0
            
            # 取得所有工序的報工統計
            all_process_reports = cls._get_all_process_reports(workorder)
            
            return {
                'target_quantity': workorder.quantity,
                'packaging_quantity': packaging_quantity,
                'progress_percentage': round(progress_percentage, 2),
                'is_completed': packaging_quantity >= workorder.quantity,
                'process_reports': all_process_reports
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'target_quantity': 0,
                'packaging_quantity': 0,
                'progress_percentage': 0,
                'is_completed': False,
                'process_reports': {}
            }
    
    @classmethod
    def _get_all_process_reports(cls, workorder):
        """
        取得所有工序的報工統計
        
        Args:
            workorder: 工單物件
            
        Returns:
            dict: 各工序報工統計
        """
        try:
            # 按工序分組統計已核准的報工數量
            process_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            ).values('process__name').annotate(
                total_quantity=Sum('work_quantity')
            )
            
            # 轉換為字典格式
            result = {}
            for report in process_reports:
                process_name = report['process__name']
                quantity = report['total_quantity']
                result[process_name] = quantity
            
            return result
            
        except Exception as e:
            logger.error(f"取得工序報工統計時發生錯誤：{str(e)}")
            return {}
    
    @classmethod
    def check_completion_on_report_approval(cls, report_id):
        """
        當報工記錄被核准時檢查完工狀態
        
        Args:
            report_id: 報工記錄ID
            
        Returns:
            bool: 是否觸發完工
        """
        try:
            report = FillWork.objects.get(id=report_id)
            
            # 只有出貨包裝工序的核准才觸發完工檢查
            if (report.approval_status == 'approved' and 
                report.process.name == cls.PACKAGING_PROCESS_NAME):
                
                logger.info(f"出貨包裝報工核准，檢查工單 {report.workorder} 完工狀態")
                
                # 檢查是否達到完工條件
                # 需要根據工單號碼找到工單ID
                try:
                    workorder = WorkOrder.objects.get(order_number=report.workorder)
                    if cls.check_report_completion(workorder.id):
                        logger.info(f"工單 {report.workorder} 填報完工條件已滿足")
                        return True
                except WorkOrder.DoesNotExist:
                    logger.error(f"找不到工單 {report.workorder}")
                    return False
            
            return False
            
        except FillWork.DoesNotExist:
            logger.error(f"報工記錄 {report_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"檢查報工核准完工狀態時發生錯誤：{str(e)}")
            return False
    
    @classmethod
    def get_completion_summary(cls, workorder_id):
        """
        取得完工摘要資訊
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工摘要
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 取得各工序報工統計
            process_reports = cls._get_all_process_reports(workorder)
            
            # 計算總報工數量
            total_reported = sum(process_reports.values())
            
            # 計算出貨包裝數量
            packaging_quantity = process_reports.get(cls.PACKAGING_PROCESS_NAME, 0)
            
            return {
                'workorder_number': workorder.order_number,
                'target_quantity': workorder.quantity,
                'total_reported': total_reported,
                'packaging_quantity': packaging_quantity,
                'process_breakdown': process_reports,
                'completion_status': {
                    'process_completed': packaging_quantity >= workorder.quantity,
                    'progress_percentage': round((packaging_quantity / workorder.quantity * 100), 2) if workorder.quantity > 0 else 0
                }
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'workorder_number': None,
                'target_quantity': 0,
                'total_reported': 0,
                'packaging_quantity': 0,
                'process_breakdown': {},
                'completion_status': {
                    'process_completed': False,
                    'progress_percentage': 0
                }
            } 