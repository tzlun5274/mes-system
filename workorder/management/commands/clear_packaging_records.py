"""
清除出貨包裝記錄管理命令
根據 MES 工單設計規範，只處理特定公司的記錄
"""

from django.core.management.base import BaseCommand
from workorder.models import WorkOrderProductionDetail
from workorder.fill_work.models import FillWork
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '清除特定公司的出貨包裝記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-code',
            type=str,
            required=True,
            help='公司代號（例如：02）',
        )
        parser.add_argument(
            '--workorder',
            type=str,
            help='指定工單號碼，只清除該工單的記錄',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際刪除資料',
        )

    def handle(self, *args, **options):
        company_code = options.get('company_code')
        workorder_number = options.get('workorder')
        dry_run = options.get('dry_run')
        
        self.stdout.write(
            self.style.SUCCESS(f'開始清除公司 {company_code} 的出貨包裝記錄...')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 不會實際刪除資料')
            )
        
        try:
            # 查詢出貨包裝報工記錄
            query = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder__company_code=company_code,
                process_name='出貨包裝'
            )
            
            if workorder_number:
                query = query.filter(
                    workorder_production__workorder__order_number=workorder_number
                )
                self.stdout.write(f'只清除工單 {workorder_number} 的記錄')
            
            records = query.all()
            self.stdout.write(f'找到 {records.count()} 筆出貨包裝報工記錄')
            
            if records.count() == 0:
                self.stdout.write(
                    self.style.WARNING('沒有找到任何出貨包裝記錄')
                )
                return
            
            # 顯示要刪除的記錄
            self.stdout.write('\n要刪除的記錄:')
            total_good = 0
            total_defect = 0
            
            for record in records:
                self.stdout.write(
                    f'  ID: {record.id}, 工單: {record.workorder_production.workorder.order_number}, '
                    f'良品: {record.work_quantity}, 不良品: {record.defect_quantity}, '
                    f'核准狀態: {record.approval_status}'
                )
                total_good += record.work_quantity
                total_defect += record.defect_quantity
            
            self.stdout.write(f'\n總計: 良品 {total_good}, 不良品 {total_defect}')
            
            # 確認刪除
            if not dry_run:
                confirm = input('\n確定要刪除這些記錄嗎？(y/N): ')
                if confirm.lower() != 'y':
                    self.stdout.write(
                        self.style.WARNING('取消刪除操作')
                    )
                    return
            
            # 執行刪除
            if not dry_run:
                deleted_count = records.count()
                records.delete()
                
                self.stdout.write(
                    self.style.SUCCESS(f'成功刪除 {deleted_count} 筆出貨包裝記錄')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'[試運行] 將刪除 {records.count()} 筆記錄')
                )
            
            # 驗證刪除結果
            remaining_records = WorkOrderProductionDetail.objects.filter(
                workorder_production__workorder__company_code=company_code,
                process_name='出貨包裝'
            )
            
            if workorder_number:
                remaining_records = remaining_records.filter(
                    workorder_production__workorder__order_number=workorder_number
                )
            
            self.stdout.write(f'刪除後剩餘記錄數: {remaining_records.count()}')
            
            if remaining_records.count() == 0:
                self.stdout.write(
                    self.style.SUCCESS('所有出貨包裝記錄已清除完成！')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'還有 {remaining_records.count()} 筆記錄未清除')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清除過程中發生錯誤: {str(e)}')
            )
            import traceback
            self.stdout.write(
                self.style.ERROR(f'詳細錯誤信息:\n{traceback.format_exc()}')
            ) 