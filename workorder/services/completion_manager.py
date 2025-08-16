"""
完工管理服務
整合工序完工判斷和填報完工判斷兩種機制，統一管理工單完工流程
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import WorkOrder, WorkOrderProcess
from ..fill_work.models import FillWork
from .process_completion_service import ProcessCompletionService
from .report_completion_service import ReportCompletionService
from ..models import (
    CompletedWorkOrder, 
    CompletedWorkOrderProcess, 
    CompletedProductionReport
)
import logging

logger = logging.getLogger(__name__)


class CompletionManager:
    """
    完工管理服務
    統一管理工單的完工判斷和資料轉移
    """
    
    @classmethod
    def check_workorder_completion(cls, workorder_id, completion_method=None):
        """
        檢查工單完工狀態
        
        Args:
            workorder_id: 工單ID
            completion_method: 完工方式 ('process', 'report', 'auto')
            
        Returns:
            dict: 完工檢查結果
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 如果指定了完工方式，只檢查該方式
            if completion_method:
                if completion_method == 'process':
                    return cls._check_process_completion_only(workorder)
                elif completion_method == 'report':
                    return cls._check_report_completion_only(workorder)
            
            # 自動檢查兩種完工方式
            process_completed = ProcessCompletionService.check_process_completion(workorder_id)
            report_completed = ReportCompletionService.check_report_completion(workorder_id)
            
            result = {
                'workorder_id': workorder_id,
                'workorder_number': workorder.order_number,
                'process_completed': process_completed,
                'report_completed': report_completed,
                'overall_completed': process_completed or report_completed,
                'completion_method': None
            }
            
            # 決定完工方式
            if process_completed and report_completed:
                result['completion_method'] = 'both'
            elif process_completed:
                result['completion_method'] = 'process'
            elif report_completed:
                result['completion_method'] = 'report'
            
            return result
            
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_id} 不存在")
            return {
                'workorder_id': workorder_id,
                'error': '工單不存在'
            }
        except Exception as e:
            logger.error(f"檢查工單完工狀態時發生錯誤：{str(e)}")
            return {
                'workorder_id': workorder_id,
                'error': str(e)
            }
    
    @classmethod
    def _check_process_completion_only(cls, workorder):
        """只檢查工序完工"""
        process_completed = ProcessCompletionService.check_process_completion(workorder.id)
        return {
            'workorder_id': workorder.id,
            'workorder_number': workorder.order_number,
            'process_completed': process_completed,
            'report_completed': False,
            'overall_completed': process_completed,
            'completion_method': 'process' if process_completed else None
        }
    
    @classmethod
    def _check_report_completion_only(cls, workorder):
        """只檢查填報完工"""
        report_completed = ReportCompletionService.check_report_completion(workorder.id)
        return {
            'workorder_id': workorder.id,
            'workorder_number': workorder.order_number,
            'process_completed': False,
            'report_completed': report_completed,
            'overall_completed': report_completed,
            'completion_method': 'report' if report_completed else None
        }
    
    @classmethod
    def complete_workorder(cls, workorder_id, completion_method=None, notes=""):
        """
        完成工單並轉移資料
        
        Args:
            workorder_id: 工單ID
            completion_method: 完工方式
            notes: 備註
            
        Returns:
            bool: 是否成功完成
        """
        try:
            with transaction.atomic():
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                # 檢查是否已經完工
                if workorder.status == 'completed':
                    logger.warning(f"工單 {workorder.order_number} 已經完工")
                    return True
                
                # 如果沒有指定完工方式，自動判斷
                if not completion_method:
                    completion_check = cls.check_workorder_completion(workorder_id)
                    completion_method = completion_check.get('completion_method')
                
                if not completion_method:
                    logger.error(f"工單 {workorder.order_number} 不符合任何完工條件")
                    return False
                
                # 執行完工流程
                success = cls._execute_completion(workorder, completion_method, notes)
                
                if success:
                    logger.info(f"工單 {workorder.order_number} 已成功完工，方式：{completion_method}")
                
                return success
                
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"完成工單時發生錯誤：{str(e)}")
            return False
    
    @classmethod
    def _execute_completion(cls, workorder, completion_method, notes):
        """
        執行完工流程
        
        Args:
            workorder: 工單物件
            completion_method: 完工方式
            notes: 備註
            
        Returns:
            bool: 是否成功
        """
        try:
            # 1. 更新工單狀態
            workorder.status = 'completed'
            workorder.completed_at = timezone.now()
            workorder.save()
            
            # 2. 計算統計資料
            stats = cls._calculate_completion_stats(workorder)
            
            # 3. 建立已完工工單記錄
            completed_workorder = cls._create_completed_workorder(
                workorder, completion_method, stats, notes
            )
            
            # 4. 轉移工序資料
            cls._transfer_process_data(workorder, completed_workorder)
            
            # 5. 轉移報工記錄
            cls._transfer_report_data(workorder, completed_workorder)
            
            # 6. 清理原始資料（可選）
            # cls._cleanup_original_data(workorder)
            
            return True
            
        except Exception as e:
            logger.error(f"執行完工流程時發生錯誤：{str(e)}")
            return False
    
    @classmethod
    def _calculate_completion_stats(cls, workorder):
        """計算完工統計資料"""
        try:
            # 計算總工時和加班時數
            total_work_hours = 0
            overtime_hours = 0
            
            # 計算良品和不良品數量
            good_quantity = 0
            defect_quantity = 0
            
            # 從報工記錄計算統計資料
            reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            )
            
            for report in reports:
                # 累加工時
                if hasattr(report, 'work_hours_calculated') and report.work_hours_calculated:
                    total_work_hours += float(report.work_hours_calculated)
                
                # 累加數量
                good_quantity += report.work_quantity or 0
                defect_quantity += report.defect_quantity or 0
            
            return {
                'total_work_hours': total_work_hours,
                'overtime_hours': overtime_hours,
                'good_quantity': good_quantity,
                'defect_quantity': defect_quantity
            }
            
        except Exception as e:
            logger.error(f"計算完工統計資料時發生錯誤：{str(e)}")
            return {
                'total_work_hours': 0,
                'overtime_hours': 0,
                'good_quantity': 0,
                'defect_quantity': 0
            }
    
    @classmethod
    def _create_completed_workorder(cls, workorder, completion_method, stats, notes):
        """建立已完工工單記錄"""
        return CompletedWorkOrder.objects.create(
            company_code=workorder.company_code,
            order_number=workorder.order_number,
            product_code=workorder.product_code,
            quantity=workorder.quantity,
            order_source=workorder.order_source,
            created_at=workorder.created_at,
            started_at=workorder.created_at,  # 可以從工序記錄取得實際開始時間
            completed_at=workorder.completed_at,
            total_work_hours=stats['total_work_hours'],
            overtime_hours=stats['overtime_hours'],
            good_quantity=stats['good_quantity'],
            defect_quantity=stats['defect_quantity'],
            completion_method=completion_method,
            notes=notes
        )
    
    @classmethod
    def _transfer_process_data(cls, workorder, completed_workorder):
        """轉移工序資料"""
        try:
            processes = WorkOrderProcess.objects.filter(workorder=workorder)
            
            for process in processes:
                # 計算工序統計資料
                process_reports = FillWork.objects.filter(
                    workorder=workorder.order_number,
                    process=process,
                    approval_status='approved'
                )
                
                process_good_quantity = sum(r.work_quantity or 0 for r in process_reports)
                process_defect_quantity = sum(r.defect_quantity or 0 for r in process_reports)
                process_actual_quantity = process_good_quantity + process_defect_quantity
                process_work_hours = sum(float(r.work_hours_calculated or 0) for r in process_reports)
                
                CompletedWorkOrderProcess.objects.create(
                    workorder=completed_workorder,
                    process_name=process.process_name,
                    process_order=process.process_order,
                    status=process.status,
                    started_at=process.started_at,
                    completed_at=process.completed_at,
                    target_quantity=process.target_quantity,
                    actual_quantity=process_actual_quantity,
                    good_quantity=process_good_quantity,
                    defect_quantity=process_defect_quantity,
                    work_hours=process_work_hours,
                    notes=process.notes or ""
                )
                
        except Exception as e:
            logger.error(f"轉移工序資料時發生錯誤：{str(e)}")
    
    @classmethod
    def _transfer_report_data(cls, workorder, completed_workorder):
        """轉移報工記錄"""
        try:
            reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            )
            
            for report in reports:
                # 找到對應的已完工工序
                completed_process = CompletedWorkOrderProcess.objects.filter(
                    workorder=completed_workorder,
                    process_name=report.process.name
                ).first()
                
                if completed_process:
                    CompletedProductionReport.objects.create(
                        completed_workorder=completed_workorder,
                        process_name=report.process.name,
                        operator=report.operator,
                        equipment=report.equipment or "",
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        work_hours=float(report.work_hours_calculated or 0),
                        overtime_hours=float(report.overtime_hours_calculated or 0),
                        report_date=report.work_date,
                        start_time=report.start_time,
                        end_time=report.end_time,
                        report_source="fill_work",
                        report_type="operator",
                        remarks=report.remarks or "",
                        approval_status=report.approval_status,
                        approved_by=report.approved_by or "",
                        approved_at=report.approved_at
                    )
                    
        except Exception as e:
            logger.error(f"轉移報工記錄時發生錯誤：{str(e)}")
    
    @classmethod
    def get_completion_summary(cls, workorder_id):
        """
        取得完工摘要資訊
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工摘要
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 取得工序完工進度
            process_progress = ProcessCompletionService.get_process_completion_progress(workorder_id)
            
            # 取得填報完工進度
            report_progress = ReportCompletionService.get_report_completion_progress(workorder_id)
            
            # 檢查完工狀態
            completion_check = cls.check_workorder_completion(workorder_id)
            
            return {
                'workorder_info': {
                    'id': workorder.id,
                    'order_number': workorder.order_number,
                    'product_code': workorder.product_code,
                    'quantity': workorder.quantity,
                    'status': workorder.status
                },
                'process_completion': process_progress,
                'report_completion': report_progress,
                'completion_status': completion_check,
                'can_complete': completion_check.get('overall_completed', False)
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'error': '工單不存在'
            }
        except Exception as e:
            return {
                'error': str(e)
            } 