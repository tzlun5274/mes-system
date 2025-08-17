#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動分配服務
為已完工工單的數量為0的填報紀錄自動分配數量
"""

import logging
from django.db import transaction
from django.db.models import Sum, Q
from workorder.models import CompletedWorkOrder
from workorder.fill_work.models import FillWork
from process.models import Operator

logger = logging.getLogger(__name__)

class AutoAllocationService:
    """
    自動分配服務類別
    負責為已完工工單的數量為0的填報紀錄自動分配數量
    """
    
    def __init__(self):
        self.packaging_process_keywords = ['出貨包裝', '包裝', 'packaging']
    
    def get_pending_allocation_summary(self, company_code=None):
        """
        獲取待分配記錄的摘要統計
        
        Args:
            company_code: 公司代號（可選）
            
        Returns:
            dict: 摘要統計資料
        """
        try:
            # 獲取所有已完工工單
            completed_workorders = CompletedWorkOrder.objects.all()
            if company_code:
                completed_workorders = completed_workorders.filter(company_code=company_code)
            
            # 獲取所有數量為0的填報紀錄
            zero_quantity_reports = FillWork.objects.filter(
                work_quantity=0,
                approval_status='approved'
            )
            
            # 篩選已完工工單的填報紀錄
            pending_reports = []
            for completed_workorder in completed_workorders:
                workorder_reports = zero_quantity_reports.filter(
                    workorder=completed_workorder.order_number,
                    product_id=completed_workorder.product_code
                )
                pending_reports.extend(list(workorder_reports))
            
            if company_code:
                # 根據多公司架構，需要同時檢查公司代號、工單號碼和產品編號
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(company_code=company_code).first()
                if company_config:
                    pending_reports = pending_reports.filter(company_name=company_config.company_name)
            
            # 按工序統計
            processes_summary = {}
            for report in pending_reports:
                process_name = report.operation
                if process_name not in processes_summary:
                    processes_summary[process_name] = {
                        'report_count': 0,
                        'total_hours': 0.0,
                        'is_packaging': self._is_packaging_process(process_name)
                    }
                
                processes_summary[process_name]['report_count'] += 1
                processes_summary[process_name]['total_hours'] += float(report.work_hours_calculated or 0)
            
            # 按工單統計
            workorders_summary = {}
            for report in pending_reports:
                workorder_number = report.workorder
                if workorder_number not in workorders_summary:
                    workorder = completed_workorders.filter(order_number=workorder_number).first()
                    workorders_summary[workorder_number] = {
                        'report_count': 0,
                        'total_hours': 0.0,
                        'planned_quantity': workorder.planned_quantity if workorder else 0
                    }
                
                workorders_summary[workorder_number]['report_count'] += 1
                workorders_summary[workorder_number]['total_hours'] += float(report.work_hours_calculated or 0)
            
            return {
                'total_pending_reports': len(pending_reports),
                'total_workorders': len(workorders_summary),
                'processes': processes_summary,
                'workorders': workorders_summary
            }
            
        except Exception as e:
            logger.error(f"獲取待分配摘要時發生錯誤: {str(e)}")
            return {'error': str(e)}
    
    def allocate_all_pending_workorders(self, company_code=None):
        """
        為所有待分配的已完工工單進行批量分配
        
        Args:
            company_code: 公司代號（可選）
            
        Returns:
            dict: 分配結果
        """
        try:
            # 獲取待分配摘要
            summary = self.get_pending_allocation_summary(company_code)
            if 'error' in summary:
                return {'error': summary['error']}
            
            results = []
            successful_allocations = 0
            failed_allocations = 0
            
            # 為每個工單進行分配
            for workorder_number in summary['workorders'].keys():
                try:
                    result = self.allocate_workorder_quantities(workorder_number, company_code)
                    results.append({
                        'workorder_number': workorder_number,
                        'result': result
                    })
                    
                    if result.get('success', True):
                        successful_allocations += 1
                    else:
                        failed_allocations += 1
                        
                except Exception as e:
                    logger.error(f"分配工單 {workorder_number} 時發生錯誤: {str(e)}")
                    results.append({
                        'workorder_number': workorder_number,
                        'result': {
                            'success': False,
                            'message': str(e)
                        }
                    })
                    failed_allocations += 1
            
            return {
                'total_workorders': len(results),
                'successful_allocations': successful_allocations,
                'failed_allocations': failed_allocations,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"批量分配時發生錯誤: {str(e)}")
            return {'error': str(e)}
    
    def allocate_workorder_quantities(self, workorder_number, company_code=None):
        """
        為指定工單分配數量
        
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
                
                # 獲取該工單數量為0的填報紀錄
                zero_reports = FillWork.objects.filter(
                    workorder=workorder_number,
                    product_id=completed_workorder.product_code,
                    work_quantity=0,
                    approval_status='approved'
                )
                
                if company_code:
                    # 根據多公司架構，需要同時檢查公司代號、工單號碼和產品編號
                    from erp_integration.models import CompanyConfig
                    company_config = CompanyConfig.objects.filter(company_code=company_code).first()
                    if company_config:
                        zero_reports = zero_reports.filter(company_name=company_config.company_name)
                
                if not zero_reports.exists():
                    return {
                        'success': False,
                        'message': f'工單 {workorder_number} 沒有需要分配的記錄'
                    }
                
                # 按工序分組
                processes_data = {}
                excluded_processes = []
                
                for report in zero_reports:
                    process_name = report.operation
                    
                    # 檢查是否為出貨包裝工序
                    if self._is_packaging_process(process_name):
                        excluded_processes.append({
                            'process_name': process_name,
                            'reason': '出貨包裝工序不參與分配',
                            'report_count': zero_reports.filter(operation=process_name).count()
                        })
                        continue
                    
                    if process_name not in processes_data:
                        processes_data[process_name] = {
                            'reports': [],
                            'total_hours': 0.0
                        }
                    
                    processes_data[process_name]['reports'].append(report)
                    processes_data[process_name]['total_hours'] += float(report.work_hours_calculated or 0)
                
                # 計算分配數量
                total_planned_quantity = completed_workorder.planned_quantity
                total_work_hours = sum(data['total_hours'] for data in processes_data.values())
                
                allocated_reports = []
                processes_allocated = []
                total_quantity_allocated = 0
                total_reports_allocated = 0
                
                for process_name, data in processes_data.items():
                    if data['total_hours'] <= 0:
                        continue
                    
                    # 按工時比例分配數量
                    process_quantity = int((data['total_hours'] / total_work_hours) * total_planned_quantity)
                    
                    # 為每個填報紀錄分配數量
                    reports_count = len(data['reports'])
                    quantity_per_report = process_quantity // reports_count
                    remainder = process_quantity % reports_count
                    
                    process_allocated_reports = []
                    
                    for i, report in enumerate(data['reports']):
                        # 分配數量（最後一個記錄獲得剩餘數量）
                        allocated_quantity = quantity_per_report + (1 if i < remainder else 0)
                        
                        # 更新填報紀錄
                        report.work_quantity = allocated_quantity
                        report.save()
                        
                        process_allocated_reports.append({
                            'operator': report.operator,
                            'report_date': report.work_date.strftime('%Y-%m-%d'),
                            'allocated_quantity': allocated_quantity,
                            'work_hours': report.work_hours_calculated or 0
                        })
                        
                        allocated_reports.append(report)
                        total_quantity_allocated += allocated_quantity
                        total_reports_allocated += 1
                    
                    processes_allocated.append({
                        'process_name': process_name,
                        'quantity_allocated': process_quantity,
                        'reports_allocated': len(data['reports']),
                        'allocated_reports': process_allocated_reports
                    })
                
                return {
                    'success': True,
                    'workorder_number': workorder_number,
                    'total_planned_quantity': total_planned_quantity,
                    'total_reports_allocated': total_reports_allocated,
                    'total_quantity_allocated': total_quantity_allocated,
                    'excluded_processes': excluded_processes,
                    'processes_allocated': processes_allocated
                }
                
        except Exception as e:
            logger.error(f"分配工單 {workorder_number} 數量時發生錯誤: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_allocation_summary(self, workorder_number):
        """
        獲取指定工單的分配摘要
        
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
            
            # 獲取該工單的所有填報紀錄
            all_reports = FillWork.objects.filter(
                workorder=workorder_number,
                product_id=completed_workorder.product_code,
                approval_status='approved'
            )
            
            # 如果工單有公司代號，則按公司分離過濾
            if completed_workorder.company_code:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(company_code=completed_workorder.company_code).first()
                if company_config:
                    all_reports = all_reports.filter(company_name=company_config.company_name)
            
            # 按工序統計
            processes_summary = {}
            excluded_processes = []
            
            for report in all_reports:
                process_name = report.operation
                
                if self._is_packaging_process(process_name):
                    if process_name not in excluded_processes:
                        excluded_processes.append(process_name)
                    continue
                
                if process_name not in processes_summary:
                    processes_summary[process_name] = {
                        'original_quantity': 0,
                        'allocated_quantity': 0,
                        'report_count': 0
                    }
                
                processes_summary[process_name]['original_quantity'] += report.work_quantity or 0
                processes_summary[process_name]['report_count'] += 1
                
                # 如果數量為0，計算需要分配的數量
                if report.work_quantity == 0:
                    processes_summary[process_name]['allocated_quantity'] += 1  # 預估分配1件
            
            return {
                'workorder_number': workorder_number,
                'planned_quantity': completed_workorder.planned_quantity,
                'total_original_quantity': sum(data['original_quantity'] for data in processes_summary.values()),
                'total_allocated_quantity': sum(data['allocated_quantity'] for data in processes_summary.values()),
                'excluded_processes': excluded_processes,
                'processes': processes_summary
            }
            
        except Exception as e:
            logger.error(f"獲取工單 {workorder_number} 分配摘要時發生錯誤: {str(e)}")
            return {'error': str(e)}
    
    def _is_packaging_process(self, process_name):
        """
        判斷是否為出貨包裝工序
        
        Args:
            process_name: 工序名稱（可能是 ProcessName 物件或字串）
            
        Returns:
            bool: 是否為出貨包裝工序
        """
        if not process_name:
            return False
        
        # 如果是 ProcessName 物件，獲取其 name 屬性
        if hasattr(process_name, 'name'):
            process_name_str = process_name.name
        else:
            process_name_str = str(process_name)
        
        process_name_lower = process_name_str.lower()
        return any(keyword in process_name_lower for keyword in self.packaging_process_keywords) 