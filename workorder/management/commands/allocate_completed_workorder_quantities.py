#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
已完工工單工序紀錄數量分配管理命令
用於執行已完工工單的數量分配功能
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workorder.services.completed_workorder_allocation_service import CompletedWorkOrderAllocationService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    已完工工單工序紀錄數量分配命令
    """
    
    help = '為已完工工單的數量為0的工序紀錄自動分配數量'
    
    def add_arguments(self, parser):
        """添加命令參數"""
        parser.add_argument(
            '--workorder',
            type=str,
            help='指定工單號碼（不指定則處理所有待分配工單）'
        )
        
        parser.add_argument(
            '--company',
            type=str,
            help='指定公司代號（可選）'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只顯示會執行的操作但不實際執行'
        )
        
        parser.add_argument(
            '--summary',
            action='store_true',
            help='只顯示分配摘要，不執行分配'
        )
    
    def handle(self, *args, **options):
        """執行命令"""
        try:
            service = CompletedWorkOrderAllocationService()
            
            # 獲取參數
            workorder_number = options.get('workorder')
            company_code = options.get('company')
            dry_run = options.get('dry_run')
            summary_only = options.get('summary')
            
            if workorder_number:
                # 處理指定工單
                self._handle_single_workorder(
                    service, workorder_number, company_code, dry_run, summary_only
                )
            else:
                # 處理所有待分配工單
                self._handle_all_workorders(
                    service, company_code, dry_run, summary_only
                )
                
        except Exception as e:
            logger.error(f"執行已完工工單數量分配時發生錯誤: {str(e)}")
            raise CommandError(f"執行失敗: {str(e)}")
    
    def _handle_single_workorder(self, service, workorder_number, company_code, dry_run, summary_only):
        """處理單一工單"""
        self.stdout.write(
            self.style.SUCCESS(f'處理工單: {workorder_number}')
        )
        
        if summary_only:
            # 只顯示摘要
            summary = service.get_allocation_summary(workorder_number)
            if 'error' in summary:
                self.stdout.write(
                    self.style.ERROR(f'錯誤: {summary["error"]}')
                )
                return
            
            self._display_allocation_summary(summary)
            return
        
        if dry_run:
            # 乾跑模式
            summary = service.get_allocation_summary(workorder_number)
            if 'error' in summary:
                self.stdout.write(
                    self.style.ERROR(f'錯誤: {summary["error"]}')
                )
                return
            
            self.stdout.write(
                self.style.WARNING('=== 乾跑模式 ===')
            )
            self._display_allocation_summary(summary)
            
            # 顯示會執行的分配
            pending_workorders = service.get_pending_allocation_workorders(company_code)
            target_workorder = next(
                (w for w in pending_workorders if w['workorder_number'] == workorder_number),
                None
            )
            
            if target_workorder:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'會為工單 {workorder_number} 分配 {target_workorder["zero_quantity_reports_count"]} 筆工序紀錄'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'工單 {workorder_number} 沒有需要分配的工序紀錄')
                )
        else:
            # 實際執行分配
            result = service.allocate_completed_workorder_quantities(
                workorder_number, company_code
            )
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'分配成功！工單 {workorder_number} 共分配 {result["total_allocated_quantity"]} 件給 {result["total_allocated_reports"]} 筆紀錄'
                    )
                )
                
                # 顯示詳細結果
                for allocation in result['allocation_results']:
                    self.stdout.write(
                        f'  工序 {allocation["process_name"]}: '
                        f'分配 {allocation["allocated_quantity"]} 件給 {allocation["allocated_reports"]} 筆紀錄'
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'分配失敗: {result["message"]}')
                )
    
    def _handle_all_workorders(self, service, company_code, dry_run, summary_only):
        """處理所有待分配工單"""
        self.stdout.write(
            self.style.SUCCESS('處理所有待分配已完工工單')
        )
        
        if summary_only:
            # 只顯示摘要
            pending_workorders = service.get_pending_allocation_workorders(company_code)
            
            if not pending_workorders:
                self.stdout.write(
                    self.style.WARNING('沒有需要分配的已完工工單')
                )
                return
            
            self.stdout.write(
                self.style.SUCCESS(f'共有 {len(pending_workorders)} 個工單需要分配')
            )
            
            for workorder_info in pending_workorders:
                summary = service.get_allocation_summary(workorder_info['workorder_number'])
                if 'error' not in summary:
                    self.stdout.write(f'\n工單 {workorder_info["workorder_number"]}:')
                    self._display_allocation_summary(summary, indent=2)
            
            return
        
        if dry_run:
            # 乾跑模式
            pending_workorders = service.get_pending_allocation_workorders(company_code)
            
            if not pending_workorders:
                self.stdout.write(
                    self.style.WARNING('沒有需要分配的已完工工單')
                )
                return
            
            self.stdout.write(
                self.style.WARNING('=== 乾跑模式 ===')
            )
            self.stdout.write(
                self.style.SUCCESS(f'會處理 {len(pending_workorders)} 個工單')
            )
            
            for workorder_info in pending_workorders:
                self.stdout.write(
                    f'  工單 {workorder_info["workorder_number"]}: '
                    f'{workorder_info["zero_quantity_reports_count"]} 筆工序紀錄需要分配'
                )
        else:
            # 實際執行分配
            result = service.allocate_all_pending_workorders(company_code)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'批量分配完成！'
                        f'處理 {result["total_processed"]} 個工單，'
                        f'成功 {result["total_success"]} 個，'
                        f'失敗 {result["total_failed"]} 個'
                    )
                )
                
                if result['failed_workorders']:
                    self.stdout.write(
                        self.style.ERROR('失敗的工單:')
                    )
                    for failed in result['failed_workorders']:
                        self.stdout.write(
                            f'  {failed["workorder_number"]}: {failed["error"]}'
                        )
            else:
                self.stdout.write(
                    self.style.ERROR(f'批量分配失敗: {result["message"]}')
                )
    
    def _display_allocation_summary(self, summary, indent=0):
        """顯示分配摘要"""
        indent_str = ' ' * indent
        
        self.stdout.write(f'{indent_str}工單號碼: {summary["workorder_number"]}')
        self.stdout.write(f'{indent_str}計劃數量: {summary["planned_quantity"]}')
        self.stdout.write(f'{indent_str}總工序紀錄: {summary["total_reports"]}')
        self.stdout.write(f'{indent_str}總數量: {summary["total_quantity"]}')
        self.stdout.write(f'{indent_str}系統分配數量: {summary["total_system_allocated"]}')
        self.stdout.write(f'{indent_str}手動填寫數量: {summary["total_manual_quantity"]}')
        self.stdout.write(f'{indent_str}數量為0的紀錄: {summary["total_zero_quantity_reports"]}')
        
        if summary['processes']:
            self.stdout.write(f'{indent_str}工序統計:')
            for process_name, data in summary['processes'].items():
                self.stdout.write(f'{indent_str}  {process_name}:')
                self.stdout.write(f'{indent_str}    總數量: {data["total_quantity"]}')
                self.stdout.write(f'{indent_str}    系統分配: {data["system_allocated_quantity"]}')
                self.stdout.write(f'{indent_str}    手動填寫: {data["manual_quantity"]}')
                self.stdout.write(f'{indent_str}    紀錄筆數: {data["report_count"]}')
                self.stdout.write(f'{indent_str}    數量為0: {data["zero_quantity_reports"]}') 