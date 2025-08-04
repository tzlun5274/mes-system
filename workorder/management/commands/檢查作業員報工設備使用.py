#!/usr/bin/env python3
"""
檢查作業員報工使用的設備紀錄
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport
from equip.models import Equipment
from django.db.models import Count


class Command(BaseCommand):
    help = '檢查作業員報工使用的設備紀錄'

    def handle(self, *args, **options):
        self.stdout.write('=== 作業員報工設備使用統計 ===')
        
        # 檢查總記錄數
        total_reports = OperatorSupplementReport.objects.count()
        self.stdout.write(f'總報工記錄數: {total_reports}')
        
        if total_reports == 0:
            self.stdout.write(self.style.WARNING('沒有作業員報工記錄'))
            return
        
        # 檢查有設備記錄的數量
        reports_with_equipment = OperatorSupplementReport.objects.filter(equipment__isnull=False).count()
        reports_without_equipment = OperatorSupplementReport.objects.filter(equipment__isnull=True).count()
        
        self.stdout.write(f'有設備記錄數: {reports_with_equipment}')
        self.stdout.write(f'無設備記錄數: {reports_without_equipment}')
        
        # 計算使用率
        usage_rate = (reports_with_equipment / total_reports) * 100
        self.stdout.write(f'設備使用率: {usage_rate:.2f}%')
        
        # 檢查設備資料
        total_equipment = Equipment.objects.count()
        self.stdout.write(f'\n總設備數: {total_equipment}')
        
        if total_equipment > 0:
            self.stdout.write('前5個設備:')
            equipment_list = Equipment.objects.all()[:5]
            for i, equipment in enumerate(equipment_list, 1):
                self.stdout.write(f'  {i}. {equipment.name} (ID: {equipment.id})')
        
        # 如果有設備記錄，顯示使用情況
        if reports_with_equipment > 0:
            self.stdout.write('\n設備使用情況:')
            equipment_usage = OperatorSupplementReport.objects.filter(
                equipment__isnull=False
            ).values('equipment__name').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            for usage in equipment_usage:
                equipment_name = usage['equipment__name']
                count = usage['count']
                self.stdout.write(f'  {equipment_name}: {count} 筆')
        
        self.stdout.write(self.style.SUCCESS('\n檢查完成')) 