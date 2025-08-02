"""
修正公司代號格式管理命令
將單位的公司代號修正為兩位數格式，例如將 "2" 修正為 "02"
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.models import WorkOrder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '修正公司代號格式，將單位的公司代號修正為兩位數格式'

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
            self._fix_company_codes(dry_run)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'修正過程中發生錯誤: {str(e)}')
            )
            logger.error(f'修正公司代號格式失敗: {str(e)}')
    
    def _fix_company_codes(self, dry_run):
        """修正公司代號格式"""
        
        # 查找所有需要修正的公司代號
        workorders_to_fix = WorkOrder.objects.filter(
            company_code__regex=r'^\d$'  # 只匹配一位數字
        ).exclude(company_code='')  # 排除空值
        
        self.stdout.write(f'找到 {workorders_to_fix.count()} 個需要修正公司代號格式的工單')
        
        if workorders_to_fix.count() == 0:
            self.stdout.write(
                self.style.SUCCESS('沒有發現需要修正的公司代號格式')
            )
            return
        
        # 顯示需要修正的工單
        self.stdout.write('\n需要修正的工單列表:')
        for workorder in workorders_to_fix:
            corrected_code = workorder.company_code.zfill(2)
            self.stdout.write(f'  ID: {workorder.id}, 工單號: {workorder.order_number}, 公司代號: "{workorder.company_code}" → "{corrected_code}"')
        
        # 按公司代號分組統計
        company_code_stats = {}
        for workorder in workorders_to_fix:
            current_code = workorder.company_code
            corrected_code = current_code.zfill(2)
            if current_code not in company_code_stats:
                company_code_stats[current_code] = {
                    'corrected_code': corrected_code,
                    'count': 0
                }
            company_code_stats[current_code]['count'] += 1
        
        self.stdout.write(f'\n公司代號修正統計:')
        for current_code, stats in company_code_stats.items():
            self.stdout.write(f'  "{current_code}" → "{stats["corrected_code"]}": {stats["count"]} 個工單')
        
        # 修正公司代號
        fixed_count = 0
        error_count = 0
        
        for workorder in workorders_to_fix:
            try:
                original_code = workorder.company_code
                corrected_code = original_code.zfill(2)
                
                self.stdout.write(f'\n修正工單 ID {workorder.id}:')
                self.stdout.write(f'  原始公司代號: "{original_code}"')
                self.stdout.write(f'  修正公司代號: "{corrected_code}"')
                
                if not dry_run:
                    with transaction.atomic():
                        # 更新公司代號
                        workorder.company_code = corrected_code
                        workorder.save()
                        
                        self.stdout.write(f'  已修正公司代號')
                        fixed_count += 1
                else:
                    self.stdout.write(f'  [乾跑模式] 將修正公司代號')
                    fixed_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  修正工單 {workorder.order_number} 時發生錯誤: {str(e)}')
                )
        
        # 輸出統計結果
        self.stdout.write('\n' + '='*50)
        self.stdout.write('公司代號修正結果統計:')
        self.stdout.write(f'  總檢查工單數: {workorders_to_fix.count()}')
        self.stdout.write(f'  成功修正數: {fixed_count}')
        self.stdout.write(f'  錯誤數: {error_count}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('注意: 此為乾跑模式，未進行實際修正')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('公司代號格式修正完成')
            )
        
        # 檢查修正後的結果
        if not dry_run:
            self._check_fixed_results()
    
    def _check_fixed_results(self):
        """檢查修正後的結果"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('修正後結果檢查:')
        
        # 檢查是否還有單位的公司代號
        remaining_single_digit = WorkOrder.objects.filter(
            company_code__regex=r'^\d$'
        ).exclude(company_code='')
        
        if remaining_single_digit.count() == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ 沒有發現單位的公司代號')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  仍有 {remaining_single_digit.count()} 個單位的公司代號')
            )
            for workorder in remaining_single_digit:
                self.stdout.write(f'  ID: {workorder.id}, 工單號: {workorder.order_number}, 公司代號: "{workorder.company_code}"')
        
        # 檢查兩位數格式的公司代號
        two_digit_codes = WorkOrder.objects.filter(
            company_code__regex=r'^\d{2}$'
        ).exclude(company_code='')
        
        self.stdout.write(f'\n兩位數格式的公司代號: {two_digit_codes.count()} 個工單')
        
        # 統計各公司代號的數量
        code_stats = {}
        for workorder in two_digit_codes:
            code = workorder.company_code
            if code not in code_stats:
                code_stats[code] = 0
            code_stats[code] += 1
        
        for code, count in sorted(code_stats.items()):
            self.stdout.write(f'  公司代號 "{code}": {count} 個工單') 