#!/usr/bin/env python3
"""
同步報表排程到 Celery Beat 的管理命令
"""

from django.core.management.base import BaseCommand
from reporting.report_schedule_sync_service import ReportScheduleSyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '同步所有報表排程到 Celery Beat'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='強制重新同步所有排程（包括停用的）',
        )

    def handle(self, *args, **options):
        """
        執行同步命令
        """
        self.stdout.write("=== 開始同步報表排程到 Celery Beat ===")
        
        try:
            # 執行同步
            result = ReportScheduleSyncService.sync_report_schedules_to_celery()
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {result['message']}")
                )
                
                # 顯示同步的排程詳情
                from reporting.models import ReportSchedule
                from django_celery_beat.models import PeriodicTask
                
                active_schedules = ReportSchedule.objects.filter(status='active')
                self.stdout.write("\n📋 已同步的排程:")
                for schedule in active_schedules:
                    task = PeriodicTask.objects.filter(name=f'report_schedule_{schedule.id}').first()
                    if task:
                        self.stdout.write(f"  • {schedule.name} ({schedule.report_type}) - {schedule.schedule_time} - ✅ 已同步")
                    else:
                        self.stdout.write(f"  • {schedule.name} ({schedule.report_type}) - {schedule.schedule_time} - ❌ 同步失敗")
                
                # 顯示停用的排程
                inactive_schedules = ReportSchedule.objects.filter(status='inactive')
                if inactive_schedules.exists():
                    self.stdout.write("\n⏸️  停用的排程（未同步）:")
                    for schedule in inactive_schedules:
                        self.stdout.write(f"  • {schedule.name} ({schedule.report_type}) - {schedule.schedule_time}")
                
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ 同步失敗: {result.get('error', '未知錯誤')}")
                )
                
        except Exception as e:
            logger.error(f"同步報表排程時發生錯誤: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"❌ 同步時發生錯誤: {str(e)}")
            )
        
        self.stdout.write("\n=== 同步完成 ===")
