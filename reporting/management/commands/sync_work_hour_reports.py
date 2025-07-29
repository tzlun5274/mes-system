# -*- coding: utf-8 -*-
"""
同步工時報表管理命令
將作業員報工記錄同步到工時報表中
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta, datetime
import logging

from reporting.models import WorkTimeReport
from reporting.calculators.time_calculator import TimeCalculator
from workorder.models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """同步工時報表命令"""
    
    help = '將作業員報工記錄同步到工時報表中'
    
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
            help='特定作業員姓名',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際更新資料庫',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新同步，覆蓋現有記錄',
        )
    
    def handle(self, *args, **options):
        """執行同步"""
        # 初始化工作時數計算器
        self.work_time_calc = TimeCalculator()
        
        # 解析日期參數
        date_from = options.get('date_from')
        date_to = options.get('date_to')
        worker = options.get('worker')
        dry_run = options.get('dry_run')
        force = options.get('force')
        
        if not date_from:
            date_from = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = date.today().strftime('%Y-%m-%d')
        
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            self.stdout.write(self.style.ERROR('日期格式錯誤，請使用 YYYY-MM-DD 格式'))
            return
        
        self.stdout.write(f'開始同步工時報表...')
        self.stdout.write(f'日期範圍: {date_from} 到 {date_to}')
        if worker:
            self.stdout.write(f'作業員: {worker}')
        if dry_run:
            self.stdout.write(self.style.WARNING('試運行模式 - 不會實際更新資料庫'))
        
        # 同步作業員報工記錄
        operator_count = self._sync_operator_reports(date_from, date_to, worker, dry_run, force)
        
        # 同步SMT報工記錄
        smt_count = self._sync_smt_reports(date_from, date_to, worker, dry_run, force)
        
        # 同步主管報工記錄
        supervisor_count = self._sync_supervisor_reports(date_from, date_to, worker, dry_run, force)
        
        total_count = operator_count + smt_count + supervisor_count
        
        self.stdout.write(self.style.SUCCESS(f'工時報表同步完成！共處理 {total_count} 筆記錄'))
        self.stdout.write(f'  - 作業員報工: {operator_count} 筆')
        self.stdout.write(f'  - SMT報工: {smt_count} 筆')
        self.stdout.write(f'  - 主管報工: {supervisor_count} 筆')
    
    def _sync_operator_reports(self, date_from, date_to, worker, dry_run, force):
        """同步作業員報工記錄"""
        self.stdout.write('同步作業員報工記錄...')
        
        queryset = OperatorSupplementReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to,
            approval_status='approved'
        )
        
        if worker:
            queryset = queryset.filter(operator__name=worker)
        
        sync_count = 0
        for report in queryset:
            try:
                # 計算工時
                work_time_data = self.work_time_calc.calculate_work_time_for_report(report)
                
                # 建立或更新工時報表記錄
                defaults = {
                    'worker_id': getattr(report.operator, 'employee_id', '') if report.operator else '',
                    'product_code': report.workorder.product_code if report.workorder else '',
                    'start_time': report.start_time,
                    'end_time': report.end_time,
                    'total_work_hours': work_time_data['total_work_hours'],
                    'actual_work_hours': work_time_data['actual_work_hours'],
                    'break_hours': work_time_data['break_hours'],
                    'regular_hours': work_time_data['regular_hours'],
                    'overtime_hours': work_time_data['overtime_hours'],
                    'completed_quantity': report.work_quantity or 0,
                    'defect_quantity': report.defect_quantity or 0,
                }
                
                if not dry_run:
                    work_hour_report, created = WorkTimeReport.objects.update_or_create(
                        report_type='daily',
                        report_date=report.work_date,
                        report_category='work_hour_report',
                        worker_name=report.operator.name if report.operator else '未知作業員',
                        workorder_number=report.workorder.order_number if report.workorder else '',
                        process_name=report.process_name or '',
                        defaults={
                            'report_period_start': report.work_date,
                            'report_period_end': report.work_date,
                            'data_source': 'workorder',
                            'calculation_method': 'time_calculator',
                            'created_by': 'system',
                            'worker_type': 'operator',
                            **defaults
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'已建立: {report.operator.name} - {report.work_date} - {report.process_name}')
                    else:
                        self.stdout.write(f'已更新: {report.operator.name} - {report.work_date} - {report.process_name}')
                else:
                    self.stdout.write(f'將處理: {report.operator.name} - {report.work_date} - {report.process_name}')
                
                sync_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'同步失敗: {report} - {str(e)}'))
                continue
        
        self.stdout.write(f'作業員報工記錄同步完成: {sync_count} 筆')
        return sync_count
    
    def _sync_smt_reports(self, date_from, date_to, worker, dry_run, force):
        """同步SMT報工記錄"""
        self.stdout.write('同步SMT報工記錄...')
        
        queryset = SMTProductionReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to,
            approval_status='approved'
        )
        
        if worker:
            queryset = queryset.filter(equipment__name=worker)
        
        sync_count = 0
        for report in queryset:
            try:
                # 計算工時
                work_time_data = self.work_time_calc.calculate_work_time_for_report(report)
                
                # 建立或更新工時報表記錄
                defaults = {
                    'worker_id': '',
                    'product_code': report.workorder.product_code if report.workorder else '',
                    'start_time': report.start_time,
                    'end_time': report.end_time,
                    'total_work_hours': work_time_data['total_work_hours'],
                    'actual_work_hours': work_time_data['actual_work_hours'],
                    'break_hours': work_time_data['break_hours'],
                    'regular_hours': work_time_data['regular_hours'],
                    'overtime_hours': work_time_data['overtime_hours'],
                    'completed_quantity': report.work_quantity or 0,
                    'defect_quantity': report.defect_quantity or 0,
                }
                
                if not dry_run:
                    work_hour_report, created = WorkTimeReport.objects.update_or_create(
                        report_type='daily',
                        report_date=report.work_date,
                        report_category='work_hour_report',
                        worker_name=report.equipment.name if report.equipment else '未知設備',
                        workorder_number=report.workorder.order_number if report.workorder else '',
                        process_name=report.process_name or '',
                        defaults={
                            'report_period_start': report.work_date,
                            'report_period_end': report.work_date,
                            'data_source': 'workorder',
                            'calculation_method': 'time_calculator',
                            'created_by': 'system',
                            'worker_type': 'smt',
                            **defaults
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'已建立: {report.equipment.name} - {report.work_date} - {report.process_name}')
                    else:
                        self.stdout.write(f'已更新: {report.equipment.name} - {report.work_date} - {report.process_name}')
                else:
                    self.stdout.write(f'將處理: {report.equipment.name} - {report.work_date} - {report.process_name}')
                
                sync_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'同步失敗: {report} - {str(e)}'))
                continue
        
        self.stdout.write(f'SMT報工記錄同步完成: {sync_count} 筆')
        return sync_count
    
    def _sync_supervisor_reports(self, date_from, date_to, worker, dry_run, force):
        """同步主管報工記錄"""
        self.stdout.write('同步主管報工記錄...')
        
        queryset = SupervisorProductionReport.objects.filter(
            work_date__gte=date_from,
            work_date__lte=date_to
        )
        
        if worker:
            queryset = queryset.filter(supervisor=worker)
        
        sync_count = 0
        for report in queryset:
            try:
                # 計算工時
                work_time_data = self.work_time_calc.calculate_work_time_for_report(report)
                
                # 建立或更新工時報表記錄
                defaults = {
                    'worker_id': '',
                    'product_code': report.workorder.product_code if report.workorder else '',
                    'start_time': report.start_time,
                    'end_time': report.end_time,
                    'total_work_hours': work_time_data['total_work_hours'],
                    'actual_work_hours': work_time_data['actual_work_hours'],
                    'break_hours': work_time_data['break_hours'],
                    'regular_hours': work_time_data['regular_hours'],
                    'overtime_hours': work_time_data['overtime_hours'],
                    'completed_quantity': report.work_quantity or 0,
                    'defect_quantity': report.defect_quantity or 0,
                }
                
                if not dry_run:
                    work_hour_report, created = WorkTimeReport.objects.update_or_create(
                        report_type='daily',
                        report_date=report.work_date,
                        report_category='work_hour_report',
                        worker_name=report.supervisor,
                        workorder_number=report.workorder.order_number if report.workorder else '',
                        process_name=report.process_name or '',
                        defaults={
                            'report_period_start': report.work_date,
                            'report_period_end': report.work_date,
                            'data_source': 'workorder',
                            'calculation_method': 'time_calculator',
                            'created_by': 'system',
                            'worker_type': 'operator',
                            **defaults
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'已建立: {report.supervisor} - {report.work_date} - {report.process_name}')
                    else:
                        self.stdout.write(f'已更新: {report.supervisor} - {report.work_date} - {report.process_name}')
                else:
                    self.stdout.write(f'將處理: {report.supervisor} - {report.work_date} - {report.process_name}')
                
                sync_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'同步失敗: {report} - {str(e)}'))
                continue
        
        self.stdout.write(f'主管報工記錄同步完成: {sync_count} 筆')
        return sync_count 