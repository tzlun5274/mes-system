"""
統一修復產品編號管理命令
整合所有產品編號修復功能，一次性解決所有問題
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
from workorder.models import WorkOrder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '統一修復所有產品編號問題'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅檢查不執行實際操作',
        )
        parser.add_argument(
            '--step',
            type=int,
            choices=[1, 2, 3, 4, 5],
            help='執行特定步驟 (1:檢查 2:修復關聯 3:補充產品編號 4:驗證 5:全部)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        step = options.get('step', 5)  # 預設執行全部步驟
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('執行乾跑模式，不會進行實際操作')
            )
        
        try:
            if step in [1, 5]:
                self._step1_check_status()
            
            if step in [2, 5]:
                self._step2_fix_workorder_relations(dry_run)
            
            if step in [3, 5]:
                self._step3_fill_product_ids(dry_run)
            
            if step in [4, 5]:
                self._step4_verify_results()
            
            self.stdout.write(
                self.style.SUCCESS('產品編號修復完成！')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'執行過程中發生錯誤: {str(e)}')
            )
            logger.error(f'統一修復產品編號命令執行錯誤: {str(e)}')
    
    def _step1_check_status(self):
        """步驟1: 檢查目前狀態"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('步驟1: 檢查目前狀態')
        self.stdout.write('='*60)
        
        # 檢查作業員報工記錄
        operator_reports = OperatorSupplementReport.objects.all()
        operator_empty = operator_reports.filter(product_id='').count()
        operator_total = operator_reports.count()
        
        self.stdout.write(f'作業員報工記錄:')
        self.stdout.write(f'  總數: {operator_total}')
        self.stdout.write(f'  產品編號為空: {operator_empty} ({operator_empty/operator_total*100:.1f}%)')
        
        # 檢查SMT報工記錄
        smt_reports = SMTProductionReport.objects.all()
        smt_empty = smt_reports.filter(product_id='').count()
        smt_total = smt_reports.count()
        
        self.stdout.write(f'SMT報工記錄:')
        self.stdout.write(f'  總數: {smt_total}')
        self.stdout.write(f'  產品編號為空: {smt_empty} ({smt_empty/smt_total*100:.1f}%)')
        
        # 檢查工單表
        workorders = WorkOrder.objects.all()
        workorder_empty = workorders.filter(product_code='').count()
        workorder_total = workorders.count()
        
        self.stdout.write(f'工單記錄:')
        self.stdout.write(f'  總數: {workorder_total}')
        self.stdout.write(f'  產品編號為空: {workorder_empty} ({workorder_empty/workorder_total*100:.1f}%)')
    
    def _step2_fix_workorder_relations(self, dry_run):
        """步驟2: 修復工單關聯"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('步驟2: 修復工單關聯')
        self.stdout.write('='*60)
        
        # 修復作業員報工記錄的工單關聯
        operator_reports_no_workorder = OperatorSupplementReport.objects.filter(
            workorder__isnull=True,
            product_id=''
        )
        
        self.stdout.write(f'找到 {operator_reports_no_workorder.count()} 筆沒有工單關聯的作業員報工記錄')
        
        fixed_count = 0
        for report in operator_reports_no_workorder:
            workorder_number = report.workorder_number
            if workorder_number and workorder_number != 'RD樣品':
                try:
                    workorder = WorkOrder.objects.get(order_number=workorder_number)
                    if not dry_run:
                        report.workorder = workorder
                        report.save()
                    self.stdout.write(f'  修復報工記錄 ID {report.id} 的工單關聯: {workorder_number}')
                    fixed_count += 1
                except WorkOrder.DoesNotExist:
                    self.stdout.write(f'  工單 {workorder_number} 不存在')
        
        self.stdout.write(f'成功修復 {fixed_count} 筆作業員報工記錄的工單關聯')
    
    def _step3_fill_product_ids(self, dry_run):
        """步驟3: 補充產品編號"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('步驟3: 補充產品編號')
        self.stdout.write('='*60)
        
        # 處理作業員報工記錄
        operator_empty = OperatorSupplementReport.objects.filter(product_id='')
        self.stdout.write(f'處理 {operator_empty.count()} 筆產品編號為空的作業員報工記錄')
        
        operator_fixed = 0
        for report in operator_empty:
            new_product_id = self._find_product_id_for_report(report)
            if new_product_id:
                if not dry_run:
                    with transaction.atomic():
                        report.product_id = new_product_id
                        report.save(update_fields=['product_id'])
                self.stdout.write(f'  修復作業員報工記錄 ID {report.id}: {report.workorder_number} -> {new_product_id}')
                operator_fixed += 1
        
        # 處理SMT報工記錄
        smt_empty = SMTProductionReport.objects.filter(product_id='')
        self.stdout.write(f'處理 {smt_empty.count()} 筆產品編號為空的SMT報工記錄')
        
        smt_fixed = 0
        for report in smt_empty:
            new_product_id = self._find_product_id_for_report(report)
            if new_product_id:
                if not dry_run:
                    with transaction.atomic():
                        report.product_id = new_product_id
                        report.save(update_fields=['product_id'])
                self.stdout.write(f'  修復SMT報工記錄 ID {report.id}: {report.workorder_number} -> {new_product_id}')
                smt_fixed += 1
        
        self.stdout.write(f'成功修復 {operator_fixed} 筆作業員報工記錄')
        self.stdout.write(f'成功修復 {smt_fixed} 筆SMT報工記錄')
    
    def _step4_verify_results(self):
        """步驟4: 驗證結果"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('步驟4: 驗證結果')
        self.stdout.write('='*60)
        
        # 檢查修復後的結果
        operator_empty = OperatorSupplementReport.objects.filter(product_id='').count()
        smt_empty = SMTProductionReport.objects.filter(product_id='').count()
        
        self.stdout.write(f'修復後結果:')
        self.stdout.write(f'  作業員報工記錄產品編號為空: {operator_empty} 筆')
        self.stdout.write(f'  SMT報工記錄產品編號為空: {smt_empty} 筆')
        
        if operator_empty == 0 and smt_empty == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ 所有產品編號都已修復完成！')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  仍有 {operator_empty + smt_empty} 筆記錄產品編號為空')
            )
    
    def _find_product_id_for_report(self, report):
        """為報工記錄尋找產品編號"""
        # 方法1: 從工單關聯取得
        if report.workorder and hasattr(report.workorder, 'product_code') and report.workorder.product_code:
            return report.workorder.product_code
        
        # 方法2: 從RD樣品產品編號取得
        if hasattr(report, 'rd_product_code') and report.rd_product_code:
            return report.rd_product_code
        
        # 方法3: 從工單號碼查找工單表
        workorder_number = report.workorder_number
        if workorder_number and workorder_number != 'None':
            try:
                workorder = WorkOrder.objects.get(order_number=workorder_number)
                if workorder.product_code:
                    return workorder.product_code
            except WorkOrder.DoesNotExist:
                pass
        
        # 方法4: 從原始工單號碼查找工單表
        if hasattr(report, 'original_workorder_number') and report.original_workorder_number:
            try:
                workorder = WorkOrder.objects.get(order_number=report.original_workorder_number)
                if workorder.product_code:
                    return workorder.product_code
            except WorkOrder.DoesNotExist:
                pass
        
        # 方法5: 從RD工單號碼查找工單表
        if hasattr(report, 'rd_workorder_number') and report.rd_workorder_number:
            try:
                workorder = WorkOrder.objects.get(order_number=report.rd_workorder_number)
                if workorder.product_code:
                    return workorder.product_code
            except WorkOrder.DoesNotExist:
                pass
        
        # 方法6: 從同工單號碼的其他記錄取得產品編號
        if workorder_number:
            if isinstance(report, OperatorSupplementReport):
                other_reports = OperatorSupplementReport.objects.filter(
                    workorder_number=workorder_number
                ).exclude(product_id='')
            else:  # SMTProductionReport
                other_reports = SMTProductionReport.objects.filter(
                    workorder_number=workorder_number
                ).exclude(product_id='')
            
            if other_reports.exists():
                return other_reports.first().product_id
        
        # 方法7: 根據工單號碼模式推測產品編號
        if workorder_number and workorder_number != 'RD樣品':
            # 嘗試從工單號碼中提取產品編號
            # 例如: 331-25723001 -> 25723001
            if '-' in workorder_number:
                parts = workorder_number.split('-')
                if len(parts) >= 2:
                    potential_product_code = parts[1]
                    # 檢查這個產品編號是否存在於工單表中
                    if WorkOrder.objects.filter(product_code=potential_product_code).exists():
                        return potential_product_code
        
        return None 