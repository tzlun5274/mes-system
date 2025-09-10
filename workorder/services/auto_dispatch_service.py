# 自動批次派工服務
# 功能：統一的自動批次派工邏輯，供手動和定時任務共用
# 作者：MES 系統
# 建立時間：2025年

from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch
import logging

logger = logging.getLogger("workorder")


class AutoDispatchService:
    """
    自動批次派工服務類
    統一處理手動和定時任務的批次派工邏輯
    """
    
    @staticmethod
    def execute_auto_dispatch(created_by="system", user_ip=None):
        """
        執行自動批次派工
        
        Args:
            created_by (str): 建立者，手動執行時為使用者名稱，定時任務時為 "system"
            user_ip (str): 使用者 IP，僅手動執行時提供
            
        Returns:
            dict: 執行結果
        """
        try:
            with transaction.atomic():
                # 取得所有未派工的工單
                undispatched_orders = WorkOrder.objects.all()
                
                # 檢查每個工單是否已有對應的派工單（使用 order_number + product_code 組合）
                truly_undispatched = []
                for wo in undispatched_orders:
                    dispatch_exists = WorkOrderDispatch.objects.filter(
                        order_number=wo.order_number,
                        product_code=wo.product_code
                    ).exists()
                    if not dispatch_exists:
                        truly_undispatched.append(wo)
                
                created = 0
                for wo in truly_undispatched:
                    # 建立派工單，直接設定為生產中狀態
                    dispatch = WorkOrderDispatch.objects.create(
                        company_code=getattr(wo, "company_code", None),
                        order_number=wo.order_number,
                        product_code=wo.product_code,
                        planned_quantity=wo.quantity,
                        status="in_production",  # 直接設定為生產中
                        dispatch_date=timezone.now().date(),  # 設定派工日期為今天
                        created_by=created_by,
                    )
                    created += 1
                    
                    # 記錄操作日誌
                    if created_by == "system":
                        logger.info(f"定時任務：自動批次派工 - 工單 {wo.order_number} 轉派為生產中狀態")
                    else:
                        logger.info(f"手動執行：自動批次派工 - 工單 {wo.order_number} 轉派為生產中狀態。操作者: {created_by}, IP: {user_ip}")
                
                success_message = f"自動批次派工完成，共建立 {created} 筆派工單"
                logger.info(success_message)
                
                return {
                    'success': True,
                    'message': success_message,
                    'created_count': created
                }
                
        except Exception as e:
            error_message = f"自動批次派工失敗：{str(e)}"
            logger.error(error_message)
            return {
                'success': False,
                'error': error_message
            }
