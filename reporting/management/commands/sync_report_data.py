#!/usr/bin/env python3
"""
報表數據同步管理命令
用於將報工記錄同步到報表快取中，提升報表查詢效能
"""

import os
import sys
import django
from datetime import datetime, date, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# 設定Django環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mes_config.settings')
django.setup()

from reporting.services.work_time_service import WorkTimeReportService


class Command(BaseCommand):
    """報表數據同步命令"""
    
    help = '同步報表數據到快取，提升查詢效能'
    
    def add_arguments(self, parser):
        """添加命令參數"""
        parser.add_argument(
            '--sync-type',
            type=str,
            choices=['work_time', 'worker_performance', 'workorder_summary', 'all'],
            default='all',
            help='同步類型 (work_time/worker_performance/workorder_summary/all)'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='開始日期 (YYYY-MM-DD)'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            help='結束日期 (YYYY-MM-DD)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='同步最近幾天的數據 (預設30天)'
        )
        
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='同步前清理舊的快取數據'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新同步，覆蓋現有快取'
        )
    
    def handle(self, *args, **options):
        """執行同步命令"""
        self.stdout.write(self.style.SUCCESS('開始同步報表數據...'))
        
        # 初始化服務
        service = WorkTimeReportService()
        
        # 解析日期參數
        start_date, end_date = self._parse_dates(options)
        
        # 清理快取（如果需要）
        if options['clear_cache']:
            self.stdout.write('清理舊的快取數據...')
            result = service.clear_cache()
            if result['success']:
                self.stdout.write(self.style.SUCCESS('快取清理完成'))
            else:
                self.stdout.write(self.style.ERROR(f'快取清理失敗: {result["error"]}'))
        
        # 執行同步
        sync_types = self._get_sync_types(options['sync_type'])
        
        for sync_type in sync_types:
            self.stdout.write(f'同步 {sync_type} 數據...')
            
            try:
                result = service.sync_report_data(start_date, end_date, sync_type)
                
                if result['success']:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'{sync_type} 同步成功: '
                            f'處理 {result["records_processed"]} 筆記錄, '
                            f'新增 {result["records_created"]} 筆, '
                            f'更新 {result["records_updated"]} 筆, '
                            f'耗時 {result["duration_seconds"]} 秒'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'{sync_type} 同步失敗: {result["error"]}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'{sync_type} 同步異常: {str(e)}')
                )
        
        self.stdout.write(self.style.SUCCESS('報表數據同步完成'))
    
    def _parse_dates(self, options):
        """解析日期參數"""
        if options['start_date'] and options['end_date']:
            try:
                start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('日期格式錯誤，請使用 YYYY-MM-DD 格式')
        else:
            # 使用預設的最近N天
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=options['days'])
        
        return start_date, end_date
    
    def _get_sync_types(self, sync_type):
        """取得要同步的類型列表"""
        if sync_type == 'all':
            return ['work_time', 'worker_performance', 'workorder_summary']
        else:
            return [sync_type]


if __name__ == '__main__':
    # 直接執行時的測試代碼
    command = Command()
    command.handle(
        sync_type='all',
        start_date=None,
        end_date=None,
        days=7,
        clear_cache=True,
        force=False
    ) 