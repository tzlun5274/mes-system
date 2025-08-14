"""
Django 管理命令：從填報資料創建缺失的工單
使用公司名稱/代號+製令號碼+產品編號作為唯一性識別
"""

from django.core.management.base import BaseCommand
from django.db import transaction
import logging

# 直接導入函數，避免循環導入問題
def create_missing_workorders_from_fillwork():
    """
    從填報資料創建缺失的工單
    以公司名稱/代號+製令號碼+產品編號作為唯一性識別
    """
    from workorder.fill_work.models import FillWork
    from workorder.models import WorkOrder
    from erp_integration.models import CompanyConfig
    from workorder.workorder_erp.models import PrdMKOrdMain, CompanyOrder
    from django.db import transaction
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 統計資訊
    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    try:
        # 取得所有填報資料
        fill_works = FillWork.objects.all()
        
        for fill_work in fill_works:
            try:
                # 檢查必要欄位
                if not fill_work.company_name or not fill_work.workorder or not fill_work.product_id:
                    logger.warning(f"填報資料缺少必要欄位: ID={fill_work.id}")
                    error_count += 1
                    continue
                
                # 從公司名稱查找公司代號
                company_code = None
                try:
                    company_config = CompanyConfig.objects.filter(
                        company_name__icontains=fill_work.company_name
                    ).first()
                    
                    if company_config:
                        company_code = company_config.company_code
                    else:
                        # 如果找不到公司配置，嘗試從製令資料中查找
                        mkord_main = PrdMKOrdMain.objects.filter(
                            MKOrdNO=fill_work.workorder,
                            ProductID=fill_work.product_id
                        ).first()
                        
                        if mkord_main:
                            # 從製令資料中查找公司代號
                            company_order = CompanyOrder.objects.filter(
                                mkordno=fill_work.workorder,
                                product_id=fill_work.product_id
                            ).first()
                            
                            if company_order:
                                company_code = company_order.company_code
                
                except Exception as e:
                    logger.error(f"查找公司代號時發生錯誤: {e}")
                    error_count += 1
                    continue
                
                if not company_code:
                    logger.warning(f"無法找到公司代號: 公司名稱={fill_work.company_name}, 工單號={fill_work.workorder}")
                    error_count += 1
                    continue
                
                # 檢查工單是否已存在（使用完整唯一性約束）
                existing_workorder = WorkOrder.objects.filter(
                    company_code=company_code,
                    order_number=fill_work.workorder,
                    product_code=fill_work.product_id
                ).first()
                
                # 如果找不到，也檢查是否有相同公司代號和工單號但不同產品編號的工單
                if not existing_workorder:
                    existing_workorder = WorkOrder.objects.filter(
                        company_code=company_code,
                        order_number=fill_work.workorder
                    ).first()
                
                if existing_workorder:
                    logger.info(f"工單已存在，跳過: {company_code}-{fill_work.workorder}-{fill_work.product_id}")
                    skipped_count += 1
                    continue
                
                # 創建新工單
                with transaction.atomic():
                    new_workorder = WorkOrder.objects.create(
                        company_code=company_code,
                        order_number=fill_work.workorder,
                        product_code=fill_work.product_id,
                        quantity=fill_work.planned_quantity or 0,
                        status='pending',
                        order_source='mes'  # 從填報資料創建的工單標記為MES來源
                    )
                    
                    created_count += 1
                    logger.info(f"成功創建工單: {new_workorder}")
                
            except Exception as e:
                logger.error(f"處理填報資料時發生錯誤 (ID={fill_work.id}): {e}")
                error_count += 1
                errors.append({
                    'fill_work_id': fill_work.id,
                    'error': str(e)
                })
        
        # 記錄統計結果
        logger.info(f"工單創建完成 - 成功: {created_count}, 跳過: {skipped_count}, 錯誤: {error_count}")
        
        return {
            'success': True,
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"創建缺失工單時發生嚴重錯誤: {e}")
        return {
            'success': False,
            'error': str(e),
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'errors': errors
        }

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '從填報資料創建缺失的工單，以公司名稱/代號+製令號碼+產品編號作為唯一性識別'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，只顯示會創建的工單但不實際創建',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細的執行過程',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('開始從填報資料創建缺失的工單...')
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('試運行模式：只會顯示會創建的工單，不會實際創建')
            )
        
        try:
            # 執行工單創建功能
            result = create_missing_workorders_from_fillwork()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'工單創建完成！\n'
                        f'成功創建: {result["created_count"]} 個工單\n'
                        f'跳過已存在: {result["skipped_count"]} 個工單\n'
                        f'處理錯誤: {result["error_count"]} 個記錄'
                    )
                )
                
                # 如果有錯誤，顯示詳細錯誤資訊
                if result['errors'] and options['verbose']:
                    self.stdout.write(
                        self.style.ERROR('\n詳細錯誤資訊:')
                    )
                    for error in result['errors']:
                        self.stdout.write(
                            self.style.ERROR(
                                f'填報資料 ID {error["fill_work_id"]}: {error["error"]}'
                            )
                        )
                
                # 顯示統計摘要
                total_processed = result['created_count'] + result['skipped_count'] + result['error_count']
                if total_processed > 0:
                    success_rate = (result['created_count'] + result['skipped_count']) / total_processed * 100
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'\n處理成功率: {success_rate:.1f}%'
                        )
                    )
                
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'工單創建失敗: {result["error"]}'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'執行過程中發生錯誤: {e}')
            )
            logger.error(f'管理命令執行錯誤: {e}')
        
        self.stdout.write(
            self.style.SUCCESS('工單創建程序結束')
        ) 