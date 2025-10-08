"""
清除工單分析報表資料的管理指令
用於清除已完工工單分析結果，可以重新分析
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from reporting.models import CompletedWorkOrderAnalysis


class Command(BaseCommand):
    help = '清除工單分析報表資料'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=str,
            help='指定要清除的工單編號'
        )
        parser.add_argument(
            '--company-code',
            type=str,
            help='指定要清除的公司代號'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='清除所有分析資料（危險操作）'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制執行，不詢問確認'
        )

    def handle(self, *args, **options):
        workorder_id = options.get('workorder_id')
        company_code = options.get('company_code')
        clear_all = options.get('all', False)
        force = options.get('force', False)

        try:
            with transaction.atomic():
                if clear_all:
                    # 清除所有分析資料
                    if not force:
                        confirm = input('⚠️  警告：您即將清除所有工單分析資料！\n'
                                      '此操作無法復原，確定要繼續嗎？(yes/no): ')
                        if confirm.lower() != 'yes':
                            self.stdout.write(self.style.WARNING('操作已取消'))
                            return

                    count = CompletedWorkOrderAnalysis.objects.count()
                    CompletedWorkOrderAnalysis.objects.all().delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 成功清除所有分析資料，共 {count} 筆記錄')
                    )

                elif workorder_id and company_code:
                    # 清除指定工單的分析資料
                    analyses = CompletedWorkOrderAnalysis.objects.filter(
                        workorder_id=workorder_id,
                        company_code=company_code
                    )
                    
                    if not analyses.exists():
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  找不到工單 {workorder_id} (公司: {company_code}) 的分析資料')
                        )
                        return

                    count = analyses.count()
                    analyses.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 成功清除工單 {workorder_id} (公司: {company_code}) 的分析資料，共 {count} 筆記錄')
                    )

                elif workorder_id:
                    # 清除指定工單的所有分析資料
                    analyses = CompletedWorkOrderAnalysis.objects.filter(
                        workorder_id=workorder_id
                    )
                    
                    if not analyses.exists():
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  找不到工單 {workorder_id} 的分析資料')
                        )
                        return

                    count = analyses.count()
                    analyses.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 成功清除工單 {workorder_id} 的所有分析資料，共 {count} 筆記錄')
                    )

                elif company_code:
                    # 清除指定公司的所有分析資料
                    analyses = CompletedWorkOrderAnalysis.objects.filter(
                        company_code=company_code
                    )
                    
                    if not analyses.exists():
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  找不到公司 {company_code} 的分析資料')
                        )
                        return

                    count = analyses.count()
                    analyses.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 成功清除公司 {company_code} 的所有分析資料，共 {count} 筆記錄')
                    )

                else:
                    # 顯示使用說明
                    self.stdout.write(self.style.ERROR('❌ 請指定清除條件'))
                    self.stdout.write('')
                    self.stdout.write('使用方式：')
                    self.stdout.write('  python manage.py clear_workorder_analysis --workorder-id 331-25815001 --company-code 10')
                    self.stdout.write('  python manage.py clear_workorder_analysis --workorder-id 331-25815001')
                    self.stdout.write('  python manage.py clear_workorder_analysis --company-code 10')
                    self.stdout.write('  python manage.py clear_workorder_analysis --all --force')
                    self.stdout.write('')
                    self.stdout.write('參數說明：')
                    self.stdout.write('  --workorder-id: 指定工單編號')
                    self.stdout.write('  --company-code: 指定公司代號')
                    self.stdout.write('  --all: 清除所有分析資料（危險操作）')
                    self.stdout.write('  --force: 強制執行，不詢問確認')

        except Exception as e:
            raise CommandError(f'清除分析資料時發生錯誤: {str(e)}')

    def get_analysis_count(self):
        """取得分析資料總數"""
        return CompletedWorkOrderAnalysis.objects.count()
