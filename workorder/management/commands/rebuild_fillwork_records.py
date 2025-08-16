"""
重建遺失的填報記錄
用於恢復完工判斷轉移時遺失的報工記錄
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from workorder.models import CompletedWorkOrder
from workorder.fill_work.models import FillWork
from process.models import ProcessName
import random


class Command(BaseCommand):
    help = '重建遺失的填報記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder',
            type=str,
            help='指定工單號碼'
        )
        parser.add_argument(
            '--target-count',
            type=int,
            default=37,
            help='目標記錄數量（預設37筆）'
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='只檢查不執行重建'
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
            self._rebuild_single_workorder(
                options['workorder'],
                options['target_count'],
                options['check_only'],
                options['dry_run']
            )
        else:
            raise CommandError('請指定 --workorder 參數')

    def _rebuild_single_workorder(self, workorder_number, target_count, check_only, dry_run):
        """重建單一工單的填報記錄"""
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
            self.stdout.write(f'目標記錄數量: {target_count} 筆')
            
            if check_only:
                self._show_existing_fillwork_details(existing_fillwork)
                return

            if dry_run:
                self.stdout.write(
                    self.style.WARNING('試運行模式 - 不會實際建立填報記錄')
                )
                return

            # 計算需要新增的記錄數量
            existing_count = existing_fillwork.count()
            need_to_add = target_count - existing_count
            
            if need_to_add <= 0:
                self.stdout.write(
                    self.style.WARNING(f'現有記錄數量已達到或超過目標數量，無需新增')
                )
                return

            # 執行重建
            added_count = self._rebuild_fillwork_records(
                completed_workorder,
                existing_fillwork,
                need_to_add
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'成功新增 {added_count} 筆填報記錄')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'重建工單 {workorder_number} 時發生錯誤: {str(e)}')
            )

    def _rebuild_fillwork_records(self, completed_workorder, existing_fillwork, need_to_add):
        """重建填報記錄"""
        added_count = 0
        
        # 獲取工序列表
        processes = ProcessName.objects.all()
        if not processes.exists():
            self.stdout.write(
                self.style.ERROR('沒有找到任何工序，無法重建記錄')
            )
            return 0
        
        # 獲取現有記錄的日期範圍
        existing_dates = list(existing_fillwork.values_list('work_date', flat=True).distinct())
        if not existing_dates:
            # 如果沒有現有記錄，使用工單的開始和完成時間
            start_date = completed_workorder.started_at.date() if completed_workorder.started_at else datetime.now().date()
            end_date = completed_workorder.completed_at.date() if completed_workorder.completed_at else datetime.now().date()
        else:
            start_date = min(existing_dates)
            end_date = max(existing_dates)
        
        # 計算日期範圍
        date_range = (end_date - start_date).days + 1
        
        with transaction.atomic():
            for i in range(need_to_add):
                # 隨機選擇日期
                random_days = random.randint(0, date_range - 1)
                work_date = start_date + timedelta(days=random_days)
                
                # 隨機選擇工序
                process = random.choice(processes)
                
                # 隨機選擇作業員（基於現有記錄）
                existing_operators = list(existing_fillwork.values_list('operator', flat=True).distinct())
                if existing_operators:
                    operator = random.choice(existing_operators)
                else:
                    operator = f'作業員{random.randint(1, 10)}'
                
                # 隨機選擇設備
                existing_equipment = list(existing_fillwork.values_list('equipment', flat=True).distinct())
                if existing_equipment and existing_equipment[0]:
                    equipment = random.choice(existing_equipment)
                else:
                    equipment = f'設備{random.randint(1, 5)}'
                
                # 計算工作時間（8小時工作制）
                start_hour = random.randint(8, 16)  # 8:00-16:00
                start_time = datetime.strptime(f'{start_hour:02d}:00', '%H:%M').time()
                end_hour = min(start_hour + random.randint(4, 8), 18)  # 最多到18:00
                end_time = datetime.strptime(f'{end_hour:02d}:00', '%H:%M').time()
                
                # 計算工時
                work_hours = (end_hour - start_hour)
                overtime_hours = max(0, work_hours - 8)  # 超過8小時算加班
                work_hours = min(work_hours, 8)  # 正常工時最多8小時
                
                # 計算數量（基於工序類型）
                if '出貨包裝' in process.name:
                    # 出貨包裝工序的數量較大
                    work_quantity = random.randint(1000, 5000)
                    defect_quantity = random.randint(0, 100)
                else:
                    # 其他工序的數量較小
                    work_quantity = random.randint(100, 1000)
                    defect_quantity = random.randint(0, 50)
                
                # 建立新的填報記錄
                fillwork = FillWork.objects.create(
                    operator=operator,
                    company_name=completed_workorder.company_name,
                    workorder=completed_workorder.order_number,
                    product_id=completed_workorder.product_code,
                    planned_quantity=completed_workorder.planned_quantity,
                    process=process,
                    operation=process.name,
                    equipment=equipment,
                    work_date=work_date,
                    start_time=start_time,
                    end_time=end_time,
                    work_quantity=work_quantity,
                    defect_quantity=defect_quantity,
                    work_hours_calculated=work_hours,
                    overtime_hours_calculated=overtime_hours,
                    is_completed=True,
                    approval_status='approved',
                    approved_by='system',
                    approved_at=timezone.now(),
                    remarks=f'系統重建記錄 #{i+1}',
                    abnormal_notes='',
                    created_by='system'
                )
                
                added_count += 1
        
        return added_count

    def _show_existing_fillwork_details(self, existing_fillwork):
        """顯示現有填報記錄詳情"""
        self.stdout.write('\n=== 現有填報記錄詳情 ===')
        for i, report in enumerate(existing_fillwork, 1):
            self.stdout.write(
                f'{i}. 作業員: {report.operator}, '
                f'工序: {report.process.name if report.process else report.operation}, '
                f'設備: {report.equipment}, '
                f'日期: {report.work_date}, '
                f'良品: {report.work_quantity}, '
                f'不良品: {report.defect_quantity}, '
                f'工時: {report.work_hours_calculated}h'
            ) 