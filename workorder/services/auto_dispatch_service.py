# 自動批次派工服務
# 功能: 統一的自動批次派工邏輯，供手動和定時任務共用
# 作者: MES 系統
# 建立時間: 2025年

from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch
import logging

logger = logging.getLogger("workorder")


class DispatchCoreService:
    """
    派工核心服務類
    統一的派工邏輯，供所有派工功能調用
    """
    
    @staticmethod
    def dispatch_single_workorder(workorder_id, created_by="system", user_ip=None):
        """
        單筆派工核心邏輯
        
        Args:
            workorder_id (int): 工單ID
            created_by (str): 建立者
            user_ip (str): 使用者 IP
            
        Returns:
            dict: 執行結果
        """
        try:
            with transaction.atomic():
                # 查詢工單
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                # 檢查是否已有派工單（使用完整的唯一識別）
                existing_dispatch = WorkOrderDispatch.objects.filter(
                    company_code=workorder.company_code,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code
                ).first()
                
                if existing_dispatch:
                    return {
                        'success': False,
                        'error': f'工單 {workorder.order_number} 已有派工單',
                        'dispatch_id': existing_dispatch.id
                    }
                
                # 建立派工單
                dispatch = WorkOrderDispatch.objects.create(
                    company_code=workorder.company_code,
                    company_name=getattr(workorder, "company_name", None),
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    product_name=workorder.product_code,  # WorkOrder 沒有 product_name，使用 product_code
                    planned_quantity=workorder.quantity,
                    status="in_production",
                    dispatch_date=timezone.now().date(),
                    created_by=created_by,
                )
                
                # 記錄日誌
                logger.info(f'單筆派工: 工單 {workorder.order_number} 轉派為生產中狀態。操作者: {created_by}, IP: {user_ip}')
                
                return {
                    'success': True,
                    'message': f'派工單建立成功，已設定為生產中狀態',
                    'dispatch_id': dispatch.id,
                    'workorder': {
                        'id': workorder.id,
                        'company_code': workorder.company_code,
                        'company_name': getattr(workorder, "company_name", None),
                        'order_number': workorder.order_number,
                        'product_code': workorder.product_code,
                        'product_name': workorder.product_code,
                        'quantity': workorder.quantity
                    }
                }
                
        except WorkOrder.DoesNotExist:
            return {
                'success': False,
                'error': '工單不存在'
            }
        except Exception as e:
            logger.error(f'單筆派工失敗: {str(e)}')
            return {
                'success': False,
                'error': f'派工失敗: {str(e)}'
            }
    
    @staticmethod
    def dispatch_workorders_by_numbers(order_numbers, created_by="system", user_ip=None):
        """
        批量派工核心邏輯
        
        Args:
            order_numbers (list): 工單號碼列表
            created_by (str): 建立者
            user_ip (str): 使用者 IP
            
        Returns:
            dict: 執行結果
        """
        try:
            with transaction.atomic():
                created = 0
                skipped = 0
                failed = 0
                
                for order_number in order_numbers:
                    # 查詢所有匹配的工單
                    workorders = WorkOrder.objects.filter(order_number=order_number)
                    
                    for workorder in workorders:
                        # 檢查是否已有派工單
                        existing_dispatch = WorkOrderDispatch.objects.filter(
                            company_code=workorder.company_code,
                            order_number=workorder.order_number,
                            product_code=workorder.product_code
                        ).first()
                        
                        if existing_dispatch:
                            skipped += 1
                            continue
                        
                        # 建立派工單
                        dispatch = WorkOrderDispatch.objects.create(
                            company_code=workorder.company_code,
                            company_name=getattr(workorder, "company_name", None),
                            order_number=workorder.order_number,
                            product_code=workorder.product_code,
                            product_name=workorder.product_code,  # WorkOrder 沒有 product_name，使用 product_code
                            planned_quantity=workorder.quantity,
                            status="in_production",
                            dispatch_date=timezone.now().date(),
                            created_by=created_by,
                        )
                        created += 1
                
                # 記錄日誌
                logger.info(f'批量派工: 共建立 {created} 筆派工單，跳過 {skipped} 筆。操作者: {created_by}, IP: {user_ip}')
                
                return {
                    'success': True,
                    'message': f'批量派工完成，共建立 {created} 筆派工單，跳過 {skipped} 筆',
                    'created_count': created,
                    'skipped_count': skipped,
                    'failed_count': failed
                }
                
        except Exception as e:
            logger.error(f'批量派工失敗: {str(e)}')
            return {
                'success': False,
                'error': f'批量派工失敗: {str(e)}'
            }
    
    @staticmethod
    def dispatch_workorders_by_ids(workorder_ids, created_by="system", user_ip=None):
        """
        批量派工核心邏輯（使用工單ID）
        
        Args:
            workorder_ids (list): 工單ID列表
            created_by (str): 建立者
            user_ip (str): 使用者 IP
            
        Returns:
            dict: 執行結果
        """
        try:
            with transaction.atomic():
                created = 0
                skipped = 0
                failed = 0
                
                for workorder_id in workorder_ids:
                    try:
                        # 查詢指定的工單
                        workorder = WorkOrder.objects.get(id=workorder_id)
                        
                        # 檢查是否已有派工單
                        existing_dispatch = WorkOrderDispatch.objects.filter(
                            company_code=workorder.company_code,
                            order_number=workorder.order_number,
                            product_code=workorder.product_code
                        ).first()
                        
                        if existing_dispatch:
                            skipped += 1
                            continue
                        
                        # 建立派工單
                        dispatch = WorkOrderDispatch.objects.create(
                            company_code=workorder.company_code,
                            company_name=getattr(workorder, "company_name", None),
                            order_number=workorder.order_number,
                            product_code=workorder.product_code,
                            product_name=workorder.product_code,  # WorkOrder 沒有 product_name，使用 product_code
                            planned_quantity=workorder.quantity,
                            status="in_production",
                            dispatch_date=timezone.now().date(),
                            created_by=created_by,
                        )
                        created += 1
                        
                    except WorkOrder.DoesNotExist:
                        failed += 1
                        continue
                
                # 記錄日誌
                logger.info(f'批量派工（ID）: 共建立 {created} 筆派工單，跳過 {skipped} 筆，失敗 {failed} 筆。操作者: {created_by}, IP: {user_ip}')
                
                return {
                    'success': True,
                    'message': f'批量派工完成，共建立 {created} 筆派工單，跳過 {skipped} 筆，失敗 {failed} 筆',
                    'created_count': created,
                    'skipped_count': skipped,
                    'failed_count': failed
                }
                
        except Exception as e:
            logger.error(f'批量派工（ID）失敗: {str(e)}')
            return {
                'success': False,
                'error': f'批量派工失敗: {str(e)}'
            }
    
    @staticmethod
    def dispatch_all_undispatched_workorders(created_by="system", user_ip=None):
        """
        自動批次派工核心邏輯
        
        Args:
            created_by (str): 建立者
            user_ip (str): 使用者 IP
            
        Returns:
            dict: 執行結果
        """
        try:
            with transaction.atomic():
                # 取得所有未派工的工單
                undispatched_orders = WorkOrder.objects.all()
                
                # 檢查每個工單是否已有對應的派工單（使用完整的唯一識別）
                truly_undispatched = []
                for wo in undispatched_orders:
                    dispatch_exists = WorkOrderDispatch.objects.filter(
                        company_code=wo.company_code,
                        order_number=wo.order_number,
                        product_code=wo.product_code
                    ).exists()
                    if not dispatch_exists:
                        truly_undispatched.append(wo)
                
                created = 0
                for wo in truly_undispatched:
                    # 建立派工單，直接設定為生產中狀態
                    dispatch = WorkOrderDispatch.objects.create(
                        company_code=wo.company_code,
                        company_name=getattr(wo, "company_name", None),
                        order_number=wo.order_number,
                        product_code=wo.product_code,
                        product_name=wo.product_code,  # WorkOrder 沒有 product_name，使用 product_code
                        planned_quantity=wo.quantity,
                        status="in_production",
                        dispatch_date=timezone.now().date(),
                        created_by=created_by,
                    )
                    created += 1
                    
                    # 記錄操作日誌
                    if created_by == "system":
                        logger.info(f"定時任務: 自動批次派工 - 工單 {wo.order_number} 轉派為生產中狀態")
                    else:
                        logger.info(f"手動執行: 自動批次派工 - 工單 {wo.order_number} 轉派為生產中狀態。操作者: {created_by}, IP: {user_ip}")
                
                success_message = f"自動批次派工完成，共建立 {created} 筆派工單"
                logger.info(success_message)
                
                return {
                    'success': True,
                    'message': success_message,
                    'created_count': created
                }
                
        except Exception as e:
            error_message = f"自動批次派工失敗: {str(e)}"
            logger.error(error_message)
            return {
                'success': False,
                'error': error_message
            }


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
                        company_name=getattr(wo, "company_name", None),
                        order_number=wo.order_number,
                        product_code=wo.product_code,
                        product_name=wo.product_code,  # WorkOrder 沒有 product_name，使用 product_code
                        planned_quantity=wo.quantity,
                        status="in_production",  # 直接設定為生產中
                        dispatch_date=timezone.now().date(),  # 設定派工日期為今天
                        created_by=created_by,
                    )
                    created += 1
                    
                    # 記錄操作日誌
                    if created_by == "system":
                        logger.info(f"定時任務: 自動批次派工 - 工單 {wo.order_number} 轉派為生產中狀態")
                    else:
                        logger.info(f"手動執行: 自動批次派工 - 工單 {wo.order_number} 轉派為生產中狀態。操作者: {created_by}, IP: {user_ip}")
                
                success_message = f"自動批次派工完成，共建立 {created} 筆派工單"
                logger.info(success_message)
                
                return {
                    'success': True,
                    'message': success_message,
                    'created_count': created
                }
                
        except Exception as e:
            error_message = f"自動批次派工失敗: {str(e)}"
            logger.error(error_message)
            return {
                'success': False,
                'error': error_message
            }
