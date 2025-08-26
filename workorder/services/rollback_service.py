"""
工單回朔服務
負責將已完工工單狀態回朔到生產中，並回寫相關資料
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime

from ..models import (
    WorkOrder, CompletedWorkOrder, CompletedWorkOrderProcess, 
    CompletedProductionReport, WorkOrderProduction, WorkOrderProductionDetail,
    WorkOrderProcess, WorkOrderAssignment
)
from ..workorder_dispatch.models import WorkOrderDispatch, WorkOrderDispatchProcess
from ..fill_work.models import FillWork

logger = logging.getLogger(__name__)


class WorkOrderRollbackService:
    """
    工單回朔服務類別
    提供將已完工工單回朔到生產中狀態的功能
    """
    
    @staticmethod
    def rollback_completed_workorder(completed_workorder_id, keep_approval_status=True):
        """
        將已完工工單回朔到生產中狀態
        
        Args:
            completed_workorder_id: 已完工工單ID
            keep_approval_status: 是否保持填報記錄的核准狀態，True=保持核准，False=改為待核准
            
        Returns:
            dict: 回朔結果
        """
        try:
            with transaction.atomic():
                # 獲取已完工工單
                completed_workorder = CompletedWorkOrder.objects.get(id=completed_workorder_id)
                
                # 檢查是否已經有對應的生產中工單
                existing_workorder = WorkOrder.objects.filter(
                    order_number=completed_workorder.order_number,
                    company_code=completed_workorder.company_code,
                    product_code=completed_workorder.product_code
                ).first()
                
                if existing_workorder and existing_workorder.status == 'in_progress':
                    raise ValidationError(f"工單 {completed_workorder.order_number} 已經在生產中狀態，無法回朔")
                
                # 1. 更新或建立原始工單記錄
                if existing_workorder:
                    # 更新現有工單狀態
                    workorder = existing_workorder
                    workorder.status = 'in_progress'
                    workorder.quantity = completed_workorder.planned_quantity
                    workorder.updated_at = timezone.now()
                    workorder.completed_at = None  # 清除完工時間
                    workorder.save()
                    logger.info(f"更新工單狀態：{workorder.order_number} → 生產中")
                else:
                    # 建立新的工單記錄
                    workorder = WorkOrder.objects.create(
                        company_code=completed_workorder.company_code,
                        order_number=completed_workorder.order_number,
                        product_code=completed_workorder.product_code,
                        quantity=completed_workorder.planned_quantity,
                        status='in_progress',
                        created_at=completed_workorder.created_at,
                        updated_at=timezone.now()
                    )
                    logger.info(f"建立新工單記錄：{workorder.order_number}")
                
                # 2. 建立或更新生產記錄
                production_record, created = WorkOrderProduction.objects.get_or_create(
                    workorder_id=workorder.id,
                    defaults={
                        'status': 'in_production',
                        'production_start_date': completed_workorder.started_at or completed_workorder.created_at,
                        'production_end_date': None,  # 清除結束時間
                        'current_process': None,
                        'completed_processes': '[]'
                    }
                )
                
                if not created:
                    # 更新現有生產記錄
                    production_record.status = 'in_production'
                    production_record.production_end_date = None
                    production_record.updated_at = timezone.now()
                    production_record.save()
                
                logger.info(f"更新生產記錄：工單 {workorder.order_number}")
                
                # 3. 回寫工序資料（重建被刪除的 WorkOrderProcess）
                WorkOrderRollbackService._rollback_workorder_processes(completed_workorder, workorder)
                
                # 4. 回寫工序分配資料（重建被刪除的 WorkOrderAssignment）
                WorkOrderRollbackService._rollback_workorder_assignments(completed_workorder, workorder)
                
                # 5. 回寫派工單資料（重建被刪除的 WorkOrderDispatch）
                WorkOrderRollbackService._rollback_dispatch_records(completed_workorder, workorder)
                
                # 6. 回寫派工單工序明細
                WorkOrderRollbackService._rollback_dispatch_processes(completed_workorder, workorder)
                
                # 7. 檢查並更新報工記錄狀態（填報記錄和現場報工記錄本來就保留，不需要重建）
                WorkOrderRollbackService._update_report_records_status(completed_workorder, workorder, keep_approval_status)
                
                # 8. 刪除相關的外鍵記錄
                WorkOrderRollbackService._delete_related_records(completed_workorder)
                
                # 9. 刪除已完工工單記錄
                completed_workorder.delete()
                logger.info(f"刪除已完工工單記錄：{completed_workorder.order_number}")
                
                return {
                    'success': True,
                    'message': f'工單 {completed_workorder.order_number} 已成功回朔到生產中狀態',
                    'workorder_id': workorder.id,
                    'order_number': workorder.order_number
                }
                
        except CompletedWorkOrder.DoesNotExist:
            logger.error(f"已完工工單 {completed_workorder_id} 不存在")
            return {
                'success': False,
                'error': '已完工工單不存在'
            }
        except ValidationError as e:
            logger.error(f"回朔驗證失敗：{str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"回朔工單失敗：{str(e)}")
            return {
                'success': False,
                'error': f'回朔失敗：{str(e)}'
            }
    
    @staticmethod
    def _rollback_workorder_processes(completed_workorder, workorder):
        """
        回寫工單工序記錄（重建被刪除的 WorkOrderProcess）
        
        Args:
            completed_workorder: 已完工工單
            workorder: 原始工單
        """
        try:
            # 獲取已完工工單的工序資料
            completed_processes = CompletedWorkOrderProcess.objects.filter(
                completed_workorder_id=completed_workorder.id
            )
            
            # 重建工單工序記錄
            for completed_process in completed_processes:
                # 檢查是否已存在相同的工序記錄
                existing_process = WorkOrderProcess.objects.filter(
                    workorder_id=workorder.id,
                    process_name=completed_process.process_name
                ).first()
                
                if not existing_process:
                    # 建立新的工序記錄
                    WorkOrderProcess.objects.create(
                        workorder_id=workorder.id,
                        process_name=completed_process.process_name,
                        planned_quantity=completed_process.planned_quantity,
                        completed_quantity=completed_process.completed_quantity,
                        status='in_progress',  # 回朔為生產中狀態
                        assigned_operator=completed_process.assigned_operator or '',
                        assigned_equipment=completed_process.assigned_equipment or '',
                        start_date=completed_process.start_date,
                        end_date=None,  # 清除結束時間
                        work_hours=completed_process.work_hours or 0,
                        overtime_hours=completed_process.overtime_hours or 0,
                        good_quantity=completed_process.good_quantity or 0,
                        defect_quantity=completed_process.defect_quantity or 0
                    )
                else:
                    # 更新現有工序記錄
                    existing_process.status = 'in_progress'
                    existing_process.end_date = None
                    existing_process.save()
            
            logger.info(f"回寫工單工序記錄完成：工單 {workorder.order_number}")
            
        except Exception as e:
            logger.error(f"回寫工單工序記錄失敗：{str(e)}")
            raise
    
    @staticmethod
    def _rollback_workorder_assignments(completed_workorder, workorder):
        """
        回寫工單分配記錄（重建被刪除的 WorkOrderAssignment）
        
        Args:
            completed_workorder: 已完工工單
            workorder: 原始工單
        """
        try:
            # 獲取已完工工單的工序資料，用於重建分配記錄
            completed_processes = CompletedWorkOrderProcess.objects.filter(
                completed_workorder_id=completed_workorder.id
            )
            
            # 重建工單分配記錄
            for completed_process in completed_processes:
                if completed_process.assigned_operator:
                    # 檢查是否已存在相同的分配記錄
                    existing_assignment = WorkOrderAssignment.objects.filter(
                        workorder_id=workorder.id,
                        process_name=completed_process.process_name,
                        operator=completed_process.assigned_operator
                    ).first()
                    
                    if not existing_assignment:
                        # 建立新的分配記錄
                        WorkOrderAssignment.objects.create(
                            workorder_id=workorder.id,
                            process_name=completed_process.process_name,
                            operator=completed_process.assigned_operator,
                            equipment=completed_process.assigned_equipment or '',
                            assigned_date=completed_process.start_date or timezone.now().date(),
                            status='assigned'
                        )
            
            logger.info(f"回寫工單分配記錄完成：工單 {workorder.order_number}")
            
        except Exception as e:
            logger.error(f"回寫工單分配記錄失敗：{str(e)}")
            raise
    
    @staticmethod
    def _rollback_dispatch_records(completed_workorder, workorder):
        """
        回寫派工單記錄（重建被刪除的 WorkOrderDispatch）
        
        Args:
            completed_workorder: 已完工工單
            workorder: 原始工單
        """
        try:
            # 檢查是否已存在派工單記錄
            existing_dispatch = WorkOrderDispatch.objects.filter(
                order_number=workorder.order_number,
                company_code=workorder.company_code,
                product_code=workorder.product_code
            ).first()
            
            if not existing_dispatch:
                # 建立新的派工單記錄
                WorkOrderDispatch.objects.create(
                    company_code=workorder.company_code,
                    company_name=completed_workorder.company_name,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    product_name='',  # 需要從其他地方獲取
                    planned_quantity=completed_workorder.planned_quantity,
                    status='in_production',  # 回朔為生產中狀態
                    dispatch_date=timezone.now().date(),
                    planned_start_date=completed_workorder.started_at.date() if completed_workorder.started_at else timezone.now().date(),
                    planned_end_date=None,  # 清除結束時間
                    assigned_operator='',  # 需要從工序資料中獲取
                    assigned_equipment=''   # 需要從工序資料中獲取
                )
                logger.info(f"建立派工單記錄：工單 {workorder.order_number}")
            else:
                # 更新現有派工單狀態
                existing_dispatch.status = 'in_production'
                existing_dispatch.save()
                logger.info(f"更新派工單狀態：工單 {workorder.order_number}")
            
        except Exception as e:
            logger.error(f"回寫派工單記錄失敗：{str(e)}")
            raise
    
    @staticmethod
    def _rollback_dispatch_processes(completed_workorder, workorder):
        """
        回寫派工單工序明細
        
        Args:
            completed_workorder: 已完工工單
            workorder: 原始工單
        """
        try:
            # 獲取已完工工單的工序資料
            completed_processes = CompletedWorkOrderProcess.objects.filter(
                completed_workorder_id=completed_workorder.id
            )
            
            # 獲取派工單
            dispatch = WorkOrderDispatch.objects.filter(
                order_number=workorder.order_number,
                company_code=workorder.company_code,
                product_code=workorder.product_code
            ).first()
            
            if not dispatch:
                logger.warning(f"找不到派工單記錄，無法回寫工序明細：工單 {workorder.order_number}")
                return
            
            # 回寫派工單工序明細
            for completed_process in completed_processes:
                # 檢查是否已存在相同的工序明細
                existing_process = WorkOrderDispatchProcess.objects.filter(
                    workorder_dispatch=dispatch,
                    process_name=completed_process.process_name
                ).first()
                
                if not existing_process:
                    # 建立新的工序明細
                    WorkOrderDispatchProcess.objects.create(
                        workorder_dispatch=dispatch,
                        process_name=completed_process.process_name,
                        planned_quantity=completed_process.planned_quantity,
                        completed_quantity=completed_process.completed_quantity,
                        status='in_progress',  # 回朔為生產中狀態
                        assigned_operator=completed_process.assigned_operator or '',
                        assigned_equipment=completed_process.assigned_equipment or '',
                        start_date=completed_process.start_date,
                        end_date=None,  # 清除結束時間
                        work_hours=completed_process.work_hours or 0,
                        overtime_hours=completed_process.overtime_hours or 0,
                        good_quantity=completed_process.good_quantity or 0,
                        defect_quantity=completed_process.defect_quantity or 0
                    )
                else:
                    # 更新現有工序明細
                    existing_process.status = 'in_progress'
                    existing_process.end_date = None
                    existing_process.save()
            
            logger.info(f"回寫派工單工序明細完成：工單 {workorder.order_number}")
            
        except Exception as e:
            logger.error(f"回寫派工單工序明細失敗：{str(e)}")
            raise
    
    @staticmethod
    def _update_report_records_status(completed_workorder, workorder, keep_approval_status=True):
        """
        更新報工記錄狀態（填報記錄和現場報工記錄本來就保留，只需要更新狀態）
        
        Args:
            completed_workorder: 已完工工單
            workorder: 原始工單
            keep_approval_status: 是否保持填報記錄的核准狀態
        """
        try:
            # 更新填報記錄狀態（如果有的話）
            fillwork_records = FillWork.objects.filter(
                workorder=workorder.order_number,
                product_id=workorder.product_code,
                company_name=completed_workorder.company_name
            )
            
            if fillwork_records.exists():
                # 將填報記錄的完工狀態設為 False，表示工單重新進入生產中
                fillwork_records.update(is_completed=False)
                
                # 根據設定決定是否保持核准狀態
                if not keep_approval_status:
                    # 將核准狀態改為待核准
                    fillwork_records.update(
                        approval_status='pending',
                        approved_by='',
                        approved_at=None
                    )
                    logger.info(f"更新 {fillwork_records.count()} 筆填報記錄狀態為待核准：工單 {workorder.order_number}")
                else:
                    logger.info(f"更新 {fillwork_records.count()} 筆填報記錄狀態（保持核准）：工單 {workorder.order_number}")
            
            # 更新現場報工記錄狀態（如果有的話）
            try:
                from ..onsite_reporting.models import OnsiteReport
                onsite_records = OnsiteReport.objects.filter(
                    workorder=workorder.order_number,
                    product_id=workorder.product_code
                )
                
                if onsite_records.exists():
                    # 將現場報工記錄的狀態設為 in_progress，表示重新進入生產中
                    onsite_records.update(status='in_progress')
                    logger.info(f"更新 {onsite_records.count()} 筆現場報工記錄狀態：工單 {workorder.order_number}")
                    
            except Exception as e:
                logger.warning(f"更新現場報工記錄狀態失敗：{str(e)}")
            
            logger.info(f"更新報工記錄狀態完成：工單 {workorder.order_number}")
            
        except Exception as e:
            logger.error(f"更新報工記錄狀態失敗：{str(e)}")
            # 不拋出異常，因為這不是關鍵步驟
    
    @staticmethod
    def _delete_related_records(completed_workorder):
        """
        刪除與已完工工單相關的記錄
        
        Args:
            completed_workorder: 已完工工單實例
        """
        try:
            # 刪除生產報表記錄
            CompletedProductionReport.objects.filter(
                completed_workorder=completed_workorder
            ).delete()
            
            # 刪除已完工工序記錄
            CompletedWorkOrderProcess.objects.filter(
                completed_workorder=completed_workorder
            ).delete()
            
            # 刪除工單分析記錄（沒有外鍵約束，需要手動刪除）
            try:
                from reporting.models import CompletedWorkOrderAnalysis
                CompletedWorkOrderAnalysis.objects.filter(
                    workorder_id=completed_workorder.workorder_id,
                    company_code=completed_workorder.company_code
                ).delete()
                logger.info(f"刪除工單分析記錄：{completed_workorder.workorder_id}")
            except ImportError:
                logger.warning("CompletedWorkOrderAnalysis 模型不存在，跳過分析記錄刪除")
            except Exception as e:
                logger.error(f"刪除工單分析記錄失敗：{str(e)}")
            
            logger.info(f"刪除相關記錄完成：工單 {completed_workorder.order_number}")
            
        except Exception as e:
            logger.error(f"刪除相關記錄失敗：{str(e)}")
            raise
    
    @staticmethod
    def can_rollback(completed_workorder_id):
        """
        檢查是否可以回朔
        
        Args:
            completed_workorder_id: 已完工工單ID
            
        Returns:
            dict: 檢查結果
        """
        try:
            completed_workorder = CompletedWorkOrder.objects.get(id=completed_workorder_id)
            
            # 檢查是否已經有對應的生產中工單
            existing_workorder = WorkOrder.objects.filter(
                order_number=completed_workorder.order_number,
                company_code=completed_workorder.company_code,
                product_code=completed_workorder.product_code
            ).first()
            
            if existing_workorder and existing_workorder.status == 'in_progress':
                return {
                    'can_rollback': False,
                    'reason': f'工單 {completed_workorder.order_number} 已經在生產中狀態'
                }
            
            return {
                'can_rollback': True,
                'reason': '可以回朔'
            }
            
        except CompletedWorkOrder.DoesNotExist:
            return {
                'can_rollback': False,
                'reason': '已完工工單不存在'
            }
        except Exception as e:
            return {
                'can_rollback': False,
                'reason': f'檢查失敗：{str(e)}'
            }
