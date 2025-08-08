"""
報工紀錄複製到生產中管理命令
將所有已核准的報工記錄複製到生產中工單詳情資料表
"""

from django.core.management.base import BaseCommand
from workorder.services import ProductionReportSyncService
from workorder.models import WorkOrderProduction, WorkOrderProductionDetail
from workorder.workorder_reporting.models import BackupOperatorSupplementReport as OperatorSupplementReport, BackupSMTSupplementReport as SMTSupplementReport
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
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細的同步過程',
        )

    def handle(self, *args, **options):
        workorder_id = options.get('workorder_id')
        force = options.get('force')
        clear = options.get('clear')
        verbose = options.get('verbose')
        
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
                smt_count = SMTSupplementReport.objects.filter(approval_status='approved').count()
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
            
            # 驗證同步結果
            self._verify_sync_results()
                    
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
            smt_count = SMTSupplementReport.objects.filter(approval_status='approved').count()
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
                    
                # 顯示報工來源分布
                source_counts = WorkOrderProductionDetail.objects.values('report_source').annotate(count=Count('report_source')).order_by('-count')
                self.stdout.write(f'  明細記錄報工來源分布:')
                for source in source_counts:
                    source_name = {
                        'operator_supplement': '作業員補登報工',
                        'smt': 'SMT報工',
                        'operator': '作業員現場報工'
                    }.get(source['report_source'], source['report_source'])
                    self.stdout.write(f'    {source_name}: {source["count"]} 筆')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'顯示統計資訊時發生錯誤: {str(e)}')
            )
    
    def _verify_sync_results(self):
        """驗證同步結果"""
        try:
            # 檢查是否有報工記錄但沒有對應的明細記錄
            operator_reports = OperatorSupplementReport.objects.filter(approval_status='approved')
            smt_reports = SMTSupplementReport.objects.filter(approval_status='approved')
            
            missing_details = []
            
            # 檢查作業員報工記錄
            for report in operator_reports:
                detail_exists = WorkOrderProductionDetail.objects.filter(
                    original_report_id=report.id,
                    original_report_type='operator'
                ).exists()
                if not detail_exists:
                    missing_details.append(f'作業員報工記錄 ID:{report.id} (工單:{report.workorder.order_number if report.workorder else "None"})')
            
            # 檢查SMT報工記錄
            for report in smt_reports:
                detail_exists = WorkOrderProductionDetail.objects.filter(
                    original_report_id=report.id,
                    original_report_type='smt'
                ).exists()
                if not detail_exists:
                    missing_details.append(f'SMT報工記錄 ID:{report.id} (工單:{report.workorder.order_number if report.workorder else "None"})')
            
            if missing_details:
                self.stdout.write(
                    self.style.WARNING(f'發現 {len(missing_details)} 筆報工記錄沒有對應的明細記錄:')
                )
                for missing in missing_details[:10]:  # 只顯示前10筆
                    self.stdout.write(f'  - {missing}')
                if len(missing_details) > 10:
                    self.stdout.write(f'  ... 還有 {len(missing_details) - 10} 筆')
            else:
                self.stdout.write(
                    self.style.SUCCESS('所有已核准報工記錄都已成功同步到明細表')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'驗證同步結果時發生錯誤: {str(e)}')
            ) 