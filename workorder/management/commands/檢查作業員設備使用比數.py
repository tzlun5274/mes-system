#!/usr/bin/env python3
"""
檢查作業員報工使用的設備紀錄比數
此命令會分析作業員報工記錄中設備使用的統計資訊
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport
from workorder.models import WorkOrderProductionDetail, CompletedProductionReport
from django.db.models import Count, Q
from collections import defaultdict
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '檢查作業員報工使用的設備紀錄比數'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['operator_supplement', 'production_detail', 'completed', 'all'],
            default='all',
            help='指定要檢查的記錄類型',
        )
        parser.add_argument(
            '--operator',
            type=str,
            help='指定特定作業員進行檢查',
        )
        parser.add_argument(
            '--date-range',
            type=str,
            help='指定日期範圍 (格式: YYYY-MM-DD,YYYY-MM-DD)',
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='匯出詳細統計結果到檔案',
        )

    def handle(self, *args, **options):
        record_type = options['type']
        operator_name = options['operator']
        date_range = options['date_range']
        export = options['export']
        
        self.stdout.write(
            self.style.SUCCESS('開始檢查作業員報工使用的設備紀錄比數...')
        )
        
        try:
            if record_type in ['operator_supplement', 'all']:
                self._check_operator_supplement_reports(operator_name, date_range, export)
            
            if record_type in ['production_detail', 'all']:
                self._check_production_detail_reports(operator_name, date_range, export)
            
            if record_type in ['completed', 'all']:
                self._check_completed_reports(operator_name, date_range, export)
            
            if record_type == 'all':
                self._show_summary_statistics()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'檢查過程中發生錯誤: {str(e)}')
            )
            logger.error(f'檢查作業員設備使用比數失敗: {str(e)}')

    def _check_operator_supplement_reports(self, operator_name, date_range, export):
        """檢查作業員補登報工記錄的設備使用情況"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('作業員補登報工記錄設備使用統計')
        self.stdout.write('='*60)
        
        # 建立查詢條件
        query = OperatorSupplementReport.objects.all()
        
        if operator_name:
            query = query.filter(operator__name__icontains=operator_name)
            self.stdout.write(f'篩選作業員: {operator_name}')
        
        if date_range:
            start_date, end_date = date_range.split(',')
            query = query.filter(work_date__range=[start_date, end_date])
            self.stdout.write(f'日期範圍: {start_date} 到 {end_date}')
        
        # 統計總記錄數
        total_reports = query.count()
        self.stdout.write(f'總記錄數: {total_reports}')
        
        if total_reports == 0:
            self.stdout.write('沒有找到符合條件的記錄')
            return
        
        # 統計設備使用情況
        equipment_stats = query.values('equipment__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 統計沒有設備的記錄
        no_equipment_count = query.filter(
            Q(equipment__isnull=True) | Q(equipment__name='')
        ).count()
        
        self.stdout.write(f'\n設備使用統計:')
        self.stdout.write(f'  有設備記錄: {total_reports - no_equipment_count} 筆 ({((total_reports - no_equipment_count)/total_reports*100):.1f}%)')
        self.stdout.write(f'  無設備記錄: {no_equipment_count} 筆 ({no_equipment_count/total_reports*100:.1f}%)')
        
        if equipment_stats:
            self.stdout.write(f'\n設備使用排行 (前10名):')
            for i, stat in enumerate(equipment_stats[:10], 1):
                equipment_name = stat['equipment__name'] or '未指定設備'
                count = stat['count']
                percentage = count / total_reports * 100
                self.stdout.write(f'  {i:2d}. {equipment_name}: {count} 筆 ({percentage:.1f}%)')
        
        # 按作業員統計設備使用
        if not operator_name:
            self._show_operator_equipment_stats(query, '作業員補登報工')
        
        if export:
            self._export_operator_stats(query, 'operator_supplement')

    def _check_production_detail_reports(self, operator_name, date_range, export):
        """檢查生產中工單明細記錄的設備使用情況"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('生產中工單明細記錄設備使用統計')
        self.stdout.write('='*60)
        
        # 建立查詢條件
        query = WorkOrderProductionDetail.objects.filter(
            report_source='operator_supplement'  # 只檢查作業員報工來源
        )
        
        if operator_name:
            query = query.filter(operator__icontains=operator_name)
            self.stdout.write(f'篩選作業員: {operator_name}')
        
        if date_range:
            start_date, end_date = date_range.split(',')
            query = query.filter(report_date__range=[start_date, end_date])
            self.stdout.write(f'日期範圍: {start_date} 到 {end_date}')
        
        # 統計總記錄數
        total_reports = query.count()
        self.stdout.write(f'總記錄數: {total_reports}')
        
        if total_reports == 0:
            self.stdout.write('沒有找到符合條件的記錄')
            return
        
        # 統計設備使用情況
        equipment_stats = query.values('equipment').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 統計沒有設備的記錄
        no_equipment_count = query.filter(
            Q(equipment__isnull=True) | Q(equipment='')
        ).count()
        
        self.stdout.write(f'\n設備使用統計:')
        self.stdout.write(f'  有設備記錄: {total_reports - no_equipment_count} 筆 ({((total_reports - no_equipment_count)/total_reports*100):.1f}%)')
        self.stdout.write(f'  無設備記錄: {no_equipment_count} 筆 ({no_equipment_count/total_reports*100:.1f}%)')
        
        if equipment_stats:
            self.stdout.write(f'\n設備使用排行 (前10名):')
            for i, stat in enumerate(equipment_stats[:10], 1):
                equipment_name = stat['equipment'] or '未指定設備'
                count = stat['count']
                percentage = count / total_reports * 100
                self.stdout.write(f'  {i:2d}. {equipment_name}: {count} 筆 ({percentage:.1f}%)')
        
        # 按作業員統計設備使用
        if not operator_name:
            self._show_operator_equipment_stats(query, '生產中工單明細')
        
        if export:
            self._export_production_stats(query, 'production_detail')

    def _check_completed_reports(self, operator_name, date_range, export):
        """檢查已完工生產報工記錄的設備使用情況"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('已完工生產報工記錄設備使用統計')
        self.stdout.write('='*60)
        
        # 建立查詢條件
        query = CompletedProductionReport.objects.filter(
            report_type='operator'  # 只檢查作業員報工
        )
        
        if operator_name:
            query = query.filter(operator__icontains=operator_name)
            self.stdout.write(f'篩選作業員: {operator_name}')
        
        if date_range:
            start_date, end_date = date_range.split(',')
            query = query.filter(report_date__range=[start_date, end_date])
            self.stdout.write(f'日期範圍: {start_date} 到 {end_date}')
        
        # 統計總記錄數
        total_reports = query.count()
        self.stdout.write(f'總記錄數: {total_reports}')
        
        if total_reports == 0:
            self.stdout.write('沒有找到符合條件的記錄')
            return
        
        # 統計設備使用情況
        equipment_stats = query.values('equipment').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 統計沒有設備的記錄
        no_equipment_count = query.filter(
            Q(equipment__isnull=True) | Q(equipment='')
        ).count()
        
        self.stdout.write(f'\n設備使用統計:')
        self.stdout.write(f'  有設備記錄: {total_reports - no_equipment_count} 筆 ({((total_reports - no_equipment_count)/total_reports*100):.1f}%)')
        self.stdout.write(f'  無設備記錄: {no_equipment_count} 筆 ({no_equipment_count/total_reports*100:.1f}%)')
        
        if equipment_stats:
            self.stdout.write(f'\n設備使用排行 (前10名):')
            for i, stat in enumerate(equipment_stats[:10], 1):
                equipment_name = stat['equipment'] or '未指定設備'
                count = stat['count']
                percentage = count / total_reports * 100
                self.stdout.write(f'  {i:2d}. {equipment_name}: {count} 筆 ({percentage:.1f}%)')
        
        # 按作業員統計設備使用
        if not operator_name:
            self._show_operator_equipment_stats(query, '已完工生產報工')
        
        if export:
            self._export_completed_stats(query, 'completed')

    def _show_operator_equipment_stats(self, query, record_type):
        """顯示按作業員分組的設備使用統計"""
        self.stdout.write(f'\n{record_type} - 作業員設備使用統計 (前10名):')
        
        # 按作業員和設備分組統計
        operator_equipment_stats = query.values('operator').annotate(
            equipment_count=Count('equipment', distinct=True),
            total_reports=Count('id')
        ).order_by('-total_reports')[:10]
        
        for i, stat in enumerate(operator_equipment_stats, 1):
            operator_name = stat['operator'] or '未指定作業員'
            equipment_count = stat['equipment_count']
            total_reports = stat['total_reports']
            self.stdout.write(f'  {i:2d}. {operator_name}: {total_reports} 筆報工, 使用 {equipment_count} 種設備')

    def _show_summary_statistics(self):
        """顯示總體統計摘要"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('總體統計摘要')
        self.stdout.write('='*60)
        
        # 各類型記錄的總數
        operator_supplement_total = OperatorSupplementReport.objects.count()
        production_detail_total = WorkOrderProductionDetail.objects.filter(
            report_source='operator_supplement'
        ).count()
        completed_total = CompletedProductionReport.objects.filter(
            report_type='operator'
        ).count()
        
        self.stdout.write(f'記錄總數統計:')
        self.stdout.write(f'  作業員補登報工: {operator_supplement_total} 筆')
        self.stdout.write(f'  生產中工單明細: {production_detail_total} 筆')
        self.stdout.write(f'  已完工生產報工: {completed_total} 筆')
        
        # 各類型記錄中有設備的比例
        operator_supplement_with_equipment = OperatorSupplementReport.objects.filter(
            equipment__isnull=False
        ).exclude(equipment__name='').count()
        
        production_detail_with_equipment = WorkOrderProductionDetail.objects.filter(
            report_source='operator_supplement',
            equipment__isnull=False
        ).exclude(equipment='').count()
        
        completed_with_equipment = CompletedProductionReport.objects.filter(
            report_type='operator',
            equipment__isnull=False
        ).exclude(equipment='').count()
        
        self.stdout.write(f'\n設備記錄比例:')
        if operator_supplement_total > 0:
            percentage = operator_supplement_with_equipment / operator_supplement_total * 100
            self.stdout.write(f'  作業員補登報工: {operator_supplement_with_equipment}/{operator_supplement_total} ({percentage:.1f}%)')
        
        if production_detail_total > 0:
            percentage = production_detail_with_equipment / production_detail_total * 100
            self.stdout.write(f'  生產中工單明細: {production_detail_with_equipment}/{production_detail_total} ({percentage:.1f}%)')
        
        if completed_total > 0:
            percentage = completed_with_equipment / completed_total * 100
            self.stdout.write(f'  已完工生產報工: {completed_with_equipment}/{completed_total} ({percentage:.1f}%)')

    def _export_operator_stats(self, query, record_type):
        """匯出作業員補登報工統計到檔案"""
        filename = f'operator_equipment_stats_{record_type}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f'作業員補登報工設備使用統計報告\n')
            f.write(f'生成時間: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            # 寫入設備使用統計
            equipment_stats = query.values('equipment__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            f.write('設備使用統計:\n')
            for stat in equipment_stats:
                equipment_name = stat['equipment__name'] or '未指定設備'
                count = stat['count']
                f.write(f'{equipment_name}: {count} 筆\n')
        
        self.stdout.write(f'統計結果已匯出到: {filename}')

    def _export_production_stats(self, query, record_type):
        """匯出生產中工單明細統計到檔案"""
        filename = f'production_equipment_stats_{record_type}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f'生產中工單明細設備使用統計報告\n')
            f.write(f'生成時間: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            # 寫入設備使用統計
            equipment_stats = query.values('equipment').annotate(
                count=Count('id')
            ).order_by('-count')
            
            f.write('設備使用統計:\n')
            for stat in equipment_stats:
                equipment_name = stat['equipment'] or '未指定設備'
                count = stat['count']
                f.write(f'{equipment_name}: {count} 筆\n')
        
        self.stdout.write(f'統計結果已匯出到: {filename}')

    def _export_completed_stats(self, query, record_type):
        """匯出已完工生產報工統計到檔案"""
        filename = f'completed_equipment_stats_{record_type}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f'已完工生產報工設備使用統計報告\n')
            f.write(f'生成時間: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            # 寫入設備使用統計
            equipment_stats = query.values('equipment').annotate(
                count=Count('id')
            ).order_by('-count')
            
            f.write('設備使用統計:\n')
            for stat in equipment_stats:
                equipment_name = stat['equipment'] or '未指定設備'
                count = stat['count']
                f.write(f'{equipment_name}: {count} 筆\n')
        
        self.stdout.write(f'統計結果已匯出到: {filename}') 