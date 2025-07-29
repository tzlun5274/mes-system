# -*- coding: utf-8 -*-
"""
重新計算工作時數管理命令
使用新的工作時數計算器重新計算所有現有記錄的工作時數
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
import logging

from reporting.models import WorkTimeReport
from reporting.services.work_time_calculator import WorkTimeCalculator
from workorder.models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport


class Command(BaseCommand):
    """重新計算工作時數命令"""
    
    help = '使用新的工作時數計算器重新計算所有現有記錄的工作時數'
    
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
            '--worker',
            type=str,
            help='特定作業員名稱',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際更新資料庫',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新計算，即使記錄已存在',
        )
    
    def handle(self, *args, **options):
        """執行命令"""
        self.logger = logging.getLogger(__name__)
        self.work_time_calc = WorkTimeCalculator()
        
        # 解析日期參數
        date_from = options.get('date_from')
        date_to = options.get('date_to')
        worker = options.get('worker')
        dry_run = options.get('dry_run')
        force = options.get('force')
        
        if date_from:
            try:
                date_from = date.fromisoformat(date_from)
            except ValueError:
                self.stdout.write(self.style.ERROR(f'無效的開始日期格式: {date_from}'))
                return
        
        if date_to:
            try:
                date_to = date.fromisoformat(date_to)
            except ValueError:
                self.stdout.write(self.style.ERROR(f'無效的結束日期格式: {date_to}'))
                return
        
        # 如果沒有指定日期範圍，預設為最近30天
        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today()
        
        self.stdout.write(f'開始重新計算工作時數...')
        self.stdout.write(f'日期範圍: {date_from} 到 {date_to}')
        if worker:
            self.stdout.write(f'作業員: {worker}')
        if dry_run:
            self.stdout.write(self.style.WARNING('試運行模式 - 不會實際更新資料庫'))
        
        # 重新計算作業員報工記錄
        self._recalculate_operator_reports(date_from, date_to, worker, dry_run, force)
        
        # 重新計算SMT報工記錄
        self._recalculate_smt_reports(date_from, date_to, worker, dry_run, force)
        
        # 重新計算主管報工記錄
        self._recalculate_supervisor_reports(date_from, date_to, worker, dry_run, force)
        
        self.stdout.write(self.style.SUCCESS('工作時數重新計算完成！'))
    
    def _recalculate_operator_reports(self, date_from, date_to, worker, dry_run, force):
        """重新計算作業員報工記錄"""
        self.stdout.write('重新計算作業員報工記錄...')
        
        queryset = OperatorSupplementReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to,
            approval_status='approved'
        )
        
        if worker:
            queryset = queryset.filter(operator__name=worker)
        
        updated_count = 0
        for report in queryset:
            try:
                # 使用新的工作時數計算器
                work_time_data = self.work_time_calc.calculate_work_time_for_report(report)
                
                # 查找對應的 WorkTimeReport 記錄
                work_time_report = WorkTimeReport.objects.filter(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.operator.name if report.operator else '未知作業員',
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    worker_type='operator'
                ).first()
                
                if work_time_report:
                    if not dry_run:
                        # 更新工作時數
                        work_time_report.total_work_hours = work_time_data['total_work_hours']
                        work_time_report.actual_work_hours = work_time_data['actual_work_hours']
                        work_time_report.break_hours = work_time_data['break_hours']
                        work_time_report.overtime_hours = work_time_data['overtime_hours']
                        work_time_report.regular_hours = work_time_data['regular_hours']
                        work_time_report.save()
                    
                    updated_count += 1
                    self.stdout.write(f'已更新: {report.operator.name} - {report.work_date} - '
                                    f'總時數: {work_time_data["total_work_hours"]:.2f}h, '
                                    f'實際時數: {work_time_data["actual_work_hours"]:.2f}h')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'更新失敗: {report} - {str(e)}'))
        
        self.stdout.write(f'作業員報工記錄更新完成: {updated_count} 筆')
    
    def _recalculate_smt_reports(self, date_from, date_to, worker, dry_run, force):
        """重新計算SMT報工記錄"""
        self.stdout.write('重新計算SMT報工記錄...')
        
        queryset = SMTProductionReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to,
            approval_status='approved'
        )
        
        if worker:
            queryset = queryset.filter(equipment__name=worker)
        
        updated_count = 0
        for report in queryset:
            try:
                # 使用新的工作時數計算器
                work_time_data = self.work_time_calc.calculate_work_time_for_report(report)
                
                # 查找對應的 WorkTimeReport 記錄
                work_time_report = WorkTimeReport.objects.filter(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.equipment.name if report.equipment else '未知設備',
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    worker_type='smt'
                ).first()
                
                if work_time_report:
                    if not dry_run:
                        # 更新工作時數
                        work_time_report.total_work_hours = work_time_data['total_work_hours']
                        work_time_report.actual_work_hours = work_time_data['actual_work_hours']
                        work_time_report.break_hours = work_time_data['break_hours']
                        work_time_report.overtime_hours = work_time_data['overtime_hours']
                        work_time_report.regular_hours = work_time_data['regular_hours']
                        work_time_report.save()
                    
                    updated_count += 1
                    self.stdout.write(f'已更新: {report.equipment.name} - {report.work_date} - '
                                    f'總時數: {work_time_data["total_work_hours"]:.2f}h, '
                                    f'實際時數: {work_time_data["actual_work_hours"]:.2f}h')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'更新失敗: {report} - {str(e)}'))
        
        self.stdout.write(f'SMT報工記錄更新完成: {updated_count} 筆')
    
    def _recalculate_supervisor_reports(self, date_from, date_to, worker, dry_run, force):
        """重新計算主管報工記錄"""
        self.stdout.write('重新計算主管報工記錄...')
        
        queryset = SupervisorProductionReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to
        )
        
        if worker:
            queryset = queryset.filter(supervisor=worker)
        
        updated_count = 0
        for report in queryset:
            try:
                # 使用新的工作時數計算器
                work_time_data = self.work_time_calc.calculate_work_time_for_report(report)
                
                # 查找對應的 WorkTimeReport 記錄
                work_time_report = WorkTimeReport.objects.filter(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.supervisor,
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    worker_type='operator'
                ).first()
                
                if work_time_report:
                    if not dry_run:
                        # 更新工作時數
                        work_time_report.total_work_hours = work_time_data['total_work_hours']
                        work_time_report.actual_work_hours = work_time_data['actual_work_hours']
                        work_time_report.break_hours = work_time_data['break_hours']
                        work_time_report.overtime_hours = work_time_data['overtime_hours']
                        work_time_report.regular_hours = work_time_data['regular_hours']
                        work_time_report.save()
                    
                    updated_count += 1
                    self.stdout.write(f'已更新: {report.supervisor} - {report.work_date} - '
                                    f'總時數: {work_time_data["total_work_hours"]:.2f}h, '
                                    f'實際時數: {work_time_data["actual_work_hours"]:.2f}h')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'更新失敗: {report} - {str(e)}'))
        
        self.stdout.write(f'主管報工記錄更新完成: {updated_count} 筆') 