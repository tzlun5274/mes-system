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
            from workorder.services.dispatch_statistics_service import DispatchStatisticsService
            DispatchStatisticsService.update_dispatch_statistics(dispatch)
            logger.info(f"已更新派工單統計資料: {dispatch.order_number}")
            
            # 如果是出貨包裝工序且已核准，特別記錄完工狀態更新
            if (instance.operation == '出貨包裝' and 
                instance.approval_status == 'approved'):
                logger.info(f"出貨包裝填報記錄已核准，派工單完工狀態: 可以完工={dispatch.can_complete}, 閾值達成={dispatch.completion_threshold_met}")
                
                # 如果達到完工條件，觸發自動完工檢查
                if dispatch.can_complete:
                    logger.info(f"派工單 {dispatch.order_number} 達到完工條件，觸發自動完工檢查")
                    try:
                        from workorder.services.completion_service import FillWorkCompletionService
                        from workorder.models import WorkOrder
                        
                        # 查找對應的工單
                        workorder = WorkOrder.objects.get(
                            order_number=dispatch.order_number,
                            product_code=dispatch.product_code,
                            company_code=dispatch.company_code
                        )
                        
                        # 執行自動完工
                        result = FillWorkCompletionService.auto_complete_workorder(workorder.id)
                        if result.get('success'):
                            logger.info(f"工單 {workorder.order_number} 自動完工成功")
                        else:
                            logger.warning(f"工單 {workorder.order_number} 自動完工失敗: {result.get('message', '未知錯誤')}")
                            
                    except Exception as e:
                        logger.error(f"觸發自動完工失敗: {str(e)}")
        else:
            logger.warning(f"找不到對應的派工單：{instance.workorder} - {instance.product_id}")
            
    except Exception as e:
        logger.error(f"更新派工單統計資料失敗：{str(e)}")
    
    # 檢查是否為出貨包裝工序且已核准，觸發智能自動完工
    if (instance.approval_status == 'approved' and 
        instance.operation == "出貨包裝"):
        
        # 檢查智能自動完工功能是否啟用
        try:
            from workorder.models import SystemConfig
            auto_completion_config = SystemConfig.objects.filter(key="auto_completion_enabled").first()
            auto_completion_enabled = auto_completion_config and auto_completion_config.value == "True"
            
            if not auto_completion_enabled:
                logger.debug("智能自動完工功能未啟用，跳過自動完工檢查")
                return
                
        except Exception as e:
            logger.error(f"檢查智能自動完工設定失敗：{str(e)}")
            return
        
        logger.info(f"出貨包裝填報記錄已核准，觸發智能自動完工檢查：{instance.workorder}")
        
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
                # 觸發智能自動完工檢查
                from workorder.services.completion_service import FillWorkCompletionService
                result = FillWorkCompletionService.auto_check_completion_on_fillwork_submit(instance)
                
                if result.get('success') and result.get('is_completed'):
                    logger.info(f"工單 {workorder.order_number} 智能自動完工成功")
                else:
                    logger.debug(f"工單 {workorder.order_number} 尚未達到完工條件：{result.get('message', '')}")
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
    if instance.process_name and not instance.operation:
        instance.operation = instance.process_name 