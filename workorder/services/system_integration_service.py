"""
系統整合服務
修復 MES 系統中各個模組之間的對應關係
包括：工單管理、派工單管理、生產監控、已完工工單等
"""

import logging
from django.db import transaction
from django.utils import timezone
from workorder.models import WorkOrder, WorkOrderProcess
from workorder.workorder_dispatch.models import WorkOrderDispatch
from workorder.fill_work.models import FillWork
import json

logger = logging.getLogger(__name__)


class SystemIntegrationService:
    """
    系統整合服務
    負責修復和維護各個模組之間的對應關係
    """
    
    @staticmethod
    def diagnose_system_issues():
        """
        診斷系統問題
        檢查各個模組之間的對應關係
        """
        issues = []
        
        try:
            # 1. 檢查工單與派工單的對應關係
            workorders = WorkOrder.objects.all()
            dispatches = WorkOrderDispatch.objects.all()
            
            # 統計基本數據
            total_workorders = workorders.count()
            total_dispatches = dispatches.count()
            
            # 檢查對應關係
            workorder_numbers = set(workorders.values_list('order_number', flat=True))
            dispatch_numbers = set(dispatches.values_list('order_number', flat=True))
            
            # 找出不匹配的工單
            workorders_without_dispatch = workorder_numbers - dispatch_numbers
            dispatches_without_workorder = dispatch_numbers - workorder_numbers
            
            if workorders_without_dispatch:
                issues.append({
                    'type': 'missing_dispatch',
                    'message': f'發現 {len(workorders_without_dispatch)} 個工單沒有對應的派工單',
                    'details': list(workorders_without_dispatch)[:10]  # 只顯示前10個
                })
            
            if dispatches_without_workorder:
                issues.append({
                    'type': 'orphan_dispatch',
                    'message': f'發現 {len(dispatches_without_workorder)} 個派工單沒有對應的工單',
                    'details': list(dispatches_without_workorder)[:10]
                })
            
            # 2. 檢查狀態不一致問題
            pending_workorders = workorders.filter(status='pending')
            dispatched_workorders = dispatches.filter(status='dispatched')
            
            # 找出狀態不一致的工單
            inconsistent_status = []
            for wo in pending_workorders:
                dispatch = dispatches.filter(order_number=wo.order_number).first()
                if dispatch and dispatch.status == 'dispatched':
                    inconsistent_status.append(wo.order_number)
            
            if inconsistent_status:
                issues.append({
                    'type': 'status_inconsistency',
                    'message': f'發現 {len(inconsistent_status)} 個工單狀態不一致',
                    'details': inconsistent_status[:10]
                })
            
            # 3. 檢查工序分配問題
            workorders_with_processes = workorders.filter(processes__isnull=False).distinct()
            workorders_with_allocations = workorders_with_processes.filter(
                processes__assigned_operator__isnull=False
            ).exclude(processes__assigned_operator='').distinct()
            
            # 有工序分配但派工單狀態還是pending的
            misaligned_dispatch_status = []
            for wo in workorders_with_allocations:
                dispatch = dispatches.filter(order_number=wo.order_number).first()
                if dispatch and dispatch.status == 'pending':
                    misaligned_dispatch_status.append(wo.order_number)
            
            if misaligned_dispatch_status:
                issues.append({
                    'type': 'dispatch_status_misaligned',
                    'message': f'發現 {len(misaligned_dispatch_status)} 個工單有工序分配但派工單狀態未更新',
                    'details': misaligned_dispatch_status[:10]
                })
            
            # 4. 檢查報工記錄對應問題
            fill_work_reports = FillWork.objects.all()
            
            # 檢查報工記錄對應的工單是否存在
            report_workorder_numbers = set(fill_work_reports.values_list('workorder', flat=True))
            
            orphan_reports = report_workorder_numbers - workorder_numbers
            
            if orphan_reports:
                issues.append({
                    'type': 'orphan_reports',
                    'message': f'發現 {len(orphan_reports)} 個報工記錄對應的工單不存在',
                    'details': list(orphan_reports)[:10]
                })
            
            return {
                'total_workorders': total_workorders,
                'total_dispatches': total_dispatches,
                'issues': issues,
                'summary': f'發現 {len(issues)} 類問題需要修復'
            }
            
        except Exception as e:
            logger.error(f"診斷系統問題時發生錯誤: {str(e)}")
            return {
                'error': str(e),
                'issues': []
            }
    
    @staticmethod
    def fix_missing_dispatches():
        """
        修復缺少派工單的工單
        為沒有派工單的工單建立對應的派工單
        """
        try:
            with transaction.atomic():
                workorders = WorkOrder.objects.all()
                existing_dispatch_numbers = set(
                    WorkOrderDispatch.objects.values_list('order_number', flat=True)
                )
                
                created_count = 0
                for workorder in workorders:
                    if workorder.order_number not in existing_dispatch_numbers:
                        WorkOrderDispatch.objects.create(
                            company_code=workorder.company_code,
                            order_number=workorder.order_number,
                            product_code=workorder.product_code,
                            planned_quantity=workorder.quantity,
                            status="in_production",  # 直接設定為生產中
                            dispatch_date=timezone.now().date(),
                            created_by="system_integration",
                        )
                        created_count += 1
                        logger.info(f"為工單 {workorder.order_number} 建立派工單（生產中狀態）")
                
                return {
                    'success': True,
                    'created_count': created_count,
                    'message': f'成功為 {created_count} 個工單建立派工單'
                }
                
        except Exception as e:
            logger.error(f"修復缺少派工單時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def fix_dispatch_status_alignment():
        """
        修復派工單狀態對齊
        根據工單的工序分配情況更新派工單狀態
        """
        try:
            from .dispatch_status_service import DispatchStatusService
            
            updated_count = DispatchStatusService.update_all_dispatch_statuses()
            
            return {
                'success': True,
                'updated_count': updated_count,
                'message': f'成功更新 {updated_count} 個派工單狀態'
            }
            
        except Exception as e:
            logger.error(f"修復派工單狀態對齊時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def fix_workorder_status_sync():
        """
        修復工單狀態同步
        根據派工單狀態和報工記錄更新工單狀態
        """
        try:
            with transaction.atomic():
                updated_count = 0
                
                # 更新生產中的工單
                in_progress_dispatches = WorkOrderDispatch.objects.filter(status='in_production')
                for dispatch in in_progress_dispatches:
                    # 使用公司代號和工單號碼組合查詢，確保唯一性
                    workorder = WorkOrder.objects.filter(order_number=dispatch.order_number).first()
                    # 注意：這裡需要從派工單中獲取公司代號，暫時保持原有邏輯
                    if workorder and workorder.status != 'in_progress':
                        workorder.status = 'in_progress'
                        workorder.save()
                        updated_count += 1
                        logger.info(f"更新工單 {workorder.order_number} 狀態為生產中")
                
                # 更新已完工的工單
                completed_dispatches = WorkOrderDispatch.objects.filter(status='completed')
                for dispatch in completed_dispatches:
                    # 使用公司代號和工單號碼組合查詢，確保唯一性
                    workorder = WorkOrder.objects.filter(order_number=dispatch.order_number).first()
                    # 注意：這裡需要從派工單中獲取公司代號，暫時保持原有邏輯
                    if workorder and workorder.status != 'completed':
                        workorder.status = 'completed'
                        workorder.save()
                        updated_count += 1
                        logger.info(f"更新工單 {workorder.order_number} 狀態為已完工")
                
                return {
                    'success': True,
                    'updated_count': updated_count,
                    'message': f'成功更新 {updated_count} 個工單狀態'
                }
                
        except Exception as e:
            logger.error(f"修復工單狀態同步時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def cleanup_orphan_data():
        """
        清理孤兒資料
        清理沒有對應工單的派工單和報工記錄
        """
        try:
            with transaction.atomic():
                workorder_numbers = set(
                    WorkOrder.objects.values_list('order_number', flat=True)
                )
                
                # 清理孤兒派工單
                orphan_dispatches = WorkOrderDispatch.objects.exclude(
                    order_number__in=workorder_numbers
                )
                orphan_dispatch_count = orphan_dispatches.count()
                orphan_dispatches.delete()
                
                # 清理孤兒報工記錄
                orphan_operator_reports = OperatorSupplementReport.objects.exclude(
                    workorder__order_number__in=workorder_numbers
                )
                orphan_operator_count = orphan_operator_reports.count()
                orphan_operator_reports.delete()
                
                orphan_smt_reports = SMTSupplementReport.objects.exclude(
                    workorder__order_number__in=workorder_numbers
                )
                orphan_smt_count = orphan_smt_reports.count()
                orphan_smt_reports.delete()
                
                return {
                    'success': True,
                    'cleaned_dispatches': orphan_dispatch_count,
                    'cleaned_operator_reports': orphan_operator_count,
                    'cleaned_smt_reports': orphan_smt_count,
                    'message': f'清理了 {orphan_dispatch_count} 個孤兒派工單，{orphan_operator_count} 個作業員報工記錄，{orphan_smt_count} 個SMT報工記錄'
                }
                
        except Exception as e:
            logger.error(f"清理孤兒資料時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def comprehensive_fix():
        """
        綜合修復
        執行所有修復步驟
        """
        try:
            results = []
            
            # 1. 診斷問題
            diagnosis = SystemIntegrationService.diagnose_system_issues()
            results.append(('診斷', diagnosis))
            
            # 2. 修復缺少的派工單
            fix_dispatches = SystemIntegrationService.fix_missing_dispatches()
            results.append(('修復派工單', fix_dispatches))
            
            # 3. 修復派工單狀態對齊
            fix_status = SystemIntegrationService.fix_dispatch_status_alignment()
            results.append(('修復狀態對齊', fix_status))
            
            # 4. 修復工單狀態同步
            fix_workorder = SystemIntegrationService.fix_workorder_status_sync()
            results.append(('修復工單狀態', fix_workorder))
            
            # 5. 清理孤兒資料
            cleanup = SystemIntegrationService.cleanup_orphan_data()
            results.append(('清理孤兒資料', cleanup))
            
            # 6. 最終診斷
            final_diagnosis = SystemIntegrationService.diagnose_system_issues()
            results.append(('最終診斷', final_diagnosis))
            
            return {
                'success': True,
                'results': results,
                'summary': '綜合處理完成'
            }
            
        except Exception as e:
            logger.error(f"綜合修復時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            } 