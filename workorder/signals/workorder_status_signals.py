"""
工單狀態自動更新信號處理器
當有工序記錄或填報記錄新增/更新時，自動更新工單狀態
當填報記錄取消核准時，自動將工單狀態轉回待生產
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import WorkOrderProductionDetail
from ..fill_work.models import FillWork
from ..services.workorder_status_service import WorkOrderStatusService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WorkOrderProductionDetail)
def update_workorder_status_on_process_save(sender, instance, created, **kwargs):
    """
    當工序記錄保存時更新工單狀態
    
    Args:
        sender: 發送者模型
        instance: 保存的實例
        created: 是否為新建記錄
        **kwargs: 其他參數
    """
    try:
        workorder = instance.workorder_production.workorder
        logger.info(f"工序記錄觸發工單狀態更新：工單 {workorder.order_number}")
        
        # 更新工單狀態
        updated = WorkOrderStatusService.update_workorder_status(workorder.id)
        
        if updated:
            logger.info(f"工單 {workorder.order_number} 狀態更新成功")
        else:
            logger.warning(f"工單 {workorder.order_number} 狀態更新失敗")
            
    except Exception as e:
        logger.error(f"工序記錄觸發工單狀態更新失敗：{str(e)}")


@receiver(post_save, sender=FillWork)
def update_workorder_status_on_report_approval(sender, instance, created, **kwargs):
    """
    當填報記錄核准狀態變更時更新工單狀態
    
    Args:
        sender: 發送者模型
        instance: 保存的實例
        created: 是否為新建記錄
        **kwargs: 其他參數
    """
    try:
        logger.info(f"填報記錄觸發工單狀態更新：工單 {instance.workorder}，核准狀態：{instance.approval_status}")
        
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
            # 根據多公司架構，需要同時檢查公司代號、工單號碼和產品編號
            workorder = WorkOrder.objects.filter(
                company_code=company_code,
                order_number=instance.workorder,
                product_code=instance.product_id
            ).first()
            
            if workorder:
                # 更新工單狀態
                updated = WorkOrderStatusService.update_workorder_status(workorder.id)
                
                if updated:
                    logger.info(f"工單 {workorder.order_number} 狀態更新成功")
                else:
                    logger.warning(f"工單 {workorder.order_number} 狀態更新失敗")
            else:
                logger.warning(f"找不到對應的工單：{instance.workorder}")
        else:
            logger.warning(f"找不到對應的公司代號：{instance.company_name}")
                
    except Exception as e:
        logger.error(f"填報記錄觸發工單狀態更新失敗：{str(e)}")


def register_workorder_status_signals():
    """
    註冊工單狀態信號
    在應用程式啟動時調用
    """
    logger.info("註冊工單狀態信號處理器")
    
    # 信號已經通過裝飾器自動註冊
    # 這裡可以添加其他初始化邏輯 