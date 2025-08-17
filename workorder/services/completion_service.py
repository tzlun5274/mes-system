"""
工單完工服務
提供工單完工相關的功能，包括完工檢查、轉移等
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from ..models import WorkOrder, CompletedWorkOrder, WorkOrderProductionDetail
from ..fill_work.models import FillWork
from ..production_monitoring.models import ProductionMonitoringData

logger = logging.getLogger(__name__)


class FillWorkCompletionService:
    """
    填報完工服務
    提供工單完工相關的功能
    """
    
    @classmethod
    def get_completion_summary(cls, workorder_id):
        """
        獲取工單完工摘要（使用 ProductionMonitoringData）
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工摘要資訊
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 取得或建立監控資料
            monitoring_data = ProductionMonitoringData.get_or_create_for_workorder(workorder)
            monitoring_data.update_all_statistics()
            
            # 從監控資料取得統計資訊
            total_quantity = monitoring_data.total_quantity
            packaging_quantity = monitoring_data.packaging_total_quantity
            completion_rate = float(monitoring_data.completion_rate)
            packaging_completion_rate = float(monitoring_data.packaging_completion_rate)
            can_complete = monitoring_data.can_complete
            
            return {
                'workorder_id': workorder_id,
                'workorder_number': workorder.order_number,
                'target_quantity': workorder.quantity,
                'onsite_quantity': monitoring_data.onsite_completed_count,  # 現場報工記錄數
                'fillwork_quantity': monitoring_data.fillwork_approved_count,  # 已核准填報記錄數
                'current_quantity': total_quantity,
                'packaging_quantity': packaging_quantity,
                'can_complete': can_complete,
                'completion_percentage': completion_rate,
                'packaging_completion_percentage': packaging_completion_rate,
                'is_completed': workorder.status == 'completed',
                'packaging_info': {
                    'packaging_quantity': packaging_quantity,
                    'threshold_quantity': workorder.quantity,
                    'completion_rate': packaging_completion_rate
                },
                'config': {
                    'packaging_quantity_threshold': 100  # 100% 為完工閾值
                }
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'error': '工單不存在'
            }
        except Exception as e:
            logger.error(f"獲取工單 {workorder_id} 完工摘要失敗: {str(e)}")
            return {
                'error': f'獲取完工摘要失敗: {str(e)}'
            }
    
    @classmethod
    def transfer_workorder_to_completed(cls, workorder_id):
        """
        將工單轉移到已完工模組
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            CompletedWorkOrder: 已完工工單物件
        """
        try:
            with transaction.atomic():
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                # 檢查是否已經轉移過
                existing_completed = CompletedWorkOrder.objects.filter(
                    original_workorder_id=workorder_id
                ).first()
                
                if existing_completed:
                    logger.info(f"工單 {workorder.order_number} 已經轉移過")
                    return existing_completed
                
                # 建立已完工工單記錄
                completed_workorder = CompletedWorkOrder.objects.create(
                    original_workorder_id=workorder.id,
                    order_number=workorder.order_number,
                    product_id=workorder.product_id,
                    quantity=workorder.quantity,
                    completed_at=workorder.completed_at or timezone.now(),
                    completion_method='manual_transfer'
                )
                
                logger.info(f"工單 {workorder.order_number} 成功轉移到已完工模組")
                return completed_workorder
                
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_id} 不存在")
            raise
        except Exception as e:
            logger.error(f"轉移工單 {workorder_id} 失敗: {str(e)}")
            raise
    
    @classmethod
    def auto_complete_workorder(cls, workorder_id):
        """
        自動完工工單
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工結果
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查工單狀態
            if workorder.status == 'completed':
                return {
                    'success': True,
                    'message': f'工單 {workorder.order_number} 已經是完工狀態'
                }
            
            # 獲取完工摘要
            summary = cls.get_completion_summary(workorder_id)
            
            if 'error' in summary:
                return {
                    'success': False,
                    'error': summary['error']
                }
                
            # 檢查是否達到完工條件
            if not summary['can_complete']:
                return {
                    'success': False,
                    'error': f'工單尚未達到完工條件，當前進度: {summary["completion_percentage"]:.1f}%'
                }
            
            # 更新工單狀態為完工
            workorder.status = 'completed'
            workorder.completed_at = timezone.now()
            workorder.save()
            
            # 轉移到已完工模組
            completed_workorder = cls.transfer_workorder_to_completed(workorder_id)
            
            return {
                'success': True,
                'message': f'工單 {workorder.order_number} 自動完工成功',
                'workorder_id': workorder_id,
                'completed_workorder_id': completed_workorder.id
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'success': False,
                'error': '工單不存在'
            }
        except Exception as e:
            logger.error(f"自動完工工單 {workorder_id} 失敗: {str(e)}")
            return {
                'success': False,
                'error': f'自動完工失敗: {str(e)}'
            }
    
    @classmethod
    def _get_onsite_quantity(cls, workorder):
        """獲取現場報工數量（從 OnsiteReport 表計算，嚴格按公司分離）"""
        try:
            from onsite_reporting.models import OnsiteReport
            
            # 基本查詢條件
            onsite_reports = OnsiteReport.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code,
                process="出貨包裝",
                status='completed'  # 只統計已完成的現場報工
            )
            
            # 嚴格的公司分離：必須同時檢查公司代號和公司名稱
            if workorder.company_code:
                # 從 CompanyConfig 獲取公司名稱
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=workorder.company_code
                ).first()
                
                if company_config:
                    # 同時按公司代號和公司名稱過濾，確保資料分離
                    onsite_reports = onsite_reports.filter(
                        company_code=workorder.company_code
                    )
                    logger.info(f"工單 {workorder.order_number} 現場報工按公司代號 '{workorder.company_code}' 過濾")
                else:
                    # 如果找不到公司配置，清空結果避免資料混淆
                    logger.warning(f"工單 {workorder.order_number} 公司代號 {workorder.company_code} 在 CompanyConfig 中找不到對應配置，清空現場報工結果")
                    onsite_reports = OnsiteReport.objects.none()
            else:
                # 如果工單沒有公司代號，清空結果避免資料混淆
                logger.warning(f"工單 {workorder.order_number} 沒有公司代號，清空現場報工結果避免資料混淆")
                onsite_reports = OnsiteReport.objects.none()
            
            # 計算良品數量
            good_quantity = onsite_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            # 計算不良品數量
            defect_quantity = onsite_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 總數量 = 良品 + 不良品
            total_quantity = good_quantity + defect_quantity
            
            logger.info(f"工單 {workorder.order_number} 現場報工數量: 良品={good_quantity}, 不良品={defect_quantity}, 總計={total_quantity}")
            
            return total_quantity
            
        except Exception as e:
            logger.error(f"獲取現場報工數量失敗: {str(e)}")
            return 0
    
    @classmethod
    def _get_fillwork_quantity(cls, workorder):
        """獲取出貨包裝填報數量（嚴格按公司分離，避免重複計算）"""
        try:
            # 基本查詢條件
            fillwork_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                process__name__exact="出貨包裝",  # 修正：使用 exact 而不是 icontains
                approval_status='approved'
            )
            
            # 嚴格的公司分離：必須同時檢查公司代號和公司名稱
            if workorder.company_code:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=workorder.company_code
                ).first()
                
                if company_config:
                    # 按公司名稱過濾，確保資料分離
                    fillwork_reports = fillwork_reports.filter(
                        company_name=company_config.company_name
                    )
                    logger.info(f"工單 {workorder.order_number} 填報記錄按公司名稱 '{company_config.company_name}' 過濾")
                else:
                    # 如果找不到公司配置，清空結果避免資料混淆
                    logger.warning(f"工單 {workorder.order_number} 公司代號 {workorder.company_code} 在 CompanyConfig 中找不到對應配置，清空填報記錄結果")
                    fillwork_reports = FillWork.objects.none()
            else:
                # 如果工單沒有公司代號，清空結果避免資料混淆
                logger.warning(f"工單 {workorder.order_number} 沒有公司代號，清空填報記錄結果避免資料混淆")
                fillwork_reports = FillWork.objects.none()
            
            # 計算良品數量
            good_quantity = fillwork_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            # 計算不良品數量
            defect_quantity = fillwork_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 總數量 = 良品 + 不良品
            total_quantity = good_quantity + defect_quantity
            
            logger.info(f"工單 {workorder.order_number} 出貨包裝填報數量: 良品={good_quantity}, 不良品={defect_quantity}, 總計={total_quantity}")
            
            return total_quantity
            
        except Exception as e:
            logger.error(f"獲取出貨包裝填報數量失敗: {str(e)}")
            return 0 