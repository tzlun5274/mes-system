"""
工單狀態自動更新服務
當有工序記錄或填報核准記錄時，自動將工單狀態更新為生產中
當所有填報記錄都取消核准時，自動將工單狀態轉回待生產
"""

import logging
from django.db import transaction
from django.utils import timezone
from ..models import WorkOrder
from ..fill_work.models import FillWork
from erp_integration.models import CompanyConfig

logger = logging.getLogger(__name__)


class WorkOrderStatusService:
    """
    工單狀態管理服務
    自動管理工單狀態的轉換
    """
    
    @staticmethod
    def update_workorder_status(workorder_id):
        """
        更新工單狀態
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 是否成功更新狀態
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查當前狀態
            if workorder.status == 'completed':
                logger.debug(f"工單 {workorder.order_number} 已完工，跳過狀態更新")
                return True
            
            # 檢查是否有生產活動
            has_production_activity = WorkOrderStatusService._check_production_activity(workorder)
            
            with transaction.atomic():
                if has_production_activity and workorder.status == 'pending':
                    # 更新為生產中狀態
                    workorder.status = 'in_progress'
                    workorder.updated_at = timezone.now()
                    workorder.save()
                    
                    logger.info(f"工單 {workorder.order_number} 狀態更新：pending → in_progress")
                    return True
                elif not has_production_activity and workorder.status == 'in_progress':
                    # 沒有生產活動但狀態為生產中，轉回待生產
                    workorder.status = 'pending'
                    workorder.updated_at = timezone.now()
                    workorder.save()
                    
                    logger.info(f"工單 {workorder.order_number} 狀態更新：in_progress → pending")
                    return True
            
            return True
            
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"更新工單 {workorder_id} 狀態失敗：{str(e)}")
            return False
    
    @staticmethod
    def _check_production_activity(workorder):
        """
        檢查工單是否有生產活動
        
        Args:
            workorder: 工單物件
            
        Returns:
            bool: 是否有生產活動
        """
        try:
            # 1. 檢查工序記錄（已移除，因為 WorkOrderProductionDetail 模型已移除外鍵關係）
            # has_process_records = WorkOrderProductionDetail.objects.filter(
            #     workorder_production__workorder=workorder
            # ).exists()
            # 
            # if has_process_records:
            #     logger.debug(f"工單 {workorder.order_number} 有工序記錄")
            #     return True
            
            # 2. 檢查現場報工記錄
            try:
                from workorder.onsite_reporting.models import OnsiteReport
                onsite_reports = OnsiteReport.objects.filter(
                    order_number=workorder.order_number,
                    product_code=workorder.product_code
                )
                
                # 如果工單有公司代號，則按公司分離過濾
                if workorder.company_code:
                    onsite_reports = onsite_reports.filter(company_code=workorder.company_code)
                
                has_onsite_reports = onsite_reports.exists()
                
                if has_onsite_reports:
                    logger.debug(f"工單 {workorder.order_number} 有現場報工記錄")
                    return True
            except ImportError:
                # 如果現場報工模組不存在，跳過檢查
                logger.debug(f"現場報工模組不存在，跳過檢查")
                has_onsite_reports = False
            
            # 3. 檢查填報核准記錄
            # 根據多公司架構，需要同時檢查公司名稱、工單號碼和產品編號
            from erp_integration.models import CompanyConfig
            
            # 先找到對應的公司配置
            company_config = CompanyConfig.objects.filter(
                company_code=workorder.company_code
            ).first()
            
            if company_config:
                has_approved_reports = FillWork.objects.filter(
                    workorder=workorder.order_number,
                    product_id=workorder.product_code,
                    company_name=company_config.company_name,
                    approval_status='approved'
                ).exists()
            else:
                has_approved_reports = False
            
            if has_approved_reports:
                logger.debug(f"工單 {workorder.order_number} 有已核准填報記錄")
                return True
            
            # 4. 檢查是否有生產記錄
            has_production_record = hasattr(workorder, 'production_record') and workorder.production_record is not None
            
            if has_production_record:
                logger.debug(f"工單 {workorder.order_number} 有生產記錄")
                return True
            
            logger.debug(f"工單 {workorder.order_number} 沒有任何生產活動")
            return False
            
        except Exception as e:
            logger.error(f"檢查工單 {workorder.order_number} 生產活動失敗：{str(e)}")
            return False
    
    @staticmethod
    def update_all_pending_workorders():
        """
        更新所有待生產工單的狀態
        
        Returns:
            dict: 更新結果統計
        """
        try:
            pending_workorders = WorkOrder.objects.filter(status='pending')
            
            updated_count = 0
            total_count = 0
            
            for workorder in pending_workorders:
                total_count += 1
                try:
                    if WorkOrderStatusService.update_workorder_status(workorder.id):
                        if workorder.status == 'in_progress':
                            updated_count += 1
                except Exception as e:
                    logger.error(f"更新工單 {workorder.order_number} 狀態失敗：{str(e)}")
            
            logger.info(f"批量更新工單狀態完成：檢查 {total_count} 個工單，更新 {updated_count} 個為生產中")
            
            return {
                'total_count': total_count,
                'updated_count': updated_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"批量更新工單狀態失敗：{str(e)}")
            return {
                'total_count': 0,
                'updated_count': 0,
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_all_in_progress_workorders():
        """
        更新所有生產中工單的狀態
        檢查是否有工單需要轉回待生產
        
        Returns:
            dict: 更新結果統計
        """
        try:
            in_progress_workorders = WorkOrder.objects.filter(status='in_progress')
            
            updated_count = 0
            total_count = 0
            
            for workorder in in_progress_workorders:
                total_count += 1
                try:
                    if WorkOrderStatusService.update_workorder_status(workorder.id):
                        if workorder.status == 'pending':
                            updated_count += 1
                except Exception as e:
                    logger.error(f"更新工單 {workorder.order_number} 狀態失敗：{str(e)}")
            
            logger.info(f"批量更新生產中工單狀態完成：檢查 {total_count} 個工單，更新 {updated_count} 個為待生產")
            
            return {
                'total_count': total_count,
                'updated_count': updated_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"批量更新生產中工單狀態失敗：{str(e)}")
            return {
                'total_count': 0,
                'updated_count': 0,
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_workorder_status_summary(workorder_id):
        """
        取得工單狀態摘要
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 狀態摘要
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查各種生產活動
            process_records_count = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=workorder
            ).count()
            
            # 根據多公司架構，需要同時檢查公司代號、工單號碼和產品編號
            approved_reports_count = FillWork.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                approval_status='approved'
            )
            
            # 如果工單有公司代號，則按公司分離過濾
            if workorder.company_code:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                if company_config:
                    approved_reports_count = approved_reports_count.filter(company_name=company_config.company_name)
            
            approved_reports_count = approved_reports_count.count()
            
            has_production_record = hasattr(workorder, 'production_record') and workorder.production_record is not None
            
            return {
                'workorder_number': workorder.order_number,
                'current_status': workorder.status,
                'planned_quantity': workorder.quantity,
                'completed_quantity': workorder.completed_quantity,
                'process_records_count': process_records_count,
                'approved_reports_count': approved_reports_count,
                'has_production_record': has_production_record,
                'should_be_in_progress': process_records_count > 0 or approved_reports_count > 0 or has_production_record
            }
            
        except WorkOrder.DoesNotExist:
            return {'error': '工單不存在'}
        except Exception as e:
            return {'error': str(e)} 