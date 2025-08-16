"""
生產填報記錄同步服務
將所有已核准的填報記錄同步到生產中工單詳情資料表
"""

import logging
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder, WorkOrderProduction, WorkOrderProductionDetail
from erp_integration.models import CompanyConfig

logger = logging.getLogger(__name__)

class ProductionReportSyncService:
    """
    生產填報記錄同步服務
    將所有已核准的填報記錄同步到生產中工單詳情資料表
    """
    
    @staticmethod
    def sync_all_approved_reports():
        """
        同步所有已核准的填報記錄到生產中工單詳情資料表
        使用公司代號 + 工單號碼 + 產品編號作為唯一性識別
        """
        try:
            logger.info("開始同步所有已核准的填報記錄...")
            
            # 1. 同步作業員補登填報記錄
            logger.info("開始同步作業員補登填報記錄...")
            ProductionReportSyncService._sync_operator_reports()
            
            # 2. 同步SMT填報記錄
            logger.info("開始同步SMT填報記錄...")
            # ProductionReportSyncService._sync_smt_reports()  # 暫時停用
            
            # 移除主管報工同步，避免混淆
            # 主管職責：監督、審核、管理，不代為報工
            
            logger.info("所有已核准填報記錄同步完成")
            return True
            
        except Exception as e:
            logger.error(f"同步填報記錄失敗: {str(e)}")
            import traceback
            logger.error(f"詳細錯誤信息: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def _sync_operator_reports():
        """同步作業員補登填報記錄"""
        try:
            from workorder.models import CompletedProductionReport
            operator_reports = CompletedProductionReport.objects.filter(
                report_type='operator',
                approval_status='approved'
            ).select_related('completed_workorder')
            
            logger.info(f"找到 {operator_reports.count()} 筆已核准的作業員填報記錄")
            
            for report in operator_reports:
                try:
                    ProductionReportSyncService._create_or_update_production_detail(
                        workorder=report.workorder,
                        process_name=report.process.name if report.process else '',
                        report_date=report.work_date,
                        report_time=timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=report.operator.name if report.operator else None,
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='operator_supplement',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        # 新增工時相關欄位
                        work_hours=float(report.work_hours_calculated) if report.work_hours_calculated else 0.0,
                        overtime_hours=float(report.overtime_hours_calculated) if report.overtime_hours_calculated else 0.0,
                        # 新增休息時間相關欄位
                        has_break=report.has_break,
                        break_start_time=report.break_start_time,
                        break_end_time=report.break_end_time,
                        break_hours=float(report.break_hours) if report.break_hours else 0.0,
                        # 新增報工類型
                        report_type='operator',  # 固定為作業員類型
                        # 新增數量相關欄位
                        allocated_quantity=report.allocated_quantity or 0,
                        quantity_source=report.quantity_source,
                        allocation_notes=report.allocation_notes,
                        # 新增完工相關欄位
                        is_completed=report.is_completed,
                        completion_method=report.completion_method,
                        auto_completed=report.auto_completed,
                        completion_time=report.completion_time,
                        cumulative_quantity=report.cumulative_quantity or 0,
                        cumulative_hours=float(report.cumulative_hours) if report.cumulative_hours else 0.0,
                        # 新增核准相關欄位
                        approval_status=report.approval_status,
                        approved_by=report.approved_by,
                        approved_at=report.approved_at if report.approved_at else None,
                        approval_remarks=report.approval_remarks,
                        rejection_reason=report.rejection_reason,
                        rejected_by=report.rejected_by,
                        rejected_at=report.rejected_at if report.rejected_at else None,
                        remarks=report.remarks,
                        abnormal_notes=report.abnormal_notes,
                        original_report_id=report.id,
                        original_report_type='operator'
                    )
                except Exception as e:
                    logger.error(f"同步作業員填報記錄 {report.id} 失敗: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"同步作業員填報記錄失敗: {str(e)}")
            raise
    
    @staticmethod
    def _sync_smt_reports():
        """同步SMT填報記錄"""
        try:
            smt_reports = SMTSupplementReport.objects.filter(
                approval_status='approved'
            ).select_related('workorder', 'equipment')
            
            logger.info(f"找到 {smt_reports.count()} 筆已核准的SMT填報記錄")
            
            for report in smt_reports:
                try:
                    ProductionReportSyncService._create_or_update_production_detail(
                        workorder=report.workorder,
                        process_name=report.operation,
                        report_date=report.work_date,
                        report_time=timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=None,  # SMT 不需要作業員
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='smt',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        # 新增工時相關欄位
                        work_hours=float(report.work_hours_calculated) if report.work_hours_calculated else 0.0,
                        overtime_hours=float(report.overtime_hours_calculated) if report.overtime_hours_calculated else 0.0,
                        # SMT 沒有休息時間相關欄位，設為預設值
                        has_break=False,
                        break_start_time=None,
                        break_end_time=None,
                        break_hours=0.0,
                        # SMT 沒有數量分配相關欄位，設為預設值
                        allocated_quantity=0,
                        quantity_source='original',
                        allocation_notes=''
                    )
                except Exception as e:
                    logger.error(f"同步SMT填報記錄 {report.id} 失敗: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"同步SMT填報記錄失敗: {str(e)}")
            raise
    
    @staticmethod
    def _create_or_update_production_detail(
        workorder, process_name, report_date, report_time, 
        work_quantity, defect_quantity, operator, equipment,
        report_source, start_time, end_time, remarks, abnormal_notes,
        original_report_id, original_report_type,
        # 新增參數
        work_hours=0.0, overtime_hours=0.0,
        has_break=False, break_start_time=None, break_end_time=None, break_hours=0.0,
        report_type='normal',
        allocated_quantity=0, quantity_source='original', allocation_notes='',
        is_completed=False, completion_method='manual', auto_completed=False, 
        completion_time=None, cumulative_quantity=0, cumulative_hours=0.0,
        approval_status='approved', approved_by=None, approved_at=None, 
        approval_remarks='', rejection_reason='', rejected_by=None, rejected_at=None
    ):
        """
        建立或更新生產報工明細記錄
        使用公司代號 + 工單號碼 + 產品編號 + 工序名稱 + 報工日期作為唯一性識別
        """
        try:
            if not workorder:
                logger.error("工單為空，無法建立填報記錄")
                return False
                
            # 確保生產中工單記錄存在
            production_record, created = WorkOrderProduction.objects.get_or_create(
                workorder=workorder,
                defaults={
                    'status': 'in_production',
                    'current_process': process_name,
                }
            )
            
            # 解析公司名稱（用於顯示）
            company_name_value = None
            try:
                if workorder and workorder.company_code:
                    cfg = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                    if cfg:
                        company_name_value = cfg.company_name
            except Exception:
                company_name_value = None

            # 檢查是否已存在相同的填報記錄（避免重複）
            # 1) 以來源紀錄唯一鍵判斷（最可靠）
            existing_detail = None
            if original_report_id is not None and original_report_type:
                existing_detail = WorkOrderProductionDetail.objects.filter(
                    workorder_production=production_record,
                    original_report_id=original_report_id,
                    original_report_type=original_report_type,
                ).first()
            # 2) 退而求其次：以主要欄位比對（需處理 None 與空字串差異）
            if existing_detail is None:
                from django.db.models import Q
                operator_q = Q(operator__isnull=True) if operator in (None, '') else Q(operator=operator)
                equipment_q = Q(equipment__isnull=True) if equipment in (None, '') else Q(equipment=equipment)
                existing_detail = WorkOrderProductionDetail.objects.filter(
                    Q(workorder_production=production_record),
                    Q(process_name=process_name),
                    Q(report_date=report_date),
                    operator_q,
                    equipment_q,
                    Q(work_quantity=work_quantity),
                    Q(defect_quantity=defect_quantity),
                    Q(report_source=report_source)
                ).first()
            
            if existing_detail:
                # 如果記錄已存在，更新所有欄位
                existing_detail.report_time = report_time
                existing_detail.start_time = start_time
                existing_detail.end_time = end_time
                existing_detail.work_hours = work_hours
                existing_detail.overtime_hours = overtime_hours
                existing_detail.has_break = has_break
                existing_detail.break_start_time = break_start_time
                existing_detail.break_end_time = break_end_time
                existing_detail.break_hours = break_hours
                existing_detail.report_type = report_type
                existing_detail.allocated_quantity = allocated_quantity
                existing_detail.quantity_source = quantity_source
                existing_detail.allocation_notes = allocation_notes
                existing_detail.is_completed = is_completed
                existing_detail.completion_method = completion_method
                existing_detail.auto_completed = auto_completed
                existing_detail.completion_time = completion_time
                existing_detail.cumulative_quantity = cumulative_quantity
                existing_detail.cumulative_hours = cumulative_hours
                existing_detail.approval_status = approval_status
                existing_detail.approved_by = approved_by
                existing_detail.approved_at = approved_at
                existing_detail.approval_remarks = approval_remarks
                existing_detail.rejection_reason = rejection_reason
                existing_detail.rejected_by = rejected_by
                existing_detail.rejected_at = rejected_at
                existing_detail.remarks = remarks or existing_detail.remarks
                existing_detail.abnormal_notes = abnormal_notes or existing_detail.abnormal_notes
                if company_name_value:
                    existing_detail.company_name = company_name_value
                existing_detail.updated_at = timezone.now()
                existing_detail.save()
                logger.debug(f"更新已存在的填報記錄: {workorder.order_number} - {process_name}")
                return True
            else:
                # 建立新的填報記錄
                detail = WorkOrderProductionDetail.objects.create(
                    workorder_production=production_record,
                    process_name=process_name,
                    report_date=report_date,
                    report_time=report_time,
                    work_quantity=work_quantity,
                    defect_quantity=defect_quantity,
                    operator=operator,
                    equipment=equipment,
                    company_name=company_name_value,
                    report_source=report_source,
                    start_time=start_time,
                    end_time=end_time,
                    # 新增欄位
                    work_hours=work_hours,
                    overtime_hours=overtime_hours,
                    has_break=has_break,
                    break_start_time=break_start_time,
                    break_end_time=break_end_time,
                    break_hours=break_hours,
                    report_type=report_type,
                    allocated_quantity=allocated_quantity,
                    quantity_source=quantity_source,
                    allocation_notes=allocation_notes,
                    is_completed=is_completed,
                    completion_method=completion_method,
                    auto_completed=auto_completed,
                    completion_time=completion_time,
                    cumulative_quantity=cumulative_quantity,
                    cumulative_hours=cumulative_hours,
                    approval_status=approval_status,
                    approved_by=approved_by,
                    approved_at=approved_at,
                    approval_remarks=approval_remarks,
                    rejection_reason=rejection_reason,
                    rejected_by=rejected_by,
                    rejected_at=rejected_at,
                    remarks=remarks,
                    abnormal_notes=abnormal_notes,
                    original_report_id=original_report_id,
                    original_report_type=original_report_type,
                    created_by=f"同步服務({original_report_type})"
                )
                logger.debug(f"建立新的填報記錄: {workorder.order_number} - {process_name} (ID: {detail.id})")
                return True
                
        except Exception as e:
            error_msg = f"建立填報記錄失敗 - 工單: {workorder.order_number if workorder else 'None'}, 工序: {process_name}, 錯誤: {str(e)}"
            logger.error(error_msg)
            # 強制輸出錯誤信息
            print(f"同步錯誤: {error_msg}")
            import traceback
            print(f"詳細錯誤: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def sync_specific_workorder(workorder_id):
        """
        同步特定工單的所有已核准填報記錄
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            with transaction.atomic():
                # 同步該工單的作業員填報記錄
                from workorder.models import CompletedProductionReport
                operator_reports = CompletedProductionReport.objects.filter(
                    completed_workorder__order_number=workorder.order_number,
                    report_type='operator',
                    approval_status='approved'
                )
                
                for report in operator_reports:
                    ProductionReportSyncService._create_or_update_production_detail(
                        workorder=workorder,
                        process_name=report.process.name if report.process else '',
                        report_date=report.work_date,
                        report_time=timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=report.operator.name if report.operator else None,
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='operator_supplement',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        # 新增工時相關欄位
                        work_hours=float(report.work_hours_calculated) if report.work_hours_calculated else 0.0,
                        overtime_hours=float(report.overtime_hours_calculated) if report.overtime_hours_calculated else 0.0,
                        # 新增休息時間相關欄位
                        has_break=report.has_break,
                        break_start_time=report.break_start_time,
                        break_end_time=report.break_end_time,
                        break_hours=float(report.break_hours) if report.break_hours else 0.0,
                        # 新增報工類型
                        report_type='operator',  # 固定為作業員類型
                        # 新增數量相關欄位
                        allocated_quantity=report.allocated_quantity or 0,
                        quantity_source=report.quantity_source,
                        allocation_notes=report.allocation_notes,
                        # 新增完工相關欄位
                        is_completed=report.is_completed,
                        completion_method=report.completion_method,
                        auto_completed=report.auto_completed,
                        completion_time=report.completion_time,
                        cumulative_quantity=report.cumulative_quantity or 0,
                        cumulative_hours=float(report.cumulative_hours) if report.cumulative_hours else 0.0,
                        # 新增核准相關欄位
                        approval_status=report.approval_status,
                        approved_by=report.approved_by,
                        approved_at=report.approved_at if report.approved_at else None,
                        approval_remarks=report.approval_remarks,
                        rejection_reason=report.rejection_reason,
                        rejected_by=report.rejected_by,
                        rejected_at=report.rejected_at if report.rejected_at else None,
                        remarks=report.remarks,
                        abnormal_notes=report.abnormal_notes,
                        original_report_id=report.id,
                        original_report_type='operator'
                    )
                
                # 同步該工單的SMT填報記錄
                from workorder.models import CompletedProductionReport
                smt_reports = CompletedProductionReport.objects.filter(
                    completed_workorder__order_number=workorder.order_number,
                    report_type='smt',
                    approval_status='approved'
                )
                
                for report in smt_reports:
                    ProductionReportSyncService._create_or_update_production_detail(
                        workorder=workorder,
                        process_name=report.process_name,
                        report_date=report.work_date,
                        report_time=timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=None,
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='smt',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        # 新增工時相關欄位
                        work_hours=float(report.work_hours_calculated) if report.work_hours_calculated else 0.0,
                        overtime_hours=float(report.overtime_hours_calculated) if report.overtime_hours_calculated else 0.0,
                        # SMT 沒有休息時間相關欄位，設為預設值
                        has_break=False,
                        break_start_time=None,
                        break_end_time=None,
                        break_hours=0.0,
                        # 新增報工類型
                        report_type='smt',  # 固定為SMT類型
                        # SMT 沒有數量分配相關欄位，設為預設值
                        allocated_quantity=0,
                        quantity_source='original',
                        allocation_notes='',
                        # SMT 沒有完工相關欄位，設為預設值
                        is_completed=report.is_completed,
                        completion_method='manual',
                        auto_completed=False,
                        completion_time=None,
                        cumulative_quantity=0,
                        cumulative_hours=0.0,
                        # 新增核准相關欄位
                        approval_status=report.approval_status,
                        approved_by=report.approved_by,
                        approved_at=report.approved_at if report.approved_at else None,
                        approval_remarks=report.approval_remarks,
                        rejection_reason=report.rejection_reason,
                        rejected_by=report.rejected_by,
                        rejected_at=report.rejected_at if report.rejected_at else None,
                        remarks=report.remarks,
                        abnormal_notes=report.abnormal_notes,
                        original_report_id=report.id,
                        original_report_type='smt'
                    )
                
                logger.info(f"工單 {workorder.order_number} 的填報記錄同步完成")
                return True
                
        except WorkOrder.DoesNotExist:
            logger.error(f"工單不存在: {workorder_id}")
            return False
        except Exception as e:
            logger.error(f"同步工單填報記錄失敗: {str(e)}")
            return False 