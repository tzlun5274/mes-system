"""
調試版填報紀錄複製到生產中管理命令
用於詳細追蹤同步過程中的問題
"""

from django.core.management.base import BaseCommand
from workorder.services import ProductionReportSyncService
from workorder.models import WorkOrderProduction, WorkOrderProductionDetail
from workorder.models import CompletedProductionReport as OperatorSupplementReport
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

class Command(BaseCommand):
            help = '調試版：將所有已核准的填報記錄複製到生產中工單詳情資料表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='限制處理的記錄數量（用於測試）',
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        
        self.stdout.write(
            self.style.SUCCESS('開始調試版填報紀錄複製...')
        )
        
        # 顯示同步前的統計資訊
        self._show_statistics('同步前')
        
        try:
            # 測試作業員填報記錄同步
            self.stdout.write('開始測試作業員填報記錄同步...')
            operator_reports = OperatorSupplementReport.objects.filter(
                approval_status='approved'
            ).select_related('workorder', 'operator', 'equipment', 'process')[:limit]
            
            self.stdout.write(f'測試處理 {operator_reports.count()} 筆作業員填報記錄')
            
            success_count = 0
            error_count = 0
            
            for i, report in enumerate(operator_reports):
                try:
                    self.stdout.write(f'處理第 {i+1} 筆記錄: ID={report.id}, 工單={report.workorder.order_number if report.workorder else "None"}')
                    
                    # 檢查必要欄位
                    if not report.workorder:
                        self.stdout.write(f'  錯誤: 工單為空')
                        error_count += 1
                        continue
                    
                    if not report.process:
                        self.stdout.write(f'  錯誤: 工序為空')
                        error_count += 1
                        continue
                    
                    # 手動建立生產記錄
                    production_record, created = WorkOrderProduction.objects.get_or_create(
                        workorder=report.workorder,
                        defaults={
                            'status': 'in_production',
                            'current_process': report.process.name,
                        }
                    )
                    
                    # 建立明細記錄
                    detail = WorkOrderProductionDetail.objects.create(
                        workorder_production=production_record,
                        process_name=report.process.name,
                        report_date=report.work_date,
                        report_time=report.start_time or timezone.now(),
                        work_quantity=report.work_quantity or 0,
                        defect_quantity=report.defect_quantity or 0,
                        operator=report.operator.name if report.operator else None,
                        equipment=report.equipment.name if report.equipment else None,
                        report_source='operator_supplement',
                        start_time=report.start_time,
                        end_time=report.end_time,
                        work_hours=float(report.work_hours_calculated) if report.work_hours_calculated else 0.0,
                        overtime_hours=float(report.overtime_hours_calculated) if report.overtime_hours_calculated else 0.0,
                        has_break=report.has_break,
                        break_start_time=report.break_start_time,
                        break_end_time=report.break_end_time,
                        break_hours=float(report.break_hours) if report.break_hours else 0.0,
                        report_type='operator',  # 固定為作業員類型
                        allocated_quantity=report.allocated_quantity or 0,
                        quantity_source=report.quantity_source,
                        allocation_notes=report.allocation_notes,
                        is_completed=report.is_completed,
                        completion_method=report.completion_method,
                        auto_completed=report.auto_completed,
                        completion_time=report.completion_time,
                        cumulative_quantity=report.cumulative_quantity or 0,
                        cumulative_hours=float(report.cumulative_hours) if report.cumulative_hours else 0.0,
                        approval_status=report.approval_status,
                        approved_by=report.approved_by,
                        approved_at=report.approved_at if report.approved_at else None,
                        approval_remarks=report.approval_remarks,
                        rejection_reason=report.rejection_reason,
                        rejected_by=report.rejected_by,
                        rejected_at=report.rejected_at if report.rejected_at else None,
                        remarks=report.remarks,
                        abnormal_notes=report.abnormal_notes,
                        original_report_id=report.id,
                        original_report_type='operator',
                        created_by=f"調試同步(operator)"
                    )
                    
                    self.stdout.write(f'  成功: 建立明細記錄 ID={detail.id}')
                    success_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  錯誤: {str(e)}')
                    )
                    error_count += 1
                    import traceback
                    self.stdout.write(f'  詳細錯誤: {traceback.format_exc()}')
            
            self.stdout.write(f'作業員填報記錄處理完成: 成功 {success_count} 筆, 錯誤 {error_count} 筆')
            
            # 顯示同步後的統計資訊
            self._show_statistics('同步後')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'調試過程中發生錯誤: {str(e)}')
            )
            import traceback
            error_traceback = traceback.format_exc()
            self.stdout.write(
                self.style.ERROR(f'詳細錯誤信息:\n{error_traceback}')
            )
    
    def _show_statistics(self, prefix):
        """顯示統計資訊"""
        try:
            operator_count = OperatorSupplementReport.objects.filter(approval_status='approved').count()
            smt_count = SMTSupplementReport.objects.filter(approval_status='approved').count()
            production_count = WorkOrderProduction.objects.count()
            detail_count = WorkOrderProductionDetail.objects.count()
            
            self.stdout.write(f'\n{prefix}統計資訊:')
            self.stdout.write(f'  已核准作業員填報記錄: {operator_count} 筆')
            self.stdout.write(f'  已核准SMT填報記錄: {smt_count} 筆')
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