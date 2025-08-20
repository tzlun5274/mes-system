"""
工單工序更新服務
更新工單工序的完成數量和狀態
"""

import logging
from django.db import transaction
from django.db.models import Sum
from workorder.models import WorkOrder, WorkOrderProcess
from workorder.models import CompletedProductionReport as OperatorSupplementReport
logger = logging.getLogger(__name__)

class ProcessUpdateService:
    """
    工單工序更新服務
    根據已核准的報工記錄更新工單工序的完成數量和狀態
    """
    
    @staticmethod
    def update_workorder_processes(workorder_id):
        """
        更新指定工單的所有工序完成數量和狀態
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            with transaction.atomic():
                # 獲取該工單的所有工序
                processes = WorkOrderProcess.objects.filter(workorder_id=workorder.id)
                
                for process in processes:
                    ProcessUpdateService._update_single_process(process)
                
                # 更新工單的完成數量
                ProcessUpdateService._update_workorder_completion(workorder)
                
                logger.info(f"工單 {workorder.order_number} 的工序更新完成")
                return True
                
        except WorkOrder.DoesNotExist:
            logger.error(f"工單不存在: {workorder_id}")
            return False
        except Exception as e:
            logger.error(f"更新工單工序失敗: {str(e)}")
            import traceback
            logger.error(f"詳細錯誤: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def _update_single_process(process):
        """
        更新單一工序的完成數量和狀態
        
        Args:
            process: WorkOrderProcess 實例
        """
        try:
            # 獲取該工序的所有已核准填報記錄
            from workorder.workorder_fill_work.models import FillWork
            
            # 先獲取工單資訊
            workorder = WorkOrder.objects.get(id=process.workorder_id)
            
            # 填報記錄：根據多公司架構唯一識別查詢
            fill_work_reports = FillWork.objects.filter(
                workorder=workorder.order_number,  # 工單號碼
                product_id=workorder.product_code,  # 產品編號
                process__name=process.process_name,  # 工序名稱
                approval_status='approved'
            )
            
            # 如果工單有公司代號，則按公司分離過濾
            if workorder.company_code:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                if company_config:
                    fill_work_reports = fill_work_reports.filter(company_name=company_config.company_name)
            
            # 計算總完成數量
            fill_work_quantity = fill_work_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            total_completed_quantity = fill_work_quantity
            
            # 更新工序完成數量
            process.completed_quantity = total_completed_quantity
            
            # 更新工序狀態
            if total_completed_quantity >= process.planned_quantity:
                process.status = 'completed'
            elif total_completed_quantity > 0:
                process.status = 'in_progress'
            else:
                process.status = 'pending'
            
            # 如果有報工記錄，設定實際開始時間
            if total_completed_quantity > 0 and not process.actual_start_time:
                # 獲取最早的報工記錄時間
                earliest_report = fill_work_reports.order_by('work_date', 'start_time').first()
                
                if earliest_report:
                    from datetime import datetime
                    from django.utils import timezone
                    # 使用 timezone-aware datetime
                    process.actual_start_time = timezone.make_aware(
                        datetime.combine(earliest_report.work_date, earliest_report.start_time)
                    )
            
            # 如果工序完成，設定實際結束時間
            if process.status == 'completed' and not process.actual_end_time:
                # 獲取最晚的報工記錄時間
                latest_report = fill_work_reports.order_by('work_date', 'end_time').last()
                
                if latest_report:
                    from datetime import datetime
                    from django.utils import timezone
                    # 使用 timezone-aware datetime
                    process.actual_end_time = timezone.make_aware(
                        datetime.combine(latest_report.work_date, latest_report.end_time)
                    )
            
            process.save()
            
            logger.debug(f"工序 {process.process_name} 更新完成：完成數量={total_completed_quantity}, 狀態={process.status}")
            
        except Exception as e:
            logger.error(f"更新工序 {process.process_name} 失敗: {str(e)}")
            raise
    
    @staticmethod
    def _update_workorder_completion(workorder):
        """
        更新工單的完成數量
        
        Args:
            workorder: WorkOrder 實例
        """
        try:
            # 計算工單總完成數量（所有工序完成數量的總和）
            total_completed = WorkOrderProcess.objects.filter(
                workorder_id=workorder.id
            ).aggregate(
                total=Sum('completed_quantity')
            )['total'] or 0
            
            # 更新工單完成數量
            workorder.completed_quantity = total_completed
            
            # 檢查是否所有工序都完成
            all_processes_completed = WorkOrderProcess.objects.filter(
                workorder_id=workorder.id,
                status__in=['pending', 'in_progress']
            ).count() == 0
            
            if all_processes_completed and total_completed > 0:
                workorder.status = 'completed'
            elif total_completed > 0:
                workorder.status = 'in_progress'
            else:
                workorder.status = 'pending'
            
            workorder.save()
            
            logger.debug(f"工單 {workorder.order_number} 更新完成: 完成數量={total_completed}, 狀態={workorder.status}")
            
        except Exception as e:
            logger.error(f"更新工單完成數量失敗: {str(e)}")
            raise
    
    @staticmethod
    def update_all_workorders():
        """
        更新所有生產中工單的工序完成數量
        
        Returns:
            bool: 更新是否成功
        """
        try:
            logger.info("開始更新所有工單的工序完成數量...")
            
            # 獲取所有生產中的工單
            workorders = WorkOrder.objects.filter(
                status__in=['pending', 'in_progress']
            )
            
            success_count = 0
            total_count = workorders.count()
            
            for workorder in workorders:
                try:
                    if ProcessUpdateService.update_workorder_processes(workorder.id):
                        success_count += 1
                except Exception as e:
                    logger.error(f"更新工單 {workorder.order_number} 失敗: {str(e)}")
            
            logger.info(f"工單工序更新完成: 成功 {success_count}/{total_count}")
            return True
            
        except Exception as e:
            logger.error(f"更新所有工單工序失敗: {str(e)}")
            return False 