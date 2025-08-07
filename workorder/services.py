"""
工單服務模組
提供工單相關的業務邏輯服務
"""

import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from workorder.models import WorkOrder, WorkOrderProcess, WorkOrderProduction, WorkOrderProductionDetail
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTSupplementReport

# 移除主管報工引用，避免混淆
# 主管職責：監督、審核、管理，不代為報工

logger = logging.getLogger(__name__)


class WorkOrderCompletionService:
    """
    工單完工服務
    處理工單完工時的資料轉移和統計計算
    """
    
    @staticmethod
    def transfer_workorder_to_completed(workorder_id):
        """
        將完工的工單資料轉移到已完工工單模組
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            CompletedWorkOrder: 已完工工單實例
        """
        try:
            with transaction.atomic():
                # 獲取原始工單
                workorder = WorkOrder.objects.select_related('production_record').get(id=workorder_id)
                
                # 檢查工單是否已經完工
                if workorder.status != 'completed':
                    raise ValueError(f"工單 {workorder.order_number} 尚未完工，無法轉移")
                
                # 檢查是否已經轉移過
                if CompletedWorkOrder.objects.filter(original_workorder_id=workorder_id).exists():
                    logger.warning(f"工單 {workorder.order_number} 已經轉移過")
                    return CompletedWorkOrder.objects.get(original_workorder_id=workorder_id)
                
                # 計算統計資料
                stats = WorkOrderCompletionService._calculate_workorder_stats(workorder)
                
                # 建立已完工工單
                completed_workorder = CompletedWorkOrder.objects.create(
                    original_workorder_id=workorder_id,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    company_code=workorder.company_code,
                    planned_quantity=workorder.planned_quantity,
                    completed_quantity=workorder.completed_quantity,
                    status='completed',
                    created_at=workorder.created_at,
                    started_at=workorder.started_at,
                    completed_at=timezone.now(),
                    production_record=workorder.production_record,
                    **stats
                )
                
                # 轉移工序資料
                WorkOrderCompletionService._transfer_processes(workorder, completed_workorder)
                
                # 轉移報工記錄
                WorkOrderCompletionService._transfer_production_reports(workorder, completed_workorder)
                
                logger.info(f"工單 {workorder.order_number} 成功轉移到已完工模組")
                return completed_workorder
                
        except Exception as e:
            logger.error(f"轉移工單 {workorder_id} 時發生錯誤: {str(e)}")
            raise
    
    @staticmethod
    def _calculate_workorder_stats(workorder):
        """
        計算工單統計資料
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            dict: 統計資料字典
        """
        # 獲取所有已核准的報工記錄
        operator_reports = OperatorSupplementReport.objects.filter(
            workorder=workorder,
            approval_status='approved'
        )
        
        smt_reports = SMTSupplementReport.objects.filter(
            workorder=workorder,
            approval_status='approved'
        )
        
        # 計算統計資料
        total_work_hours = 0.0
        total_overtime_hours = 0.0
        total_good_quantity = 0
        total_defect_quantity = 0
        total_report_count = 0
        unique_operators = set()
        unique_equipment = set()
        
        # 處理作業員報工記錄
        for report in operator_reports:
            total_work_hours += float(report.work_hours_calculated or 0)
            total_overtime_hours += float(report.overtime_hours_calculated or 0)
            total_good_quantity += report.work_quantity or 0
            total_defect_quantity += report.defect_quantity or 0
            total_report_count += 1
            if report.operator and report.operator.name:
                unique_operators.add(report.operator.name)
            if report.equipment and report.equipment.name:
                unique_equipment.add(report.equipment.name)
        
        # 處理SMT報工記錄
        for report in smt_reports:
            total_work_hours += float(report.work_hours_calculated or 0)
            total_overtime_hours += float(report.overtime_hours_calculated or 0)
            total_good_quantity += report.work_quantity or 0
            total_defect_quantity += report.defect_quantity or 0
            total_report_count += 1
            if report.equipment and report.equipment.name:
                unique_equipment.add(report.equipment.name)
        
        return {
            'total_work_hours': total_work_hours,
            'total_overtime_hours': total_overtime_hours,
            'total_all_hours': total_work_hours + total_overtime_hours,
            'total_good_quantity': total_good_quantity,
            'total_defect_quantity': total_defect_quantity,
            'total_report_count': total_report_count,
            'unique_operators': list(unique_operators),
            'unique_equipment': list(unique_equipment),
        }
    
    @staticmethod
    def _transfer_processes(workorder, completed_workorder):
        """
        轉移工序資料
        
        Args:
            workorder: 原始工單
            completed_workorder: 已完工工單
        """
        for process in workorder.processes.all():
            # 計算工序統計資料
            process_stats = WorkOrderCompletionService._calculate_process_stats(process)
            
            CompletedWorkOrderProcess.objects.create(
                completed_workorder=completed_workorder,
                process_name=process.process_name,
                process_order=process.process_order,
                planned_quantity=process.planned_quantity,
                completed_quantity=process.completed_quantity,
                status=process.status,
                assigned_operator=process.assigned_operator,
                assigned_equipment=process.assigned_equipment,
                **process_stats
            )
    
    @staticmethod
    def _calculate_process_stats(process):
        """
        計算工序統計資料
        
        Args:
            process: WorkOrderProcess 實例
            
        Returns:
            dict: 統計資料字典
        """
        # 獲取該工序的所有報工記錄
        operator_reports = OperatorSupplementReport.objects.filter(
            workorder=process.workorder,
            process=process,
            approval_status='approved'
        )
        
        smt_reports = SMTSupplementReport.objects.filter(
            workorder=process.workorder,
            operation=process.process_name,
            approval_status='approved'
        )
        
        # 計算統計資料
        total_work_hours = 0.0
        total_good_quantity = 0
        total_defect_quantity = 0
        report_count = 0
        operators = set()
        equipment = set()
        
        # 處理作業員報工記錄
        for report in operator_reports:
            total_work_hours += float(report.work_hours_calculated or 0)
            total_good_quantity += report.work_quantity or 0
            total_defect_quantity += report.defect_quantity or 0
            report_count += 1
            if report.operator and report.operator.name:
                operators.add(report.operator.name)
            if report.equipment and report.equipment.name:
                equipment.add(report.equipment.name)
        
        # 處理SMT報工記錄
        for report in smt_reports:
            total_work_hours += float(report.work_hours_calculated or 0)
            total_good_quantity += report.work_quantity or 0
            total_defect_quantity += report.defect_quantity or 0
            report_count += 1
            if report.equipment and report.equipment.name:
                equipment.add(report.equipment.name)
        
        return {
            'total_work_hours': total_work_hours,
            'total_good_quantity': total_good_quantity,
            'total_defect_quantity': total_defect_quantity,
            'report_count': report_count,
            'operators': list(operators),
            'equipment': list(equipment),
        }
    
    @staticmethod
    def _transfer_production_reports(workorder, completed_workorder):
        """
        轉移報工記錄
        
        Args:
            workorder: 原始工單
            completed_workorder: 已完工工單
        """
        # 轉移作業員報工記錄
        for report in OperatorSupplementReport.objects.filter(
            workorder=workorder,
            approval_status='approved'
        ):
            CompletedProductionReport.objects.create(
                completed_workorder=completed_workorder,
                report_date=report.work_date,
                process_name=report.process_name,
                operator=report.operator.name if report.operator else '-',
                equipment=report.equipment.name if report.equipment else '-',
                work_quantity=report.work_quantity or 0,
                defect_quantity=report.defect_quantity or 0,
                work_hours=float(report.work_hours_calculated or 0),
                overtime_hours=float(report.overtime_hours_calculated or 0),
                start_time=report.start_time,
                end_time=report.end_time,
                report_source='作業員補登報工',
                report_type='operator',
                remarks=report.remarks,
                abnormal_notes=report.abnormal_notes,
                approval_status=report.approval_status,
                approved_by=report.approved_by,
                approved_at=report.approved_at,
            )
        
        # 轉移SMT報工記錄
        for report in SMTSupplementReport.objects.filter(
            workorder=workorder,
            approval_status='approved'
        ):
            CompletedProductionReport.objects.create(
                completed_workorder=completed_workorder,
                report_date=report.work_date,
                process_name=report.operation,
                operator='-',
                equipment=report.equipment.name if report.equipment else '-',
                work_quantity=report.work_quantity or 0,
                defect_quantity=report.defect_quantity or 0,
                work_hours=float(report.work_hours_calculated or 0),
                overtime_hours=float(report.overtime_hours_calculated or 0),
                start_time=report.start_time,
                end_time=report.end_time,
                report_source='SMT報工',
                report_type='smt',
                remarks=report.remarks,
                abnormal_notes=report.abnormal_notes,
                approval_status=report.approval_status,
                approved_by=report.approved_by,
                approved_at=report.approved_at,
            ) 