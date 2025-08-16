"""
完工觸發信號處理器
實現即時觸發機制：當工序記錄或填報記錄新增/更新時，立即檢查完工條件
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import WorkOrderProductionDetail
from ..fill_work.models import FillWork
from ..services.completion_trigger_service import CompletionTriggerService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WorkOrderProductionDetail)
def trigger_completion_on_process_save(sender, instance, created, **kwargs):
    """
    當工序記錄保存時觸發完工檢查
    
    Args:
        sender: 發送者模型
        instance: 保存的實例
        created: 是否為新建記錄
        **kwargs: 其他參數
    """
    try:
        # 只檢查出貨包裝工序
        if instance.process_name == "出貨包裝":
            workorder = instance.workorder_production.workorder
            logger.info(f"工序記錄觸發完工檢查：工單 {workorder.order_number}, 數量 {instance.work_quantity}")
            
            # 檢查完工觸發
            triggered = CompletionTriggerService.check_workorder_completion(workorder.id)
            
            if triggered:
                logger.info(f"工序記錄觸發完工成功：工單 {workorder.order_number}")
            else:
                logger.debug(f"工序記錄觸發完工檢查：工單 {workorder.order_number} 未達完工條件")
                
    except Exception as e:
        logger.error(f"工序記錄觸發完工檢查失敗：{str(e)}")


@receiver(post_save, sender=FillWork)
def trigger_completion_on_report_approval(sender, instance, created, **kwargs):
    """
    當填報記錄核准時觸發完工檢查
    
    Args:
        sender: 發送者模型
        instance: 保存的實例
        created: 是否為新建記錄
        **kwargs: 其他參數
    """
    try:
        # 只檢查已核准的出貨包裝填報記錄
        if (instance.approval_status == "approved" and 
            "出貨包裝" in instance.process.name):
            
            logger.info(f"填報記錄觸發完工檢查：工單 {instance.workorder}, 數量 {instance.work_quantity}")
            
            # 查找對應的工單
            from ..models import WorkOrder
            from erp_integration.models import CompanyConfig
            
            # 從公司名稱找到公司代號
            company_code = None
            try:
                company_config = CompanyConfig.objects.filter(
                    company_name=instance.company_name
                ).first()
                if company_config:
                    company_code = company_config.company_code
            except Exception:
                pass
            
            if company_code:
                workorder = WorkOrder.objects.filter(
                    company_code=company_code,
                    order_number=instance.workorder
                ).first()
                
                if workorder:
                    # 檢查完工觸發
                    triggered = CompletionTriggerService.check_workorder_completion(workorder.id)
                    
                    if triggered:
                        logger.info(f"填報記錄觸發完工成功：工單 {workorder.order_number}")
                    else:
                        logger.debug(f"填報記錄觸發完工檢查：工單 {workorder.order_number} 未達完工條件")
                else:
                    logger.warning(f"找不到對應的工單：{instance.workorder}")
            else:
                logger.warning(f"找不到對應的公司代號：{instance.company_name}")
                
    except Exception as e:
        logger.error(f"填報記錄觸發完工檢查失敗：{str(e)}")


def register_completion_trigger_signals():
    """
    註冊完工觸發信號
    在應用程式啟動時調用
    """
    logger.info("註冊完工觸發信號處理器")
    
    # 信號已經通過裝飾器自動註冊
    # 這裡可以添加其他初始化邏輯 