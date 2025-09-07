"""
管理命令：更新派工單的公司名稱
將現有的派工單記錄的公司名稱從 CompanyConfig 中取得並更新
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.workorder_dispatch.models import WorkOrderDispatch
from erp_integration.models import CompanyConfig


class Command(BaseCommand):
    help = '更新派工單的公司名稱'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只顯示會更新的記錄，不實際執行更新',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('執行乾跑模式，不會實際更新資料'))
        
        # 取得所有需要更新的派工單
        dispatches_to_update = WorkOrderDispatch.objects.filter(
            company_code__isnull=False,
            company_name__isnull=True
        ).exclude(company_code='')
        
        self.stdout.write(f'找到 {dispatches_to_update.count()} 個需要更新公司名稱的派工單')
        
        updated_count = 0
        error_count = 0
        
        for dispatch in dispatches_to_update:
            try:
                # 查找對應的公司配置
                company_config = CompanyConfig.objects.filter(
                    company_code=dispatch.company_code
                ).first()
                
                if company_config:
                    if not dry_run:
                        with transaction.atomic():
                            dispatch.company_name = company_config.company_name
                            dispatch.save(update_fields=['company_name'])
                    
                    self.stdout.write(
                        f'更新派工單 {dispatch.order_number}: '
                        f'公司代號 {dispatch.company_code} -> 公司名稱 {company_config.company_name}'
                    )
                    updated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'找不到公司代號 {dispatch.company_code} 的配置，派工單 {dispatch.order_number}'
                        )
                    )
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'更新派工單 {dispatch.order_number} 時發生錯誤: {str(e)}'
                    )
                )
                error_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'乾跑完成：會更新 {updated_count} 個記錄，{error_count} 個錯誤'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'更新完成：成功更新 {updated_count} 個記錄，{error_count} 個錯誤'
                )
            ) 