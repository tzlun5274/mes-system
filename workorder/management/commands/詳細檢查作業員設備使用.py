#!/usr/bin/env python3
"""
詳細檢查作業員報工使用的設備紀錄比數
此命令會提供更詳細的統計資訊，包含設備資料和作業員資料
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
from workorder.models import WorkOrderProductionDetail, CompletedProductionReport
from equip.models import Equipment
from process.models import Operator
from django.db.models import Count, Q
from collections import defaultdict
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '詳細檢查作業員報工使用的設備紀錄比數'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-equipment',
            action='store_true',
            help='顯示設備清單',
        )
        parser.add_argument(
            '--show-operators',
            action='store_true',
            help='顯示作業員清單',
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='匯出詳細統計結果到檔案',
        )

    def handle(self, *args, **options):
        show_equipment = options['show_equipment']
        show_operators = options['show_operators']
        export = options['export']
        
        self.stdout.write(
            self.style.SUCCESS('開始詳細檢查作業員報工使用的設備紀錄比數...')
        )
        
        try:
            # 檢查設備資料
            self._check_equipment_data(show_equipment)
            
            # 檢查作業員資料
            self._check_operator_data(show_operators)
            
            # 檢查作業員補登報工記錄
            self._check_operator_supplement_reports()
            
            # 檢查SMT報工記錄
            self._check_smt_reports()
            
            # 檢查生產中工單明細
            self._check_production_details()
            
            # 檢查已完工報工記錄
            self._check_completed_reports()
            
            # 顯示總體統計
            self._show_overall_statistics()
            
            if export:
                self._export_detailed_report()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'檢查過程中發生錯誤: {str(e)}')
            )
            logger.error(f'詳細檢查作業員設備使用比數失敗: {str(e)}')

    def _check_equipment_data(self, show_equipment):
        """檢查設備資料"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('設備資料統計')
        self.stdout.write('='*60)
        
        total_equipment = Equipment.objects.count()
        self.stdout.write(f'設備總數: {total_equipment}')
        
        if total_equipment > 0:
            # 按狀態統計
            equipment_by_status = Equipment.objects.values('status').annotate(
                count=Count('id')
            ).order_by('-count')
            
            self.stdout.write(f'\n設備狀態分布:')
            for stat in equipment_by_status:
                status = stat['status'] or '未設定'
                count = stat['count']
                self.stdout.write(f'  {status}: {count} 台')
            
            # 按產線統計
            equipment_by_line = Equipment.objects.values('production_line__line_name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            self.stdout.write(f'\n設備產線分布:')
            for stat in equipment_by_line:
                line_name = stat['production_line__line_name'] or '未分配產線'
                count = stat['count']
                self.stdout.write(f'  {line_name}: {count} 台')
            
            if show_equipment:
                self.stdout.write(f'\n設備清單:')
                equipments = Equipment.objects.all().order_by('name')
                for i, equipment in enumerate(equipments, 1):
                    line_name = equipment.production_line.line_name if equipment.production_line else '未分配產線'
                    self.stdout.write(f'  {i:2d}. {equipment.name} ({equipment.model}) - {line_name} - {equipment.get_status_display()}')
        else:
            self.stdout.write('⚠️  沒有找到任何設備資料')

    def _check_operator_data(self, show_operators):
        """檢查作業員資料"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('作業員資料統計')
        self.stdout.write('='*60)
        
        total_operators = Operator.objects.count()
        self.stdout.write(f'作業員總數: {total_operators}')
        
        if total_operators > 0:
            # 按產線統計
            operators_by_line = Operator.objects.values('production_line__line_name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            self.stdout.write(f'\n作業員產線分布:')
            for stat in operators_by_line:
                line_name = stat['production_line__line_name'] or '未分配產線'
                count = stat['count']
                self.stdout.write(f'  {line_name}: {count} 人')
            
            if show_operators:
                self.stdout.write(f'\n作業員清單:')
                operators = Operator.objects.all().order_by('name')
                for i, operator in enumerate(operators, 1):
                    line_name = operator.production_line.line_name if operator.production_line else '未分配產線'
                    self.stdout.write(f'  {i:2d}. {operator.name} - {line_name}')
        else:
            self.stdout.write('⚠️  沒有找到任何作業員資料')

    def _check_operator_supplement_reports(self):
        """檢查作業員補登報工記錄"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('作業員補登報工記錄統計')
        self.stdout.write('='*60)
        
        total_reports = OperatorSupplementReport.objects.count()
        self.stdout.write(f'總記錄數: {total_reports}')
        
        if total_reports > 0:
            # 有設備的記錄
            reports_with_equipment = OperatorSupplementReport.objects.filter(
                equipment__isnull=False
            ).count()
            
            # 沒有設備的記錄
            reports_without_equipment = total_reports - reports_with_equipment
            
            self.stdout.write(f'有設備記錄: {reports_with_equipment} 筆 ({reports_with_equipment/total_reports*100:.1f}%)')
            self.stdout.write(f'無設備記錄: {reports_without_equipment} 筆 ({reports_without_equipment/total_reports*100:.1f}%)')
            
            # 按作業員統計
            operator_stats = OperatorSupplementReport.objects.values('operator__name').annotate(
                count=Count('id'),
                with_equipment=Count('id', filter=Q(equipment__isnull=False))
            ).order_by('-count')[:10]
            
            self.stdout.write(f'\n作業員報工統計 (前10名):')
            for stat in operator_stats:
                operator_name = stat['operator__name'] or '未指定'
                count = stat['count']
                with_equipment = stat['with_equipment']
                without_equipment = count - with_equipment
                self.stdout.write(f'  {operator_name}: {count} 筆 (有設備: {with_equipment}, 無設備: {without_equipment})')
        else:
            self.stdout.write('⚠️  沒有找到任何作業員補登報工記錄')

    def _check_smt_reports(self):
        """檢查SMT報工記錄"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('SMT報工記錄統計')
        self.stdout.write('='*60)
        
        total_reports = SMTProductionReport.objects.count()
        self.stdout.write(f'總記錄數: {total_reports}')
        
        if total_reports > 0:
            # 有設備的記錄
            reports_with_equipment = SMTProductionReport.objects.filter(
                equipment__isnull=False
            ).count()
            
            # 沒有設備的記錄
            reports_without_equipment = total_reports - reports_with_equipment
            
            self.stdout.write(f'有設備記錄: {reports_with_equipment} 筆 ({reports_with_equipment/total_reports*100:.1f}%)')
            self.stdout.write(f'無設備記錄: {reports_without_equipment} 筆 ({reports_without_equipment/total_reports*100:.1f}%)')
            
            # 按設備統計
            equipment_stats = SMTProductionReport.objects.values('equipment__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            if equipment_stats:
                self.stdout.write(f'\nSMT設備使用統計:')
                for stat in equipment_stats:
                    equipment_name = stat['equipment__name'] or '未指定設備'
                    count = stat['count']
                    self.stdout.write(f'  {equipment_name}: {count} 筆')
        else:
            self.stdout.write('⚠️  沒有找到任何SMT報工記錄')

    def _check_production_details(self):
        """檢查生產中工單明細"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('生產中工單明細統計')
        self.stdout.write('='*60)
        
        total_details = WorkOrderProductionDetail.objects.count()
        self.stdout.write(f'總記錄數: {total_details}')
        
        if total_details > 0:
            # 按報工來源統計
            source_stats = WorkOrderProductionDetail.objects.values('report_source').annotate(
                count=Count('id')
            ).order_by('-count')
            
            self.stdout.write(f'\n報工來源分布:')
            for stat in source_stats:
                source = stat['report_source'] or '未指定'
                count = stat['count']
                self.stdout.write(f'  {source}: {count} 筆')
            
            # 有設備的記錄
            details_with_equipment = WorkOrderProductionDetail.objects.filter(
                equipment__isnull=False
            ).exclude(equipment='').count()
            
            self.stdout.write(f'\n有設備記錄: {details_with_equipment} 筆 ({details_with_equipment/total_details*100:.1f}%)')
            self.stdout.write(f'無設備記錄: {total_details - details_with_equipment} 筆 ({(total_details - details_with_equipment)/total_details*100:.1f}%)')
        else:
            self.stdout.write('⚠️  沒有找到任何生產中工單明細記錄')

    def _check_completed_reports(self):
        """檢查已完工報工記錄"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('已完工報工記錄統計')
        self.stdout.write('='*60)
        
        total_reports = CompletedProductionReport.objects.count()
        self.stdout.write(f'總記錄數: {total_reports}')
        
        if total_reports > 0:
            # 按報工類型統計
            type_stats = CompletedProductionReport.objects.values('report_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            self.stdout.write(f'\n報工類型分布:')
            for stat in type_stats:
                report_type = stat['report_type'] or '未指定'
                count = stat['count']
                self.stdout.write(f'  {report_type}: {count} 筆')
            
            # 有設備的記錄
            reports_with_equipment = CompletedProductionReport.objects.filter(
                equipment__isnull=False
            ).exclude(equipment='').count()
            
            self.stdout.write(f'\n有設備記錄: {reports_with_equipment} 筆 ({reports_with_equipment/total_reports*100:.1f}%)')
            self.stdout.write(f'無設備記錄: {total_reports - reports_with_equipment} 筆 ({(total_reports - reports_with_equipment)/total_reports*100:.1f}%)')
        else:
            self.stdout.write('⚠️  沒有找到任何已完工報工記錄')

    def _show_overall_statistics(self):
        """顯示總體統計"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('總體統計摘要')
        self.stdout.write('='*60)
        
        # 各類型記錄總數
        operator_supplement_total = OperatorSupplementReport.objects.count()
        smt_total = SMTProductionReport.objects.count()
        production_detail_total = WorkOrderProductionDetail.objects.count()
        completed_total = CompletedProductionReport.objects.count()
        
        self.stdout.write(f'記錄總數統計:')
        self.stdout.write(f'  作業員補登報工: {operator_supplement_total} 筆')
        self.stdout.write(f'  SMT報工: {smt_total} 筆')
        self.stdout.write(f'  生產中工單明細: {production_detail_total} 筆')
        self.stdout.write(f'  已完工報工: {completed_total} 筆')
        
        # 設備使用比例
        operator_supplement_with_equipment = OperatorSupplementReport.objects.filter(
            equipment__isnull=False
        ).count()
        
        smt_with_equipment = SMTProductionReport.objects.filter(
            equipment__isnull=False
        ).count()
        
        production_detail_with_equipment = WorkOrderProductionDetail.objects.filter(
            equipment__isnull=False
        ).exclude(equipment='').count()
        
        completed_with_equipment = CompletedProductionReport.objects.filter(
            equipment__isnull=False
        ).exclude(equipment='').count()
        
        self.stdout.write(f'\n設備記錄比例:')
        if operator_supplement_total > 0:
            percentage = operator_supplement_with_equipment / operator_supplement_total * 100
            self.stdout.write(f'  作業員補登報工: {operator_supplement_with_equipment}/{operator_supplement_total} ({percentage:.1f}%)')
        
        if smt_total > 0:
            percentage = smt_with_equipment / smt_total * 100
            self.stdout.write(f'  SMT報工: {smt_with_equipment}/{smt_total} ({percentage:.1f}%)')
        
        if production_detail_total > 0:
            percentage = production_detail_with_equipment / production_detail_total * 100
            self.stdout.write(f'  生產中工單明細: {production_detail_with_equipment}/{production_detail_total} ({percentage:.1f}%)')
        
        if completed_total > 0:
            percentage = completed_with_equipment / completed_total * 100
            self.stdout.write(f'  已完工報工: {completed_with_equipment}/{completed_total} ({percentage:.1f}%)')
        
        # 總結
        total_reports = operator_supplement_total + smt_total + production_detail_total + completed_total
        total_with_equipment = operator_supplement_with_equipment + smt_with_equipment + production_detail_with_equipment + completed_with_equipment
        
        if total_reports > 0:
            overall_percentage = total_with_equipment / total_reports * 100
            self.stdout.write(f'\n整體設備記錄比例: {total_with_equipment}/{total_reports} ({overall_percentage:.1f}%)')
            
            if overall_percentage < 50:
                self.stdout.write(self.style.WARNING('⚠️  設備記錄比例偏低，建議檢查報工流程是否正確記錄設備資訊'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ 設備記錄比例良好'))

    def _export_detailed_report(self):
        """匯出詳細報告"""
        filename = f'operator_equipment_detailed_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('作業員設備使用詳細統計報告\n')
            f.write(f'生成時間: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            
            # 設備統計
            f.write('設備統計:\n')
            f.write(f'設備總數: {Equipment.objects.count()}\n')
            equipment_by_type = Equipment.objects.values('equipment_type').annotate(count=Count('id'))
            for stat in equipment_by_type:
                equipment_type = stat['equipment_type'] or '未分類'
                count = stat['count']
                f.write(f'{equipment_type}: {count} 台\n')
            
            # 作業員統計
            f.write('\n作業員統計:\n')
            f.write(f'作業員總數: {Operator.objects.count()}\n')
            
            # 報工記錄統計
            f.write('\n報工記錄統計:\n')
            operator_supplement_total = OperatorSupplementReport.objects.count()
            smt_total = SMTProductionReport.objects.count()
            production_detail_total = WorkOrderProductionDetail.objects.count()
            completed_total = CompletedProductionReport.objects.count()
            
            f.write(f'作業員補登報工: {operator_supplement_total} 筆\n')
            f.write(f'SMT報工: {smt_total} 筆\n')
            f.write(f'生產中工單明細: {production_detail_total} 筆\n')
            f.write(f'已完工報工: {completed_total} 筆\n')
        
        self.stdout.write(f'詳細報告已匯出到: {filename}') 