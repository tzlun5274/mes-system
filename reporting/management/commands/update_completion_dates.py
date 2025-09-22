"""
更新已完工工單分析報表的完工日期

此命令會重新分析所有已完工工單，將完工日期更新為出貨包裝工序的最後一個日期，
而不是工單轉移到已完工工單表的時間。

注意：此命令會自動排除工單號碼包含「RD樣品」的工單。
"""

from django.core.management.base import BaseCommand
from reporting.workorder_analysis_service import WorkOrderAnalysisService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '更新已完工工單分析報表的完工日期'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=str,
            help='指定公司代號，只更新該公司的工單'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新分析，即使已經分析過'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='限制處理的工單數量（預設100）'
        )

    def handle(self, *args, **options):
        company_code = options.get('company')
        force = options.get('force', False)
        limit = options.get('limit', 100)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'開始更新已完工工單分析報表的完工日期...\n'
                f'公司代號: {company_code or "全部"}\n'
                f'強制重新分析: {force}\n'
                f'處理數量限制: {limit}\n'
                f'注意：會自動排除工單號碼包含「RD樣品」的工單'
            )
        )
        
        try:
            # 使用批量分析服務
            result = WorkOrderAnalysisService.analyze_completed_workorders_batch(
                company_code=company_code,
                force=force,
                limit=limit
            )
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ 更新完成！\n'
                        f'成功處理: {result["success_count"]} 個工單\n'
                        f'跳過: {result["skipped_count"]} 個工單\n'
                        f'失敗: {result["error_count"]} 個工單\n'
                        f'總計: {result["total_count"]} 個工單'
                    )
                )
                
                if result.get('errors'):
                    self.stdout.write(
                        self.style.WARNING('⚠️ 處理過程中的錯誤:')
                    )
                    for error in result['errors'][:10]:  # 只顯示前10個錯誤
                        self.stdout.write(f'  - {error}')
                    
                    if len(result['errors']) > 10:
                        self.stdout.write(f'  ... 還有 {len(result["errors"]) - 10} 個錯誤')
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ 更新失敗: {result.get("error", "未知錯誤")}')
                )
                
        except Exception as e:
            logger.error(f'更新完工日期時發生錯誤: {e}')
            self.stdout.write(
                self.style.ERROR(f'❌ 更新過程中發生錯誤: {str(e)}')
            )
