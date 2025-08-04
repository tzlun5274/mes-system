#!/usr/bin/env python3
"""
智能補充產品編號
此命令會使用多種方式來補充作業員和SMT記錄中空白的產品編號
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
from workorder.models import WorkOrder
from django.db import transaction
from collections import defaultdict


class Command(BaseCommand):
    help = '智能補充作業員和SMT記錄中空白的產品編號'

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
        
        # 建立工單號碼到產品編號的對應表
        workorder_product_map = self._build_workorder_product_map()
        
        total_updated = 0
        
        if record_type in ['operator', 'all']:
            operator_updated = self._process_operator_reports(workorder_product_map, dry_run)
            total_updated += operator_updated
        
        if record_type in ['smt', 'all']:
            smt_updated = self._process_smt_reports(workorder_product_map, dry_run)
            total_updated += smt_updated
        
        self.stdout.write(f'\n=== 總計更新結果 ===')
        self.stdout.write(f'總共更新: {total_updated} 筆記錄')
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('智能補充產品編號完成！'))
        else:
            self.stdout.write(self.style.WARNING('乾跑模式完成，未實際更新資料'))

    def _build_workorder_product_map(self):
        """建立工單號碼到產品編號的對應表"""
        self.stdout.write('建立工單號碼到產品編號的對應表...')
        
        workorder_map = {}
        
        # 從工單表取得對應關係
        workorders = WorkOrder.objects.filter(product_code__isnull=False).exclude(product_code='')
        for workorder in workorders:
            workorder_map[workorder.order_number] = workorder.product_code
        
        self.stdout.write(f'工單對應表建立完成，共 {len(workorder_map)} 筆工單')
        return workorder_map

    def _process_operator_reports(self, workorder_product_map, dry_run):
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
                new_product_id = self._find_product_id_for_report(report, workorder_product_map)
                
                if new_product_id:
                    if not dry_run:
                        with transaction.atomic():
                            report.product_id = new_product_id
                            report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新作業員記錄: {report.workorder_number} -> {new_product_id}')
                    else:
                        self.stdout.write(f'將更新作業員記錄: {report.workorder_number} -> {new_product_id}')
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'更新作業員記錄失敗: {report.id} - {str(e)}'))
        
        self.stdout.write(f'作業員記錄更新完成: 成功 {updated_count}, 失敗 {error_count}')
        return updated_count

    def _process_smt_reports(self, workorder_product_map, dry_run):
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
                new_product_id = self._find_product_id_for_report(report, workorder_product_map)
                
                if new_product_id:
                    if not dry_run:
                        with transaction.atomic():
                            report.product_id = new_product_id
                            report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新SMT記錄: {report.workorder_number} -> {new_product_id}')
                    else:
                        self.stdout.write(f'將更新SMT記錄: {report.workorder_number} -> {new_product_id}')
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'更新SMT記錄失敗: {report.id} - {str(e)}'))
        
        self.stdout.write(f'SMT記錄更新完成: 成功 {updated_count}, 失敗 {error_count}')
        return updated_count

    def _find_product_id_for_report(self, report, workorder_product_map):
        """為報工記錄尋找產品編號"""
        # 方法1: 從工單關聯取得
        if report.workorder and hasattr(report.workorder, 'product_code') and report.workorder.product_code:
            return report.workorder.product_code
        
        # 方法2: 從工單號碼對應表取得
        workorder_number = report.workorder_number
        if workorder_number and workorder_number in workorder_product_map:
            return workorder_product_map[workorder_number]
        
        # 方法3: 從RD樣品產品編號取得
        if hasattr(report, 'rd_product_code') and report.rd_product_code:
            return report.rd_product_code
        
        # 方法4: 從同工單的其他記錄取得（如果這個記錄有產品編號）
        if workorder_number:
            # 查找同工單的其他記錄
            if isinstance(report, OperatorSupplementReport):
                # 使用 workorder_id 來查詢同工單的其他記錄
                if report.workorder_id:
                    other_reports = OperatorSupplementReport.objects.filter(
                        workorder_id=report.workorder_id
                    ).exclude(product_id='')
                else:
                    # 如果沒有工單關聯，使用 rd_workorder_number
                    other_reports = OperatorSupplementReport.objects.filter(
                        rd_workorder_number=workorder_number
                    ).exclude(product_id='')
            else:  # SMTProductionReport
                # 使用 workorder_id 來查詢同工單的其他記錄
                if report.workorder_id:
                    other_reports = SMTProductionReport.objects.filter(
                        workorder_id=report.workorder_id
                    ).exclude(product_id='')
                else:
                    # 如果沒有工單關聯，使用 rd_workorder_number
                    other_reports = SMTProductionReport.objects.filter(
                        rd_workorder_number=workorder_number
                    ).exclude(product_id='')
            
            if other_reports.exists():
                return other_reports.first().product_id
        
        return None 