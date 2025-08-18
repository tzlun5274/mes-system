"""
管理命令：批量更新派工單的公司名稱
將所有派工單的公司名稱從 CompanyConfig 模型中取得並更新
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.workorder_dispatch.models import WorkOrderDispatch
from erp_integration.models import CompanyConfig
import logging

logger = logging.getLogger('workorder')


class Command(BaseCommand):
    help = '批量更新派工單的公司名稱'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際更新資料庫',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制更新所有派工單，包括已有公司名稱的',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS('開始批量更新派工單公司名稱...')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('試運行模式：不會實際更新資料庫')
            )
        
        # 取得所有派工單
        dispatches = WorkOrderDispatch.objects.all()
        total_count = dispatches.count()
        
        self.stdout.write(f'總共找到 {total_count} 筆派工單')
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for dispatch in dispatches:
            try:
                # 檢查是否需要更新
                needs_update = force or not dispatch.company_name
                
                if not needs_update:
                    skipped_count += 1
                    continue
                
                # 根據公司代號取得公司名稱
                if dispatch.company_code:
                    company_config = CompanyConfig.objects.filter(
                        company_code=dispatch.company_code
                    ).first()
                    
                    if company_config:
                        new_company_name = company_config.company_name
                        old_company_name = dispatch.company_name or '(空白)'
                        
                        if dry_run:
                            self.stdout.write(
                                f'[試運行] 派工單 {dispatch.order_number}: '
                                f'{old_company_name} → {new_company_name}'
                            )
                        else:
                            # 實際更新資料庫
                            with transaction.atomic():
                                dispatch.company_name = new_company_name
                                dispatch.save(update_fields=['company_name'])
                            
                            self.stdout.write(
                                f'✓ 派工單 {dispatch.order_number}: '
                                f'{old_company_name} → {new_company_name}'
                            )
                        
                        updated_count += 1
                    else:
                        # 找不到公司配置，使用公司代號作為公司名稱
                        if not dispatch.company_name or dispatch.company_name != dispatch.company_code:
                            if dry_run:
                                self.stdout.write(
                                    f'[試運行] 派工單 {dispatch.order_number}: '
                                    f'找不到公司配置，使用公司代號: {dispatch.company_code}'
                                )
                            else:
                                with transaction.atomic():
                                    dispatch.company_name = dispatch.company_code
                                    dispatch.save(update_fields=['company_name'])
                                
                                self.stdout.write(
                                    f'⚠ 派工單 {dispatch.order_number}: '
                                    f'找不到公司配置，使用公司代號: {dispatch.company_code}'
                                )
                            
                            updated_count += 1
                        else:
                            skipped_count += 1
                else:
                    # 沒有公司代號
                    if not dispatch.company_name:
                        if dry_run:
                            self.stdout.write(
                                f'[試運行] 派工單 {dispatch.order_number}: '
                                f'沒有公司代號，設定為 "-"'
                            )
                        else:
                            with transaction.atomic():
                                dispatch.company_name = '-'
                                dispatch.save(update_fields=['company_name'])
                            
                            self.stdout.write(
                                f'⚠ 派工單 {dispatch.order_number}: '
                                f'沒有公司代號，設定為 "-"'
                            )
                        
                        updated_count += 1
                    else:
                        skipped_count += 1
                        
            except Exception as e:
                error_count += 1
                error_msg = f'更新派工單 {dispatch.order_number} 失敗: {str(e)}'
                self.stdout.write(
                    self.style.ERROR(error_msg)
                )
                logger.error(error_msg)
        
        # 顯示統計結果
        self.stdout.write('\n' + '='*50)
        self.stdout.write('批量更新完成！')
        self.stdout.write(f'總計: {total_count} 筆')
        self.stdout.write(f'更新: {updated_count} 筆')
        self.stdout.write(f'跳過: {skipped_count} 筆')
        self.stdout.write(f'錯誤: {error_count} 筆')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n這是試運行模式，資料庫沒有被修改')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n所有派工單的公司名稱已更新完成！')
            ) 