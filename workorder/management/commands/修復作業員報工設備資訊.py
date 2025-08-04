#!/usr/bin/env python3
"""
修復作業員報工設備資訊
此命令會修復作業員報工記錄中缺失的設備資訊
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport
from equip.models import Equipment
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '修復作業員報工記錄中缺失的設備資訊'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='乾跑模式，只顯示會更新的記錄數量，不實際更新',
        )
        parser.add_argument(
            '--operator',
            type=str,
            help='指定特定作業員進行修復',
        )
        parser.add_argument(
            '--date-range',
            type=str,
            help='指定日期範圍 (格式: YYYY-MM-DD,YYYY-MM-DD)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        operator_name = options['operator']
        date_range = options['date_range']
        
        self.stdout.write(
            self.style.SUCCESS('開始修復作業員報工設備資訊...')
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== 乾跑模式 ==='))
        
        try:
            # 檢查設備資料
            self._check_equipment_data()
            
            # 修復作業員報工記錄的設備資訊
            self._fix_operator_reports_equipment(operator_name, date_range, dry_run)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'修復過程中發生錯誤: {str(e)}')
            )
            logger.error(f'修復作業員報工設備資訊失敗: {str(e)}')

    def _check_equipment_data(self):
        """檢查設備資料"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('設備資料檢查')
        self.stdout.write('='*60)
        
        total_equipment = Equipment.objects.count()
        self.stdout.write(f'設備總數: {total_equipment}')
        
        if total_equipment > 0:
            # 顯示一些設備範例
            equipments = Equipment.objects.all()[:10]
            self.stdout.write(f'\n設備範例 (前10台):')
            for i, equipment in enumerate(equipments, 1):
                line_name = equipment.production_line.line_name if equipment.production_line else '未分配產線'
                self.stdout.write(f'  {i:2d}. {equipment.name} ({equipment.model}) - {line_name}')
        else:
            self.stdout.write('⚠️  沒有找到任何設備資料')

    def _fix_operator_reports_equipment(self, operator_name, date_range, dry_run):
        """修復作業員報工記錄的設備資訊"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('修復作業員報工記錄設備資訊')
        self.stdout.write('='*60)
        
        # 建立查詢條件
        query = OperatorSupplementReport.objects.filter(equipment__isnull=True)
        
        if operator_name:
            query = query.filter(operator__name__icontains=operator_name)
            self.stdout.write(f'篩選作業員: {operator_name}')
        
        if date_range:
            start_date, end_date = date_range.split(',')
            query = query.filter(work_date__range=[start_date, end_date])
            self.stdout.write(f'日期範圍: {start_date} 到 {end_date}')
        
        # 統計需要修復的記錄
        total_reports = query.count()
        self.stdout.write(f'需要修復的記錄數: {total_reports}')
        
        if total_reports == 0:
            self.stdout.write('沒有找到需要修復的記錄')
            return
        
        # 建立設備名稱對應表
        equipment_map = {}
        equipments = Equipment.objects.all()
        for equipment in equipments:
            equipment_map[equipment.name] = equipment
            # 也建立不區分大小寫的對應
            equipment_map[equipment.name.lower()] = equipment
            equipment_map[equipment.name.upper()] = equipment
        
        self.stdout.write(f'設備對應表建立完成，共 {len(equipment_map)} 個對應')
        
        # 修復記錄
        fixed_count = 0
        error_count = 0
        not_found_count = 0
        
        for report in query:
            try:
                # 從備註中尋找設備資訊
                equipment_name = self._extract_equipment_from_remarks(report.remarks)
                
                if not equipment_name:
                    # 如果備註中沒有，嘗試從工序名稱推測
                    equipment_name = self._guess_equipment_from_process(report.process.name if report.process else '')
                
                if equipment_name and equipment_name in equipment_map:
                    equipment = equipment_map[equipment_name]
                    
                    if not dry_run:
                        with transaction.atomic():
                            report.equipment = equipment
                            report.save(update_fields=['equipment'])
                    
                    self.stdout.write(f'修復記錄 ID {report.id}: {report.operator.name} - {equipment_name}')
                    fixed_count += 1
                else:
                    if equipment_name:
                        self.stdout.write(f'找不到設備 "{equipment_name}" (記錄 ID: {report.id})')
                        not_found_count += 1
                    else:
                        not_found_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'修復記錄 ID {report.id} 時發生錯誤: {str(e)}')
                )
        
        # 顯示結果
        self.stdout.write(f'\n修復結果:')
        self.stdout.write(f'  成功修復: {fixed_count} 筆')
        self.stdout.write(f'  找不到設備: {not_found_count} 筆')
        self.stdout.write(f'  修復失敗: {error_count} 筆')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('乾跑模式完成，未實際更新資料'))
        else:
            self.stdout.write(self.style.SUCCESS('設備資訊修復完成！'))

    def _extract_equipment_from_remarks(self, remarks):
        """從備註中提取設備名稱"""
        if not remarks:
            return None
        
        # 常見的設備關鍵字
        equipment_keywords = [
            'CT101-01', 'CT101-02', 'CT201', 'CT301', 'CT401', 'CT602-1', 'CT602-2', 'CT602-3',
            'AOI-1', 'AOI-2', 'AOI-3', 'AOI檢測機-01', 'AOI檢測機-02',
            'ATE-2S-20', 'ATE40MB-1', 'ATE40MB-2',
            '燒碼機-1', '燒碼機-2', '燒錄機-01', '燒錄機-02',
            '包裝機-01', '包裝機-02',
            '目檢台-01', '目檢台-02',
            '組合機-01', '組合機-02',
            '補錫機-01', '補錫機-02',
            '電測機-01', '電測機-02', '電測機-03',
            '自動焊錫機', '自動點膠機-1', '自動點膠機-2',
            '熱壓熔錫焊接機', '熱風循環烘箱', 'UV燈', 'V-Cut 裁板機',
            'Hot Bar機-01', 'Hot Bar機-02',
            'MEQ-C-APE-GPS1-01', 'TIN-C-CT201-01', 'TIN-C-GPS5-01'
        ]
        
        for keyword in equipment_keywords:
            if keyword in remarks:
                return keyword
        
        return None

    def _guess_equipment_from_process(self, process_name):
        """根據工序名稱推測設備"""
        if not process_name:
            return None
        
        # 工序到設備的對應關係
        process_equipment_map = {
            '碼別驗證': ['CT101-01', 'CT101-02'],
            '燒碼': ['燒碼機-1', '燒碼機-2'],
            '燒錄': ['燒錄機-01', '燒錄機-02'],
            'AOI 檢測': ['AOI-1', 'AOI-2', 'AOI-3'],
            '電測': ['CT101-01', 'CT101-02', 'CT201', 'CT301', 'CT401'],
            '二次電測': ['CT602-1', 'CT602-2', 'CT602-3'],
            '包裝': ['包裝機-01', '包裝機-02'],
            '目檢': ['目檢台-01', '目檢台-02'],
            '組合': ['組合機-01', '組合機-02'],
            '補錫': ['補錫機-01', '補錫機-02'],
            '自動焊錫': ['自動焊錫機'],
            '自動點膠': ['自動點膠機-1', '自動點膠機-2'],
            '熱壓熔錫': ['熱壓熔錫焊接機'],
            '烘烤': ['熱風循環烘箱'],
            'UV固化': ['UV燈'],
            '裁板': ['V-Cut 裁板機'],
            'Hot Bar': ['Hot Bar機-01', 'Hot Bar機-02']
        }
        
        for process_keyword, equipment_list in process_equipment_map.items():
            if process_keyword in process_name:
                # 返回第一個可用的設備
                for equipment_name in equipment_list:
                    if Equipment.objects.filter(name=equipment_name).exists():
                        return equipment_name
        
        return None 