"""
重置 SMT 現場報工系統的管理命令
用於清除所有 SMT 報工記錄並重置設備狀態
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import date
from workorder.models import SMTProductionReport
from equip.models import Equipment
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '重置 SMT 現場報工系統（清除報工記錄並重置設備狀態）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='確認重置操作（避免誤操作）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='預覽重置操作，但不實際執行',
        )
        parser.add_argument(
            '--reset-equipment',
            action='store_true',
            help='同時重置設備狀態為閒置',
        )

    def handle(self, *args, **options):
        """執行重置操作"""
        
        # 檢查確認參數
        if not options['confirm'] and not options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  警告：此操作將重置 SMT 現場報工系統！\n'
                    '包括：\n'
                    '  • 清除所有 SMT 報工記錄\n'
                    '  • 重置設備狀態（如果使用 --reset-equipment）\n'
                    '請使用 --confirm 參數確認操作，或使用 --dry-run 預覽操作。'
                )
            )
            return

        # 查詢 SMT 設備
        smt_equipment = Equipment.objects.filter(
            name__icontains='SMT'
        ).order_by('name')
        
        if not smt_equipment.exists():
            self.stdout.write(
                self.style.WARNING('⚠️  沒有找到 SMT 設備')
            )
            return

        # 查詢 SMT 報工記錄
        smt_reports = SMTProductionReport.objects.all()
        total_reports = smt_reports.count()

        # 顯示當前狀態
        self.stdout.write(
            self.style.SUCCESS('📊 當前 SMT 系統狀態：')
        )
        
        self.stdout.write(f'  • SMT 設備數量：{smt_equipment.count()}')
        self.stdout.write(f'  • SMT 報工記錄：{total_reports} 筆')
        
        # 顯示設備狀態
        self.stdout.write('\n🔧 設備狀態：')
        for equipment in smt_equipment:
            today_reports = SMTProductionReport.objects.filter(
                equipment=equipment,
                report_time__date=date.today()
            ).count()
            
            status_icon = "🟢" if equipment.status == 'running' else "🟡" if equipment.status == 'idle' else "🔴"
            
            self.stdout.write(
                f'  {status_icon} {equipment.name}: '
                f'{equipment.get_status_display()}, '
                f'今日報工 {today_reports} 筆'
            )

        # 如果是預覽模式，只顯示統計不執行
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'\n🔍 預覽模式：\n'
                    f'  • 將清除 {total_reports} 筆 SMT 報工記錄\n'
                )
            )
            
            if options['reset_equipment']:
                self.stdout.write(
                    self.style.WARNING(
                        f'  • 將重置所有 SMT 設備狀態為閒置\n'
                    )
                )
            
            self.stdout.write(
                self.style.WARNING(
                    '使用 --confirm 參數實際執行重置操作'
                )
            )
            return

        # 確認重置
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR(
                    '\n❌ 請使用 --confirm 參數確認重置操作'
                )
            )
            return

        # 執行重置操作
        try:
            # 1. 清除 SMT 報工記錄
            if total_reports > 0:
                deleted_count = smt_reports.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ 成功清除 {deleted_count} 筆 SMT 報工記錄'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ 沒有 SMT 報工記錄需要清除')
                )

            # 2. 重置設備狀態
            if options['reset_equipment']:
                updated_count = 0
                for equipment in smt_equipment:
                    if equipment.status != 'idle':
                        equipment.status = 'idle'
                        equipment.save()
                        updated_count += 1
                
                if updated_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ 成功重置 {updated_count} 台設備狀態為閒置'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('✅ 所有設備狀態已經是閒置')
                    )

            # 記錄操作日誌
            logger.info(
                f'管理員重置 SMT 系統: 清除 {total_reports} 筆報工記錄, '
                f'重置設備狀態: {options["reset_equipment"]}'
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ 重置失敗：{str(e)}')
            )
            logger.error(f'重置 SMT 系統失敗: {str(e)}')
            raise CommandError(f'重置失敗：{str(e)}')

        # 顯示重置後的狀態
        self.stdout.write('\n📊 重置後狀態：')
        
        # 重新查詢設備狀態
        smt_equipment = Equipment.objects.filter(
            name__icontains='SMT'
        ).order_by('name')
        
        remaining_reports = SMTProductionReport.objects.count()
        self.stdout.write(f'  • 剩餘 SMT 報工記錄：{remaining_reports} 筆')
        
        self.stdout.write('\n🔧 設備狀態：')
        for equipment in smt_equipment:
            today_reports = SMTProductionReport.objects.filter(
                equipment=equipment,
                report_time__date=date.today()
            ).count()
            
            status_icon = "🟢" if equipment.status == 'running' else "🟡" if equipment.status == 'idle' else "🔴"
            
            self.stdout.write(
                f'  {status_icon} {equipment.name}: '
                f'{equipment.get_status_display()}, '
                f'今日報工 {today_reports} 筆'
            )

        self.stdout.write(
            self.style.SUCCESS('\n🎉 SMT 現場報工系統重置完成！')
        )
        
        # 顯示後續操作建議
        self.stdout.write(
            self.style.WARNING(
                '\n💡 建議後續操作：\n'
                '  1. 檢查設備狀態是否正確\n'
                '  2. 重新開始 SMT 現場報工\n'
                '  3. 確認即時模式正常運作'
            )
        ) 