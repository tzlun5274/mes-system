#!/usr/bin/env python3
"""
快速測試設備匯入修復
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport
from equip.models import Equipment
from process.models import Operator, ProcessName
from datetime import date, time


class Command(BaseCommand):
    help = '快速測試設備匯入修復'

    def handle(self, *args, **options):
        self.stdout.write('=== 快速測試設備匯入修復 ===')
        
        # 檢查必要資料
        operators = Operator.objects.all()
        processes = ProcessName.objects.all()
        equipment_list = Equipment.objects.all()
        
        if not operators.exists() or not processes.exists() or not equipment_list.exists():
            self.stdout.write(self.style.ERROR('缺少必要資料'))
            return
        
        operator = operators.first()
        process = processes.first()
        equipment = equipment_list.first()
        
        self.stdout.write(f'使用作業員: {operator.name}')
        self.stdout.write(f'使用工序: {process.name}')
        self.stdout.write(f'使用設備: {equipment.name}')
        
        # 建立測試記錄
        test_report = OperatorSupplementReport.objects.create(
            operator=operator,
            process=process,
            equipment=equipment,  # 這裡設定設備
            work_date=date.today(),
            start_time=time(15, 0),
            end_time=time(19, 0),
            work_quantity=100,
            defect_quantity=2,
            remarks='測試設備匯入修復',
            abnormal_notes='',
            created_by='test_user'
        )
        
        # 檢查設備欄位
        self.stdout.write(f'記錄建立成功，ID: {test_report.id}')
        self.stdout.write(f'設備欄位值: {test_report.equipment.name if test_report.equipment else "無設備"}')
        
        if test_report.equipment:
            self.stdout.write(self.style.SUCCESS('✓ 設備欄位成功寫入'))
        else:
            self.stdout.write(self.style.ERROR('✗ 設備欄位為空'))
        
        # 清理測試記錄
        test_report.delete()
        self.stdout.write('測試記錄已清理')
        
        self.stdout.write(self.style.SUCCESS('=== 測試完成 ===')) 