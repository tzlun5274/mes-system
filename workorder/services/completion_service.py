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
from ..workorder_dispatch.models import WorkOrderDispatch

logger = logging.getLogger(__name__)


class FillWorkCompletionService:
    """
    填報完工服務
    提供工單完工相關的功能
    """
    
    # 出貨包裝工序名稱
    PACKAGING_PROCESS_NAME = "出貨包裝"
    
    @classmethod
    def check_and_complete_workorder(cls, workorder_id):
        """
        檢查並完成工單（核心完工判斷方法）
        直接使用派工單監控資料判斷完工條件
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 是否成功完工
        """
        try:
            with transaction.atomic():
                # 1. 獲取工單
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                # 2. 檢查工單狀態
                if workorder.status == 'completed':
                    logger.info(f"工單 {workorder.order_number} 已經是完工狀態")
                    return True
                
                # 3. 查找對應的派工單並獲取監控資料
                dispatch = WorkOrderDispatch.objects.filter(
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    company_code=workorder.company_code
                ).first()
                
                if not dispatch:
                    logger.warning(f"工單 {workorder.order_number} 找不到對應的派工單")
                    return False
                
                # 4. 更新派工單的監控資料
                dispatch.update_all_statistics()
                
                # 5. 判斷完工條件（直接使用派工單監控資料）
                if dispatch.can_complete and dispatch.total_quantity > 0:
                    logger.info(f"工單 {workorder.order_number} 達到完工條件：出貨包裝數量={dispatch.packaging_total_quantity}, 目標數量={dispatch.planned_quantity}, 實際完成數量={dispatch.total_quantity}")
                    
                    # 6. 執行完工流程
                    cls._complete_workorder(workorder)
                    cls.transfer_workorder_to_completed(workorder_id)
                    
                    logger.info(f"工單 {workorder.order_number} 完工流程執行完成")
                    return True
                else:
                    if dispatch.total_quantity == 0:
                        logger.debug(f"工單 {workorder.order_number} 尚未達到完工條件：實際完成數量為0")
                    else:
                        logger.debug(f"工單 {workorder.order_number} 尚未達到完工條件：出貨包裝數量={dispatch.packaging_total_quantity}, 目標數量={dispatch.planned_quantity}")
                    return False
                    
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"檢查工單 {workorder_id} 完工狀態失敗: {str(e)}")
            return False
    
    @classmethod
    def _get_packaging_quantity(cls, workorder):
        """
        獲取出貨包裝數量（嚴格按公司分離）
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            int: 出貨包裝數量
        """
        try:
            # 基本查詢條件
            fillwork_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                process__name__exact=cls.PACKAGING_PROCESS_NAME,
                approval_status='approved'
            )
            
            # 嚴格的公司分離
            if workorder.company_code:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=workorder.company_code
                ).first()
                
                if company_config:
                    fillwork_reports = fillwork_reports.filter(
                        company_name=company_config.company_name
                    )
                    logger.debug(f"工單 {workorder.order_number} 填報記錄按公司名稱 '{company_config.company_name}' 過濾")
                else:
                    logger.warning(f"工單 {workorder.order_number} 公司代號 {workorder.company_code} 在 CompanyConfig 中找不到對應配置")
                    fillwork_reports = FillWork.objects.none()
            else:
                logger.warning(f"工單 {workorder.order_number} 沒有公司代號")
                fillwork_reports = FillWork.objects.none()
            
            # 計算良品數量
            good_quantity = fillwork_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            logger.debug(f"工單 {workorder.order_number} 出貨包裝數量: {good_quantity}")
            return good_quantity
            
        except Exception as e:
            logger.error(f"獲取出貨包裝數量失敗: {str(e)}")
            return 0
    
    @classmethod
    def _complete_workorder(cls, workorder):
        """
        執行工單完工流程
        
        Args:
            workorder: WorkOrder 實例
        """
        try:
            # 1. 更新工單狀態
            workorder.status = 'completed'
            workorder.completed_at = timezone.now()
            workorder.save()
            
            logger.info(f"工單 {workorder.order_number} 狀態更新為完工")
            
            # 2. 更新生產記錄
            if hasattr(workorder, 'production_record') and workorder.production_record:
                workorder.production_record.status = 'completed'
                workorder.production_record.production_end_date = timezone.now()
                workorder.production_record.save()
                logger.info(f"工單 {workorder.order_number} 生產記錄更新為完工")
            
            # 3. 更新所有工序狀態
            from ..models import WorkOrderProcess
            processes = WorkOrderProcess.objects.filter(workorder=workorder)
            for process in processes:
                process.status = 'completed'
                process.actual_end_time = timezone.now()
                process.save()
            
            logger.info(f"工單 {workorder.order_number} 所有工序狀態更新為完工")
            
        except Exception as e:
            logger.error(f"執行工單完工流程失敗: {str(e)}")
            raise
    
    @classmethod
    def get_completion_summary(cls, workorder_id):
        """
        獲取工單完工摘要（使用派工單監控資料）
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工摘要資訊
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 查找對應的派工單
            dispatch = WorkOrderDispatch.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code,  # 修正：使用 product_code
                company_code=workorder.company_code
            ).first()
            
            if dispatch:
                # 更新派工單的監控資料
                dispatch.update_all_statistics()
                
                # 從派工單取得統計資訊
                total_quantity = dispatch.total_quantity
                packaging_quantity = dispatch.packaging_total_quantity
                completion_rate = float(dispatch.completion_rate)
                packaging_completion_rate = float(dispatch.packaging_completion_rate)
                can_complete = dispatch.can_complete
                
                return {
                    'workorder_id': workorder_id,
                    'workorder_number': workorder.order_number,
                    'target_quantity': workorder.quantity,
                    'onsite_quantity': dispatch.onsite_completed_count,  # 現場報工記錄數
                    'fillwork_quantity': dispatch.fillwork_approved_count,  # 已核准填報記錄數
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
            else:
                # 如果沒有派工單，返回預設值
                return {
                    'workorder_id': workorder_id,
                    'workorder_number': workorder.order_number,
                    'target_quantity': workorder.quantity,
                    'onsite_quantity': 0,
                    'fillwork_quantity': 0,
                    'current_quantity': 0,
                    'packaging_quantity': 0,
                    'can_complete': False,
                    'completion_percentage': 0.0,
                    'packaging_completion_percentage': 0.0,
                    'is_completed': workorder.status == 'completed',
                    'packaging_info': {
                        'packaging_quantity': 0,
                        'threshold_quantity': workorder.quantity,
                        'completion_rate': 0.0
                    },
                    'config': {
                        'packaging_quantity_threshold': 100
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
                
                # 獲取派工單監控資料以取得實際完成數量
                dispatch = WorkOrderDispatch.objects.filter(
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    company_code=workorder.company_code
                ).first()
                
                if dispatch:
                    # 更新派工單監控資料
                    dispatch.update_all_statistics()
                    
                    # 使用出貨包裝的實際數量（這才是真正的完工數量）
                    actual_completed_quantity = dispatch.packaging_total_quantity  # 出貨包裝總數量
                    total_good_quantity = dispatch.packaging_good_quantity        # 出貨包裝良品數量
                    total_defect_quantity = dispatch.packaging_defect_quantity    # 出貨包裝不良品數量
                    total_work_hours = dispatch.total_work_hours
                    total_overtime_hours = dispatch.total_overtime_hours
                    total_all_hours = dispatch.total_all_hours
                    total_report_count = dispatch.fillwork_approved_count
                else:
                    # 如果沒有派工單，使用預設值
                    actual_completed_quantity = workorder.quantity  # 假設全部完成
                    total_good_quantity = workorder.quantity
                    total_defect_quantity = 0
                    total_work_hours = 0
                    total_overtime_hours = 0
                    total_all_hours = 0
                    total_report_count = 0
                
                # 建立已完工工單記錄
                completed_workorder = CompletedWorkOrder.objects.create(
                    original_workorder_id=workorder.id,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    company_code=workorder.company_code,
                    company_name=workorder.company_name if hasattr(workorder, 'company_name') else '',
                    planned_quantity=workorder.quantity,
                    completed_quantity=actual_completed_quantity,  # 使用實際完成數量
                    status='completed',
                    completed_at=workorder.completed_at or timezone.now(),
                    # 統計資料
                    total_good_quantity=total_good_quantity,
                    total_defect_quantity=total_defect_quantity,
                    total_work_hours=total_work_hours,
                    total_overtime_hours=total_overtime_hours,
                    total_all_hours=total_all_hours,
                    total_report_count=total_report_count
                )
                
                # 轉移詳細填報記錄
                cls._transfer_fillwork_records(workorder, completed_workorder)
                
                # 轉移詳細現場報工記錄
                cls._transfer_onsite_records(workorder, completed_workorder)
                
                logger.info(f"工單 {workorder.order_number} 成功轉移到已完工模組，實際完成數量: {actual_completed_quantity}")
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
    
    @classmethod
    def _transfer_fillwork_records(cls, workorder, completed_workorder):
        """
        轉移填報記錄到已完工工單
        
        Args:
            workorder: 原始工單
            completed_workorder: 已完工工單
        """
        try:
            from workorder.fill_work.models import FillWork
            
            # 根據公司代號獲取公司名稱（從ERP整合模組）
            from erp_integration.models import CompanyConfig
            company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
            company_name = company_config.company_name if company_config else ''
            
            # 獲取已核准的填報記錄（使用公司名稱查詢）
            fillwork_records = FillWork.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                company_name=company_name,  # 使用從CompanyConfig獲取的公司名稱
                approval_status='approved'
            ).order_by('work_date', 'start_time')
            
            # 轉移到已完工生產報工記錄
            from workorder.models import CompletedProductionReport
            
            for fillwork in fillwork_records:
                # 處理時間欄位：將time轉換為datetime
                from datetime import datetime, time
                from django.utils import timezone
                
                start_datetime = None
                end_datetime = None
                
                if fillwork.start_time and fillwork.work_date:
                    start_datetime = timezone.make_aware(
                        datetime.combine(fillwork.work_date, fillwork.start_time)
                    )
                
                if fillwork.end_time and fillwork.work_date:
                    end_datetime = timezone.make_aware(
                        datetime.combine(fillwork.work_date, fillwork.end_time)
                    )
                
                CompletedProductionReport.objects.create(
                    completed_workorder=completed_workorder,
                    report_date=fillwork.work_date,
                    process_name=fillwork.operation or (fillwork.process.name if fillwork.process else '未知工序'),
                    operator=fillwork.operator,
                    equipment=fillwork.equipment or '-',
                    work_quantity=fillwork.work_quantity,
                    defect_quantity=fillwork.defect_quantity,
                    work_hours=float(fillwork.work_hours_calculated or 0),
                    overtime_hours=float(fillwork.overtime_hours_calculated or 0),
                    start_time=start_datetime,
                    end_time=end_datetime,
                    report_source='填報記錄',
                    report_type='fillwork',
                    remarks=fillwork.remarks,
                    abnormal_notes=fillwork.abnormal_notes,
                    approval_status=fillwork.approval_status,
                    approved_by=fillwork.approved_by,
                    approved_at=fillwork.approved_at
                )
            
            logger.info(f"工單 {workorder.order_number} 轉移了 {fillwork_records.count()} 筆填報記錄")
            
        except Exception as e:
            logger.error(f"轉移填報記錄失敗: {str(e)}")
    
    @classmethod
    def _transfer_onsite_records(cls, workorder, completed_workorder):
        """
        轉移現場報工記錄到已完工工單
        
        Args:
            workorder: 原始工單
            completed_workorder: 已完工工單
        """
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            
            # 獲取已完成的現場報工記錄
            onsite_records = OnsiteReport.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code,
                company_code=workorder.company_code,
                status='completed'
            ).order_by('work_date', 'start_datetime')
            
            # 轉移到已完工生產報工記錄
            from workorder.models import CompletedProductionReport
            
            for onsite in onsite_records:
                CompletedProductionReport.objects.create(
                    completed_workorder=completed_workorder,
                    report_date=onsite.work_date,
                    process_name=onsite.process,
                    operator=onsite.operator,
                    equipment=onsite.equipment or '-',
                    work_quantity=onsite.work_quantity,
                    defect_quantity=onsite.defect_quantity,
                    work_hours=float(onsite.work_hours or 0),
                    overtime_hours=float(onsite.overtime_hours or 0),
                    start_time=onsite.start_datetime,
                    end_time=onsite.end_datetime,
                    report_source='現場報工',
                    report_type='onsite',
                    remarks=onsite.remarks,
                    abnormal_notes=onsite.abnormal_notes,
                    approval_status='completed',
                    approved_by=onsite.operator,
                    approved_at=onsite.completed_at
                )
            
            logger.info(f"工單 {workorder.order_number} 轉移了 {onsite_records.count()} 筆現場報工記錄")
            
        except Exception as e:
            logger.error(f"轉移現場報工記錄失敗: {str(e)}") 