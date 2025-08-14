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
from workorder.fill_work.models import FillWork
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
        # 獲取所有已核准的填報記錄
        fill_work_reports = FillWork.objects.filter(
            workorder=workorder.order_number,
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
        
        # 處理填報記錄
        for report in fill_work_reports:
            total_work_hours += float(report.work_hours_calculated or 0)
            total_overtime_hours += float(report.overtime_hours_calculated or 0)
            total_good_quantity += report.work_quantity or 0
            total_defect_quantity += report.defect_quantity or 0
            total_report_count += 1
            if report.operator:
                unique_operators.add(report.operator)
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
                process_name=report.process.name if report.process else '',
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

def create_missing_workorders_from_fillwork():
    """
    從填報資料創建缺失的工單
    以公司名稱/代號+製令號碼+產品編號作為唯一性識別
    """
    from .fill_work.models import FillWork
    from .models import WorkOrder
    from erp_integration.models import CompanyConfig
    from .workorder_erp.models import PrdMKOrdMain, CompanyOrder
    from django.db import transaction
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 統計資訊
    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    try:
        # 取得所有填報資料
        fill_works = FillWork.objects.all()
        
        for fill_work in fill_works:
            try:
                # 檢查必要欄位
                if not fill_work.company_name or not fill_work.workorder or not fill_work.product_id:
                    logger.warning(f"填報資料缺少必要欄位: ID={fill_work.id}")
                    error_count += 1
                    continue
                
                # 從公司名稱查找公司代號
                company_code = None
                try:
                    company_config = CompanyConfig.objects.filter(
                        company_name__icontains=fill_work.company_name
                    ).first()
                    
                    if company_config:
                        company_code = company_config.company_code
                    else:
                        # 如果找不到公司配置，嘗試從製令資料中查找
                        mkord_main = PrdMKOrdMain.objects.filter(
                            MKOrdNO=fill_work.workorder,
                            ProductID=fill_work.product_id
                        ).first()
                        
                        if mkord_main:
                            # 從製令資料中查找公司代號
                            company_order = CompanyOrder.objects.filter(
                                mkordno=fill_work.workorder,
                                product_id=fill_work.product_id
                            ).first()
                            
                            if company_order:
                                company_code = company_order.company_code
                
                except Exception as e:
                    logger.error(f"查找公司代號時發生錯誤: {e}")
                    error_count += 1
                    continue
                
                if not company_code:
                    logger.warning(f"無法找到公司代號: 公司名稱={fill_work.company_name}, 工單號={fill_work.workorder}")
                    error_count += 1
                    continue
                
                # 檢查工單是否已存在
                existing_workorder = WorkOrder.objects.filter(
                    company_code=company_code,
                    order_number=fill_work.workorder,
                    product_code=fill_work.product_id
                ).first()
                
                if existing_workorder:
                    logger.info(f"工單已存在，跳過: {company_code}-{fill_work.workorder}-{fill_work.product_id}")
                    skipped_count += 1
                    continue
                
                # 創建新工單
                with transaction.atomic():
                    new_workorder = WorkOrder.objects.create(
                        company_code=company_code,
                        order_number=fill_work.workorder,
                        product_code=fill_work.product_id,
                        quantity=fill_work.planned_quantity or 0,
                        status='pending',
                        order_source='mes'  # 從填報資料創建的工單標記為MES來源
                    )
                    
                    created_count += 1
                    logger.info(f"成功創建工單: {new_workorder}")
                
            except Exception as e:
                logger.error(f"處理填報資料時發生錯誤 (ID={fill_work.id}): {e}")
                error_count += 1
                errors.append({
                    'fill_work_id': fill_work.id,
                    'error': str(e)
                })
        
        # 記錄統計結果
        logger.info(f"工單創建完成 - 成功: {created_count}, 跳過: {skipped_count}, 錯誤: {error_count}")
        
        return {
            'success': True,
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"創建缺失工單時發生嚴重錯誤: {e}")
        return {
            'success': False,
            'error': str(e),
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'errors': errors
        } 