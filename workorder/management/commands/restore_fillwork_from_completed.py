"""
從已完工報工記錄恢復填報記錄
用於修復完工判斷轉移時的資料遺失問題
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from workorder.models import CompletedWorkOrder, CompletedProductionReport
from workorder.fill_work.models import FillWork
from process.models import ProcessName


class Command(BaseCommand):
    help = '從已完工報工記錄恢復填報記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder',
            type=str,
            help='指定工單號碼'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='處理所有已完工工單'
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='只檢查不執行恢復'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際更新資料庫'
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 不會實際更新資料庫')
            )

        if options['workorder']:
            self._restore_single_workorder(
                options['workorder'],
                options['check_only'],
                options['dry_run']
            )
        elif options['all']:
            self._restore_all_workorders(
                options['check_only'],
                options['dry_run']
            )
        else:
            raise CommandError(
                '請指定 --workorder 或 --all 參數'
            )

    def _restore_single_workorder(self, workorder_number, check_only, dry_run):
        """恢復單一工單的填報記錄"""
        try:
            # 檢查已完工工單是否存在
            completed_workorder = CompletedWorkOrder.objects.filter(
                order_number=workorder_number
            ).first()
            
            if not completed_workorder:
                self.stdout.write(
                    self.style.ERROR(f'工單 {workorder_number} 的已完工記錄不存在')
                )
                return

            # 檢查現有的填報記錄
            existing_fillwork = FillWork.objects.filter(
                workorder=workorder_number
            )
            
            self.stdout.write(f'=== 工單 {workorder_number} 資料檢查 ===')
            self.stdout.write(f'已完工工單記錄: 存在')
            self.stdout.write(f'現有填報記錄: {existing_fillwork.count()} 筆')
            
            # 檢查已完工報工記錄
            completed_reports = CompletedProductionReport.objects.filter(
                completed_workorder=completed_workorder
            )
            
            self.stdout.write(f'已完工報工記錄: {completed_reports.count()} 筆')
            
            if check_only:
                self._show_completed_reports_details(completed_reports)
                return

            if dry_run:
                self.stdout.write(
                    self.style.WARNING('試運行模式 - 不會實際建立填報記錄')
                )
                return

            # 執行恢復
            restored_count = self._restore_fillwork_records(
                completed_workorder,
                completed_reports
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'成功恢復 {restored_count} 筆填報記錄')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'恢復工單 {workorder_number} 時發生錯誤: {str(e)}')
            )

    def _restore_all_workorders(self, check_only, dry_run):
        """恢復所有已完工工單的填報記錄"""
        completed_workorders = CompletedWorkOrder.objects.all()
        
        self.stdout.write(f'=== 總共找到 {completed_workorders.count()} 個已完工工單 ===')
        
        total_restored = 0
        for completed_workorder in completed_workorders:
            try:
                # 檢查現有的填報記錄
                existing_fillwork = FillWork.objects.filter(
                    workorder=completed_workorder.order_number
                )
                
                # 檢查已完工報工記錄
                completed_reports = CompletedProductionReport.objects.filter(
                    completed_workorder=completed_workorder
                )
                
                if check_only:
                    self.stdout.write(
                        f'工單 {completed_workorder.order_number}: '
                        f'填報記錄 {existing_fillwork.count()} 筆, '
                        f'已完工報工記錄 {completed_reports.count()} 筆'
                    )
                    continue

                if dry_run:
                    self.stdout.write(
                        f'工單 {completed_workorder.order_number}: '
                        f'將恢復 {completed_reports.count()} 筆填報記錄'
                    )
                    continue

                # 執行恢復
                restored_count = self._restore_fillwork_records(
                    completed_workorder,
                    completed_reports
                )
                
                if restored_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'工單 {completed_workorder.order_number}: '
                            f'恢復 {restored_count} 筆填報記錄'
                        )
                    )
                    total_restored += restored_count

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'恢復工單 {completed_workorder.order_number} 時發生錯誤: {str(e)}'
                    )
                )

        if not check_only and not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'總共恢復 {total_restored} 筆填報記錄')
            )

    def _restore_fillwork_records(self, completed_workorder, completed_reports):
        """從已完工報工記錄恢復填報記錄"""
        restored_count = 0
        
        with transaction.atomic():
            for report in completed_reports:
                # 檢查是否已存在對應的填報記錄
                existing_fillwork = FillWork.objects.filter(
                    workorder=completed_workorder.order_number,
                    operator=report.operator,
                    work_date=report.work_date,
                    start_time=report.start_time,
                    end_time=report.end_time,
                    work_quantity=report.work_quantity,
                    defect_quantity=report.defect_quantity
                ).first()
                
                if existing_fillwork:
                    # 如果已存在，只更新完工標記
                    existing_fillwork.is_completed = True
                    existing_fillwork.save()
                    continue
                
                # 獲取工序
                process = None
                if report.process_name:
                    process = ProcessName.objects.filter(
                        name=report.process_name
                    ).first()
                
                # 建立新的填報記錄
                fillwork = FillWork.objects.create(
                    operator=report.operator,
                    company_name=completed_workorder.company_name,
                    workorder=completed_workorder.order_number,
                    product_id=completed_workorder.product_code,
                    planned_quantity=completed_workorder.planned_quantity,
                    process=process,
                    operation=report.process_name,
                    equipment=report.equipment,
                    work_date=report.work_date,
                    start_time=report.start_time,
                    end_time=report.end_time,
                    work_quantity=report.work_quantity,
                    defect_quantity=report.defect_quantity,
                    work_hours_calculated=report.work_hours,
                    overtime_hours_calculated=report.overtime_hours,
                    is_completed=True,
                    approval_status='approved',
                    approved_by='system',
                    approved_at=timezone.now(),
                    remarks=report.remarks,
                    abnormal_notes=report.abnormal_notes,
                    created_by='system'
                )
                
                restored_count += 1
        
        return restored_count

    def _show_completed_reports_details(self, completed_reports):
        """顯示已完工報工記錄詳情"""
        self.stdout.write('\n=== 已完工報工記錄詳情 ===')
        for i, report in enumerate(completed_reports, 1):
            self.stdout.write(
                f'{i}. 作業員: {report.operator}, '
                f'工序: {report.process_name}, '
                f'設備: {report.equipment}, '
                f'日期: {report.work_date}, '
                f'良品: {report.work_quantity}, '
                f'不良品: {report.defect_quantity}, '
                f'工時: {report.work_hours}h'
            ) 