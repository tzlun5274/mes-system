#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動分配服務 - 為數量為0的報工記錄分配數量
排除出貨包裝工序，因為出貨包裝是前置準備動作
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from workorder.workorder_reporting.models import OperatorSupplementReport
from workorder.models import WorkOrder, CompletedWorkOrder, CompletedProductionReport

logger = logging.getLogger(__name__)


class AutoAllocationService:
    """
    自動分配服務
    為數量為0的報工記錄分配數量，基於生產數量/工序次數和工作時數比例
    """
    
    def __init__(self):
        self.packaging_process_names = [
            '出貨包裝', '包裝', '包裝出貨', 'final_packaging', 'shipping_packaging'
        ]
    
    def is_packaging_process(self, process_name):
        """
        判斷是否為包裝工序
        """
        if not process_name:
            return False
        return process_name.strip() in self.packaging_process_names
    
    def allocate_workorder_quantities(self, workorder_number, company_code=None):
        """
        為指定工單的所有數量為0的報工記錄分配數量
        
        Args:
            workorder_number (str): 工單號碼
            company_code (str): 公司代號（可選）
        
        Returns:
            dict: 分配結果統計
        """
        try:
            # 獲取工單資訊
            workorder = WorkOrder.objects.get(order_number=workorder_number)
            if company_code and workorder.company_code != company_code:
                raise ValueError(f"工單 {workorder_number} 不屬於公司代號 {company_code}")
            
            logger.info(f"開始為工單 {workorder_number} 進行自動分配")
            
            # 獲取所有報工記錄
            all_reports = OperatorSupplementReport.objects.filter(
                workorder=workorder
            ).select_related('operator', 'process').order_by('work_date', 'start_time')
            
            if not all_reports.exists():
                logger.warning(f"工單 {workorder_number} 沒有找到報工記錄")
                return {"success": False, "message": "沒有找到報工記錄"}
            
            # 按工序分組
            process_groups = self._group_reports_by_process(all_reports)
            
            allocation_results = {
                "workorder_number": workorder_number,
                "total_planned_quantity": workorder.quantity,
                "processes_allocated": [],
                "total_reports_allocated": 0,
                "total_quantity_allocated": 0,
                "excluded_processes": []
            }
            
            # 為每個工序進行分配
            for process_name, reports in process_groups.items():
                if self.is_packaging_process(process_name):
                    # 跳過包裝工序
                    allocation_results["excluded_processes"].append({
                        "process_name": process_name,
                        "reason": "包裝工序不參與自動分配",
                        "report_count": len(reports)
                    })
                    logger.info(f"跳過包裝工序: {process_name}")
                    continue
                
                process_result = self._allocate_process_quantities(
                    process_name, reports, workorder.quantity
                )
                allocation_results["processes_allocated"].append(process_result)
                allocation_results["total_reports_allocated"] += process_result["reports_allocated"]
                allocation_results["total_quantity_allocated"] += process_result["quantity_allocated"]
            
            logger.info(f"工單 {workorder_number} 自動分配完成")
            return allocation_results
            
        except WorkOrder.DoesNotExist:
            logger.error(f"工單 {workorder_number} 不存在")
            return {"success": False, "message": f"工單 {workorder_number} 不存在"}
        except Exception as e:
            logger.error(f"為工單 {workorder_number} 分配數量時發生錯誤: {str(e)}")
            return {"success": False, "message": f"分配失敗: {str(e)}"}
    
    def _group_reports_by_process(self, reports):
        """
        按工序名稱分組報工記錄
        """
        process_groups = {}
        for report in reports:
            process_name = report.process.name if report.process else "未知工序"
            if process_name not in process_groups:
                process_groups[process_name] = []
            process_groups[process_name].append(report)
        return process_groups
    
    def _allocate_process_quantities(self, process_name, reports, total_planned_quantity):
        """
        為單一工序的報工記錄分配數量
        
        Args:
            process_name (str): 工序名稱
            reports (list): 該工序的報工記錄列表
            total_planned_quantity (int): 工單總計劃數量
        
        Returns:
            dict: 分配結果
        """
        logger.info(f"開始為工序 {process_name} 分配數量")
        
        # 分離已填寫數量和未填寫數量的記錄
        filled_reports = [r for r in reports if r.work_quantity and r.work_quantity > 0]
        unfilled_reports = [r for r in reports if not r.work_quantity or r.work_quantity == 0]
        
        # 計算已填寫的總數量
        total_filled_quantity = sum(r.work_quantity for r in filled_reports)
        
        # 計算剩餘需要分配的數量
        remaining_quantity = total_planned_quantity - total_filled_quantity
        
        if remaining_quantity <= 0:
            logger.info(f"工序 {process_name} 已填寫數量 {total_filled_quantity} 超過計劃數量 {total_planned_quantity}")
            return {
                "process_name": process_name,
                "reports_allocated": 0,
                "quantity_allocated": 0,
                "message": f"已填寫數量({total_filled_quantity})超過計劃數量({total_planned_quantity})"
            }
        
        # 計算未填寫記錄的總工時
        total_work_hours = sum(
            (r.work_hours_calculated or 0) + (r.overtime_hours_calculated or 0)
            for r in unfilled_reports
        )
        
        if total_work_hours <= 0:
            logger.warning(f"工序 {process_name} 未填寫記錄的總工時為0")
            return {
                "process_name": process_name,
                "reports_allocated": 0,
                "quantity_allocated": 0,
                "message": "未填寫記錄的總工時為0"
            }
        
        # 按工時比例分配數量
        allocated_reports = []
        total_allocated = 0
        
        for report in unfilled_reports:
            report_hours = (report.work_hours_calculated or 0) + (report.overtime_hours_calculated or 0)
            if report_hours > 0:
                # 按工時比例分配
                allocation_ratio = report_hours / total_work_hours
                allocated_quantity = int(remaining_quantity * allocation_ratio)
                
                # 更新報工記錄
                with transaction.atomic():
                    report.allocated_quantity = allocated_quantity
                    report.quantity_source = 'auto_allocated'
                    report.allocation_notes = (
                        f"自動分配 - 工時比例: {allocation_ratio:.2%}, "
                        f"分配數量: {allocated_quantity}, "
                        f"分配時間: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    report.save()
                
                allocated_reports.append({
                    "report_id": report.id,
                    "operator": report.operator.name if report.operator else "未知",
                    "work_date": report.work_date,
                    "work_hours": report_hours,
                    "allocated_quantity": allocated_quantity
                })
                
                total_allocated += allocated_quantity
                logger.info(f"為 {report.operator.name if report.operator else '未知'} "
                          f"分配 {allocated_quantity} 件 (工時: {report_hours}小時)")
        
        return {
            "process_name": process_name,
            "reports_allocated": len(allocated_reports),
            "quantity_allocated": total_allocated,
            "total_filled_quantity": total_filled_quantity,
            "remaining_quantity": remaining_quantity,
            "allocated_reports": allocated_reports,
            "message": f"成功分配 {total_allocated} 件給 {len(allocated_reports)} 筆記錄"
        }
    
    def allocate_all_pending_workorders(self, company_code=None):
        """
        為所有待分配的工單進行自動分配
        
        Args:
            company_code (str): 公司代號（可選）
        
        Returns:
            dict: 批量分配結果
        """
        logger.info("開始批量自動分配")
        
        # 查詢已完工工單資料表中的待分配記錄
        pending_reports = CompletedProductionReport.objects.filter(
            work_quantity=0,  # 數量為0
            report_source__in=['operator_supplement', 'smt']  # 作業員或SMT報工來源
        ).exclude(
            remarks__contains='[自動分配]'  # 排除已分配過的記錄
        ).select_related('completed_workorder')
        
        if company_code:
            pending_reports = pending_reports.filter(
                completed_workorder__company_code=company_code
            )
        
        # 查詢原始報工記錄中未檢查過的記錄
        from workorder.workorder_reporting.models import OperatorSupplementReport
        original_pending_reports = OperatorSupplementReport.objects.filter(
            work_quantity=0,  # 數量為0
            allocation_checked=False  # 未檢查過的記錄
        ).select_related('workorder', 'process')
        
        if company_code:
            original_pending_reports = original_pending_reports.filter(
                workorder__company_code=company_code
            )
        
        # 標記出貨包裝記錄為已檢查，避免重複檢查
        packaging_reports = []
        for report in original_pending_reports:
            process_name = report.process.name if report.process else "未知工序"
            if self.is_packaging_process(process_name):
                packaging_reports.append(report)
        
        # 批量更新出貨包裝記錄為已檢查
        if packaging_reports:
            from django.utils import timezone
            for report in packaging_reports:
                report.allocation_checked = True
                report.allocation_checked_at = timezone.now()
                report.allocation_check_result = 'excluded_packaging'
                report.save()
            logger.info(f"標記了 {len(packaging_reports)} 筆出貨包裝記錄為已檢查")
        
        # 按工單分組，避免重複處理
        workorder_groups = {}
        for report in pending_reports:
            workorder_number = report.completed_workorder.order_number
            if workorder_number not in workorder_groups:
                workorder_groups[workorder_number] = []
            workorder_groups[workorder_number].append(report)
        
        logger.info(f"找到 {len(workorder_groups)} 個工單需要分配，共 {len(pending_reports)} 筆記錄")
        
        batch_results = {
            "total_workorders": len(workorder_groups),
            "total_reports": len(pending_reports),
            "successful_allocations": 0,
            "failed_allocations": 0,
            "results": []
        }
        
        for workorder_number, reports in workorder_groups.items():
            try:
                # 直接使用已查詢的記錄進行分配
                result = self._allocate_workorder_from_reports(
                    workorder_number, 
                    reports
                )
                
                if result.get("success", True):  # 預設為成功
                    batch_results["successful_allocations"] += 1
                else:
                    batch_results["failed_allocations"] += 1
                
                batch_results["results"].append({
                    "workorder_number": workorder_number,
                    "result": result
                })
                
            except Exception as e:
                batch_results["failed_allocations"] += 1
                batch_results["results"].append({
                    "workorder_number": workorder_number,
                    "result": {"success": False, "message": str(e)}
                })
                logger.error(f"為工單 {workorder_number} 分配失敗: {str(e)}")
        
        logger.info(f"批量分配完成: 成功 {batch_results['successful_allocations']} 個工單, "
                   f"失敗 {batch_results['failed_allocations']} 個工單")
        
        return batch_results
    
    def _allocate_workorder_from_reports(self, workorder_number, reports):
        """
        從已查詢的記錄中為工單分配數量（高效版本）
        
        Args:
            workorder_number (str): 工單號碼
            reports (list): 已查詢的已完工報工記錄列表
        
        Returns:
            dict: 分配結果
        """
        try:
            if not reports:
                return {"success": False, "message": "沒有需要分配的記錄"}
            
            # 獲取已完工工單資訊（從第一個記錄中取得）
            completed_workorder = reports[0].completed_workorder
            total_planned_quantity = completed_workorder.planned_quantity
            
            logger.info(f"開始為已完工工單 {workorder_number} 進行自動分配（{len(reports)} 筆記錄）")
            
            # 按工序分組
            process_groups = self._group_completed_reports_by_process(reports)
            
            allocation_results = {
                "workorder_number": workorder_number,
                "total_planned_quantity": total_planned_quantity,
                "processes_allocated": [],
                "total_reports_allocated": 0,
                "total_quantity_allocated": 0,
                "excluded_processes": []
            }
            
            # 為每個工序進行分配
            for process_name, process_reports in process_groups.items():
                if self.is_packaging_process(process_name):
                    # 跳過包裝工序
                    allocation_results["excluded_processes"].append({
                        "process_name": process_name,
                        "reason": "包裝工序不參與自動分配",
                        "report_count": len(process_reports)
                    })
                    logger.info(f"跳過包裝工序: {process_name}")
                    continue
                
                process_result = self._allocate_completed_process_quantities(
                    process_name, process_reports, total_planned_quantity
                )
                allocation_results["processes_allocated"].append(process_result)
                allocation_results["total_reports_allocated"] += process_result["reports_allocated"]
                allocation_results["total_quantity_allocated"] += process_result["quantity_allocated"]
            
            logger.info(f"已完工工單 {workorder_number} 自動分配完成")
            return allocation_results
            
        except Exception as e:
            logger.error(f"為已完工工單 {workorder_number} 分配數量時發生錯誤: {str(e)}")
            return {"success": False, "message": f"分配失敗: {str(e)}"}
    
    def get_pending_allocation_summary(self, company_code=None):
        """
        獲取待分配記錄的摘要統計（高效版本）
        
        Args:
            company_code (str): 公司代號（可選）
        
        Returns:
            dict: 摘要統計
        """
        # 查詢已完工工單資料表中的待分配記錄
        pending_reports = CompletedProductionReport.objects.filter(
            work_quantity=0,  # 數量為0
            report_source__in=['operator_supplement', 'smt']  # 作業員或SMT報工來源
        ).exclude(
            remarks__contains='[自動分配]'  # 排除已分配過的記錄
        ).select_related('completed_workorder')
        
        # 同時查詢原始報工記錄中未檢查過的記錄
        from workorder.workorder_reporting.models import OperatorSupplementReport
        original_pending_reports = OperatorSupplementReport.objects.filter(
            work_quantity=0,  # 數量為0
            allocation_checked=False  # 未檢查過的記錄
        ).select_related('workorder', 'process')
        
        if company_code:
            original_pending_reports = original_pending_reports.filter(
                workorder__company_code=company_code
            )
        
        if company_code:
            pending_reports = pending_reports.filter(
                completed_workorder__company_code=company_code
            )
        
        summary = {
            "total_pending_reports": pending_reports.count() + original_pending_reports.count(),
            "total_workorders": (
                pending_reports.values('completed_workorder__order_number').distinct().count() +
                original_pending_reports.values('workorder__order_number').distinct().count()
            ),
            "processes": {},
            "workorders": {},
            "company_code": company_code
        }
        
        # 按工序統計 - 已完工工單記錄
        for report in pending_reports:
            process_name = report.process_name
            if process_name not in summary["processes"]:
                summary["processes"][process_name] = {
                    "is_packaging": self.is_packaging_process(process_name),
                    "report_count": 0,
                    "total_hours": 0
                }
            
            summary["processes"][process_name]["report_count"] += 1
            summary["processes"][process_name]["total_hours"] += (
                report.work_hours + report.overtime_hours
            )
        
        # 按工序統計 - 原始報工記錄
        for report in original_pending_reports:
            process_name = report.process.name if report.process else "未知工序"
            if process_name not in summary["processes"]:
                summary["processes"][process_name] = {
                    "is_packaging": self.is_packaging_process(process_name),
                    "report_count": 0,
                    "total_hours": 0
                }
            
            summary["processes"][process_name]["report_count"] += 1
            summary["processes"][process_name]["total_hours"] += (
                float(report.work_hours_calculated or 0) + float(report.overtime_hours_calculated or 0)
            )
        
        # 按工單統計 - 已完工工單記錄
        for report in pending_reports:
            workorder_number = report.completed_workorder.order_number
            if workorder_number not in summary["workorders"]:
                summary["workorders"][workorder_number] = {
                    "company_code": report.completed_workorder.company_code,
                    "planned_quantity": report.completed_workorder.planned_quantity,
                    "report_count": 0,
                    "total_hours": 0
                }
            
            summary["workorders"][workorder_number]["report_count"] += 1
            summary["workorders"][workorder_number]["total_hours"] += (
                report.work_hours + report.overtime_hours
            )
        
        # 按工單統計 - 原始報工記錄
        for report in original_pending_reports:
            workorder_number = report.workorder.order_number if report.workorder else "未知工單"
            if workorder_number not in summary["workorders"]:
                summary["workorders"][workorder_number] = {
                    "company_code": report.workorder.company_code if report.workorder else "",
                    "planned_quantity": report.workorder.quantity if report.workorder else 0,
                    "report_count": 0,
                    "total_hours": 0
                }
            
            summary["workorders"][workorder_number]["report_count"] += 1
            summary["workorders"][workorder_number]["total_hours"] += (
                float(report.work_hours_calculated or 0) + float(report.overtime_hours_calculated or 0)
            )
        
        return summary
    
    def get_allocation_summary(self, workorder_number):
        """
        獲取指定工單的分配摘要
        
        Args:
            workorder_number (str): 工單號碼
        
        Returns:
            dict: 分配摘要
        """
        try:
            workorder = WorkOrder.objects.get(order_number=workorder_number)
            reports = OperatorSupplementReport.objects.filter(
                workorder=workorder
            ).select_related('operator', 'process')
            
            summary = {
                "workorder_number": workorder_number,
                "planned_quantity": workorder.quantity,
                "processes": {},
                "total_original_quantity": 0,
                "total_allocated_quantity": 0,
                "excluded_processes": []
            }
            
            for report in reports:
                process_name = report.process.name if report.process else "未知工序"
                
                if process_name not in summary["processes"]:
                    summary["processes"][process_name] = {
                        "is_packaging": self.is_packaging_process(process_name),
                        "original_quantity": 0,
                        "allocated_quantity": 0,
                        "report_count": 0
                    }
                
                summary["processes"][process_name]["report_count"] += 1
                summary["processes"][process_name]["original_quantity"] += report.work_quantity or 0
                summary["processes"][process_name]["allocated_quantity"] += report.allocated_quantity or 0
                
                summary["total_original_quantity"] += report.work_quantity or 0
                summary["total_allocated_quantity"] += report.allocated_quantity or 0
            
            # 標記排除的工序
            for process_name, data in summary["processes"].items():
                if data["is_packaging"]:
                    summary["excluded_processes"].append(process_name)
            
            return summary
            
        except WorkOrder.DoesNotExist:
            return {"error": f"工單 {workorder_number} 不存在"}
        except Exception as e:
            return {"error": f"獲取摘要失敗: {str(e)}"}
    
    def _group_completed_reports_by_process(self, reports):
        """
        按工序名稱分組已完工報工記錄
        """
        process_groups = {}
        for report in reports:
            process_name = report.process_name
            if process_name not in process_groups:
                process_groups[process_name] = []
            process_groups[process_name].append(report)
        return process_groups
    
    def _allocate_completed_process_quantities(self, process_name, reports, total_planned_quantity):
        """
        為單一工序的已完工報工記錄分配數量
        
        Args:
            process_name (str): 工序名稱
            reports (list): 該工序的已完工報工記錄列表
            total_planned_quantity (int): 工單總計劃數量
        
        Returns:
            dict: 分配結果
        """
        logger.info(f"開始為已完工工序 {process_name} 分配數量")
        
        # 分離已填寫數量和未填寫數量的記錄
        filled_reports = [r for r in reports if r.work_quantity and r.work_quantity > 0]
        unfilled_reports = [r for r in reports if not r.work_quantity or r.work_quantity == 0]
        
        # 計算已填寫的總數量
        total_filled_quantity = sum(r.work_quantity for r in filled_reports)
        
        # 計算剩餘需要分配的數量
        remaining_quantity = total_planned_quantity - total_filled_quantity
        
        if remaining_quantity <= 0:
            logger.info(f"已完工工序 {process_name} 已填寫數量 {total_filled_quantity} 超過計劃數量 {total_planned_quantity}")
            return {
                "process_name": process_name,
                "reports_allocated": 0,
                "quantity_allocated": 0,
                "message": f"已填寫數量({total_filled_quantity})超過計劃數量({total_planned_quantity})"
            }
        
        # 計算未填寫記錄的總工時
        total_work_hours = sum(
            r.work_hours + r.overtime_hours
            for r in unfilled_reports
        )
        
        if total_work_hours <= 0:
            logger.warning(f"已完工工序 {process_name} 未填寫記錄的總工時為0")
            return {
                "process_name": process_name,
                "reports_allocated": 0,
                "quantity_allocated": 0,
                "message": "未填寫記錄的總工時為0"
            }
        
        # 按工時比例分配數量
        allocated_reports = []
        total_allocated = 0
        
        for report in unfilled_reports:
            report_hours = report.work_hours + report.overtime_hours
            if report_hours > 0:
                # 按工時比例分配
                allocation_ratio = report_hours / total_work_hours
                allocated_quantity = int(remaining_quantity * allocation_ratio)
                
                # 更新已完工報工記錄
                with transaction.atomic():
                    report.work_quantity = allocated_quantity
                    report.remarks = (
                        f"{report.remarks or ''}\n"
                        f"[自動分配] 工時比例: {allocation_ratio:.2%}, "
                        f"分配數量: {allocated_quantity}, "
                        f"分配時間: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ).strip()
                    report.save()
                
                allocated_reports.append({
                    "report_id": report.id,
                    "operator": report.operator,
                    "report_date": report.report_date,
                    "work_hours": report_hours,
                    "allocated_quantity": allocated_quantity
                })
                
                total_allocated += allocated_quantity
                logger.info(f"為 {report.operator} "
                          f"分配 {allocated_quantity} 件 (工時: {report_hours}小時)")
        
        return {
            "process_name": process_name,
            "reports_allocated": len(allocated_reports),
            "quantity_allocated": total_allocated,
            "total_filled_quantity": total_filled_quantity,
            "remaining_quantity": remaining_quantity,
            "allocated_reports": allocated_reports,
            "message": f"成功分配 {total_allocated} 件給 {len(allocated_reports)} 筆記錄"
        } 