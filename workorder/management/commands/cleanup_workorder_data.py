#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django 管理命令：清理工單資料不一致問題
清理已完工工單的統計資料不一致問題
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workorder.models import CompletedWorkOrder, CompletedProductionReport
from workorder.fill_work.models import FillWork
import logging
from django.db.models import Sum

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '清理工單資料的不一致問題'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder',
            type=str,
            help='指定工單號碼進行清理'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='清理所有已完工工單的資料'
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='只檢查不實際更新'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際更新資料庫'
        )
        parser.add_argument(
            '--restore-fillwork',
            action='store_true',
            help='還原填報紀錄的核准狀態'
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 不會實際更新資料庫')
            )
        
        if options['restore_fillwork']:
            self._restore_fillwork_approval_status(options['workorder'])
            return
        
        if options['workorder']:
            self._cleanup_single_workorder(
                options['workorder'], 
                options['check_only'],
                options['dry_run']
            )
        elif options['all']:
            self._cleanup_all_workorders(
                options['check_only'],
                options['dry_run']
            )
        else:
            raise CommandError(
                '請指定 --workorder 或 --all 參數，或使用 --restore-fillwork'
            )

    def _restore_fillwork_approval_status(self, workorder_number):
        """還原填報紀錄的核准狀態"""
        if workorder_number:
            reports = FillWork.objects.filter(workorder=workorder_number)
        else:
            reports = FillWork.objects.all()
        
        self.stdout.write(f'找到 {reports.count()} 筆填報紀錄')
        
        # 檢查核准狀態
        pending_count = reports.filter(approval_status='pending').count()
        approved_count = reports.filter(approval_status='approved').count()
        
        self.stdout.write(f'待核准: {pending_count} 筆')
        self.stdout.write(f'已核准: {approved_count} 筆')
        
        if pending_count > 0:
            self.stdout.write('將所有待核准的填報紀錄設為已核准...')
            with transaction.atomic():
                updated = reports.filter(approval_status='pending').update(approval_status='approved')
                self.stdout.write(
                    self.style.SUCCESS(f'已更新 {updated} 筆填報紀錄的核准狀態')
                )

    def _cleanup_single_workorder(self, workorder_number, check_only, dry_run):
        """清理單一工單的資料"""
        self.stdout.write(f'開始清理工單 {workorder_number} 的資料...')
        
        try:
            # 獲取已完工工單
            completed_workorder = CompletedWorkOrder.objects.filter(
                order_number=workorder_number
            ).first()
            
            if not completed_workorder:
                self.stdout.write(
                    self.style.ERROR(f'工單 {workorder_number} 不存在或未完工')
                )
                return
            
            # 顯示目前的資料狀況
            self._show_data_status(workorder_number)
            
            if check_only:
                self.stdout.write(
                    self.style.WARNING('檢查模式 - 不進行更新')
                )
                return
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('試運行模式 - 不進行更新')
                )
                return
            
            # 清理不一致的資料
            with transaction.atomic():
                # 刪除所有 CompletedProductionReport 記錄
                deleted_reports = CompletedProductionReport.objects.filter(
                    completed_workorder=completed_workorder
                ).delete()
                
                self.stdout.write(
                    self.style.SUCCESS(f'已刪除 {deleted_reports[0]} 筆 CompletedProductionReport 記錄')
                )
                
                # 重新計算統計資料
                self._recalculate_stats(completed_workorder)
                
                self.stdout.write(
                    self.style.SUCCESS(f'工單 {workorder_number} 資料已清理')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清理工單 {workorder_number} 時發生錯誤: {str(e)}')
            )

    def _cleanup_all_workorders(self, check_only, dry_run):
        """清理所有已完工工單的資料"""
        self.stdout.write('開始清理所有已完工工單的資料...')
        
        completed_workorders = CompletedWorkOrder.objects.all()
        total_count = completed_workorders.count()
        
        if total_count == 0:
            self.stdout.write('沒有找到已完工工單')
            return
        
        self.stdout.write(f'找到 {total_count} 個已完工工單')
        
        success_count = 0
        error_count = 0
        
        for completed_workorder in completed_workorders:
            try:
                workorder_number = completed_workorder.order_number
                
                if check_only:
                    self._show_data_status(workorder_number)
                    continue
                
                if dry_run:
                    self.stdout.write(f'工單 {workorder_number}: 將清理資料')
                    continue
                
                # 清理不一致的資料
                with transaction.atomic():
                    # 刪除所有 CompletedProductionReport 記錄
                    deleted_reports = CompletedProductionReport.objects.filter(
                        completed_workorder=completed_workorder
                    ).delete()
                    
                    # 重新計算統計資料
                    self._recalculate_stats(completed_workorder)
                    
                    success_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'清理工單 {workorder_number} 時發生錯誤: {str(e)}')
                )
                error_count += 1
        
        self.stdout.write('\n=== 清理結果 ===')
        self.stdout.write(
            self.style.SUCCESS(f'成功清理: {success_count} 個工單')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'清理失敗: {error_count} 個工單')
            )

    def _show_data_status(self, workorder_number):
        """顯示資料狀況"""
        # 檢查 FillWork 記錄
        fillwork_count = FillWork.objects.filter(workorder=workorder_number).count()
        fillwork_approved = FillWork.objects.filter(
            workorder=workorder_number, 
            approval_status='approved'
        ).count()
        
        # 檢查 CompletedProductionReport 記錄
        completed_reports_count = CompletedProductionReport.objects.filter(
            completed_workorder__order_number=workorder_number
        ).count()
        
        self.stdout.write(f'工單 {workorder_number}:')
        self.stdout.write(f'  FillWork 記錄: {fillwork_count} 筆 (已核准: {fillwork_approved} 筆)')
        self.stdout.write(f'  CompletedProductionReport 記錄: {completed_reports_count} 筆')

    def _recalculate_stats(self, completed_workorder):
        """重新計算統計資料"""
        # 獲取該工單的所有已核准填報紀錄
        fillwork_reports = FillWork.objects.filter(
            workorder=completed_workorder.order_number,
            approval_status='approved'
        )
        
        # 計算統計資料
        total_reports = fillwork_reports.count()
        total_work_quantity = fillwork_reports.aggregate(
            total=Sum('work_quantity')
        )['total'] or 0
        total_defect_quantity = fillwork_reports.aggregate(
            total=Sum('defect_quantity')
        )['total'] or 0
        total_work_hours = fillwork_reports.aggregate(
            total=Sum('work_hours_calculated')
        )['total'] or 0.0
        total_overtime_hours = fillwork_reports.aggregate(
            total=Sum('overtime_hours_calculated')
        )['total'] or 0.0
        
        # 獲取參與人員和設備
        unique_operators = list(set(
            report.operator for report in fillwork_reports 
            if report.operator
        ))
        unique_equipment = list(set(
            report.equipment for report in fillwork_reports 
            if report.equipment
        ))
        
        # 更新已完工工單的統計資料
        completed_workorder.completed_quantity = total_work_quantity
        completed_workorder.total_good_quantity = total_work_quantity
        completed_workorder.total_defect_quantity = total_defect_quantity
        completed_workorder.total_work_hours = total_work_hours
        completed_workorder.total_overtime_hours = total_overtime_hours
        completed_workorder.total_all_hours = total_work_hours + total_overtime_hours
        completed_workorder.total_report_count = total_reports
        completed_workorder.unique_operators = unique_operators
        completed_workorder.unique_equipment = unique_equipment
        completed_workorder.save() 