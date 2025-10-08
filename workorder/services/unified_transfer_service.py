"""
統一資料轉移服務
將所有資料轉移邏輯統一到一個服務中，避免重複程式碼
"""

import logging
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from ..models import WorkOrder, CompletedWorkOrder, CompletedProductionReport, CompletedWorkOrderProcess
from ..fill_work.models import FillWork
from ..onsite_reporting.models import OnsiteReport

logger = logging.getLogger(__name__)


class UnifiedTransferService:
    """
    統一資料轉移服務
    將所有工單資料轉移邏輯統一管理
    """
    
    @classmethod
    def transfer_workorder_to_completed(cls, workorder_id, transfer_reason="系統轉移"):
        """
        統一的工單轉移方法
        這是唯一應該使用的轉移方法
        
        Args:
            workorder_id: 工單ID
            transfer_reason: 轉移原因
            
        Returns:
            dict: 轉移結果
        """
        try:
            with transaction.atomic():
                # 1. 獲取工單
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                # 2. 檢查是否已經轉移過
                existing = CompletedWorkOrder.objects.filter(
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    company_code=workorder.company_code
                ).first()
                
                if existing:
                    return {
                        'success': True,
                        'message': f'工單 {workorder.order_number} 已經轉移過',
                        'completed_workorder_id': existing.id,
                        'was_already_transferred': True
                    }
                
                # 3. 建立已完工工單
                completed_workorder = cls._create_completed_workorder(workorder, transfer_reason)
                
                # 4. 轉移所有相關資料
                cls._transfer_all_data(workorder, completed_workorder)
                
                # 5. 更新統計資料
                cls._update_statistics(completed_workorder)
                
                # 6. 清理原始資料
                cls._cleanup_original_data(workorder)
                
                logger.info(f"工單 {workorder.order_number} 轉移完成")
                
                return {
                    'success': True,
                    'message': f'工單 {workorder.order_number} 轉移成功',
                    'completed_workorder_id': completed_workorder.id,
                    'was_already_transferred': False
                }
                
        except WorkOrder.DoesNotExist:
            return {
                'success': False,
                'error': f'工單 {workorder_id} 不存在'
            }
        except Exception as e:
            logger.error(f"轉移工單 {workorder_id} 失敗: {str(e)}")
            return {
                'success': False,
                'error': f'轉移失敗: {str(e)}'
            }
    
    @classmethod
    def _create_completed_workorder(cls, workorder, transfer_reason):
        """建立已完工工單記錄"""
        # 獲取公司名稱
        company_name = ""
        if workorder.company_code:
            try:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                if company_config:
                    company_name = company_config.company_name
            except:
                pass
        
        return CompletedWorkOrder.objects.create(
            original_workorder_id=workorder.id,
            company_code=workorder.company_code,
            company_name=company_name,
            order_number=workorder.order_number,
            product_code=workorder.product_code,
            planned_quantity=workorder.quantity,
            completed_quantity=workorder.quantity,  # 暫時設為計劃數量，後續會更新
            status='completed',
            started_at=workorder.created_at,
            completed_at=workorder.completed_at or timezone.now(),
            production_record_id=None
        )
    
    @classmethod
    def _transfer_all_data(cls, workorder, completed_workorder):
        """轉移所有相關資料"""
        # 轉移填報記錄
        cls._transfer_fillwork_records(workorder, completed_workorder)
        
        # 轉移現場報工記錄
        cls._transfer_onsite_records(workorder, completed_workorder)
        
        # 轉移工序記錄
        cls._transfer_process_records(workorder, completed_workorder)
    
    @classmethod
    def _transfer_fillwork_records(cls, workorder, completed_workorder):
        """轉移填報記錄"""
        try:
            fillwork_records = FillWork.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                company_name=completed_workorder.company_name,
                approval_status='approved'
            )
            
            for record in fillwork_records:
                try:
                    # 處理時間欄位
                    start_datetime = None
                    end_datetime = None
                    
                    if record.start_time and record.work_date:
                        start_datetime = timezone.make_aware(
                            datetime.combine(record.work_date, record.start_time)
                        )
                    
                    if record.end_time and record.work_date:
                        end_datetime = timezone.make_aware(
                            datetime.combine(record.work_date, record.end_time)
                        )
                    
                    # 建立轉移記錄
                    CompletedProductionReport.objects.create(
                        completed_workorder_id=completed_workorder.id,
                        report_date=record.work_date,
                        process_name=record.operation or '未知工序',
                        operator=record.operator,
                        equipment=record.equipment or '-',
                        work_quantity=record.work_quantity or 0,
                        defect_quantity=record.defect_quantity or 0,
                        work_hours=float(record.work_hours_calculated or 0),
                        overtime_hours=float(record.overtime_hours_calculated or 0),
                        start_time=start_datetime,
                        end_time=end_datetime,
                        report_source='填報記錄',
                        report_type='fillwork',
                        remarks=record.remarks or '',
                        abnormal_notes=record.abnormal_notes or '',
                        approval_status=record.approval_status or 'approved',
                        approved_by=record.approved_by or '',
                        allocation_method='manual'
                    )
                except Exception as e:
                    logger.error(f"轉移填報記錄失敗 {record.id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"轉移填報記錄失敗: {str(e)}")
    
    @classmethod
    def _transfer_onsite_records(cls, workorder, completed_workorder):
        """轉移現場報工記錄"""
        try:
            onsite_records = OnsiteReport.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                company_name=completed_workorder.company_name,
                status='completed'
            )
            
            for record in onsite_records:
                try:
                    CompletedProductionReport.objects.create(
                        completed_workorder_id=completed_workorder.id,
                        report_date=record.work_date,
                        process_name=record.process,
                        operator=record.operator,
                        equipment=record.equipment or '-',
                        work_quantity=record.work_quantity or 0,
                        defect_quantity=record.defect_quantity or 0,
                        work_hours=float(record.work_minutes or 0) / 60,  # 分鐘轉小時
                        overtime_hours=0.0,
                        start_time=record.start_datetime,
                        end_time=record.end_datetime,
                        report_source='現場報工',
                        report_type='onsite',
                        remarks=record.remarks or '',
                        abnormal_notes=record.abnormal_notes or '',
                        approval_status='completed',
                        approved_by=record.operator or '',
                        allocation_method='manual'
                    )
                except Exception as e:
                    logger.error(f"轉移現場報工記錄失敗 {record.id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"轉移現場報工記錄失敗: {str(e)}")
    
    @classmethod
    def _transfer_process_records(cls, workorder, completed_workorder):
        """轉移工序記錄"""
        try:
            from ..models import WorkOrderProcess
            
            process_records = WorkOrderProcess.objects.filter(
                workorder_id=workorder.id
            ).order_by('step_order')
            
            for process in process_records:
                try:
                    # 從填報記錄統計該工序的實際資料
                    fill_work_records = FillWork.objects.filter(
                        workorder=workorder.order_number,
                        product_id=workorder.product_code,
                        operation=process.process_name,
                        approval_status='approved'
                    )
                    
                    # 統計實際資料
                    total_work_hours = sum(float(record.work_hours_calculated or 0) for record in fill_work_records)
                    total_overtime_hours = sum(float(record.overtime_hours_calculated or 0) for record in fill_work_records)
                    total_good_quantity = sum(int(record.work_quantity or 0) for record in fill_work_records)
                    total_defect_quantity = sum(int(record.defect_quantity or 0) for record in fill_work_records)
                    report_count = fill_work_records.count()
                    
                    # 收集參與的作業員和設備
                    operators = list(set(record.operator for record in fill_work_records if record.operator))
                    equipment = list(set(record.equipment for record in fill_work_records if record.equipment))
                    
                    # 如果沒有從填報記錄找到資料，使用原始工序的分配資訊
                    if not operators and process.assigned_operator:
                        operators = [process.assigned_operator]
                    if not equipment and process.assigned_equipment:
                        equipment = [process.assigned_equipment]
                    
                    # 轉移到已完工工單工序記錄
                    CompletedWorkOrderProcess.objects.create(
                        completed_workorder_id=completed_workorder.id,
                        process_name=process.process_name,
                        process_order=process.step_order,
                        planned_quantity=process.planned_quantity,
                        completed_quantity=process.completed_quantity,
                        status=process.status,
                        assigned_operator=process.assigned_operator or '',
                        assigned_equipment=process.assigned_equipment or '',
                        total_work_hours=total_work_hours,
                        total_good_quantity=total_good_quantity,
                        total_defect_quantity=total_defect_quantity,
                        report_count=report_count,
                        operators=operators,
                        equipment=equipment
                    )
                except Exception as e:
                    logger.error(f"轉移工序記錄失敗 {process.id}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"轉移工序記錄失敗: {str(e)}")
    
    @classmethod
    def _update_statistics(cls, completed_workorder):
        """更新統計資料"""
        try:
            # 從已轉移的記錄重新計算統計資料
            production_reports = CompletedProductionReport.objects.filter(
                completed_workorder_id=completed_workorder.id
            )
            
            total_work_hours = sum(report.work_hours for report in production_reports)
            total_overtime_hours = sum(report.overtime_hours for report in production_reports)
            total_good_quantity = sum(report.work_quantity for report in production_reports)
            total_defect_quantity = sum(report.defect_quantity for report in production_reports)
            
            completed_workorder.total_work_hours = total_work_hours
            completed_workorder.total_overtime_hours = total_overtime_hours
            completed_workorder.total_all_hours = total_work_hours + total_overtime_hours
            completed_workorder.total_good_quantity = total_good_quantity
            completed_workorder.total_defect_quantity = total_defect_quantity
            completed_workorder.total_report_count = production_reports.count()
            completed_workorder.save()
            
        except Exception as e:
            logger.error(f"更新統計資料失敗: {str(e)}")
    
    @classmethod
    def _cleanup_original_data(cls, workorder):
        """清理原始資料"""
        try:
            # 更新派工單狀態
            from ..workorder_dispatch.models import WorkOrderDispatch
            dispatch = WorkOrderDispatch.objects.filter(
                order_number=workorder.order_number,
                product_code=workorder.product_code,
                company_code=workorder.company_code
            ).first()
            
            if dispatch:
                dispatch.status = 'completed'
                dispatch.production_end_date = timezone.now()
                dispatch.save()
                
                # 刪除派工單記錄
                dispatch.delete()
                logger.info(f"刪除派工單記錄：{workorder.order_number}")
            
            # 刪除原始工單記錄
            workorder.delete()
            
        except Exception as e:
            logger.error(f"清理原始資料失敗: {str(e)}")
