"""
資料轉移觸發信號處理器
當工單狀態變為「已完工」時，自動觸發資料轉移功能
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from ..models import WorkOrder

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WorkOrder)
def trigger_data_transfer_on_completion(sender, instance, created, **kwargs):
    """
    當工單狀態變為「已完工」時，自動觸發資料轉移功能
    
    Args:
        sender: 發送者模型 (WorkOrder)
        instance: 保存的工單實例
        created: 是否為新建記錄
        **kwargs: 其他參數
    """
    try:
        # 只處理狀態變更，不處理新建記錄
        if created:
            return
            
        # 檢查工單狀態是否為「已完工」
        if instance.status == 'completed':
            logger.info(f"工單 {instance.order_number} 狀態變為已完工，觸發資料轉移檢查")
            
            # 檢查智能自動完工功能是否啟用（資料轉移使用同一個開關）
            try:
                from ..models import SystemConfig
                auto_completion_config = SystemConfig.objects.get(key="auto_completion_enabled")
                transfer_enabled = auto_completion_config.value.lower() == 'true'
            except SystemConfig.DoesNotExist:
                transfer_enabled = True  # 預設啟用
                logger.info("未找到智能自動完工啟用設定，使用預設值啟用")
            
            if not transfer_enabled:
                logger.info("資料轉移功能已停用，跳過自動轉移")
                return
            
            # 檢查是否已經轉移過
            from ..models import CompletedWorkOrder
            existing_completed = CompletedWorkOrder.objects.filter(
                original_workorder_id=instance.id
            ).first()
            
            if existing_completed:
                logger.info(f"工單 {instance.order_number} 已經轉移過，跳過重複轉移")
                return
            
            # 延遲執行資料轉移，避免在信號處理中執行複雜操作
            from ..tasks import auto_data_transfer_task
            auto_data_transfer_task.delay()
            
            logger.info(f"工單 {instance.order_number} 已觸發資料轉移任務")
            
    except Exception as e:
        logger.error(f"觸發資料轉移失敗：{str(e)}")


def register_data_transfer_signals():
    """
    註冊資料轉移信號
    在應用程式啟動時調用
    """
    logger.info("註冊資料轉移信號處理器")
    
    # 信號已經通過裝飾器自動註冊
    # 這裡可以添加其他初始化邏輯
