"""
派工單統計服務
負責處理派工單的所有統計計算和業務邏輯
從模型中完整分離出來的服務層，一個字都不少
"""

import logging
from django.db.models import Sum
from django.utils import timezone
from workorder.workorder_dispatch.models import WorkOrderDispatch

logger = logging.getLogger('workorder')


class DispatchStatisticsService:
    """派工單統計服務類別"""
    
    @staticmethod
    def update_all_statistics(dispatch):
        """
        更新派工單所有統計資料
        從模型中的 update_all_statistics 方法完整分離出來
        """
        try:
            # 1. 更新填報記錄統計
            DispatchStatisticsService._update_fillwork_statistics(dispatch)
            
            # 2. 更新現場報工統計
            DispatchStatisticsService._update_onsite_statistics(dispatch)
            
            # 3. 更新工序進度統計
            DispatchStatisticsService._update_process_statistics(dispatch)
            
            # 4. 更新人員和設備統計
            DispatchStatisticsService._update_operator_equipment_statistics(dispatch)
            
            # 5. 更新完成率計算
            DispatchStatisticsService._update_completion_rates(dispatch)
            
            # 6. 更新完工判斷
            DispatchStatisticsService._update_completion_status(dispatch)
            
            # 7. 同步工單狀態
            DispatchStatisticsService._sync_workorder_status(dispatch)
            
            dispatch.save()
            
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger('workorder')
            error_details = traceback.format_exc()
            logger.error(f"更新派工單 {dispatch.order_number} 統計資料失敗: {str(e)}\n詳細錯誤:\n{error_details}")
            # 即使有錯誤，也要嘗試儲存已更新的資料
            try:
                dispatch.save()
            except:
                pass
    
    @staticmethod
    def _update_fillwork_statistics(dispatch):
        """更新填報記錄統計"""
        from workorder.fill_work.models import FillWork
        
        # 基本查詢條件
        fillwork_reports = FillWork.objects.filter(
            workorder=dispatch.order_number,
            product_id=dispatch.product_code
        )
        
        # 按公司分離
        if dispatch.company_code:
            fillwork_reports = fillwork_reports.filter(
                company_name=DispatchStatisticsService._get_company_name(dispatch)
            )
        
        # 統計數量
        dispatch.fillwork_report_count = fillwork_reports.count()
        dispatch.fillwork_approved_count = fillwork_reports.filter(approval_status='approved').count()
        dispatch.fillwork_pending_count = fillwork_reports.filter(approval_status='pending').count()
        
        # 統計時數
        approved_reports = fillwork_reports.filter(approval_status='approved')
        dispatch.total_work_hours = approved_reports.aggregate(
            total=Sum('work_hours_calculated')
        )['total'] or 0
        
        dispatch.total_overtime_hours = approved_reports.aggregate(
            total=Sum('overtime_hours_calculated')
        )['total'] or 0
        
        dispatch.total_all_hours = dispatch.total_work_hours + dispatch.total_overtime_hours
        
        # 統計數量
        dispatch.total_good_quantity = approved_reports.aggregate(
            total=Sum('work_quantity')
        )['total'] or 0
        
        dispatch.total_defect_quantity = approved_reports.aggregate(
            total=Sum('defect_quantity')
        )['total'] or 0
        
        dispatch.total_quantity = dispatch.total_good_quantity + dispatch.total_defect_quantity
        
        # 出貨包裝專項統計（填報記錄）
        packaging_reports = approved_reports.filter(operation='出貨包裝')
        packaging_good_quantity = packaging_reports.aggregate(
            total=Sum('work_quantity')
        )['total'] or 0
        
        packaging_defect_quantity = packaging_reports.aggregate(
            total=Sum('defect_quantity')
        )['total'] or 0
        
        # 加上現場報工出貨包裝數量
        onsite_packaging_quantity = DispatchStatisticsService._get_onsite_packaging_quantity(dispatch)
        
        # 總出貨包裝數量 = 填報記錄 + 現場報工
        dispatch.packaging_good_quantity = packaging_good_quantity + onsite_packaging_quantity['good']
        dispatch.packaging_defect_quantity = packaging_defect_quantity + onsite_packaging_quantity['defect']
        dispatch.packaging_total_quantity = dispatch.packaging_good_quantity + dispatch.packaging_defect_quantity
        
        # 更新最後填報時間
        if approved_reports.exists():
            dispatch.last_fillwork_update = approved_reports.latest('updated_at').updated_at
    
    @staticmethod
    def _update_onsite_statistics(dispatch):
        """更新現場報工統計"""
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            
            onsite_reports = OnsiteReport.objects.filter(
                order_number=dispatch.order_number,
                product_code=dispatch.product_code
            )
            
            # 按公司分離
            if dispatch.company_code:
                onsite_reports = onsite_reports.filter(
                    company_code=dispatch.company_code
                )
            
            dispatch.onsite_report_count = onsite_reports.count()
            dispatch.onsite_completed_count = onsite_reports.filter(status='completed').count()
            
            # 更新最後現場報工時間
            if onsite_reports.exists():
                dispatch.last_onsite_update = onsite_reports.latest('updated_at').updated_at
                
        except ImportError:
            # 如果現場報工模組不存在，跳過更新
            pass
    
    @staticmethod
    def _update_process_statistics(dispatch):
        """更新工序進度統計"""
        try:
            # 從產品工序路線獲取總工序數
            from process.models import ProductProcessRoute
            total_processes = ProductProcessRoute.objects.filter(
                product_id=dispatch.product_code
            ).count()
            
            # 從填報記錄獲取已完成的工序
            from workorder.fill_work.models import FillWork
            from erp_integration.models import CompanyConfig
            
            # 獲取公司名稱
            company_name = None
            if dispatch.company_code:
                company_config = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
                if company_config:
                    company_name = company_config.company_name
            
            # 統計已完成的工序（有報工記錄的工序）
            if company_name:
                completed_processes = FillWork.objects.filter(
                    workorder=dispatch.order_number,
                    product_id=dispatch.product_code,
                    company_name=company_name,
                    approval_status='approved'
                ).values('operation').distinct().count()
            else:
                completed_processes = 0
            
            # 統計進行中的工序（有報工記錄但未完成的工序）
            # 這裡簡化處理，假設有報工記錄的工序就是進行中
            in_progress_processes = completed_processes
            
            # 待處理工序 = 總工序數 - 已完成工序
            pending_processes = max(0, total_processes - completed_processes)
            
            # 更新派工單的工序統計
            dispatch.total_processes = total_processes
            dispatch.completed_processes = completed_processes
            dispatch.in_progress_processes = in_progress_processes
            dispatch.pending_processes = pending_processes
            
        except Exception as e:
            # 如果發生錯誤，設定預設值
            dispatch.total_processes = 0
            dispatch.completed_processes = 0
            dispatch.in_progress_processes = 0
            dispatch.pending_processes = 0
    
    @staticmethod
    def _update_operator_equipment_statistics(dispatch):
        """更新人員和設備統計"""
        # 這裡可以根據實際需求實現人員和設備統計邏輯
        pass
    
    @staticmethod
    def _update_completion_rates(dispatch):
        """更新完成率計算"""
        if dispatch.planned_quantity and dispatch.planned_quantity > 0:
            dispatch.completion_rate = (dispatch.total_quantity / dispatch.planned_quantity) * 100
        else:
            dispatch.completion_rate = 0
        
        if dispatch.planned_quantity and dispatch.planned_quantity > 0:
            dispatch.packaging_completion_rate = (dispatch.packaging_total_quantity / dispatch.planned_quantity) * 100
        else:
            dispatch.packaging_completion_rate = 0
    
    @staticmethod
    def _update_completion_status(dispatch):
        """更新完工判斷 - 簡化版本，複雜邏輯移至服務層"""
        if (dispatch.packaging_total_quantity >= dispatch.planned_quantity and 
            dispatch.planned_quantity > 0):
            dispatch.completion_threshold_met = True
            dispatch.can_complete = True
        else:
            dispatch.completion_threshold_met = False
            dispatch.can_complete = False
    
    @staticmethod
    def _get_company_name(dispatch):
        """取得公司名稱"""
        from erp_integration.models import CompanyConfig
        company_config = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
        return company_config.company_name if company_config else None

    @staticmethod
    def _get_onsite_packaging_quantity(dispatch):
        """獲取現場報工出貨包裝數量"""
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            
            onsite_packaging_reports = OnsiteReport.objects.filter(
                workorder=dispatch.order_number,
                product_id=dispatch.product_code,
                operation='出貨包裝',
                status='completed'
            )
            
            # 按公司分離
            if dispatch.company_code:
                onsite_packaging_reports = onsite_packaging_reports.filter(
                    company_code=dispatch.company_code
                )
            
            # 統計良品和不良品數量
            good_quantity = onsite_packaging_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            defect_quantity = onsite_packaging_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            return {
                'good': good_quantity,
                'defect': defect_quantity,
                'total': good_quantity + defect_quantity
            }
            
        except ImportError:
            # 如果現場報工模組不存在，返回0
            return {'good': 0, 'defect': 0, 'total': 0}
    
    @staticmethod
    def _sync_workorder_status(dispatch):
        """同步工單狀態"""
        try:
            from workorder.models import WorkOrder
            import logging
            logger = logging.getLogger('workorder')
            
            # 查找對應的工單
            workorder = WorkOrder.objects.filter(
                order_number=dispatch.order_number,
                product_code=dispatch.product_code,
                company_code=dispatch.company_code
            ).first()
            
            if workorder:
                # 根據派工單狀態和完工判斷來更新工單狀態
                if dispatch.can_complete:
                    # 如果達到完工條件，標記為已完成
                    if workorder.status != 'completed':
                        workorder.status = 'completed'
                        # 只有在完工時間未設定時才設定為當前時間
                        if workorder.completed_at is None:
                            workorder.completed_at = timezone.now()
                        workorder.save()
                        logger.info(f"工單 {workorder.order_number} 狀態更新為已完成")
                elif dispatch.total_quantity > 0:
                    # 如果有生產數量，標記為生產中
                    if workorder.status == 'pending':
                        workorder.status = 'in_progress'
                        workorder.save()
                        logger.info(f"工單 {workorder.order_number} 狀態更新為生產中")
                else:
                    # 如果沒有生產數量，保持待生產狀態
                    if workorder.status != 'pending':
                        workorder.status = 'pending'
                        workorder.save()
                        logger.info(f"工單 {workorder.order_number} 狀態更新為待生產")
                        
        except Exception as e:
            import logging
            logger = logging.getLogger('workorder')
            logger.error(f"同步工單狀態失敗: {str(e)}")
    
    @staticmethod
    def update_all_dispatches_statistics():
        """
        更新所有派工單的統計資料
        用於批次更新
        """
        try:
            dispatches = WorkOrderDispatch.objects.filter(status='in_production')
            updated_count = 0
            error_count = 0
            
            for dispatch in dispatches:
                try:
                    DispatchStatisticsService.update_all_statistics(dispatch)
                    updated_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"更新派工單 {dispatch.order_number} 統計資料失敗: {str(e)}")
            
            logger.info(f"批次更新派工單統計完成：成功 {updated_count} 個，失敗 {error_count} 個")
            return {
                'success': True,
                'updated_count': updated_count,
                'error_count': error_count,
                'message': f'批次更新完成：成功 {updated_count} 個，失敗 {error_count} 個'
            }
            
        except Exception as e:
            logger.error(f"批次更新派工單統計失敗: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'updated_count': 0,
                'error_count': 1
            }