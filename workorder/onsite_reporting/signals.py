"""
現場報工子模組 - 信號處理
負責現場報工的信號處理邏輯
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import OnsiteReport
from workorder.services.process_update_service import ProcessUpdateService
import logging
from django.db.models import Sum

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OnsiteReport)
def onsite_report_post_save(sender, instance, created, **kwargs):
    """
    現場報工記錄儲存後的信號處理
    當現場報工記錄被建立或更新時，自動更新對應工單的工序完成數量
    """
    try:
        # 查找對應的工單
        from workorder.models import WorkOrder
        try:
            workorder = WorkOrder.objects.filter(
                order_number=instance.order_number,
                product_code=instance.product_code
            ).first()
            
            # 如果工單有公司代號，進一步檢查公司代號是否匹配
            if workorder and workorder.company_code and instance.company_code:
                if workorder.company_code != instance.company_code:
                    # 公司代號不匹配，視為找不到工單
                    workorder = None
            
            if workorder:
                # 更新工單狀態 - 新增
                from workorder.services.workorder_status_service import WorkOrderStatusService
                updated = WorkOrderStatusService.update_workorder_status(workorder.id)
                
                if updated:
                    logger.info(f"現場報工記錄觸發工單狀態更新成功：工單 {workorder.order_number}")
                else:
                    logger.warning(f"現場報工記錄觸發工單狀態更新失敗：工單 {workorder.order_number}")
            
        except Exception as e:
            logger.error(f"現場報工記錄查找工單失敗：{str(e)}")
        
        # 只處理已完成的報工記錄
        if instance.status == 'completed':
            logger.info(f"現場報工記錄完成，更新工序：{instance.order_number} - {instance.process}")
            
            # 查找對應的工單
            from workorder.models import WorkOrder
            try:
                workorder = WorkOrder.objects.get(order_number=instance.order_number)
                
                # 更新工序完成數量
                from workorder.models import WorkOrderProcess
                process = WorkOrderProcess.objects.filter(
                    workorder=workorder,
                    process_name=instance.process
                ).first()
                
                if process:
                    # 計算該工序的總完成數量（包括現場報工和填報記錄）
                    from workorder.fill_work.models import FillWork
                    
                    # 現場報工數量
                    onsite_quantity = OnsiteReport.objects.filter(
                        order_number=instance.order_number,
                        process=instance.process,
                        status='completed'
                    ).aggregate(
                        total=Sum('work_quantity')
                    )['total'] or 0
                    
                    # 填報記錄數量
                    fill_work_quantity = FillWork.objects.filter(
                        workorder=instance.order_number,
                        process__name=instance.process,
                        approval_status='approved'
                    ).aggregate(
                        total=Sum('work_quantity')
                    )['total'] or 0
                    
                    # 總完成數量
                    total_completed = onsite_quantity + fill_work_quantity
                    
                    # 更新工序完成數量
                    process.completed_quantity = total_completed
                    
                    # 更新工序狀態
                    if total_completed >= process.planned_quantity:
                        process.status = 'completed'
                        process.actual_end_time = timezone.now()
                    elif total_completed > 0:
                        process.status = 'in_progress'
                        if not process.actual_start_time:
                            process.actual_start_time = timezone.now()
                    else:
                        process.status = 'pending'
                    
                    process.save()
                    
                    logger.info(f"工序 {instance.process} 更新完成：完成數量={total_completed}, 狀態={process.status}")
                    
                    # 更新工單整體完成數量
                    ProcessUpdateService._update_workorder_completion(workorder)
                    
                else:
                    logger.warning(f"找不到對應的工序：{instance.order_number} - {instance.process}")
                    
            except WorkOrder.DoesNotExist:
                logger.warning(f"找不到對應的工單：{instance.order_number}")
                
    except Exception as e:
        logger.error(f"現場報工信號處理錯誤：{str(e)}")


@receiver(post_save, sender=OnsiteReport)
def onsite_report_completion_check(sender, instance, created, **kwargs):
    """
    現場報工完成後檢查工單完工狀態
    """
    try:
        # 只處理已完成的報工記錄
        if instance.status == 'completed':
            logger.info(f"檢查工單完工狀態：{instance.order_number}")
            
            # 查找對應的工單
            from workorder.models import WorkOrder
            try:
                workorder = WorkOrder.objects.get(order_number=instance.order_number)
                
                # 檢查是否所有工序都完成
                from workorder.services.process_completion_service import ProcessCompletionService
                if ProcessCompletionService.check_process_completion(workorder.id):
                    logger.info(f"工單 {workorder.order_number} 所有工序已完成，觸發完工檢查")
                    
                    # 觸發完工檢查
                    from workorder.tasks import auto_check_workorder_completion
                    auto_check_workorder_completion.delay()
                    
            except WorkOrder.DoesNotExist:
                logger.warning(f"找不到對應的工單：{instance.order_number}")
                
    except Exception as e:
        logger.error(f"現場報工完工檢查錯誤：{str(e)}") 