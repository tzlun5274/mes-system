"""
從工單號碼提取產品編號管理命令
針對沒有其他資料來源的記錄，從工單號碼中提取產品編號
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '從工單號碼中提取產品編號'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅檢查不執行實際操作',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('執行乾跑模式，不會進行實際操作')
            )
        
        try:
            self._extract_from_operator_reports(dry_run)
            self._extract_from_smt_reports(dry_run)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'執行過程中發生錯誤: {str(e)}')
            )
            logger.error(f'從工單號碼提取產品編號命令執行錯誤: {str(e)}')
    
    def _extract_from_operator_reports(self, dry_run):
        """從作業員報工記錄中提取產品編號"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('從作業員報工記錄中提取產品編號')
        self.stdout.write('='*60)
        
        # 獲取所有產品編號為空的記錄
        empty_reports = OperatorSupplementReport.objects.filter(product_id='')
        
        self.stdout.write(f'找到 {empty_reports.count()} 筆產品編號為空的作業員報工記錄')
        
        extracted_count = 0
        error_count = 0
        
        for report in empty_reports:
            try:
                # 從工單號碼中提取產品編號
                extracted_product_id = self._extract_product_id_from_workorder_number(report)
                
                if extracted_product_id:
                    if not dry_run:
                        with transaction.atomic():
                            report.product_id = extracted_product_id
                            report.save(update_fields=['product_id'])
                    
                    workorder_number = report.original_workorder_number or report.rd_workorder_number or '未知'
                    self.stdout.write(f'  提取成功: {workorder_number} -> {extracted_product_id}')
                    extracted_count += 1
                else:
                    workorder_number = report.original_workorder_number or report.rd_workorder_number or '未知'
                    self.stdout.write(f'  無法提取: {workorder_number}')
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  處理記錄 ID {report.id} 時發生錯誤: {str(e)}')
                )
        
        self.stdout.write(f'\n提取結果:')
        self.stdout.write(f'  成功提取: {extracted_count} 筆')
        self.stdout.write(f'  提取失敗: {error_count} 筆')
    
    def _extract_from_smt_reports(self, dry_run):
        """從SMT報工記錄中提取產品編號"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('從SMT報工記錄中提取產品編號')
        self.stdout.write('='*60)
        
        # 獲取所有產品編號為空的記錄
        empty_reports = SMTProductionReport.objects.filter(product_id='')
        
        self.stdout.write(f'找到 {empty_reports.count()} 筆產品編號為空的SMT報工記錄')
        
        extracted_count = 0
        error_count = 0
        
        for report in empty_reports:
            try:
                # 從工單號碼中提取產品編號
                extracted_product_id = self._extract_product_id_from_workorder_number(report)
                
                if extracted_product_id:
                    if not dry_run:
                        with transaction.atomic():
                            report.product_id = extracted_product_id
                            report.save(update_fields=['product_id'])
                    
                    workorder_number = report.original_workorder_number or report.rd_workorder_number or '未知'
                    self.stdout.write(f'  提取成功: {workorder_number} -> {extracted_product_id}')
                    extracted_count += 1
                else:
                    workorder_number = report.original_workorder_number or report.rd_workorder_number or '未知'
                    self.stdout.write(f'  無法提取: {workorder_number}')
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  處理記錄 ID {report.id} 時發生錯誤: {str(e)}')
                )
        
        self.stdout.write(f'\n提取結果:')
        self.stdout.write(f'  成功提取: {extracted_count} 筆')
        self.stdout.write(f'  提取失敗: {error_count} 筆')
    
    def _extract_product_id_from_workorder_number(self, report):
        """從工單號碼中提取產品編號"""
        # 獲取工單號碼
        workorder_number = None
        
        if hasattr(report, 'original_workorder_number') and report.original_workorder_number:
            workorder_number = report.original_workorder_number
        elif hasattr(report, 'rd_workorder_number') and report.rd_workorder_number:
            workorder_number = report.rd_workorder_number
        
        if not workorder_number or workorder_number == 'RD樣品':
            return None
        
        # 提取產品編號的方法
        extracted_id = None
        
        # 方法1: 從格式 "331-25723001" 提取 "25723001"
        if '-' in workorder_number:
            parts = workorder_number.split('-')
            if len(parts) >= 2:
                potential_id = parts[1]
                # 檢查是否為有效的產品編號格式（數字或字母數字組合）
                if self._is_valid_product_id(potential_id):
                    extracted_id = potential_id
        
        # 方法2: 如果沒有破折號，直接使用工單號碼
        elif self._is_valid_product_id(workorder_number):
            extracted_id = workorder_number
        
        return extracted_id
    
    def _is_valid_product_id(self, product_id):
        """檢查是否為有效的產品編號格式"""
        if not product_id:
            return False
        
        # 產品編號應該至少包含一些字母或數字
        if len(product_id) < 3:
            return False
        
        # 檢查是否包含有效的字符（字母、數字、連字符等）
        valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
        if not all(c in valid_chars for c in product_id):
            return False
        
        return True 