"""
修復報工記錄關聯管理命令
修復因為工單被刪除而失去關聯的報工記錄
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
from workorder.models import CompletedWorkOrder, WorkOrder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '修復失去工單關聯的報工記錄'

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
            self._fix_operator_reports(dry_run)
            self._fix_smt_reports(dry_run)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'執行過程中發生錯誤: {str(e)}')
            )
            logger.error(f'修復報工記錄關聯命令執行錯誤: {str(e)}')
    
    def _fix_operator_reports(self, dry_run):
        """修復作業員報工記錄的工單關聯"""
        # 獲取所有失去工單關聯的已審核作業員報工
        orphaned_reports = OperatorSupplementReport.objects.filter(
            approval_status='approved',
            workorder__isnull=True
        )
        
        self.stdout.write(f'找到 {orphaned_reports.count()} 筆失去工單關聯的已審核作業員報工')
        
        fixed_count = 0
        
        for report in orphaned_reports:
            workorder_number = report.original_workorder_number
            
            if not workorder_number:
                self.stdout.write(f'  報工記錄 ID {report.id} 沒有工單號碼，跳過')
                continue
            
            # 優先從WorkOrder表找到對應的工單
            workorder = WorkOrder.objects.filter(
                order_number=workorder_number
            ).first()
            
            if workorder:
                # 直接更新報工記錄的工單關聯
                if not dry_run:
                    report.workorder = workorder
                    report.save()
                    self.stdout.write(f'  修復報工記錄 ID {report.id} 的工單關聯: {workorder.order_number}')
                else:
                    self.stdout.write(f'  將修復報工記錄 ID {report.id} 的工單關聯: {workorder.order_number}')
                
                fixed_count += 1
            else:
                # 如果WorkOrder表中沒有，嘗試從已完工工單表找到對應的工單
                completed_workorder = CompletedWorkOrder.objects.filter(
                    order_number=workorder_number
                ).first()
                
                if completed_workorder:
                    # 創建新的WorkOrder記錄
                    if not dry_run:
                        workorder = WorkOrder.objects.create(
                            order_number=completed_workorder.order_number,
                            product_code=completed_workorder.product_code,
                            company_code=completed_workorder.company_code,
                            quantity=completed_workorder.planned_quantity,
                            status='completed',
                            completed_at=completed_workorder.completed_at
                        )
                        self.stdout.write(f'  創建工單記錄: {workorder.order_number}')
                    else:
                        self.stdout.write(f'  將創建工單記錄: {completed_workorder.order_number}')
                    
                    # 更新報工記錄的工單關聯
                    if not dry_run:
                        report.workorder = workorder
                        report.save()
                        self.stdout.write(f'  修復報工記錄 ID {report.id} 的工單關聯: {workorder.order_number}')
                    else:
                        self.stdout.write(f'  將修復報工記錄 ID {report.id} 的工單關聯: {workorder.order_number}')
                    
                    fixed_count += 1
                else:
                    self.stdout.write(f'  找不到工單號 {workorder_number} 的記錄')
        
        self.stdout.write(f'成功修復 {fixed_count} 筆作業員報工記錄')
    
    def _fix_smt_reports(self, dry_run):
        """修復SMT報工記錄的工單關聯"""
        # 獲取所有失去工單關聯的已審核SMT報工
        orphaned_reports = SMTProductionReport.objects.filter(
            approval_status='approved',
            workorder__isnull=True
        )
        
        self.stdout.write(f'找到 {orphaned_reports.count()} 筆失去工單關聯的已審核SMT報工')
        
        fixed_count = 0
        
        for report in orphaned_reports:
            workorder_number = report.original_workorder_number
            
            if not workorder_number:
                self.stdout.write(f'  報工記錄 ID {report.id} 沒有工單號碼，跳過')
                continue
            
            # 優先從WorkOrder表找到對應的工單
            workorder = WorkOrder.objects.filter(
                order_number=workorder_number
            ).first()
            
            if workorder:
                # 直接更新報工記錄的工單關聯
                if not dry_run:
                    report.workorder = workorder
                    report.save()
                    self.stdout.write(f'  修復報工記錄 ID {report.id} 的工單關聯: {workorder.order_number}')
                else:
                    self.stdout.write(f'  將修復報工記錄 ID {report.id} 的工單關聯: {workorder.order_number}')
                
                fixed_count += 1
            else:
                # 如果WorkOrder表中沒有，嘗試從已完工工單表找到對應的工單
                completed_workorder = CompletedWorkOrder.objects.filter(
                    order_number=workorder_number
                ).first()
                
                if completed_workorder:
                    # 創建新的WorkOrder記錄
                    if not dry_run:
                        workorder = WorkOrder.objects.create(
                            order_number=completed_workorder.order_number,
                            product_code=completed_workorder.product_code,
                            company_code=completed_workorder.company_code,
                            quantity=completed_workorder.planned_quantity,
                            status='completed',
                            completed_at=completed_workorder.completed_at
                        )
                        self.stdout.write(f'  創建工單記錄: {workorder.order_number}')
                    else:
                        self.stdout.write(f'  將創建工單記錄: {completed_workorder.order_number}')
                    
                    # 更新報工記錄的工單關聯
                    if not dry_run:
                        report.workorder = workorder
                        report.save()
                        self.stdout.write(f'  修復報工記錄 ID {report.id} 的工單關聯: {workorder.order_number}')
                    else:
                        self.stdout.write(f'  將修復報工記錄 ID {report.id} 的工單關聯: {workorder.order_number}')
                    
                    fixed_count += 1
                else:
                    self.stdout.write(f'  找不到工單號 {workorder_number} 的記錄')
        
        self.stdout.write(f'成功修復 {fixed_count} 筆SMT報工記錄') 