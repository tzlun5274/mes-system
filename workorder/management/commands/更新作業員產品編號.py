#!/usr/bin/env python3
"""
更新作業員補登報工記錄的產品編號
此命令會自動從工單取得產品編號並更新到作業員記錄中
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport
from django.db import transaction


class Command(BaseCommand):
    help = '更新作業員補登報工記錄的產品編號'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只顯示會更新的記錄數量，不實際更新',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== 乾跑模式 ==='))
        
        # 取得所有作業員記錄
        reports = OperatorSupplementReport.objects.all()
        total_count = reports.count()
        
        self.stdout.write(f'總記錄數: {total_count}')
        
        # 統計需要更新的記錄
        need_update_count = 0
        updated_count = 0
        error_count = 0
        
        for report in reports:
            try:
                # 檢查是否需要更新產品編號
                should_update = False
                new_product_id = ''
                
                if report.workorder and hasattr(report.workorder, 'product_code') and report.workorder.product_code:
                    # 從工單取得產品編號
                    new_product_id = report.workorder.product_code
                    if report.product_id != new_product_id:
                        should_update = True
                elif report.report_type == 'rd_sample' and report.rd_product_code:
                    # RD樣品模式使用rd_product_code
                    new_product_id = report.rd_product_code
                    if report.product_id != new_product_id:
                        should_update = True
                
                if should_update:
                    need_update_count += 1
                    
                    if not dry_run:
                        # 實際更新
                        with transaction.atomic():
                            report.product_id = new_product_id
                            report.save(update_fields=['product_id'])
                        updated_count += 1
                        self.stdout.write(f'已更新: {report.workorder_number} -> {new_product_id}')
                    else:
                        # 乾跑模式只顯示
                        self.stdout.write(f'將更新: {report.workorder_number} -> {new_product_id}')
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'更新失敗: {report.id} - {str(e)}'))
        
        # 顯示結果
        self.stdout.write('\n=== 更新結果 ===')
        self.stdout.write(f'需要更新的記錄: {need_update_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('乾跑模式完成，未實際更新資料'))
        else:
            self.stdout.write(f'成功更新: {updated_count}')
            self.stdout.write(f'更新失敗: {error_count}')
            self.stdout.write(self.style.SUCCESS('產品編號更新完成！'))
        
        # 顯示更新後的統計
        if not dry_run:
            self.stdout.write('\n=== 更新後統計 ===')
            empty_product_id = OperatorSupplementReport.objects.filter(product_id='').count()
            self.stdout.write(f'產品編號為空的記錄: {empty_product_id}')
            
            if empty_product_id == 0:
                self.stdout.write(self.style.SUCCESS('所有記錄的產品編號都已正確填充！'))
            else:
                self.stdout.write(self.style.WARNING(f'仍有 {empty_product_id} 筆記錄的產品編號為空')) 