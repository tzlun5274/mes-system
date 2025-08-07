"""
處理重複工單記錄管理命令
處理因公司代號格式不同而產生的重複工單記錄
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.models import WorkOrder, WorkOrderProductionDetail
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTSupplementReport
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '處理重複的工單記錄，將錯誤格式的記錄合併到正確格式的記錄中'

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
            self._handle_duplicate_workorders(dry_run)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'處理過程中發生錯誤: {str(e)}')
            )
            logger.error(f'處理重複工單記錄失敗: {str(e)}')
    
    def _handle_duplicate_workorders(self, dry_run):
        """處理重複的工單記錄"""
        
        # 查找所有有重複記錄的工單號碼
        from django.db.models import Count
        duplicate_order_numbers = WorkOrder.objects.values('order_number').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        self.stdout.write(f'找到 {duplicate_order_numbers.count()} 個有重複記錄的工單號碼')
        
        if duplicate_order_numbers.count() == 0:
            self.stdout.write(
                self.style.SUCCESS('沒有發現重複的工單記錄')
            )
            return
        
        processed_count = 0
        error_count = 0
        
        for duplicate_info in duplicate_order_numbers:
            order_number = duplicate_info['order_number']
            count = duplicate_info['count']
            
            self.stdout.write(f'\n處理工單號碼: {order_number} (有 {count} 筆記錄)')
            
            # 獲取該工單號碼的所有記錄
            workorders = WorkOrder.objects.filter(order_number=order_number).order_by('id')
            
            # 找出正確格式的記錄（公司代號為兩位數）
            correct_workorder = None
            wrong_workorders = []
            
            for workorder in workorders:
                if workorder.company_code and len(workorder.company_code) == 2 and workorder.company_code.isdigit():
                    correct_workorder = workorder
                else:
                    wrong_workorders.append(workorder)
            
            if not correct_workorder:
                self.stdout.write(
                    self.style.WARNING(f'  沒有找到正確格式的記錄，跳過處理')
                )
                continue
            
            self.stdout.write(f'  正確記錄: ID {correct_workorder.id}, 公司代號 "{correct_workorder.company_code}"')
            
            for wrong_workorder in wrong_workorders:
                self.stdout.write(f'  錯誤記錄: ID {wrong_workorder.id}, 公司代號 "{wrong_workorder.company_code}"')
                
                try:
                    if not dry_run:
                        with transaction.atomic():
                            # 合併資料到正確的工單
                            self._merge_workorder_data(wrong_workorder, correct_workorder)
                            # 刪除錯誤的工單
                            wrong_workorder.delete()
                            self.stdout.write(f'    已合併資料並刪除錯誤記錄')
                    else:
                        self.stdout.write(f'    [乾跑模式] 將合併資料並刪除錯誤記錄')
                    
                    processed_count += 1
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'    處理錯誤記錄時發生錯誤: {str(e)}')
                    )
        
        # 輸出統計結果
        self.stdout.write('\n' + '='*50)
        self.stdout.write('重複工單記錄處理結果統計:')
        self.stdout.write(f'  總處理記錄數: {processed_count}')
        self.stdout.write(f'  錯誤數: {error_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('注意: 此為乾跑模式，未進行實際操作')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('重複工單記錄處理完成')
            )
    
    def _merge_workorder_data(self, wrong_workorder, correct_workorder):
        """
        將錯誤工單的資料合併到正確工單中
        
        Args:
            wrong_workorder: 錯誤的工單
            correct_workorder: 正確的工單
        """
        try:
            # 更新生產中工單明細記錄
            production_details = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=wrong_workorder
            )
            
            for detail in production_details:
                detail.workorder_production.workorder = correct_workorder
                detail.workorder_production.save()
            
            self.stdout.write(f'      已更新 {production_details.count()} 筆生產明細記錄')
            
            # 更新作業員報工記錄
            operator_reports = OperatorSupplementReport.objects.filter(workorder=wrong_workorder)
            for report in operator_reports:
                report.workorder = correct_workorder
                report.save()
            
            self.stdout.write(f'      已更新 {operator_reports.count()} 筆作業員報工記錄')
            
            # 更新SMT報工記錄
            smt_reports = SMTSupplementReport.objects.filter(workorder=wrong_workorder)
            for report in smt_reports:
                report.workorder = correct_workorder
                report.save()
            
            self.stdout.write(f'      已更新 {smt_reports.count()} 筆SMT報工記錄')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'      合併資料時發生錯誤: {str(e)}')
            )
            raise 