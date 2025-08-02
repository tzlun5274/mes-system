"""
報工紀錄複製到生產中管理命令
將所有已核准的報工記錄複製到生產中工單詳情資料表
"""

from django.core.management.base import BaseCommand
from workorder.services import ProductionReportSyncService
from workorder.models import WorkOrderProduction, WorkOrderProductionDetail
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '將所有已核准的報工記錄複製到生產中工單詳情資料表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder-id',
            type=int,
            help='指定複製特定工單的報工記錄',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新複製所有記錄',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除現有的生產中工單明細記錄後重新複製',
        )

    def handle(self, *args, **options):
        workorder_id = options.get('workorder_id')
        force = options.get('force')
        clear = options.get('clear')
        
        self.stdout.write(
            self.style.SUCCESS('開始複製報工紀錄到生產中工單資料表...')
        )
        
        # 顯示同步前的統計資訊
        self._show_statistics('同步前')
        
        try:
            if clear:
                # 清除現有的生產中工單明細記錄
                self.stdout.write('清除現有的生產中工單明細記錄...')
                deleted_count = WorkOrderProductionDetail.objects.count()
                WorkOrderProductionDetail.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(f'已清除 {deleted_count} 筆現有記錄')
                )
            
            if workorder_id:
                # 複製特定工單
                self.stdout.write(f'複製工單 {workorder_id} 的報工記錄...')
                success = ProductionReportSyncService.sync_specific_workorder(workorder_id)
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f'工單 {workorder_id} 的報工記錄複製完成')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'工單 {workorder_id} 的報工記錄複製失敗')
                    )
            else:
                # 複製所有工單
                self.stdout.write('複製所有已核准的報工記錄...')
                
                # 檢查報工記錄數量
                operator_count = OperatorSupplementReport.objects.filter(approval_status='approved').count()
                smt_count = SMTProductionReport.objects.filter(approval_status='approved').count()
                total_reports = operator_count + smt_count
                
                self.stdout.write(f'找到 {operator_count} 筆已核准作業員報工記錄')
                self.stdout.write(f'找到 {smt_count} 筆已核准SMT報工記錄')
                self.stdout.write(f'總計 {total_reports} 筆報工記錄需要同步')
                
                if total_reports == 0:
                    self.stdout.write(
                        self.style.WARNING('沒有找到任何已核准的報工記錄')
                    )
                    return
                
                # 執行同步
                success = ProductionReportSyncService.sync_all_approved_reports()
                if success:
                    self.stdout.write(
                        self.style.SUCCESS('所有已核准報工記錄複製完成')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('複製報工記錄失敗')
                    )
            
            # 顯示同步後的統計資訊
            self._show_statistics('同步後')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'複製過程中發生錯誤: {str(e)}')
            )
            import traceback
            error_traceback = traceback.format_exc()
            self.stdout.write(
                self.style.ERROR(f'詳細錯誤信息:\n{error_traceback}')
            )
            logger.error(f"複製報工記錄命令執行失敗: {str(e)}")
            logger.error(f"詳細錯誤信息: {error_traceback}")
            # 強制輸出錯誤信息
            print(f"錯誤詳情: {error_traceback}")
    
    def _show_statistics(self, prefix):
        """顯示統計資訊"""
        try:
            operator_count = OperatorSupplementReport.objects.filter(approval_status='approved').count()
            smt_count = SMTProductionReport.objects.filter(approval_status='approved').count()
            production_count = WorkOrderProduction.objects.count()
            detail_count = WorkOrderProductionDetail.objects.count()
            
            self.stdout.write(f'\n{prefix}統計資訊:')
            self.stdout.write(f'  已核准作業員報工記錄: {operator_count} 筆')
            self.stdout.write(f'  已核准SMT報工記錄: {smt_count} 筆')
            self.stdout.write(f'  生產中工單記錄: {production_count} 筆')
            self.stdout.write(f'  生產中工單明細記錄: {detail_count} 筆')
            
            if detail_count > 0:
                # 顯示明細記錄的工序分布
                from django.db.models import Count
                process_counts = WorkOrderProductionDetail.objects.values('process_name').annotate(count=Count('process_name')).order_by('-count')
                self.stdout.write(f'  明細記錄工序分布:')
                for process in process_counts[:5]:  # 只顯示前5個
                    self.stdout.write(f'    {process["process_name"]}: {process["count"]} 筆')
                if process_counts.count() > 5:
                    self.stdout.write(f'    ... 還有 {process_counts.count() - 5} 個工序')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'顯示統計資訊時發生錯誤: {str(e)}')
            ) 