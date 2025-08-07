"""
更新SMT報工記錄的作業員名稱
將現有的SMT報工記錄更新為使用新的作業員名稱格式
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import SMTProductionReport
from workorder.services.smt_operator_service import SMTOperatorService


class Command(BaseCommand):
    help = '更新SMT報工記錄的作業員名稱，使用新的格式'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只顯示會更新的記錄，不實際執行更新',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS('開始更新SMT報工記錄的作業員名稱...')
        )
        
        # 取得所有SMT報工記錄
        smt_reports = SMTProductionReport.objects.filter(
            equipment__name__icontains='SMT'
        ).select_related('equipment')
        
        updated_count = 0
        total_count = smt_reports.count()
        
        self.stdout.write(f'找到 {total_count} 筆SMT報工記錄')
        
        for report in smt_reports:
            if not report.equipment:
                continue
                
            # 計算新的作業員名稱
            new_operator_name = SMTOperatorService.get_smt_equipment_operator_name(
                report.equipment.name
            )
            
            # 檢查是否需要更新
            if (report.operator != new_operator_name or 
                not report.equipment_operator_name):
                
                if dry_run:
                    self.stdout.write(
                        f'會更新記錄 ID {report.id}: '
                        f'設備={report.equipment.name}, '
                        f'原作業員="{report.operator}", '
                        f'新作業員="{new_operator_name}"'
                    )
                else:
                    # 實際更新
                    report.operator = new_operator_name
                    report.equipment_operator_name = new_operator_name
                    report.save()
                    
                    self.stdout.write(
                        f'已更新記錄 ID {report.id}: '
                        f'設備={report.equipment.name}, '
                        f'作業員="{new_operator_name}"'
                    )
                
                updated_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'乾跑模式：會更新 {updated_count} 筆記錄'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'完成！已更新 {updated_count} 筆SMT報工記錄'
                )
            )
        
        # 顯示統計資訊
        stats = SMTOperatorService.get_operator_statistics()
        self.stdout.write('\n統計資訊:')
        self.stdout.write(f'- 真實作業員: {stats["real_operators"]} 位')
        self.stdout.write(f'- SMT設備: {stats["smt_equipment"]} 台')
        self.stdout.write(f'- SMT報工記錄: {stats["smt_reports"]} 筆')
        self.stdout.write(f'- 總作業員數: {stats["total_operators"]} 位') 