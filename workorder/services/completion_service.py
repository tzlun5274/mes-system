"""
填報紀錄完工判斷服務
負責自動判斷工單是否達到完工條件，並執行完工流程
基於填報紀錄（FillWork）的出貨包裝數量進行判斷
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q
from workorder.models import (
    WorkOrder, WorkOrderProcess, WorkOrderProduction, 
    WorkOrderProductionDetail, CompletedWorkOrder, 
    CompletedWorkOrderProcess, CompletedProductionReport
)
from workorder.fill_work.models import FillWork
from erp_integration.models import CompanyConfig

logger = logging.getLogger(__name__)

class FillWorkCompletionService:
    """
    填報紀錄完工判斷服務類別
    負責自動判斷工單是否達到完工條件，並執行完工流程
    基於填報紀錄（FillWork）的出貨包裝數量進行判斷
    """
    
    # 完工判斷的工序名稱（可配置）
    PACKAGING_PROCESS_NAME = "出貨包裝"
    
    @staticmethod
    def check_workorder_completion(workorder_id):
        """
        檢查工單完工條件（基於填報紀錄）
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工檢查結果
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 獲取出貨包裝累計數量（從填報紀錄）
            packaging_quantity = FillWorkCompletionService._get_packaging_quantity_from_fillwork(workorder)
            
            # 判斷是否達到完工條件
            can_complete = packaging_quantity >= workorder.quantity
            
            # 計算完工進度百分比
            completion_percentage = (packaging_quantity / workorder.quantity * 100) if workorder.quantity > 0 else 0
            
            return {
                'workorder_id': workorder_id,
                'order_number': workorder.order_number,
                'planned_quantity': workorder.quantity,
                'packaging_quantity': packaging_quantity,
                'can_complete': can_complete,
                'completion_percentage': round(completion_percentage, 1),
                'reason': f"出貨包裝累計數量（填報紀錄）: {packaging_quantity}/{workorder.quantity}",
                'error': None
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'workorder_id': workorder_id,
                'error': f'工單 {workorder_id} 不存在'
            }
        except Exception as e:
            logger.error(f"檢查工單 {workorder_id} 完工條件時發生錯誤: {str(e)}")
            return {
                'workorder_id': workorder_id,
                'error': f'檢查完工條件時發生錯誤: {str(e)}'
            }
    
    @staticmethod
    def auto_complete_workorder(workorder_id):
        """
        自動完工工單（基於填報紀錄）
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工結果
        """
        try:
            # 先檢查完工條件
            completion_check = FillWorkCompletionService.check_workorder_completion(workorder_id)
            
            if completion_check.get('error'):
                return {
                    'success': False,
                    'message': completion_check['error']
                }
            
            # 執行完工流程
            with transaction.atomic():
                # 獲取工單
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                # 檢查是否已經轉移到已完工模組
                if CompletedWorkOrder.objects.filter(original_workorder_id=workorder_id).exists():
                    return {
                        'success': True,
                        'message': f"工單 {workorder.order_number} 已經轉移到已完工模組"
                    }
                
                # 檢查工單狀態
                if workorder.status == 'completed':
                    # 即使狀態是 completed，也要執行轉移
                    FillWorkCompletionService.transfer_workorder_to_completed(workorder_id)
                    return {
                        'success': True,
                        'message': f"工單 {workorder.order_number} 已成功轉移到已完工模組"
                    }
                
                # 檢查是否達到完工條件
                if not completion_check['can_complete']:
                    return {
                        'success': False,
                        'message': f"工單 {completion_check['order_number']} 尚未達到完工條件：{completion_check['reason']}"
                    }
                
                # 執行完整完工流程
                FillWorkCompletionService._complete_workorder(workorder)
                FillWorkCompletionService.transfer_workorder_to_completed(workorder_id)
                
                return {
                    'success': True,
                    'message': f"工單 {workorder.order_number} 已成功自動完工並轉移到已完工模組"
                }
                
        except Exception as e:
            logger.error(f"自動完工工單 {workorder_id} 時發生錯誤: {str(e)}")
            return {
                'success': False,
                'message': f"自動完工失敗: {str(e)}"
            }
    
    @staticmethod
    def check_and_complete_workorder(workorder_id):
        """
        檢查並完成工單（基於填報紀錄）
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            bool: 是否成功完工
        """
        try:
            with transaction.atomic():
                # 獲取工單
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                # 檢查是否已經轉移到已完工模組
                if CompletedWorkOrder.objects.filter(original_workorder_id=workorder_id).exists():
                    logger.info(f"工單 {workorder.order_number} 已經轉移到已完工模組")
                    return True
                
                # 檢查工單狀態
                if workorder.status == 'completed':
                    logger.info(f"工單 {workorder.order_number} 狀態是完工，但尚未轉移，執行轉移流程")
                    # 即使狀態是 completed，也要執行轉移
                    FillWorkCompletionService.transfer_workorder_to_completed(workorder_id)
                    return True
                
                # 獲取出貨包裝數量（從填報紀錄）
                packaging_quantity = FillWorkCompletionService._get_packaging_quantity_from_fillwork(workorder)
                
                # 判斷完工條件
                if packaging_quantity >= workorder.quantity:
                    # 執行完工流程
                    FillWorkCompletionService._complete_workorder(workorder)
                    FillWorkCompletionService.transfer_workorder_to_completed(workorder_id)
                    logger.info(f"工單 {workorder.order_number} 已成功完工並轉移")
                    return True
                else:
                    logger.debug(f"工單 {workorder.order_number} 尚未達到完工條件：包裝數量 {packaging_quantity} < 目標數量 {workorder.quantity}")
                    return False
                    
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"檢查工單 {workorder_id} 完工狀態時發生錯誤: {str(e)}")
            return False
    
    @staticmethod
    def _get_packaging_quantity_from_fillwork(workorder):
        """
        從填報紀錄獲取工單的出貨包裝累積數量（良品+不良品）
        
        Args:
            workorder: WorkOrder 實例
            
        Returns:
            int: 出貨包裝累積總數量（良品+不良品）
        """
        try:
            # 從填報紀錄查詢出貨包裝的填報記錄
            packaging_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                process__name__icontains='出貨包裝',
                approval_status='approved'
            )
            
            # 計算良品累積數量
            good_quantity = packaging_reports.aggregate(
                total=Sum('work_quantity')
            )['total'] or 0
            
            # 計算不良品累積數量
            defect_quantity = packaging_reports.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 總數量 = 良品 + 不良品
            total_quantity = good_quantity + defect_quantity
            
            # 記錄日誌
            logger.info(f"工單 {workorder.order_number} 出貨包裝累積數量（填報紀錄）: 良品={good_quantity}, 不良品={defect_quantity}, 總計={total_quantity}")
            
            return total_quantity
            
        except Exception as e:
            logger.error(f"獲取工單 {workorder.order_number} 出貨包裝累積數量時發生錯誤: {str(e)}")
            return 0
    
    @staticmethod
    def get_completion_summary(workorder_id):
        """
        獲取工單的完工判斷摘要資訊（基於填報紀錄）
        
        Args:
            workorder_id: 工單ID
            
        Returns:
            dict: 完工判斷摘要資訊
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 獲取出貨包裝累計數量（從填報紀錄）
            packaging_quantity = FillWorkCompletionService._get_packaging_quantity_from_fillwork(workorder)
            
            # 判斷是否達到完工條件
            can_complete = packaging_quantity >= workorder.quantity
            
            # 計算完工進度百分比
            completion_percentage = (packaging_quantity / workorder.quantity * 100) if workorder.quantity > 0 else 0
            
            # 獲取出貨包裝填報記錄詳情（從填報紀錄）
            packaging_details = []
            
            # 從填報紀錄獲取出貨包裝記錄
            packaging_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                process__name__icontains='出貨包裝',
                approval_status='approved'
            ).order_by('-work_date', '-start_time')
            
            for report in packaging_reports:
                packaging_details.append({
                    'source': '填報紀錄',
                    'report_date': report.work_date,
                    'operator': report.operator or '-',
                    'equipment': report.equipment or '-',
                    'work_quantity': report.work_quantity or 0,
                    'defect_quantity': report.defect_quantity or 0,
                    'work_hours': float(report.work_hours_calculated or 0),
                    'start_time': report.start_time,
                    'end_time': report.end_time,
                    'approval_status': report.approval_status,
                    'report_time': report.created_at,
                })
            
            return {
                'workorder_id': workorder_id,
                'order_number': workorder.order_number,
                'planned_quantity': workorder.quantity,
                'packaging_quantity': packaging_quantity,
                'can_complete': can_complete,
                'completion_percentage': round(completion_percentage, 1),
                'packaging_details': packaging_details,
                'packaging_count': len(packaging_details),
                'reason': f"出貨包裝累計數量（填報紀錄）: {packaging_quantity}/{workorder.quantity}",
                'error': None
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'error': f'工單 {workorder_id} 不存在'
            }
        except Exception as e:
            logger.error(f"獲取工單 {workorder_id} 完工判斷摘要時發生錯誤: {str(e)}")
            return {
                'error': f'獲取完工判斷摘要時發生錯誤: {str(e)}'
            }
    
    @staticmethod
    def _complete_workorder(workorder):
        """
        完成工單
        
        Args:
            workorder: 工單實例
        """
        try:
            # 更新工單狀態
            workorder.status = 'completed'
            workorder.completed_at = timezone.now()
            workorder.save()
            
            # 更新生產記錄
            if hasattr(workorder, 'production_record') and workorder.production_record:
                workorder.production_record.status = 'completed'
                workorder.production_record.production_end_date = timezone.now()
                workorder.production_record.save()
            
            # 更新所有工序狀態
            for process in workorder.processes.all():
                process.status = 'completed'
                process.actual_end_time = timezone.now()
                process.save()
            
            logger.info(f"工單 {workorder.order_number} 狀態已更新為完工")
            
        except Exception as e:
            logger.error(f"完成工單 {workorder.order_number} 時發生錯誤: {str(e)}")
            raise
    
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
                stats = FillWorkCompletionService._calculate_workorder_stats(workorder)
                
                # 獲取生產記錄（可能為None）
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
                FillWorkCompletionService._transfer_processes(workorder, completed_workorder)
                
                # 轉移填報記錄
                FillWorkCompletionService._transfer_production_reports(workorder, completed_workorder)
                
                # 清理生產中工單資料
                FillWorkCompletionService._cleanup_production_data(workorder)
                
                # 刪除原始工單記錄（已轉移到已完工工單表）
                workorder.delete()
                
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
            workorder: 工單實例
            
        Returns:
            dict: 統計資料
        """
        try:
            # 從填報記錄中獲取統計資料
            fill_work_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            )
            
            # 計算總工時統計資料（所有工序）
            total_work_hours = sum(report.work_hours_calculated or 0 for report in fill_work_reports)
            total_overtime_hours = sum(report.overtime_hours_calculated or 0 for report in fill_work_reports)
            
            # 計算出貨包裝工序的數量統計（以出貨包裝為主）
            packaging_reports = fill_work_reports.filter(
                process__name__icontains='出貨包裝'
            )
            total_good_quantity = sum(report.work_quantity or 0 for report in packaging_reports)
            total_defect_quantity = sum(report.defect_quantity or 0 for report in packaging_reports)
            
            # 獲取參與人員和設備
            unique_operators = list(set(report.operator for report in fill_work_reports if report.operator))
            unique_equipment = list(set(report.equipment for report in fill_work_reports if report.equipment))
            
            return {
                'total_work_hours': total_work_hours,
                'total_overtime_hours': total_overtime_hours,
                'total_all_hours': total_work_hours + total_overtime_hours,
                'total_good_quantity': total_good_quantity,
                'total_defect_quantity': total_defect_quantity,
                'total_report_count': fill_work_reports.count(),
                'unique_operators': unique_operators,
                'unique_equipment': unique_equipment,
            }
            
        except Exception as e:
            logger.error(f"計算工單 {workorder.order_number} 統計資料時發生錯誤: {str(e)}")
            return {
                'total_work_hours': 0.0,
                'total_overtime_hours': 0.0,
                'total_all_hours': 0.0,
                'total_good_quantity': 0,
                'total_defect_quantity': 0,
                'total_report_count': 0,
                'unique_operators': [],
                'unique_equipment': [],
            }
    
    @staticmethod
    def _transfer_processes(workorder, completed_workorder):
        """
        轉移工序資料
        
        Args:
            workorder: 原始工單
            completed_workorder: 已完工工單
        """
        try:
            for process in workorder.processes.all():
                # 計算工序統計資料
                process_reports = FillWork.objects.filter(
                    workorder=workorder.order_number,
                    process__name=process.process_name,  # 修正：使用 process__name
                    approval_status='approved'
                )
                
                process_stats = {
                    'total_work_hours': sum(report.work_hours_calculated or 0 for report in process_reports),
                    'total_good_quantity': sum(report.work_quantity or 0 for report in process_reports),
                    'total_defect_quantity': sum(report.defect_quantity or 0 for report in process_reports),
                    'report_count': process_reports.count(),
                }
                
                # 建立已完工工序記錄
                CompletedWorkOrderProcess.objects.create(
                    completed_workorder=completed_workorder,
                    process_name=process.process_name,
                    process_order=process.step_order,
                    planned_quantity=process.planned_quantity,
                    completed_quantity=process.completed_quantity,
                    status='completed',
                    assigned_operator=process.assigned_operator,
                    assigned_equipment=process.assigned_equipment,
                    **process_stats
                )
                
        except Exception as e:
            logger.error(f"轉移工序資料時發生錯誤: {str(e)}")
            raise
    
    @staticmethod
    def _transfer_production_reports(workorder, completed_workorder):
        """
        轉移填報記錄
        
        Args:
            workorder: 原始工單
            completed_workorder: 已完工工單
        """
        try:
            # 從填報記錄中獲取填報資料
            fill_work_reports = FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            )
            
            for report in fill_work_reports:
                # 建立已完工填報記錄
                CompletedProductionReport.objects.create(
                    completed_workorder=completed_workorder,
                    report_type='fill_work',
                    report_source='operator',
                    operator=report.operator,
                    process_name=report.process.name if hasattr(report.process, 'name') else str(report.process),
                    equipment=report.equipment or '',
                    report_date=report.work_date,
                    start_time=report.start_datetime if hasattr(report, 'start_datetime') else None,
                    end_time=report.end_datetime if hasattr(report, 'end_datetime') else None,
                    work_quantity=report.work_quantity,
                    defect_quantity=report.defect_quantity,
                    work_hours=report.work_hours_calculated or 0.0,
                    overtime_hours=report.overtime_hours_calculated or 0.0,
                    remarks=report.remarks,
                    abnormal_notes=report.abnormal_notes,
                    approval_status='approved'
                )
                
        except Exception as e:
            logger.error(f"轉移填報記錄時發生錯誤: {str(e)}")
            raise
    
    @staticmethod
    def _cleanup_production_data(workorder):
        """
        清理生產中工單資料
        
        Args:
            workorder: 工單實例
        """
        try:
            # 刪除工序記錄
            workorder.processes.all().delete()
            
            # 刪除生產記錄（如果存在）
            if hasattr(workorder, 'production_record') and workorder.production_record:
                # 先刪除生產記錄的明細資料
                workorder.production_record.production_details.all().delete()
                # 再刪除生產記錄本身
                workorder.production_record.delete()
            
            # 注意：不刪除填報記錄（FillWork），因為它們是原始的填報資料
            # 只將完工標記設為 True 表示已完工
            from workorder.fill_work.models import FillWork
            FillWork.objects.filter(
                workorder=workorder.order_number,
                approval_status='approved'
            ).update(is_completed=True)
            
            # 刪除工序日誌記錄
            from workorder.models import WorkOrderProcessLog
            WorkOrderProcessLog.objects.filter(
                workorder_process__workorder=workorder
            ).delete()
            
            # 刪除派工記錄
            from workorder.models import DispatchLog
            DispatchLog.objects.filter(
                workorder=workorder
            ).delete()
            
            # 刪除工單分配記錄
            from workorder.models import WorkOrderAssignment
            WorkOrderAssignment.objects.filter(
                workorder=workorder
            ).delete()
            
            # 刪除工序產能記錄
            from workorder.models import WorkOrderProcessCapacity
            WorkOrderProcessCapacity.objects.filter(
                workorder_process__workorder=workorder
            ).delete()
            
            # 刪除派工單相關記錄
            try:
                from workorder.workorder_dispatch.models import WorkOrderDispatch, WorkOrderDispatchProcess, DispatchHistory
                
                # 刪除派工單歷史記錄
                DispatchHistory.objects.filter(
                    workorder_dispatch__order_number=workorder.order_number
                ).delete()
                
                # 刪除派工單工序明細
                WorkOrderDispatchProcess.objects.filter(
                    workorder_dispatch__order_number=workorder.order_number
                ).delete()
                
                # 刪除派工單主表記錄
                WorkOrderDispatch.objects.filter(
                    order_number=workorder.order_number
                ).delete()
                
            except ImportError:
                logger.warning(f"無法導入派工單模組，跳過派工單記錄清理")
            except Exception as e:
                logger.warning(f"清理派工單記錄時發生錯誤: {str(e)}")
            
            logger.info(f"工單 {workorder.order_number} 生產資料已清理")
            
        except Exception as e:
            logger.error(f"清理工單 {workorder.order_number} 生產資料時發生錯誤: {str(e)}")
            raise 