"""
管理命令：手動執行客戶訂單同步
"""

from django.core.management.base import BaseCommand
from scheduling.customer_order_management import OrderManager


class Command(BaseCommand):
    help = '手動執行訂單資料同步從 ERP 到 MES'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制同步，即使有錯誤也繼續執行'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，只顯示會同步的資料，不實際執行'
        )

    def handle(self, *args, **options):
        self.stdout.write('開始執行客戶訂單同步...')
        
        force = options['force']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write('🔍 試運行模式：只檢查資料，不實際同步')
        
        try:
            # 創建客戶訂單管理器
            order_manager = OrderManager()
            
            if dry_run:
                # 試運行模式：只檢查資料
                self.dry_run_sync(order_manager)
            else:
                # 實際執行同步
                result = order_manager.sync_orders_from_erp()
                
                if result.get('status') == 'success':
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ 客戶訂單同步成功！共同步 {result.get("total_orders", 0)} 筆訂單'
                        )
                    )
                else:
                    error_msg = f'❌ 客戶訂單同步失敗：{result.get("message", "未知錯誤")}'
                    if force:
                        self.stdout.write(self.style.WARNING(error_msg))
                        self.stdout.write('⚠️ 由於使用 --force 參數，繼續執行...')
                    else:
                        self.stdout.write(self.style.ERROR(error_msg))
                        return
                        
        except Exception as e:
            error_msg = f'❌ 客戶訂單同步執行失敗：{str(e)}'
            if force:
                self.stdout.write(self.style.WARNING(error_msg))
                self.stdout.write('⚠️ 由於使用 --force 參數，繼續執行...')
            else:
                self.stdout.write(self.style.ERROR(error_msg))
                return

    def dry_run_sync(self, order_manager):
        """試運行模式：檢查會同步的資料"""
        try:
            from scheduling.models import CompanyView
            from django.conf import settings
            from django.db import connections
            
            companies = CompanyView.objects.all()
            self.stdout.write(f'📋 找到 {len(companies)} 家公司')
            
            total_orders = 0
            
            for company in companies:
                self.stdout.write(f'\n🏢 公司：{company.company_name}')
                self.stdout.write(f'   資料庫：{company.mes_database}')
                
                if not company.mes_database:
                    self.stdout.write(self.style.WARNING('   ⚠️ 資料庫設定為空，跳過'))
                    continue
                
                try:
                    # 建立資料庫連線
                    db_config = settings.DATABASES["default"].copy()
                    db_config["NAME"] = company.mes_database
                    connections.databases[company.mes_database] = db_config
                    
                    with connections[company.mes_database].cursor() as cursor:
                        # 檢查國內訂單
                        cursor.execute(
                            """
                            SELECT COUNT(*) FROM "ordBillMain" m
                            LEFT JOIN "ordBillSub" s ON m."BillNO" = s."BillNO"
                            WHERE m."BillNO" LIKE '113-%'
                            AND m."BillDate" >= 20200101
                            AND (m."BillStatus" = 0 OR m."BillStatus" IS NULL)
                            AND s."QtyRemain" > 0
                            AND s."ProdID" LIKE 'PFP-%'
                            """
                        )
                        domestic_count = cursor.fetchone()[0]
                        
                        # 檢查國外訂單
                        cursor.execute(
                            """
                            SELECT COUNT(*) FROM "TraBillMain" m
                            LEFT JOIN "TraBillSub" s ON m."BillNo" = s."BillNo"
                            WHERE m."BillNo" LIKE '542-%'
                            AND m."BillDate" >= 20200101
                            AND (m."BillStatus" = 0 OR m."BillStatus" IS NULL)
                            AND s."QtyRemain" > 0
                            """
                        )
                        foreign_count = cursor.fetchone()[0]
                        
                        company_total = domestic_count + foreign_count
                        total_orders += company_total
                        
                        self.stdout.write(f'   國內訂單：{domestic_count} 筆')
                        self.stdout.write(f'   國外訂單：{foreign_count} 筆')
                        self.stdout.write(f'   總計：{company_total} 筆')
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ❌ 查詢失敗：{str(e)}'))
                finally:
                    # 清理連線
                    if company.mes_database in connections.databases:
                        del connections.databases[company.mes_database]
            
            self.stdout.write(f'\n📊 試運行結果：總共會同步 {total_orders} 筆訂單')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'試運行失敗：{str(e)}'))
