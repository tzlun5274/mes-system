"""
生產報工記錄同步服務
將所有已核准的報工記錄同步到生產中工單詳情資料表
"""

import logging
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder, WorkOrderProduction, WorkOrderProductionDetail
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport

logger = logging.getLogger(__name__)


class ProductionReportSyncService:
    """
    生產報工記錄同步服務
    將所有已核准的報工記錄同步到生產中工單詳情資料表
    """
    
    @staticmethod
    def sync_all_approved_reports():
        """
        同步所有已核准的報工記錄到生產中工單詳情資料表
        使用公司代號 + 工單號碼 + 產品編號作為唯一性識別
        """
        try:
            logger.info("開始同步所有已核准的報工記錄...")
            
            # 1. 同步作業員補登報工記錄
            logger.info("開始同步作業員補登報工記錄...")
            ProductionReportSyncService._sync_operator_reports()
            
            # 2. 同步SMT報工記錄
            logger.info("開始同步SMT報工記錄...")
            ProductionReportSyncService._sync_smt_reports()
            
            # 3. 同步主管報工記錄
            logger.info("開始同步主管報工記錄...")
            ProductionReportSyncService._sync_supervisor_reports()
            
            logger.info("所有已核准報工記錄同步完成")
            return True
            
        except Exception as e:
            logger.error(f"同步報工記錄失敗: {str(e)}")
            import traceback
            logger.error(f"詳細錯誤信息: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def _sync_operator_reports():
        """同步作業員補登報工記錄"""
        try:
            operator_reports = OperatorSupplementReport.objects.filter(
                approval_status='approved'
            ).select_related('workorder', 'operator', 'equipment', 'process')
            
            logger.info(f"找到 {operator_reports.count()} 筆已核准的作業員報工記錄")
            
            for report in operator_reports:
                try:
                    ProductionReportSyncService._create_or_update_production_detail(
                        workorder=report.workorder,
                        process_name=report.process.name if report.process else '',
                        report_date=report.work_date,
                        report_time=report.start_time or timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=report.operator.name if report.operator else None,
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='operator_supplement',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        remarks=report.remarks,
                        abnormal_notes=report.abnormal_notes,
                        original_report_id=report.id,
                        original_report_type='operator'
                    )
                except Exception as e:
                    logger.error(f"同步作業員報工記錄 {report.id} 失敗: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"同步作業員報工記錄失敗: {str(e)}")
            raise
    
    @staticmethod
    def _sync_smt_reports():
        """同步SMT報工記錄"""
        smt_reports = SMTProductionReport.objects.filter(
            approval_status='approved'
        ).select_related('workorder', 'equipment')
        
        for report in smt_reports:
            ProductionReportSyncService._create_or_update_production_detail(
                workorder=report.workorder,
                process_name=report.operation,
                report_date=report.work_date,
                report_time=report.start_time or timezone.now(),
                work_quantity=report.work_quantity or 0,
                defect_quantity=report.defect_quantity or 0,
                operator=None,  # SMT報工通常沒有作業員
                equipment=report.equipment.name if report.equipment else None,
                report_source='smt',
                start_time=report.start_time,
                end_time=report.end_time,
                remarks=report.remarks,
                abnormal_notes=report.abnormal_notes,
                original_report_id=report.id,
                original_report_type='smt'
            )
    
    @staticmethod
    def _sync_supervisor_reports():
        """同步主管報工記錄"""
        supervisor_reports = SupervisorProductionReport.objects.filter(
            approval_status='approved'
        ).select_related('workorder', 'operator', 'equipment')
        
        for report in supervisor_reports:
            ProductionReportSyncService._create_or_update_production_detail(
                workorder=report.workorder,
                process_name=report.process.name if report.process else '',
                report_date=report.work_date,
                report_time=report.start_time or timezone.now(),
                work_quantity=report.work_quantity or 0,
                defect_quantity=report.defect_quantity or 0,
                operator=report.operator.name if report.operator else None,
                equipment=report.equipment.name if report.equipment else None,
                report_source='supervisor',
                start_time=report.start_time,
                end_time=report.end_time,
                remarks=report.remarks,
                abnormal_notes=report.abnormal_notes,
                original_report_id=report.id,
                original_report_type='supervisor'
            )
    
    @staticmethod
    def _create_or_update_production_detail(
        workorder, process_name, report_date, report_time, 
        work_quantity, defect_quantity, operator, equipment,
        report_source, start_time, end_time, remarks, abnormal_notes,
        original_report_id, original_report_type
    ):
        """
        建立或更新生產報工明細記錄
        使用公司代號 + 工單號碼 + 產品編號 + 工序名稱 + 報工日期作為唯一性識別
        """
        try:
            # 確保生產中工單記錄存在
            production_record, created = WorkOrderProduction.objects.get_or_create(
                workorder=workorder,
                defaults={
                    'status': 'in_production',
                    'current_process': process_name,
                }
            )
            
            # 檢查是否已存在相同的報工記錄（避免重複）
            existing_detail = WorkOrderProductionDetail.objects.filter(
                workorder_production=production_record,
                process_name=process_name,
                report_date=report_date,
                operator=operator or '',
                equipment=equipment or '',
                work_quantity=work_quantity,
                defect_quantity=defect_quantity,
                report_source=report_source
            ).first()
            
            if existing_detail:
                # 如果記錄已存在，更新時間和備註
                existing_detail.report_time = report_time
                existing_detail.start_time = start_time
                existing_detail.end_time = end_time
                existing_detail.remarks = remarks or existing_detail.remarks
                existing_detail.abnormal_notes = abnormal_notes or existing_detail.abnormal_notes
                existing_detail.updated_at = timezone.now()
                existing_detail.save()
                logger.debug(f"更新已存在的報工記錄: {workorder.order_number} - {process_name}")
            else:
                # 建立新的報工記錄
                WorkOrderProductionDetail.objects.create(
                    workorder_production=production_record,
                    process_name=process_name,
                    report_date=report_date,
                    report_time=report_time,
                    work_quantity=work_quantity,
                    defect_quantity=defect_quantity,
                    operator=operator,
                    equipment=equipment,
                    report_source=report_source,
                    start_time=start_time,
                    end_time=end_time,
                    remarks=remarks,
                    abnormal_notes=abnormal_notes,
                    created_by=f"同步服務({original_report_type})"
                )
                logger.debug(f"建立新的報工記錄: {workorder.order_number} - {process_name}")
                
        except Exception as e:
            logger.error(f"建立報工記錄失敗 - 工單: {workorder.order_number}, 工序: {process_name}, 錯誤: {str(e)}")
    
    @staticmethod
    def sync_specific_workorder(workorder_id):
        """
        同步特定工單的所有已核准報工記錄
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            with transaction.atomic():
                # 同步該工單的作業員報工記錄
                operator_reports = OperatorSupplementReport.objects.filter(
                    workorder=workorder,
                    approval_status='approved'
                ).select_related('operator', 'equipment')
                
                for report in operator_reports:
                    ProductionReportSyncService._create_or_update_production_detail(
                        workorder=workorder,
                        process_name=report.process.name if report.process else '',
                        report_date=report.work_date,
                        report_time=report.start_time or timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=report.operator.name if report.operator else None,
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='operator_supplement',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        remarks=report.remarks,
                        abnormal_notes=report.abnormal_notes,
                        original_report_id=report.id,
                        original_report_type='operator'
                    )
                
                # 同步該工單的SMT報工記錄
                smt_reports = SMTProductionReport.objects.filter(
                    workorder=workorder,
                    approval_status='approved'
                ).select_related('equipment')
                
                for report in smt_reports:
                    ProductionReportSyncService._create_or_update_production_detail(
                        workorder=workorder,
                        process_name=report.operation,
                        report_date=report.work_date,
                        report_time=report.start_time or timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=None,
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='smt',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        remarks=report.remarks,
                        abnormal_notes=report.abnormal_notes,
                        original_report_id=report.id,
                        original_report_type='smt'
                    )
                
                # 同步該工單的主管報工記錄
                supervisor_reports = SupervisorProductionReport.objects.filter(
                    workorder=workorder,
                    approval_status='approved'
                ).select_related('operator', 'equipment')
                
                for report in supervisor_reports:
                    ProductionReportSyncService._create_or_update_production_detail(
                        workorder=workorder,
                        process_name=report.process.name if report.process else '',
                        report_date=report.work_date,
                        report_time=report.start_time or timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=report.operator.name if report.operator else None,
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='supervisor',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        remarks=report.remarks,
                        abnormal_notes=report.abnormal_notes,
                        original_report_id=report.id,
                        original_report_type='supervisor'
                    )
                
                logger.info(f"工單 {workorder.order_number} 的報工記錄同步完成")
                return True
                
        except WorkOrder.DoesNotExist:
            logger.error(f"工單不存在: {workorder_id}")
            return False
        except Exception as e:
            logger.error(f"同步工單報工記錄失敗: {str(e)}")
            return False 