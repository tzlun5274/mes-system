#!/usr/bin/env python3
"""
從其他記錄補充產品編號
此命令會從同工單的其他記錄中比對並補充空白的產品編號
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
from django.db import transaction
from collections import defaultdict


class Command(BaseCommand):
    help = '從其他記錄比對並補充報工記錄中空白的產品編號'

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
            self.stdout.write(self.style.SUCCESS('從其他記錄補充產品編號完成！'))
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
        
        # 建立工單號碼到產品編號的對應表
        workorder_product_map = {}
        
        # 從有產品編號的記錄建立對應表
        for report in reports:
            if report.product_id and report.product_id.strip():  # 有產品編號的記錄
                # 使用原始工單號碼作為鍵值
                if report.original_workorder_number:
                    workorder_product_map[report.original_workorder_number] = report.product_id
                
                # 也使用RD工單號碼作為鍵值（如果有的話）
                if report.rd_workorder_number and report.rd_workorder_number != 'None':
                    workorder_product_map[report.rd_workorder_number] = report.product_id
        
        self.stdout.write(f'建立工單對應表，共 {len(workorder_product_map)} 個工單號碼有產品編號')
        
        # 顯示一些對應表的範例
        if workorder_product_map:
            self.stdout.write('工單對應表示範:')
            for i, (key, product_id) in enumerate(list(workorder_product_map.items())[:5]):
                self.stdout.write(f'  {key} -> {product_id}')
        
        # 處理產品編號為空的記錄
        empty_reports = reports.filter(product_id='')
        
        # 統計空白記錄的工單識別情況
        no_workorder_key_count = 0
        no_match_count = 0
        
        for report in empty_reports:
            try:
                # 優先使用原始工單號碼
                workorder_key = None
                if report.original_workorder_number and report.original_workorder_number != 'None':
                    workorder_key = report.original_workorder_number
                elif report.rd_workorder_number and report.rd_workorder_number != 'None':
                    workorder_key = report.rd_workorder_number
                
                if not workorder_key:
                    no_workorder_key_count += 1
                    continue
                
                if workorder_key in workorder_product_map:
                    new_product_id = workorder_product_map[workorder_key]
                    
                    if not dry_run:
                        with transaction.atomic():
                            report.product_id = new_product_id
                            report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新作業員記錄: {workorder_key} -> {new_product_id}')
                    else:
                        self.stdout.write(f'將更新作業員記錄: {workorder_key} -> {new_product_id}')
                else:
                    no_match_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'更新作業員記錄失敗: {report.id} - {str(e)}'))
        
        self.stdout.write(f'作業員記錄更新完成: 成功 {updated_count}, 失敗 {error_count}')
        self.stdout.write(f'無法識別工單的記錄: {no_workorder_key_count}')
        self.stdout.write(f'找不到對應產品編號的記錄: {no_match_count}')
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
        
        # 按工單分組，找出每個工單的產品編號
        workorder_product_map = {}
        
        # 先建立工單到產品編號的對應表
        for report in reports:
            if report.product_id and report.product_id.strip():  # 有產品編號的記錄
                workorder_key = self._get_workorder_key(report)
                if workorder_key:
                    workorder_product_map[workorder_key] = report.product_id
        
        self.stdout.write(f'建立工單對應表，共 {len(workorder_product_map)} 個工單有產品編號')
        
        # 處理產品編號為空的記錄
        empty_reports = reports.filter(product_id='')
        
        for report in empty_reports:
            try:
                workorder_key = self._get_workorder_key(report)
                if workorder_key and workorder_key in workorder_product_map:
                    new_product_id = workorder_product_map[workorder_key]
                    
                    if not dry_run:
                        with transaction.atomic():
                            report.product_id = new_product_id
                            report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新SMT記錄: {workorder_key} -> {new_product_id}')
                    else:
                        self.stdout.write(f'將更新SMT記錄: {workorder_key} -> {new_product_id}')
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'更新SMT記錄失敗: {report.id} - {str(e)}'))
        
        self.stdout.write(f'SMT記錄更新完成: 成功 {updated_count}, 失敗 {error_count}')
        return updated_count

    def _get_workorder_key(self, report):
        """取得工單的唯一識別鍵"""
        # 優先使用工單關聯
        if report.workorder_id:
            return f"workorder_{report.workorder_id}"
        
        # 使用RD工單號碼
        if hasattr(report, 'rd_workorder_number') and report.rd_workorder_number:
            return f"rd_{report.rd_workorder_number}"
        
        # 使用原始工單號碼
        if hasattr(report, 'original_workorder_number') and report.original_workorder_number:
            return f"original_{report.original_workorder_number}"
        
        return None 