#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
已完工工單工序紀錄數量分配服務
為已完工工單的數量為0的工序紀錄自動分配數量
"""

import logging
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from workorder.models import CompletedWorkOrder, CompletedProductionReport
from workorder.fill_work.models import FillWork

logger = logging.getLogger(__name__)

class CompletedWorkOrderAllocationService:
    """
    已完工工單工序紀錄數量分配服務
    負責為已完工工單的數量為0的工序紀錄自動分配數量
    """
    
    def __init__(self):
        self.packaging_process_keywords = ['出貨包裝', '包裝', 'packaging']
    
    def allocate_completed_workorder_quantities(self, workorder_number, company_code=None):
        """
        為已完工工單分配工序紀錄數量
        
        分配規則：
        1. 排除出貨包裝工序
        2. 每個工序名稱分配完整的工單數量
        3. 同一個工序名稱的多筆記錄平均分配該工序的數量
        4. 如果某筆記錄已有數量，則從分配數量中扣除
        
        範例：
        - 工單數量1000，一個工序名稱一筆記錄 → 分配1000
        - 工單數量1000，一個工序名稱兩筆記錄 → 每筆分配500
        - 工單數量1000，兩個工序名稱各一筆記錄 → 每個工序分配1000，每筆記錄分配1000
        - 工單數量1000，10個目檢記錄 → 每筆分配100
        
        Args:
            workorder_number: 工單號碼
            company_code: 公司代號（可選）
            
        Returns:
            dict: 分配結果
        """
        try:
            with transaction.atomic():
                # 獲取已完工工單
                completed_workorder = CompletedWorkOrder.objects.filter(
                    order_number=workorder_number
                ).first()
                
                if not completed_workorder:
                    return {
                        'success': False,
                        'message': f'工單 {workorder_number} 不存在或未完工'
                    }
                
                # 獲取該工單的所有工序紀錄（從已完工生產報工記錄）
                production_reports = CompletedProductionReport.objects.filter(
                    completed_workorder=completed_workorder
                )
                
                # 排除出貨包裝工序
                production_reports = production_reports.exclude(
                    process_name__icontains='出貨包裝'
                )
                
                if not production_reports.exists():
                    return {
                        'success': False,
                        'message': f'工單 {workorder_number} 沒有需要分配的工序紀錄'
                    }
                
                # 按工序名稱分組
                processes_data = {}
                
                for report in production_reports:
                    process_name = report.process_name
                    
                    if process_name not in processes_data:
                        processes_data[process_name] = {
                            'reports': [],
                            'total_existing_quantity': 0,
                            'zero_quantity_reports': []
                        }
                    
                    processes_data[process_name]['reports'].append(report)
                    
                    # 統計已有數量
                    if report.work_quantity > 0:
                        processes_data[process_name]['total_existing_quantity'] += report.work_quantity
                    else:
                        processes_data[process_name]['zero_quantity_reports'].append(report)
                
                # 計算分配結果
                total_planned_quantity = completed_workorder.planned_quantity
                allocation_results = []
                total_allocated_quantity = 0
                total_allocated_reports = 0
                
                # 每個工序名稱分配完整的工單數量
                for process_name, data in processes_data.items():
                    if not data['zero_quantity_reports']:
                        # 沒有需要分配的紀錄
                        continue
                    
                    # 該工序分配完整的工單數量
                    process_quantity = total_planned_quantity
                    
                    # 扣除已有數量
                    existing_quantity = data['total_existing_quantity']
                    remaining_quantity = process_quantity - existing_quantity
                    
                    if remaining_quantity <= 0:
                        # 已有數量已達到工單總數量，不需要分配
                        continue
                    
                    # 計算每筆紀錄的分配數量（平均分配）
                    zero_reports_count = len(data['zero_quantity_reports'])
                    quantity_per_report = remaining_quantity // zero_reports_count
                    report_remainder = remaining_quantity % zero_reports_count
                    
                    process_allocated_quantity = 0
                    process_allocated_reports = 0
                    
                    for j, report in enumerate(data['zero_quantity_reports']):
                        # 分配數量（前面的紀錄獲得餘數）
                        allocated_quantity = quantity_per_report + (1 if j < report_remainder else 0)
                        
                        # 更新紀錄
                        report.work_quantity = allocated_quantity
                        report.is_system_allocated = True
                        report.allocated_at = timezone.now()
                        report.allocation_method = 'completed_workorder_allocation'
                        report.save()
                        
                        process_allocated_quantity += allocated_quantity
                        process_allocated_reports += 1
                        total_allocated_quantity += allocated_quantity
                        total_allocated_reports += 1
                    
                    allocation_results.append({
                        'process_name': process_name,
                        'process_quantity': process_quantity,
                        'existing_quantity': existing_quantity,
                        'remaining_quantity': remaining_quantity,
                        'zero_reports_count': zero_reports_count,
                        'allocated_quantity': process_allocated_quantity,
                        'allocated_reports': process_allocated_reports,
                        'quantity_per_report': quantity_per_report,
                        'remainder': report_remainder
                    })
                
                return {
                    'success': True,
                    'workorder_number': workorder_number,
                    'total_planned_quantity': total_planned_quantity,
                    'total_allocated_quantity': total_allocated_quantity,
                    'total_allocated_reports': total_allocated_reports,
                    'allocation_results': allocation_results
                }
                
        except Exception as e:
            logger.error(f"分配已完工工單 {workorder_number} 數量時發生錯誤: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_allocation_summary(self, workorder_number):
        """
        獲取指定已完工工單的分配摘要
        
        Args:
            workorder_number: 工單號碼
            
        Returns:
            dict: 分配摘要
        """
        try:
            # 獲取已完工工單
            completed_workorder = CompletedWorkOrder.objects.filter(
                order_number=workorder_number
            ).first()
            
            if not completed_workorder:
                return {'error': f'工單 {workorder_number} 不存在或未完工'}
            
            # 獲取該工單的所有工序紀錄
            production_reports = CompletedProductionReport.objects.filter(
                completed_workorder=completed_workorder
            )
            
            # 排除出貨包裝工序
            production_reports = production_reports.exclude(
                process_name__icontains='出貨包裝'
            )
            
            # 按工序統計
            processes_summary = {}
            
            for report in production_reports:
                process_name = report.process_name
                
                if process_name not in processes_summary:
                    processes_summary[process_name] = {
                        'total_quantity': 0,
                        'system_allocated_quantity': 0,
                        'manual_quantity': 0,
                        'report_count': 0,
                        'zero_quantity_reports': 0
                    }
                
                processes_summary[process_name]['total_quantity'] += report.work_quantity
                processes_summary[process_name]['report_count'] += 1
                
                if report.is_system_allocated:
                    processes_summary[process_name]['system_allocated_quantity'] += report.work_quantity
                else:
                    processes_summary[process_name]['manual_quantity'] += report.work_quantity
                
                if report.work_quantity == 0:
                    processes_summary[process_name]['zero_quantity_reports'] += 1
            
            return {
                'workorder_number': workorder_number,
                'planned_quantity': completed_workorder.planned_quantity,
                'total_reports': production_reports.count(),
                'total_quantity': sum(data['total_quantity'] for data in processes_summary.values()),
                'total_system_allocated': sum(data['system_allocated_quantity'] for data in processes_summary.values()),
                'total_manual_quantity': sum(data['manual_quantity'] for data in processes_summary.values()),
                'total_zero_quantity_reports': sum(data['zero_quantity_reports'] for data in processes_summary.values()),
                'processes': processes_summary
            }
            
        except Exception as e:
            logger.error(f"獲取已完工工單 {workorder_number} 分配摘要時發生錯誤: {str(e)}")
            return {'error': str(e)}
    
    def get_pending_allocation_workorders(self, company_code=None):
        """
        獲取需要分配的已完工工單列表
        
        Args:
            company_code: 公司代號（可選）
            
        Returns:
            list: 需要分配的工單列表
        """
        try:
            # 獲取所有已完工工單
            completed_workorders = CompletedWorkOrder.objects.all()
            if company_code:
                completed_workorders = completed_workorders.filter(company_code=company_code)
            
            logger.info(f"找到 {completed_workorders.count()} 個已完工工單")
            
            pending_workorders = []
            
            for workorder in completed_workorders:
                logger.debug(f"檢查工單: {workorder.order_number}")
                
                # 檢查是否有數量為0的工序紀錄
                zero_quantity_reports = CompletedProductionReport.objects.filter(
                    completed_workorder=workorder,
                    work_quantity=0
                ).exclude(
                    process_name__icontains='出貨包裝'
                )
                
                zero_count = zero_quantity_reports.count()
                logger.debug(f"工單 {workorder.order_number} 數量為0的記錄數: {zero_count}")
                
                if zero_count > 0:
                    pending_workorders.append({
                        'workorder_number': workorder.order_number,
                        'product_code': workorder.product_code,
                        'planned_quantity': workorder.planned_quantity,
                        'zero_quantity_reports_count': zero_count,
                        'completed_at': workorder.completed_at
                    })
                    logger.info(f"工單 {workorder.order_number} 加入待分配列表")
            
            logger.info(f"總共找到 {len(pending_workorders)} 個待分配工單")
            return pending_workorders
            
        except Exception as e:
            logger.error(f"獲取待分配已完工工單列表時發生錯誤: {str(e)}")
            return []
    
    def allocate_all_pending_workorders(self, company_code=None):
        """
        為所有待分配的已完工工單執行分配
        
        Args:
            company_code: 公司代號（可選）
            
        Returns:
            dict: 分配結果摘要
        """
        try:
            pending_workorders = self.get_pending_allocation_workorders(company_code)
            
            if not pending_workorders:
                return {
                    'success': True,
                    'message': '沒有需要分配的已完工工單',
                    'total_processed': 0,
                    'total_success': 0,
                    'total_failed': 0
                }
            
            total_processed = len(pending_workorders)
            total_success = 0
            total_failed = 0
            failed_workorders = []
            
            for workorder_info in pending_workorders:
                result = self.allocate_completed_workorder_quantities(
                    workorder_info['workorder_number'],
                    company_code
                )
                
                if result['success']:
                    total_success += 1
                else:
                    total_failed += 1
                    failed_workorders.append({
                        'workorder_number': workorder_info['workorder_number'],
                        'error': result['message']
                    })
            
            return {
                'success': True,
                'total_processed': total_processed,
                'total_success': total_success,
                'total_failed': total_failed,
                'failed_workorders': failed_workorders
            }
            
        except Exception as e:
            logger.error(f"批量分配已完工工單時發生錯誤: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            } 