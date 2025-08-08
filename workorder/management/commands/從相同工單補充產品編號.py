#!/usr/bin/env python3
"""
從相同工單補充產品編號
從相同公司代號和工單號的其他記錄中找到產品編號來補充空白記錄
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import BackupOperatorSupplementReport as OperatorSupplementReport, BackupSMTSupplementReport as SMTSupplementReport
from workorder.models import WorkOrder
from django.db import transaction, models


class Command(BaseCommand):
    help = '從相同公司代號和工單號的其他記錄中補充產品編號'

    def handle(self, *args, **options):
        self.stdout.write('開始從相同工單補充產品編號...')
        
        # 處理作業員記錄
        operator_updated = self._update_operator_reports()
        
        # 處理SMT記錄
        smt_updated = self._update_smt_reports()
        
        self.stdout.write(f'完成！作業員記錄更新: {operator_updated}, SMT記錄更新: {smt_updated}')

    def _update_operator_reports(self):
        """更新作業員記錄的產品編號"""
        self.stdout.write('處理作業員記錄...')
        
        # 找出產品編號為空的記錄
        empty_reports = OperatorSupplementReport.objects.filter(
            models.Q(product_id='') | 
            models.Q(product_id__isnull=True) |
            models.Q(product_id='nan')
        )
        self.stdout.write(f'找到 {empty_reports.count()} 筆空白產品編號的作業員記錄')
        
        updated_count = 0
        
        for report in empty_reports:
            try:
                # 方法1: 從相同公司代號和工單號的其他記錄中找到產品編號
                if report.company_code and report.original_workorder_number:
                    # 查找相同公司代號和工單號的其他記錄
                    same_company_workorder_reports = OperatorSupplementReport.objects.filter(
                        company_code=report.company_code,
                        original_workorder_number=report.original_workorder_number
                    ).exclude(
                        models.Q(product_id='') | 
                        models.Q(product_id__isnull=True) |
                        models.Q(product_id='nan')
                    )
                    
                    if same_company_workorder_reports.exists():
                        # 找到有產品編號的記錄
                        reference_report = same_company_workorder_reports.first()
                        report.product_id = reference_report.product_id
                        report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新(相同工單): {report.company_code}-{report.original_workorder_number} -> {reference_report.product_id}')
                        continue
                
                # 方法2: 從工單關聯取得產品編號
                if report.workorder and report.workorder.product_code:
                    report.product_id = report.workorder.product_code
                    report.save(update_fields=['product_id'])
                    updated_count += 1
                    self.stdout.write(f'已更新(關聯工單): {report.original_workorder_number} -> {report.workorder.product_code}')
                    continue
                
                # 方法3: 從original_workorder_number查找工單
                if report.original_workorder_number:
                    workorders = WorkOrder.objects.filter(order_number=report.original_workorder_number)
                    
                    if workorders.count() == 1:
                        workorder = workorders.first()
                        if workorder.product_code:
                            report.product_id = workorder.product_code
                            report.save(update_fields=['product_id'])
                            updated_count += 1
                            self.stdout.write(f'已更新(單一工單): {report.original_workorder_number} -> {workorder.product_code}')
                            continue
                    
                    elif workorders.count() > 1:
                        workorder_with_product = workorders.filter(product_code__isnull=False).exclude(product_code='').first()
                        if workorder_with_product:
                            report.product_id = workorder_with_product.product_code
                            report.save(update_fields=['product_id'])
                            updated_count += 1
                            self.stdout.write(f'已更新(多工單選擇): {report.original_workorder_number} -> {workorder_with_product.product_code}')
                            continue
                
                # 如果都沒有找到，標記為無法更新
                self.stdout.write(f'無法找到產品編號: {report.company_code}-{report.original_workorder_number}')
                
            except Exception as e:
                self.stdout.write(f'更新失敗: {report.id} - {str(e)}')
        
        return updated_count

    def _update_smt_reports(self):
        """更新SMT記錄的產品編號"""
        self.stdout.write('處理SMT記錄...')
        
        # 找出產品編號為空的記錄
        empty_reports = SMTSupplementReport.objects.filter(
            models.Q(product_id='') | 
            models.Q(product_id__isnull=True) |
            models.Q(product_id='nan')
        )
        self.stdout.write(f'找到 {empty_reports.count()} 筆空白產品編號的SMT記錄')
        
        updated_count = 0
        
        for report in empty_reports:
            try:
                # 方法1: 從相同公司代號和工單號的其他記錄中找到產品編號
                if report.company_code and report.original_workorder_number:
                    # 查找相同公司代號和工單號的其他記錄
                    same_company_workorder_reports = SMTSupplementReport.objects.filter(
                        company_code=report.company_code,
                        original_workorder_number=report.original_workorder_number
                    ).exclude(
                        models.Q(product_id='') | 
                        models.Q(product_id__isnull=True) |
                        models.Q(product_id='nan')
                    )
                    
                    if same_company_workorder_reports.exists():
                        # 找到有產品編號的記錄
                        reference_report = same_company_workorder_reports.first()
                        report.product_id = reference_report.product_id
                        report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新(相同工單): {report.company_code}-{report.original_workorder_number} -> {reference_report.product_id}')
                        continue
                
                # 方法2: 從工單關聯取得產品編號
                if report.workorder and report.workorder.product_code:
                    report.product_id = report.workorder.product_code
                    report.save(update_fields=['product_id'])
                    updated_count += 1
                    self.stdout.write(f'已更新(關聯工單): {report.original_workorder_number} -> {report.workorder.product_code}')
                    continue
                
                # 方法3: 從original_workorder_number查找工單
                if report.original_workorder_number:
                    workorders = WorkOrder.objects.filter(order_number=report.original_workorder_number)
                    
                    if workorders.count() == 1:
                        workorder = workorders.first()
                        if workorder.product_code:
                            report.product_id = workorder.product_code
                            report.save(update_fields=['product_id'])
                            updated_count += 1
                            self.stdout.write(f'已更新(單一工單): {report.original_workorder_number} -> {workorder.product_code}')
                            continue
                    
                    elif workorders.count() > 1:
                        workorder_with_product = workorders.filter(product_code__isnull=False).exclude(product_code='').first()
                        if workorder_with_product:
                            report.product_id = workorder_with_product.product_code
                            report.save(update_fields=['product_id'])
                            updated_count += 1
                            self.stdout.write(f'已更新(多工單選擇): {report.original_workorder_number} -> {workorder_with_product.product_code}')
                            continue
                
                # 如果都沒有找到，標記為無法更新
                self.stdout.write(f'無法找到產品編號: {report.company_code}-{report.original_workorder_number}')
                
            except Exception as e:
                self.stdout.write(f'更新失敗: {report.id} - {str(e)}')
        
        return updated_count 