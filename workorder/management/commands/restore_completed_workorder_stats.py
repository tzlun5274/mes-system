#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django 管理命令：還原已完工工單統計資料
將已完工工單的統計資料還原為基於填報紀錄的狀態
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum
from workorder.models import CompletedWorkOrder
from workorder.fill_work.models import FillWork
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '將已完工工單的統計資料還原為基於填報紀錄的狀態'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder',
            type=str,
            help='指定工單號碼進行還原'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='還原所有已完工工單的統計資料'
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
        """還原單一已完工工單的統計資料"""
        self.stdout.write(f'開始還原工單 {workorder_number} 的統計資料...')
        
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
            
            # 顯示目前的統計資料
            self._show_current_stats(completed_workorder)
            
            # 計算基於填報紀錄的統計資料
            fillwork_stats = self._calculate_fillwork_stats(workorder_number)
            
            # 顯示基於填報紀錄的統計資料
            self.stdout.write('\n=== 基於填報紀錄的統計 ===')
            self.stdout.write(f'填報紀錄總數: {fillwork_stats["total_reports"]}')
            self.stdout.write(f'總工作數量: {fillwork_stats["total_work_quantity"]}')
            self.stdout.write(f'總不良品數量: {fillwork_stats["total_defect_quantity"]}')
            self.stdout.write(f'總工作時數: {fillwork_stats["total_work_hours"]}')
            self.stdout.write(f'總加班時數: {fillwork_stats["total_overtime_hours"]}')
            
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
            
            # 更新已完工工單的統計資料
            with transaction.atomic():
                completed_workorder.completed_quantity = fillwork_stats["total_work_quantity"]
                completed_workorder.total_good_quantity = fillwork_stats["total_work_quantity"]
                completed_workorder.total_defect_quantity = fillwork_stats["total_defect_quantity"]
                completed_workorder.total_work_hours = fillwork_stats["total_work_hours"]
                completed_workorder.total_overtime_hours = fillwork_stats["total_overtime_hours"]
                completed_workorder.total_all_hours = fillwork_stats["total_work_hours"] + fillwork_stats["total_overtime_hours"]
                completed_workorder.total_report_count = fillwork_stats["total_reports"]
                completed_workorder.unique_operators = fillwork_stats["unique_operators"]
                completed_workorder.unique_equipment = fillwork_stats["unique_equipment"]
                completed_workorder.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'工單 {workorder_number} 統計資料已還原')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'還原工單 {workorder_number} 時發生錯誤: {str(e)}')
            )

    def _restore_all_workorders(self, check_only, dry_run):
        """還原所有已完工工單的統計資料"""
        self.stdout.write('開始還原所有已完工工單的統計資料...')
        
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
                
                # 計算基於填報紀錄的統計資料
                fillwork_stats = self._calculate_fillwork_stats(workorder_number)
                
                if check_only:
                    self.stdout.write(f'工單 {workorder_number}: 填報紀錄 {fillwork_stats["total_reports"]} 筆')
                    continue
                
                if dry_run:
                    self.stdout.write(f'工單 {workorder_number}: 將更新統計資料')
                    continue
                
                # 更新已完工工單的統計資料
                with transaction.atomic():
                    completed_workorder.completed_quantity = fillwork_stats["total_work_quantity"]
                    completed_workorder.total_good_quantity = fillwork_stats["total_work_quantity"]
                    completed_workorder.total_defect_quantity = fillwork_stats["total_defect_quantity"]
                    completed_workorder.total_work_hours = fillwork_stats["total_work_hours"]
                    completed_workorder.total_overtime_hours = fillwork_stats["total_overtime_hours"]
                    completed_workorder.total_all_hours = fillwork_stats["total_work_hours"] + fillwork_stats["total_overtime_hours"]
                    completed_workorder.total_report_count = fillwork_stats["total_reports"]
                    completed_workorder.unique_operators = fillwork_stats["unique_operators"]
                    completed_workorder.unique_equipment = fillwork_stats["unique_equipment"]
                    completed_workorder.save()
                    
                    success_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'還原工單 {workorder_number} 時發生錯誤: {str(e)}')
                )
                error_count += 1
        
        self.stdout.write('\n=== 還原結果 ===')
        self.stdout.write(
            self.style.SUCCESS(f'成功還原: {success_count} 個工單')
        )
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'還原失敗: {error_count} 個工單')
            )

    def _show_current_stats(self, completed_workorder):
        """顯示目前的統計資料"""
        self.stdout.write('\n=== 目前統計資料 ===')
        self.stdout.write(f'工單號: {completed_workorder.order_number}')
        self.stdout.write(f'計劃數量: {completed_workorder.planned_quantity}')
        self.stdout.write(f'完工數量: {completed_workorder.completed_quantity}')
        self.stdout.write(f'合格品數量: {completed_workorder.total_good_quantity}')
        self.stdout.write(f'不良品數量: {completed_workorder.total_defect_quantity}')
        self.stdout.write(f'總工作時數: {completed_workorder.total_work_hours}')
        self.stdout.write(f'總加班時數: {completed_workorder.total_overtime_hours}')
        self.stdout.write(f'填報紀錄數: {completed_workorder.total_report_count}')

    def _calculate_fillwork_stats(self, workorder_number):
        """計算基於填報紀錄的統計資料"""
        # 獲取該工單的所有填報紀錄
        fillwork_reports = FillWork.objects.filter(
            workorder=workorder_number,
            approval_status='approved'
        )
        
        # 計算基本統計資料
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
        
        return {
            'total_reports': total_reports,
            'total_work_quantity': total_work_quantity,
            'total_defect_quantity': total_defect_quantity,
            'total_work_hours': total_work_hours,
            'total_overtime_hours': total_overtime_hours,
            'unique_operators': unique_operators,
            'unique_equipment': unique_equipment,
        } 