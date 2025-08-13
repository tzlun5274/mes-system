"""
工單完工判斷服務
根據報工記錄判斷工單是否完工
"""

import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q
from workorder.models import WorkOrder, WorkOrderProduction, WorkOrderProductionDetail, CompletedWorkOrder
from workorder.workorder_reporting.models import BackupOperatorSupplementReport as OperatorSupplementReport, BackupSMTSupplementReport as SMTSupplementReport
from erp_integration.models import CompanyConfig

# 移除主管報工引用，避免混淆
# 主管職責：監督、審核、管理，不代為報工

logger = logging.getLogger(__name__)


class WorkOrderCompletionService:
    """
    工單完工服務
    處理工單完工時的資料轉移和統計計算
    """
    
    # 出貨包裝工序名稱（可配置）
    PACKAGING_PROCESS_NAME = "出貨包裝"
    
    # 完工判斷方法已移除，避免資料汙染
    # @staticmethod
    # def check_and_complete_workorder(workorder_id):
    #     """
    #     檢查工單是否達到完工條件並自動完工（優化版本）
    #     使用生產中記錄進行完工判斷，提升效能
    #     """
    #     此方法已移除
    
    @staticmethod
    def _get_packaging_quantity(workorder):
        """
        獲取工單的出貨包裝報工數量
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            int: 出貨包裝報工總數量
        """
        # 獲取出貨包裝工序的所有已核准報工記錄
        # 修復：正確查詢工序名稱，process 是外鍵，需要查詢 process.name
        packaging_reports = OperatorSupplementReport.objects.filter(
            workorder=workorder,
            process__name=WorkOrderCompletionService.PACKAGING_PROCESS_NAME,
            approval_status='approved'
        )
        
        # 計算總數量（良品數量）
        total_quantity = packaging_reports.aggregate(
            total=Sum('work_quantity')
        )['total'] or 0
        
        logger.debug(f"工單 {workorder.order_number} 出貨包裝報工數量: {total_quantity}")
        return total_quantity
    
    @staticmethod
    def _get_packaging_quantity_optimized(workorder):
        """
        優化版本：從生產中記錄獲取工單的出貨包裝報工數量
        直接查詢 WorkOrderProductionDetail，避免查詢大量原始報工記錄
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            int: 出貨包裝報工總數量
        """
        try:
            # 直接查詢生產中的出貨包裝記錄
            packaging_reports = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=workorder,
                process_name=WorkOrderCompletionService.PACKAGING_PROCESS_NAME,
                report_source='operator_supplement'  # 只統計作業員補登報工
            )
            
            # 計算總數量（良品數量）
            total_quantity = packaging_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            logger.debug(f"工單 {workorder.order_number} 出貨包裝報工數量(優化版): {total_quantity}")
            return total_quantity
            
        except Exception as e:
            logger.error(f"優化版出貨包裝數量查詢失敗: {str(e)}")
            # 如果優化版失敗，回退到原始方法
            return WorkOrderCompletionService._get_packaging_quantity(workorder)
    
    # 優化版本完工判斷方法已移除，避免資料汙染
    # @staticmethod
    # def check_and_complete_workorder_optimized(workorder_id):
    #     """
    #     優化版本：檢查工單是否達到完工條件並自動完工
    #     使用生產中記錄進行判斷，提升效能
    #     """
    #     此方法已移除
    
    @staticmethod
    def _complete_workorder(workorder):
        """
        執行工單完工流程
        
        Args:
            workorder: WorkOrder 實例
        """
        # 更新工單狀態
        workorder.status = 'completed'
        workorder.completed_at = timezone.now()
        workorder.save()
        
        # 更新生產記錄
        if hasattr(workorder, 'production_record') and workorder.production_record:
            production_record = workorder.production_record
            production_record.status = 'completed'
            production_record.production_end_date = timezone.now()
            production_record.save()
        
        # 更新所有工序狀態為已完成
        for process in workorder.processes.all():
            process.status = 'completed'
            process.actual_end_time = timezone.now()
            process.save()
        
        logger.info(f"工單 {workorder.order_number} 狀態已更新為完工")
    
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
                
                # 安全地獲取生產記錄（可能為None）
                production_record = None
                try:
                    production_record = workorder.production_record
                except:
                    logger.warning(f"工單 {workorder.order_number} 沒有生產記錄，將使用None")
                
                # 建立已完工工單
                completed_workorder = CompletedWorkOrder.objects.create(
                    original_workorder_id=workorder_id,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    company_code=workorder.company_code,
                    company_name=(
                        CompanyConfig.objects.filter(company_code=workorder.company_code).first().company_name
                        if workorder.company_code and CompanyConfig.objects.filter(company_code=workorder.company_code).exists()
                        else ""
                    ),
                    planned_quantity=workorder.quantity,
                    completed_quantity=stats['total_good_quantity'],
                    status='completed',
                    created_at=workorder.created_at,
                    started_at=workorder.start_time,
                    completed_at=timezone.now(),
                    production_record=production_record,  # 可能為None
                    **stats
                )
                
                # 轉移工序資料
                WorkOrderCompletionService._transfer_processes(workorder, completed_workorder)
                
                # 轉移報工記錄
                WorkOrderCompletionService._transfer_production_reports(workorder, completed_workorder)
                
                # 清理生產中工單資料
                WorkOrderCompletionService._cleanup_production_data(workorder)
                
                # 刪除原始工單記錄（已轉移到已完工工單表）
                workorder.delete()
                
                logger.info(f"工單 {workorder.order_number} 成功轉移到已完工模組")
                return completed_workorder
                
        except Exception as e:
            logger.error(f"轉移工單 {workorder_id} 時發生錯誤: {str(e)}")
            raise
    
    @staticmethod
    def _cleanup_production_data(workorder):
        """
        清理生產中工單的資料，從生產中工單表移除已完工的資料
        注意：原始報工記錄永久保存，只清理生產中相關記錄
        
        Args:
            workorder: WorkOrder 實例
        """
        try:
            # 注意：原始報工記錄（OperatorSupplementReport, SMTSupplementReport）
            # 移除主管報工引用，避免混淆
            # 主管職責：監督、審核、管理，不代為報工
            
            # 刪除工序記錄
            workorder.processes.all().delete()
            
            # 刪除工序日誌
            from workorder.models import WorkOrderProcessLog
            WorkOrderProcessLog.objects.filter(workorder_process__workorder=workorder).delete()
            
            # 刪除派工記錄
            from workorder.models import DispatchLog
            DispatchLog.objects.filter(workorder=workorder).delete()
            
            # 刪除工單分配記錄
            from workorder.models import WorkOrderAssignment
            WorkOrderAssignment.objects.filter(workorder=workorder).delete()
            
            # 刪除生產記錄
            if hasattr(workorder, 'production_record') and workorder.production_record:
                workorder.production_record.delete()
            
            # 刪除生產明細記錄（這些記錄已經轉移到已完工工單）
            WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=workorder
            ).delete()
            
            logger.info(f"工單 {workorder.order_number} 的生產中資料已清理（原始報工記錄保留）")
            
        except Exception as e:
            logger.error(f"清理工單 {workorder.order_number} 生產資料時發生錯誤: {str(e)}")
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
                process_order=process.step_order,
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
            process=process.process_name,
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
            # 修復：正確處理時間欄位，將 TimeField 轉換為 DateTimeField
            start_datetime = None
            end_datetime = None
            if report.start_time and report.work_date:
                from django.utils import timezone
                start_datetime = timezone.make_aware(
                    datetime.combine(report.work_date, report.start_time)
                )
            if report.end_time and report.work_date:
                from django.utils import timezone
                end_datetime = timezone.make_aware(
                    datetime.combine(report.work_date, report.end_time)
                )
            
            CompletedProductionReport.objects.create(
                completed_workorder=completed_workorder,
                report_date=report.work_date,
                process_name=report.process.name if report.process else '-',
                operator=report.operator.name if report.operator else '-',
                equipment=report.equipment.name if report.equipment else '-',
                work_quantity=report.work_quantity or 0,
                defect_quantity=report.defect_quantity or 0,
                work_hours=float(report.work_hours_calculated or 0),
                overtime_hours=float(report.overtime_hours_calculated or 0),
                start_time=start_datetime,
                end_time=end_datetime,
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
            # 修復：正確處理時間欄位
            start_datetime = None
            end_datetime = None
            if report.start_time and report.work_date:
                from django.utils import timezone
                start_datetime = timezone.make_aware(
                    datetime.combine(report.work_date, report.start_time)
                )
            if report.end_time and report.work_date:
                from django.utils import timezone
                end_datetime = timezone.make_aware(
                    datetime.combine(report.work_date, report.end_time)
                )
            
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
                start_time=start_datetime,
                end_time=end_datetime,
                report_source='SMT報工',
                report_type='smt',
                remarks=report.remarks,
                abnormal_notes=report.abnormal_notes,
                approval_status=report.approval_status,
                approved_by=report.approved_by,
                approved_at=report.approved_at,
            ) 