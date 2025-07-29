# -*- coding: utf-8 -*-
"""
重新同步工作時間報表管理命令
使用新的工作時數計算邏輯重新同步報表資料
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, date, timedelta
from reporting.models import WorkTimeReport
from reporting.services.work_time_calculator import WorkTimeCalculator
from workorder.models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """重新同步工作時間報表命令"""
    
    help = '使用新的工作時數計算邏輯重新同步工作時間報表'
    
    def add_arguments(self, parser):
        """添加命令參數"""
        parser.add_argument(
            '--date-from',
            type=str,
            help='開始日期 (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--date-to',
            type=str,
            help='結束日期 (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新同步，即使記錄已存在',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際更新資料庫',
        )
    
    def handle(self, *args, **options):
        """執行命令"""
        try:
            # 解析日期參數
            date_from, date_to = self._parse_date_range(options)
            
            # 初始化工作時數計算器
            work_time_calc = WorkTimeCalculator()
            
            # 執行重新同步
            self._resync_work_time_reports(
                date_from, date_to, work_time_calc, options
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'成功重新同步工作時間報表: {date_from} ~ {date_to}'
                )
            )
            
        except Exception as e:
            logger.error(f"重新同步工作時間報表失敗: {str(e)}")
            raise CommandError(f"重新同步失敗: {str(e)}")
    
    def _parse_date_range(self, options):
        """解析日期範圍"""
        if options['date_from'] and options['date_to']:
            try:
                date_from = datetime.strptime(options['date_from'], '%Y-%m-%d').date()
                date_to = datetime.strptime(options['date_to'], '%Y-%m-%d').date()
            except ValueError as e:
                raise CommandError(f"日期格式錯誤: {str(e)}")
        else:
            # 預設同步最近30天
            date_to = date.today()
            date_from = date_to - timedelta(days=30)
        
        return date_from, date_to
    
    def _resync_work_time_reports(self, date_from, date_to, work_time_calc, options):
        """重新同步工作時間報表"""
        force = options['force']
        dry_run = options['dry_run']
        
        self.stdout.write(f"開始重新同步工作時間報表: {date_from} ~ {date_to}")
        if dry_run:
            self.stdout.write("試運行模式 - 不會實際更新資料庫")
        
        # 統計變數
        total_processed = 0
        total_updated = 0
        total_created = 0
        total_skipped = 0
        
        # 處理作業員報工記錄
        self.stdout.write("處理作業員報工記錄...")
        operator_reports = OperatorSupplementReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to,
            approval_status='approved'
        ).select_related('operator', 'workorder', 'process', 'equipment')
        
        for report in operator_reports:
            total_processed += 1
            
            # 計算新的工作時數
            work_time_data = work_time_calc.calculate_work_time_for_report(report)
            
            # 檢查是否已存在記錄
            existing_record = WorkTimeReport.objects.filter(
                report_type='daily',
                report_date=report.work_date,
                worker_name=report.operator.name if report.operator else '未知作業員',
                workorder_number=report.workorder.order_number if report.workorder else '',
                process_name=report.operation or (report.process.name if report.process else ''),
                start_time=report.start_time,
                end_time=report.end_time
            ).first()
            
            if existing_record and not force:
                total_skipped += 1
                continue
            
            # 準備更新資料
            update_data = {
                'report_period_start': date_from,
                'report_period_end': date_to,
                'worker_type': 'operator',
                'product_code': report.product_id or (report.workorder.product_code if report.workorder else ''),
                'process_name': report.operation or (report.process.name if report.process else ''),
                'start_time': report.start_time,
                'end_time': report.end_time,
                'total_work_hours': work_time_data['total_work_hours'],
                'actual_work_hours': work_time_data['actual_work_hours'],
                'break_hours': work_time_data['break_hours'],
                'overtime_hours': work_time_data['overtime_hours'],
                'completed_quantity': report.work_quantity,
                'defect_quantity': report.defect_quantity,
                'yield_rate': self._calculate_yield_rate(report.work_quantity, report.defect_quantity),
                'efficiency_rate': self._calculate_efficiency(work_time_data['actual_work_hours'], report.work_quantity),
                'original_quantity': report.work_quantity,
                'allocated_quantity': report.allocated_quantity or 0,
                'quantity_source': 'allocated' if report.allocated_quantity and report.allocated_quantity > 0 else 'original',
                'allocation_notes': report.allocation_notes or '',
                'abnormal_notes': report.abnormal_notes or '',
                'data_source': 'workorder',
                'calculation_method': 'new_work_time_calculator',
                'created_by': 'resync_command'
            }
            
            if not dry_run:
                if existing_record:
                    # 更新現有記錄
                    for key, value in update_data.items():
                        setattr(existing_record, key, value)
                    existing_record.save()
                    total_updated += 1
                else:
                    # 建立新記錄
                    WorkTimeReport.objects.create(
                        report_type='daily',
                        report_date=report.work_date,
                        worker_name=report.operator.name if report.operator else '未知作業員',
                        workorder_number=report.workorder.order_number if report.workorder else '',
                        **update_data
                    )
                    total_created += 1
            else:
                # 試運行模式
                if existing_record:
                    total_updated += 1
                else:
                    total_created += 1
        
        # 處理SMT報工記錄
        self.stdout.write("處理SMT報工記錄...")
        smt_reports = SMTProductionReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to,
            approval_status='approved'
        ).select_related('workorder', 'equipment')
        
        for report in smt_reports:
            total_processed += 1
            
            # 計算新的工作時數
            work_time_data = work_time_calc.calculate_work_time_for_report(report)
            
            # 檢查是否已存在記錄
            existing_record = WorkTimeReport.objects.filter(
                report_type='daily',
                report_date=report.work_date,
                worker_name=report.equipment.name if report.equipment else '未知設備',
                workorder_number=report.workorder.order_number if report.workorder else '',
                process_name=report.operation or '',
                start_time=report.start_time,
                end_time=report.end_time
            ).first()
            
            if existing_record and not force:
                total_skipped += 1
                continue
            
            # 準備更新資料
            update_data = {
                'report_period_start': date_from,
                'report_period_end': date_to,
                'worker_type': 'smt',
                'product_code': report.product_id or (report.workorder.product_code if report.workorder else ''),
                'process_name': report.operation or '',
                'start_time': report.start_time,
                'end_time': report.end_time,
                'total_work_hours': work_time_data['total_work_hours'],
                'actual_work_hours': work_time_data['actual_work_hours'],
                'break_hours': work_time_data['break_hours'],
                'overtime_hours': work_time_data['overtime_hours'],
                'completed_quantity': report.work_quantity,
                'defect_quantity': report.defect_quantity,
                'yield_rate': self._calculate_yield_rate(report.work_quantity, report.defect_quantity),
                'efficiency_rate': self._calculate_efficiency(work_time_data['actual_work_hours'], report.work_quantity),
                'original_quantity': report.work_quantity,
                'allocated_quantity': 0,
                'quantity_source': 'original',
                'allocation_notes': '',
                'abnormal_notes': report.abnormal_notes or '',
                'data_source': 'workorder',
                'calculation_method': 'new_work_time_calculator',
                'created_by': 'resync_command'
            }
            
            if not dry_run:
                if existing_record:
                    # 更新現有記錄
                    for key, value in update_data.items():
                        setattr(existing_record, key, value)
                    existing_record.save()
                    total_updated += 1
                else:
                    # 建立新記錄
                    WorkTimeReport.objects.create(
                        report_type='daily',
                        report_date=report.work_date,
                        worker_name=report.equipment.name if report.equipment else '未知設備',
                        workorder_number=report.workorder.order_number if report.workorder else '',
                        **update_data
                    )
                    total_created += 1
            else:
                # 試運行模式
                if existing_record:
                    total_updated += 1
                else:
                    total_created += 1
        
        # 處理主管報工記錄
        self.stdout.write("處理主管報工記錄...")
        supervisor_reports = SupervisorProductionReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to
        ).select_related('workorder', 'process', 'equipment', 'operator')
        
        for report in supervisor_reports:
            total_processed += 1
            
            # 計算新的工作時數
            work_time_data = work_time_calc.calculate_work_time_for_report(report)
            
            # 檢查是否已存在記錄
            existing_record = WorkTimeReport.objects.filter(
                report_type='daily',
                report_date=report.work_date,
                worker_name=report.supervisor,
                workorder_number=report.workorder.order_number if report.workorder else '',
                process_name=report.process.name if report.process else '',
                start_time=report.start_time,
                end_time=report.end_time
            ).first()
            
            if existing_record and not force:
                total_skipped += 1
                continue
            
            # 準備更新資料
            update_data = {
                'report_period_start': date_from,
                'report_period_end': date_to,
                'worker_type': 'operator',
                'product_code': report.workorder.product_code if report.workorder else '',
                'process_name': report.process.name if report.process else '',
                'start_time': report.start_time,
                'end_time': report.end_time,
                'total_work_hours': work_time_data['total_work_hours'],
                'actual_work_hours': work_time_data['actual_work_hours'],
                'break_hours': work_time_data['break_hours'],
                'overtime_hours': work_time_data['overtime_hours'],
                'completed_quantity': report.work_quantity,
                'defect_quantity': report.defect_quantity,
                'yield_rate': self._calculate_yield_rate(report.work_quantity, report.defect_quantity),
                'efficiency_rate': self._calculate_efficiency(work_time_data['actual_work_hours'], report.work_quantity),
                'original_quantity': report.work_quantity,
                'allocated_quantity': 0,
                'quantity_source': 'original',
                'allocation_notes': '',
                'abnormal_notes': report.abnormal_notes or '',
                'data_source': 'workorder',
                'calculation_method': 'new_work_time_calculator',
                'created_by': 'resync_command'
            }
            
            if not dry_run:
                if existing_record:
                    # 更新現有記錄
                    for key, value in update_data.items():
                        setattr(existing_record, key, value)
                    existing_record.save()
                    total_updated += 1
                else:
                    # 建立新記錄
                    WorkTimeReport.objects.create(
                        report_type='daily',
                        report_date=report.work_date,
                        worker_name=report.supervisor,
                        workorder_number=report.workorder.order_number if report.workorder else '',
                        **update_data
                    )
                    total_created += 1
            else:
                # 試運行模式
                if existing_record:
                    total_updated += 1
                else:
                    total_created += 1
        
        # 輸出統計結果
        self.stdout.write("\n重新同步完成！")
        self.stdout.write(f"總處理記錄數: {total_processed}")
        self.stdout.write(f"更新記錄數: {total_updated}")
        self.stdout.write(f"新增記錄數: {total_created}")
        self.stdout.write(f"跳過記錄數: {total_skipped}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("試運行模式 - 資料庫未實際更新")
            )
    
    def _calculate_yield_rate(self, completed_quantity, defect_quantity):
        """計算良率"""
        total_quantity = completed_quantity + defect_quantity
        if total_quantity > 0:
            return round((completed_quantity / total_quantity) * 100, 2)
        return 0.0
    
    def _calculate_efficiency(self, work_hours, quantity):
        """計算效率"""
        if work_hours > 0:
            return round(quantity / work_hours, 2)
        return 0.0 