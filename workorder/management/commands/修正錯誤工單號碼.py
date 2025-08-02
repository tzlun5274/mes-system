"""
修正錯誤工單號碼管理命令
修正工單號碼中的空格錯誤，例如將 "331-2 5212001" 修正為 "331-25212001"
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.models import WorkOrder, WorkOrderProductionDetail
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '修正工單號碼中的空格錯誤'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅檢查不執行實際修正',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('執行乾跑模式，不會進行實際修正')
            )
        
        try:
            self._fix_workorder_numbers(dry_run)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'修正過程中發生錯誤: {str(e)}')
            )
            logger.error(f'修正錯誤工單號碼失敗: {str(e)}')
    
    def _fix_workorder_numbers(self, dry_run):
        """修正工單號碼中的空格錯誤"""
        
        # 查找所有包含空格的工單號碼
        workorders_with_spaces = WorkOrder.objects.filter(
            order_number__contains=' '
        )
        
        self.stdout.write(f'找到 {workorders_with_spaces.count()} 個包含空格的工單號碼')
        
        if workorders_with_spaces.count() == 0:
            self.stdout.write(
                self.style.SUCCESS('沒有發現包含空格的工單號碼')
            )
            return
        
        # 顯示所有包含空格的工單號碼
        self.stdout.write('\n包含空格的工單號碼列表:')
        for workorder in workorders_with_spaces:
            self.stdout.write(f'  ID: {workorder.id}, 錯誤工單號: "{workorder.order_number}"')
        
        # 修正每個工單號碼
        fixed_count = 0
        error_count = 0
        
        for workorder in workorders_with_spaces:
            try:
                original_number = workorder.order_number
                corrected_number = original_number.replace(' ', '')
                
                self.stdout.write(f'\n修正工單 ID {workorder.id}:')
                self.stdout.write(f'  原始號碼: "{original_number}"')
                self.stdout.write(f'  修正號碼: "{corrected_number}"')
                
                # 檢查修正後的號碼是否已存在
                existing_workorder = WorkOrder.objects.filter(
                    order_number=corrected_number
                ).exclude(id=workorder.id).first()
                
                if existing_workorder:
                    self.stdout.write(
                        self.style.WARNING(f'  警告: 修正後的號碼 "{corrected_number}" 已存在 (工單ID: {existing_workorder.id})')
                    )
                    self.stdout.write(f'  建議: 將錯誤工單的資料合併到正確工單中，然後刪除錯誤工單')
                    
                    if not dry_run:
                        # 合併資料到正確的工單
                        self._merge_workorder_data(workorder, existing_workorder)
                        # 刪除錯誤的工單
                        workorder.delete()
                        self.stdout.write(f'  已合併資料並刪除錯誤工單')
                        fixed_count += 1
                    else:
                        self.stdout.write(f'  [乾跑模式] 將合併資料並刪除錯誤工單')
                        fixed_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        # 更新工單號碼
                        workorder.order_number = corrected_number
                        workorder.save()
                        
                        # 更新相關的生產中工單明細記錄
                        production_details = WorkOrderProductionDetail.objects.filter(
                            workorder_production__workorder=workorder
                        )
                        
                        self.stdout.write(f'  已修正工單號碼')
                        self.stdout.write(f'  相關生產明細記錄: {production_details.count()} 筆')
                        
                        fixed_count += 1
                else:
                    self.stdout.write(f'  [乾跑模式] 將修正工單號碼')
                    fixed_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  修正工單 {workorder.order_number} 時發生錯誤: {str(e)}')
                )
        
        # 輸出統計結果
        self.stdout.write('\n' + '='*50)
        self.stdout.write('工單號碼修正結果統計:')
        self.stdout.write(f'  總檢查工單數: {workorders_with_spaces.count()}')
        self.stdout.write(f'  成功修正數: {fixed_count}')
        self.stdout.write(f'  錯誤數: {error_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('注意: 此為乾跑模式，未進行實際修正')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('工單號碼修正完成')
            )
    
    def _merge_workorder_data(self, wrong_workorder, correct_workorder):
        """
        將錯誤工單的資料合併到正確工單中
        
        Args:
            wrong_workorder: 錯誤的工單
            correct_workorder: 正確的工單
        """
        try:
            # 更新生產中工單明細記錄，將錯誤工單的記錄指向正確工單
            production_details = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder=wrong_workorder
            )
            
            for detail in production_details:
                # 更新工單關聯
                detail.workorder_production.workorder = correct_workorder
                detail.workorder_production.save()
            
            self.stdout.write(f'    已更新 {production_details.count()} 筆生產明細記錄')
            
            # 更新報工記錄
            from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
            
            operator_reports = OperatorSupplementReport.objects.filter(workorder=wrong_workorder)
            for report in operator_reports:
                report.workorder = correct_workorder
                report.save()
            
            smt_reports = SMTProductionReport.objects.filter(workorder=wrong_workorder)
            for report in smt_reports:
                report.workorder = correct_workorder
                report.save()
            
            self.stdout.write(f'    已更新 {operator_reports.count()} 筆作業員報工記錄')
            self.stdout.write(f'    已更新 {smt_reports.count()} 筆SMT報工記錄')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'    合併資料時發生錯誤: {str(e)}')
            )
            raise 