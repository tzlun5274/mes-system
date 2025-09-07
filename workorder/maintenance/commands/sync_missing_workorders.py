"""
同步缺失工單資料的管理命令
從填報記錄中找出缺失的工單號碼，並創建對應的工單記錄
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from workorder.fill_work.models import FillWork
from workorder.models import WorkOrder
from erp_integration.models import CompanyConfig
from datetime import datetime
from django.db import models


class Command(BaseCommand):
    help = '從填報記錄中同步缺失的工單資料到 MES 系統'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只顯示會創建的工單，不實際創建',
        )
        parser.add_argument(
            '--company-code',
            type=str,
            help='指定公司代號，只同步該公司的工單',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        company_code = options['company_code']
        
        self.stdout.write('開始同步缺失的工單資料...')
        
        # 獲取所有填報記錄中的工單號碼
        workorder_numbers_in_reports = set(
            FillWork.objects.values_list('workorder', flat=True).distinct()
        )
        
        # 獲取 MES 系統中已存在的工單號碼
        existing_workorder_numbers = set(
            WorkOrder.objects.values_list('order_number', flat=True)
        )
        
        # 找出缺失的工單號碼
        missing_workorder_numbers = workorder_numbers_in_reports - existing_workorder_numbers
        
        if not missing_workorder_numbers:
            self.stdout.write(
                self.style.SUCCESS('沒有發現缺失的工單資料')
            )
            return
        
        self.stdout.write(f'發現 {len(missing_workorder_numbers)} 個缺失的工單號碼')
        
        # 按公司代號分組
        workorders_by_company = {}
        for workorder_number in missing_workorder_numbers:
            # 從工單號碼中提取公司代號（前3位）
            company_code_from_number = workorder_number[:3]
            
            if company_code and company_code_from_number != company_code:
                continue
                
            if company_code_from_number not in workorders_by_company:
                workorders_by_company[company_code_from_number] = []
            workorders_by_company[company_code_from_number].append(workorder_number)
        
        # 獲取公司配置
        company_configs = {
            config.company_code: config.company_name 
            for config in CompanyConfig.objects.all()
        }
        
        if dry_run:
            self.stdout.write('\n=== 乾跑模式：以下工單將被創建 ===')
        else:
            self.stdout.write('\n=== 開始創建缺失的工單 ===')
        
        created_count = 0
        
        for company_code_from_number, workorder_numbers in workorders_by_company.items():
            company_name = company_configs.get(company_code_from_number, f'公司{company_code_from_number}')
            
            self.stdout.write(f'\n公司: {company_name} ({company_code_from_number})')
            
            for workorder_number in workorder_numbers:
                # 從填報記錄中獲取該工單的基本資訊
                first_report = FillWork.objects.filter(
                    workorder=workorder_number
                ).first()
                
                if not first_report:
                    continue
                
                # 提取產品編號（假設格式為：工單號碼-產品編號）
                product_code = workorder_number
                
                # 計算該工單的總數量（從所有填報記錄）
                total_quantity = FillWork.objects.filter(
                    workorder=workorder_number
                ).aggregate(
                    total=models.Sum('work_quantity')
                )['total'] or 0
                
                # 如果沒有數量資訊，設定為預設值
                if total_quantity == 0:
                    total_quantity = 1000  # 預設數量
                
                if dry_run:
                    self.stdout.write(
                        f'  將創建: {workorder_number} - {product_code} - 數量: {total_quantity}'
                    )
                else:
                    try:
                        with transaction.atomic():
                            workorder = WorkOrder.objects.create(
                                order_number=workorder_number,
                                product_code=product_code,
                                quantity=total_quantity,
                                company_code=company_code_from_number,
                                order_source='manual',  # 標記為手動創建
                                status='completed',  # 設為已完成狀態
                                created_at=first_report.created_at or datetime.now(),
                                updated_at=datetime.now()
                            )
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ 已創建: {workorder_number}'
                                )
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ 創建失敗: {workorder_number} - {str(e)}'
                            )
                        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n乾跑完成：將創建 {len(missing_workorder_numbers)} 個工單'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n同步完成：成功創建 {created_count} 個工單'
                )
            ) 