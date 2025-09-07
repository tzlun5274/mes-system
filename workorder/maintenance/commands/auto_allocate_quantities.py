#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Django 管理命令：自動分配報工數量
為數量為0的報工記錄分配數量，排除出貨包裝工序
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workorder.services.auto_allocation_service import AutoAllocationService
import json


class Command(BaseCommand):
    help = '為數量為0的已完工報工記錄自動分配數量，排除出貨包裝工序'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workorder',
            type=str,
            help='指定已完工工單號碼進行分配'
        )
        parser.add_argument(
            '--company',
            type=str,
            help='指定公司代號'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='為所有待分配的已完工工單進行批量分配'
        )
        parser.add_argument(
            '--summary',
            action='store_true',
            help='顯示分配摘要'
        )
        parser.add_argument(
            '--pending-summary',
            action='store_true',
            help='顯示待分配記錄的摘要統計'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='試運行模式，不實際更新資料庫'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='限制處理的工單數量（用於測試）'
        )

    def handle(self, *args, **options):
        service = AutoAllocationService()
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 不會實際更新資料庫')
            )
        
        if options['pending_summary']:
            # 顯示待分配摘要
            self._show_pending_summary(service, options['company'])
        elif options['workorder']:
            # 為指定已完工工單分配
            self._allocate_single_completed_workorder(
                service, 
                options['workorder'], 
                options['company'],
                options['summary'],
                options['dry_run']
            )
        elif options['all']:
            # 批量分配
            self._allocate_all_workorders(
                service, 
                options['company'],
                options['dry_run'],
                options['limit']
            )
        else:
            raise CommandError(
                '請指定 --pending-summary、--workorder 或 --all 參數'
            )

    def _allocate_single_completed_workorder(self, service, workorder_number, company_code, show_summary, dry_run):
        """為單一已完工工單分配數量"""
        self.stdout.write(f'開始為已完工工單 {workorder_number} 進行自動分配...')
        
        if show_summary:
            # 顯示分配前摘要
            summary = service.get_pending_allocation_summary(company_code)
            if 'error' in summary:
                self.stdout.write(
                    self.style.ERROR(f'獲取摘要失敗: {summary["error"]}')
                )
                return
            
            self.stdout.write('\n=== 分配前摘要 ===')
            self._print_pending_summary(summary)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 跳過實際分配')
            )
            return
        
        # 執行分配
        result = service.allocate_all_pending_workorders(company_code)
        
        # 篩選指定工單的結果
        workorder_result = None
        for item in result.get('results', []):
            if item['workorder_number'] == workorder_number:
                workorder_result = item['result']
                break
        
        if workorder_result and workorder_result.get('success', True):
            self.stdout.write(
                self.style.SUCCESS(f'已完工工單 {workorder_number} 分配完成')
            )
            self._print_allocation_result(workorder_result)
        else:
            self.stdout.write(
                self.style.ERROR(f'分配失敗: {workorder_result.get("message", "未知錯誤") if workorder_result else "工單不存在"}')
            )
    
    def _allocate_single_workorder(self, service, workorder_number, company_code, show_summary, dry_run):
        """為單一工單分配數量（原始版本）"""
        self.stdout.write(f'開始為工單 {workorder_number} 進行自動分配...')
        
        if show_summary:
            # 顯示分配前摘要
            summary = service.get_allocation_summary(workorder_number)
            if 'error' in summary:
                self.stdout.write(
                    self.style.ERROR(f'獲取摘要失敗: {summary["error"]}')
                )
                return
            
            self.stdout.write('\n=== 分配前摘要 ===')
            self._print_summary(summary)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 跳過實際分配')
            )
            return
        
        # 執行分配
        result = service.allocate_workorder_quantities(workorder_number, company_code)
        
        if result.get('success', True):
            self.stdout.write(
                self.style.SUCCESS(f'工單 {workorder_number} 分配完成')
            )
            self._print_allocation_result(result)
        else:
            self.stdout.write(
                self.style.ERROR(f'分配失敗: {result.get("message", "未知錯誤")}')
            )

    def _show_pending_summary(self, service, company_code):
        """顯示待分配記錄的摘要"""
        self.stdout.write('=== 待分配記錄摘要 ===')
        
        summary = service.get_pending_allocation_summary(company_code)
        
        self.stdout.write(f'總待分配記錄數: {summary["total_pending_reports"]}')
        self.stdout.write(f'總工單數: {summary["total_workorders"]}')
        
        if company_code:
            self.stdout.write(f'公司代號: {company_code}')
        
        if summary.get('processes'):
            self.stdout.write('\n按工序統計:')
            for process_name, data in summary['processes'].items():
                status = '[排除]' if data['is_packaging'] else ''
                self.stdout.write(
                    f'  - {process_name} {status}: '
                    f'{data["report_count"]} 筆記錄, '
                    f'總工時 {data["total_hours"]:.2f} 小時'
                )
        
        if summary.get('workorders'):
            self.stdout.write('\n按工單統計 (前10個):')
            count = 0
            for workorder_number, data in summary['workorders'].items():
                if count >= 10:
                    self.stdout.write(f'  ... 還有 {len(summary["workorders"]) - 10} 個工單')
                    break
                self.stdout.write(
                    f'  - {workorder_number}: '
                    f'{data["report_count"]} 筆記錄, '
                    f'計劃數量 {data["planned_quantity"]}, '
                    f'總工時 {data["total_hours"]:.2f} 小時'
                )
                count += 1

    def _allocate_all_workorders(self, service, company_code, dry_run, limit=None):
        """批量分配所有工單"""
        self.stdout.write('開始批量自動分配...')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('試運行模式 - 跳過實際分配')
            )
            return
        
        if limit:
            self.stdout.write(f'限制處理工單數量: {limit}')
        
        result = service.allocate_all_pending_workorders(company_code)
        
        # 如果設定了限制，只處理前N個工單
        if limit and result.get('results'):
            result['results'] = result['results'][:limit]
            result['total_workorders'] = min(result['total_workorders'], limit)
            result['successful_allocations'] = len([r for r in result['results'] if r['result'].get('success', True)])
            result['failed_allocations'] = len([r for r in result['results'] if not r['result'].get('success', True)])
        
        self.stdout.write('\n=== 批量分配結果 ===')
        self.stdout.write(f'總工單數: {result["total_workorders"]}')
        self.stdout.write(
            self.style.SUCCESS(f'成功分配: {result["successful_allocations"]} 個工單')
        )
        self.stdout.write(
            self.style.ERROR(f'分配失敗: {result["failed_allocations"]} 個工單')
        )
        
        # 顯示詳細結果
        for item in result['results']:
            workorder_number = item['workorder_number']
            item_result = item['result']
            
            if item_result.get('success', True):
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {workorder_number}: 分配成功')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ {workorder_number}: {item_result.get("message", "分配失敗")}')
                )

    def _print_allocation_result(self, result):
        """列印分配結果"""
        self.stdout.write(f'\n工單號碼: {result["workorder_number"]}')
        self.stdout.write(f'計劃數量: {result["total_planned_quantity"]}')
        self.stdout.write(f'總分配記錄數: {result["total_reports_allocated"]}')
        self.stdout.write(f'總分配數量: {result["total_quantity_allocated"]}')
        
        if result.get('excluded_processes'):
            self.stdout.write('\n排除的工序:')
            for process in result['excluded_processes']:
                self.stdout.write(
                    f'  - {process["process_name"]}: {process["reason"]} '
                    f'({process["report_count"]} 筆記錄)'
                )
        
        if result.get('processes_allocated'):
            self.stdout.write('\n分配結果:')
            for process in result['processes_allocated']:
                self.stdout.write(
                    f'  - {process["process_name"]}: '
                    f'{process["quantity_allocated"]} 件 '
                    f'({process["reports_allocated"]} 筆記錄)'
                )
                
                if process.get('allocated_reports'):
                    for report in process['allocated_reports']:
                        self.stdout.write(
                            f'    * {report["operator"]} ({report["report_date"]}): '
                            f'{report["allocated_quantity"]} 件 '
                            f'(工時: {report["work_hours"]}小時)'
                        )

    def _print_pending_summary(self, summary):
        """列印待分配摘要"""
        self.stdout.write(f'總待分配記錄數: {summary["total_pending_reports"]}')
        self.stdout.write(f'總工單數: {summary["total_workorders"]}')
        
        if summary.get('processes'):
            self.stdout.write('\n按工序統計:')
            for process_name, data in summary['processes'].items():
                status = '[排除]' if data['is_packaging'] else ''
                self.stdout.write(
                    f'  - {process_name} {status}: '
                    f'{data["report_count"]} 筆記錄, '
                    f'總工時 {data["total_hours"]:.2f} 小時'
                )
        
        if summary.get('workorders'):
            self.stdout.write('\n按工單統計 (前10個):')
            count = 0
            for workorder_number, data in summary['workorders'].items():
                if count >= 10:
                    self.stdout.write(f'  ... 還有 {len(summary["workorders"]) - 10} 個工單')
                    break
                self.stdout.write(
                    f'  - {workorder_number}: '
                    f'{data["report_count"]} 筆記錄, '
                    f'計劃數量 {data["planned_quantity"]}, '
                    f'總工時 {data["total_hours"]:.2f} 小時'
                )
                count += 1

    def _print_summary(self, summary):
        """列印分配摘要"""
        self.stdout.write(f'工單號碼: {summary["workorder_number"]}')
        self.stdout.write(f'計劃數量: {summary["planned_quantity"]}')
        self.stdout.write(f'原始數量總計: {summary["total_original_quantity"]}')
        self.stdout.write(f'已分配數量總計: {summary["total_allocated_quantity"]}')
        
        if summary.get('excluded_processes'):
            self.stdout.write(f'排除工序: {", ".join(summary["excluded_processes"])}')
        
        self.stdout.write('\n各工序統計:')
        for process_name, data in summary['processes'].items():
            status = '[排除]' if data['is_packaging'] else ''
            self.stdout.write(
                f'  - {process_name} {status}: '
                f'原始 {data["original_quantity"]} 件, '
                f'已分配 {data["allocated_quantity"]} 件, '
                f'{data["report_count"]} 筆記錄'
            ) 