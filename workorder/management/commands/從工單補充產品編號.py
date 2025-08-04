#!/usr/bin/env python3
"""
從工單補充產品編號
此命令會直接從工單表取得產品編號來補充報工記錄
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
from workorder.models import WorkOrder
from django.db import transaction


class Command(BaseCommand):
    help = '從工單表取得產品編號來補充報工記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只顯示會更新的記錄數量，不實際更新',
        )
        parser.add_argument(
            '--type',
            choices=['operator', 'smt', 'all'],
            default='all',
            help='指定要處理的記錄類型',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        record_type = options['type']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== 乾跑模式 ==='))
        
        self.stdout.write(f'處理記錄類型: {record_type}')
        
        total_updated = 0
        
        if record_type in ['operator', 'all']:
            operator_updated = self._process_operator_reports(dry_run)
            total_updated += operator_updated
        
        if record_type in ['smt', 'all']:
            smt_updated = self._process_smt_reports(dry_run)
            total_updated += smt_updated
        
        self.stdout.write(f'\n=== 總計更新結果 ===')
        self.stdout.write(f'總共更新: {total_updated} 筆記錄')
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('從工單補充產品編號完成！'))
        else:
            self.stdout.write(self.style.WARNING('乾跑模式完成，未實際更新資料'))

    def _process_operator_reports(self, dry_run):
        """處理作業員記錄"""
        self.stdout.write('\n=== 處理作業員記錄 ===')
        
        reports = OperatorSupplementReport.objects.all()
        total_count = reports.count()
        empty_product_id = reports.filter(product_id='').count()
        
        self.stdout.write(f'總記錄數: {total_count}')
        self.stdout.write(f'產品編號為空的記錄: {empty_product_id}')
        
        updated_count = 0
        error_count = 0
        
        # 處理產品編號為空的記錄
        empty_reports = reports.filter(product_id='')
        
        for report in empty_reports:
            try:
                new_product_id = self._find_product_id_from_workorder(report)
                
                if new_product_id:
                    if not dry_run:
                        with transaction.atomic():
                            report.product_id = new_product_id
                            report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新作業員記錄: {report.original_workorder_number} -> {new_product_id}')
                    else:
                        self.stdout.write(f'將更新作業員記錄: {report.original_workorder_number} -> {new_product_id}')
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'更新作業員記錄失敗: {report.id} - {str(e)}'))
        
        self.stdout.write(f'作業員記錄更新完成: 成功 {updated_count}, 失敗 {error_count}')
        return updated_count

    def _process_smt_reports(self, dry_run):
        """處理SMT記錄"""
        self.stdout.write('\n=== 處理SMT記錄 ===')
        
        reports = SMTProductionReport.objects.all()
        total_count = reports.count()
        empty_product_id = reports.filter(product_id='').count()
        
        self.stdout.write(f'總記錄數: {total_count}')
        self.stdout.write(f'產品編號為空的記錄: {empty_product_id}')
        
        updated_count = 0
        error_count = 0
        
        # 處理產品編號為空的記錄
        empty_reports = reports.filter(product_id='')
        
        for report in empty_reports:
            try:
                new_product_id = self._find_product_id_from_workorder(report)
                
                if new_product_id:
                    if not dry_run:
                        with transaction.atomic():
                            report.product_id = new_product_id
                            report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新SMT記錄: {report.original_workorder_number} -> {new_product_id}')
                    else:
                        self.stdout.write(f'將更新SMT記錄: {report.original_workorder_number} -> {new_product_id}')
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'更新SMT記錄失敗: {report.id} - {str(e)}'))
        
        self.stdout.write(f'SMT記錄更新完成: 成功 {updated_count}, 失敗 {error_count}')
        return updated_count

    def _find_product_id_from_workorder(self, report):
        """從工單表尋找產品編號"""
        # 方法1: 從工單關聯取得
        if report.workorder and hasattr(report.workorder, 'product_code') and report.workorder.product_code:
            return report.workorder.product_code
        
        # 方法2: 從original_workorder_number查找工單
        if report.original_workorder_number and report.original_workorder_number != 'None':
            try:
                workorder = WorkOrder.objects.get(order_number=report.original_workorder_number)
                if workorder.product_code:
                    return workorder.product_code
            except WorkOrder.DoesNotExist:
                pass
        
        # 方法3: 從rd_workorder_number查找工單
        if report.rd_workorder_number and report.rd_workorder_number != 'None':
            try:
                workorder = WorkOrder.objects.get(order_number=report.rd_workorder_number)
                if workorder.product_code:
                    return workorder.product_code
            except WorkOrder.DoesNotExist:
                pass
        
        return None 