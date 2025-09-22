#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動分配服務
為已完工工單的數量為0的填報紀錄自動分配數量
整合了 CompletedWorkOrderAllocationService 的功能
"""

import logging
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from workorder.models import CompletedWorkOrder, CompletedProductionReport
from workorder.fill_work.models import FillWork
from process.models import Operator

logger = logging.getLogger(__name__)

class AutoAllocationService:
    """
    自動分配服務類別
    負責為已完工工單的數量為0的填報紀錄自動分配數量
    整合了 CompletedWorkOrderAllocationService 的功能
    """
    
    def __init__(self):
        self.packaging_process_keywords = ['出貨包裝', '包裝', 'packaging']
    
    def _is_packaging_process(self, process_name):
        """
        判斷是否為出貨包裝工序
        
        Args:
            process_name: 工序名稱
            
        Returns:
            bool: 是否為出貨包裝工序
        """
        if not process_name:
            return False
        
        process_name_lower = process_name.lower()
        return any(keyword.lower() in process_name_lower for keyword in self.packaging_process_keywords)
    
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
            
            # 獲取所有數量為0的已完工生產報工記錄
            zero_quantity_reports = CompletedProductionReport.objects.filter(work_quantity=0)
            
            # 篩選已完工工單的報工記錄
            pending_reports = []
            for completed_workorder in completed_workorders:
                workorder_reports = zero_quantity_reports.filter(
                    completed_workorder_id=completed_workorder.id
                )
                pending_reports.extend(list(workorder_reports))
            
            # 排除出貨包裝工序
            pending_reports = [r for r in pending_reports if not self._is_packaging_process(r.process_name)]
            
            # 按工序統計
            processes_summary = {}
            for report in pending_reports:
                process_name = report.process_name
                if process_name not in processes_summary:
                    processes_summary[process_name] = {
                        'report_count': 0,
                        'total_hours': 0.0,
                        'is_packaging': self._is_packaging_process(process_name)
                    }
                
                processes_summary[process_name]['report_count'] += 1
                processes_summary[process_name]['total_hours'] += float(report.work_hours or 0)
            
            # 按工單統計
            workorders_summary = {}
            for report in pending_reports:
                # 通過 completed_workorder_id 查找工單
                workorder = completed_workorders.filter(id=report.completed_workorder_id).first()
                if workorder:
                    workorder_number = workorder.order_number
                    if workorder_number not in workorders_summary:
                        workorders_summary[workorder_number] = {
                            'report_count': 0,
                            'total_hours': 0.0,
                            'planned_quantity': workorder.planned_quantity
                        }
                    
                    workorders_summary[workorder_number]['report_count'] += 1
                    workorders_summary[workorder_number]['total_hours'] += float(report.work_hours or 0)
            
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
                return summary
            
            # 獲取所有已完工工單
            completed_workorders = CompletedWorkOrder.objects.all()
            if company_code:
                completed_workorders = completed_workorders.filter(company_code=company_code)
            
            total_allocated_workorders = 0
            total_allocated_quantity = 0
            total_allocated_reports = 0
            allocation_results = []
            
            for completed_workorder in completed_workorders:
                result = self.allocate_completed_workorder_quantities(
                    completed_workorder.order_number, 
                    company_code
                )
                
                if result.get('success', False):
                    total_allocated_workorders += 1
                    total_allocated_quantity += result.get('total_allocated_quantity', 0)
                    total_allocated_reports += result.get('total_allocated_reports', 0)
                    allocation_results.append(result)
            
            return {
                'success': True,
                'total_allocated_workorders': total_allocated_workorders,
                'total_allocated_quantity': total_allocated_quantity,
                'total_allocated_reports': total_allocated_reports,
                'allocation_results': allocation_results
            }
            
        except Exception as e:
            logger.error(f"批量分配時發生錯誤: {str(e)}")
            return {'error': str(e)}
    
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
                    completed_workorder_id=completed_workorder.id
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
                        # 沒有需要分配的記錄
                        continue
                    
                    # 該工序分配完整的工單數量
                    process_quantity = total_planned_quantity
                    
                    # 扣除已有數量
                    existing_quantity = data['total_existing_quantity']
                    remaining_quantity = process_quantity - existing_quantity
                    
                    if remaining_quantity <= 0:
                        # 已有數量已達到工單總數量，不需要分配
                        continue
                    
                    # 計算每筆記錄的分配數量（平均分配）
                    zero_reports_count = len(data['zero_quantity_reports'])
                    quantity_per_report = remaining_quantity // zero_reports_count
                    report_remainder = remaining_quantity % zero_reports_count
                    
                    process_allocated_quantity = 0
                    process_allocated_reports = 0
                    
                    for j, report in enumerate(data['zero_quantity_reports']):
                        # 分配數量（前面的記錄獲得餘數）
                        allocated_quantity = quantity_per_report + (1 if j < report_remainder else 0)
                        
                        # 更新記錄
                        report.work_quantity = allocated_quantity
                        report.is_system_allocated = True
                        report.allocated_at = timezone.now()
                        report.allocation_method = 'auto_allocation'
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
                completed_workorder_id=completed_workorder.id
            )
            
            # 排除出貨包裝工序
            production_reports = production_reports.exclude(
                process_name__icontains='出貨包裝'
            )
            
            # 按工序名稱分組統計
            processes_summary = {}
            total_reports = 0
            total_zero_quantity_reports = 0
            total_existing_quantity = 0
            
            for report in production_reports:
                process_name = report.process_name
                total_reports += 1
                
                if process_name not in processes_summary:
                    processes_summary[process_name] = {
                        'total_reports': 0,
                        'zero_quantity_reports': 0,
                        'existing_quantity': 0,
                        'is_packaging': self._is_packaging_process(process_name)
                    }
                
                processes_summary[process_name]['total_reports'] += 1
                
                if report.work_quantity == 0:
                    processes_summary[process_name]['zero_quantity_reports'] += 1
                    total_zero_quantity_reports += 1
                else:
                    processes_summary[process_name]['existing_quantity'] += report.work_quantity
                    total_existing_quantity += report.work_quantity
            
            return {
                'workorder_number': workorder_number,
                'planned_quantity': completed_workorder.planned_quantity,
                'total_reports': total_reports,
                'total_zero_quantity_reports': total_zero_quantity_reports,
                'total_existing_quantity': total_existing_quantity,
                'processes': processes_summary
            }
            
        except Exception as e:
            logger.error(f"獲取工單 {workorder_number} 分配摘要時發生錯誤: {str(e)}")
            return {'error': str(e)}
    
    def allocate_single_report(self, report_id, allocated_quantity):
        """
        為單筆填報紀錄分配數量
        
        Args:
            report_id: 填報紀錄ID
            allocated_quantity: 分配數量
            
        Returns:
            dict: 分配結果
        """
        try:
            with transaction.atomic():
                # 獲取填報紀錄
                report = FillWork.objects.get(id=report_id)
                
                # 檢查是否為出貨包裝工序
                if self._is_packaging_process(report.process_name):
                    return {
                        'success': False,
                        'message': '出貨包裝工序不參與數量分配'
                    }
                
                # 檢查是否已經有數量
                if report.work_quantity > 0:
                    return {
                        'success': False,
                        'message': '該紀錄已有數量，無法重新分配'
                    }
                
                # 分配數量
                report.work_quantity = allocated_quantity
                report.is_system_allocated = True
                report.allocated_at = timezone.now()
                report.allocation_method = 'manual_allocation'
                report.save()
                
                logger.info(f"成功為填報紀錄 {report_id} 分配數量 {allocated_quantity}")
                
                return {
                    'success': True,
                    'report_id': report_id,
                    'allocated_quantity': allocated_quantity,
                    'message': '數量分配成功'
                }
                
        except FillWork.DoesNotExist:
            return {
                'success': False,
                'message': f'填報紀錄 {report_id} 不存在'
            }
        except Exception as e:
            logger.error(f"分配單筆紀錄 {report_id} 時發生錯誤: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            } 