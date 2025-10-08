"""
清理 WorkOrderReportData 表中的重複資料
解決排程報表執行失敗的問題
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from reporting.models import WorkOrderReportData
from django.db.models import Count, Max
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理 WorkOrderReportData 表中的重複資料'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只顯示會刪除的記錄，不實際執行刪除',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='批次處理大小，預設 100',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        self.stdout.write('開始清理 WorkOrderReportData 重複資料...')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN 模式：只顯示會刪除的記錄'))
        
        try:
            # 找出所有重複的記錄
            duplicates = WorkOrderReportData.objects.values(
                'workorder_id', 'company', 'work_date'
            ).annotate(
                count=Count('id'),
                max_id=Max('id')
            ).filter(count__gt=1).order_by('-count')
            
            total_duplicates = duplicates.count()
            self.stdout.write(f'找到 {total_duplicates} 組重複資料')
            
            if total_duplicates == 0:
                self.stdout.write(self.style.SUCCESS('沒有重複資料需要清理'))
                return
            
            # 顯示重複資料統計
            self.stdout.write('\n重複資料統計（前10組）：')
            for i, dup in enumerate(duplicates[:10]):
                self.stdout.write(
                    f'{i+1}. 工單: {dup["workorder_id"]}, '
                    f'公司: {dup["company"]}, '
                    f'日期: {dup["work_date"]}, '
                    f'重複次數: {dup["count"]}'
                )
            
            if dry_run:
                self.stdout.write(f'\nDRY RUN: 將會刪除 {total_duplicates} 組重複資料')
                return
            
            # 確認是否繼續
            confirm = input(f'\n確定要刪除 {total_duplicates} 組重複資料嗎？(y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('操作已取消')
                return
            
            # 開始清理重複資料
            deleted_count = 0
            processed_groups = 0
            
            with transaction.atomic():
                for dup in duplicates:
                    # 取得這組重複資料的所有記錄
                    records = WorkOrderReportData.objects.filter(
                        workorder_id=dup['workorder_id'],
                        company=dup['company'],
                        work_date=dup['work_date']
                    ).order_by('id')
                    
                    # 保留最新的記錄（ID 最大的），刪除其他記錄
                    records_to_delete = records.exclude(id=dup['max_id'])
                    delete_count = records_to_delete.count()
                    
                    if delete_count > 0:
                        records_to_delete.delete()
                        deleted_count += delete_count
                        processed_groups += 1
                        
                        if processed_groups % batch_size == 0:
                            self.stdout.write(f'已處理 {processed_groups} 組重複資料...')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'清理完成！共處理 {processed_groups} 組重複資料，'
                    f'刪除 {deleted_count} 筆記錄'
                )
            )
            
            # 顯示清理後的統計
            remaining_count = WorkOrderReportData.objects.count()
            unique_count = WorkOrderReportData.objects.values(
                'workorder_id', 'company', 'work_date'
            ).distinct().count()
            
            self.stdout.write(f'清理後統計：')
            self.stdout.write(f'- 總記錄數: {remaining_count}')
            self.stdout.write(f'- 唯一記錄數: {unique_count}')
            self.stdout.write(f'- 重複記錄數: {remaining_count - unique_count}')
            
        except Exception as e:
            logger.error(f'清理重複資料失敗: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'清理失敗: {str(e)}')
            )
            raise
