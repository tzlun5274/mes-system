"""
填報作業管理子模組 - 信號處理
負責填報作業的信號處理邏輯
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import FillWork
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FillWork)
def fill_work_post_save(sender, instance, created, **kwargs):
    """
    填報作業儲存後的信號處理
    注意：工單狀態更新邏輯已移至 workorder/signals/workorder_status_signals.py
    避免重複處理
    """
    if created:
        # 新增填報作業時的處理
        logger.info(f"新增填報作業: {instance.operator} - {instance.workorder}")
    else:
        # 更新填報作業時的處理
        logger.info(f"更新填報作業: {instance.operator} - {instance.workorder}")
    
    # 自動更新派工單統計資料
    try:
        from workorder.workorder_dispatch.models import WorkOrderDispatch
        from erp_integration.models import CompanyConfig
        
        # 從公司名稱找到公司代號
        company_code = None
        if instance.company_name:
            company_config = CompanyConfig.objects.filter(
                company_name=instance.company_name
            ).first()
            if company_config:
                company_code = company_config.company_code
        
        # 查找對應的派工單
        dispatch = None
        if company_code:
            dispatch = WorkOrderDispatch.objects.filter(
                company_code=company_code,
                order_number=instance.workorder,
                product_code=instance.product_id
            ).first()
        else:
            # 如果沒有公司代號，嘗試直接查找
            dispatch = WorkOrderDispatch.objects.filter(
                order_number=instance.workorder,
                product_code=instance.product_id
            ).first()
        
        if dispatch:
            # 更新派工單統計資料
            dispatch.update_all_statistics()
            logger.info(f"已更新派工單統計資料: {dispatch.order_number}")
        else:
            logger.warning(f"找不到對應的派工單：{instance.workorder} - {instance.product_id}")
            
    except Exception as e:
        logger.error(f"更新派工單統計資料失敗：{str(e)}")
    
    # 檢查是否為出貨包裝工序且已核准，觸發完工判斷
    if (instance.approval_status == 'approved' and 
        instance.process and 
        instance.process.name == "出貨包裝"):
        
        logger.info(f"出貨包裝填報記錄已核准，觸發完工判斷檢查：{instance.workorder}")
        
        try:
            # 查找對應的工單
            from workorder.models import WorkOrder
            from erp_integration.models import CompanyConfig
            
            # 從公司名稱找到公司代號
            company_code = None
            if instance.company_name:
                company_config = CompanyConfig.objects.filter(
                    company_name=instance.company_name
                ).first()
                if company_config:
                    company_code = company_config.company_code
            
            # 查找工單
            workorder = None
            if company_code:
                workorder = WorkOrder.objects.filter(
                    company_code=company_code,
                    order_number=instance.workorder,
                    product_code=instance.product_id
                ).first()
            else:
                # 如果沒有公司代號，嘗試直接查找
                workorder = WorkOrder.objects.filter(
                    order_number=instance.workorder,
                    product_code=instance.product_id
                ).first()
            
            if workorder:
                # 觸發完工判斷
                from workorder.services.completion_service import FillWorkCompletionService
                success = FillWorkCompletionService.check_and_complete_workorder(workorder.id)
                
                if success:
                    logger.info(f"工單 {workorder.order_number} 完工判斷成功，已標記為完工")
                else:
                    logger.debug(f"工單 {workorder.order_number} 尚未達到完工條件")
            else:
                logger.warning(f"找不到對應的工單：{instance.workorder} - {instance.product_id}")
                
        except Exception as e:
            logger.error(f"觸發完工判斷失敗：{str(e)}")


@receiver(pre_save, sender=FillWork)
def fill_work_pre_save(sender, instance, **kwargs):
    """
    填報作業儲存前的信號處理
    """
    # 自動設定工序名稱
    if instance.process and not instance.operation:
        instance.operation = instance.process.name 