#!/usr/bin/env python3
"""
實際測試設備匯入功能
真正執行匯入並檢查設備資料是否正確寫入資料表
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport
from equip.models import Equipment
from process.models import Operator, ProcessName
from workorder.models import WorkOrder
from datetime import date, time
import pandas as pd
import os


class Command(BaseCommand):
    help = '實際測試設備匯入功能，真正執行匯入並檢查結果'

    def handle(self, *args, **options):
        self.stdout.write('=== 實際測試設備匯入功能 ===')
        
        # 1. 檢查現有資料
        self.stdout.write('\n1. 檢查匯入前的資料...')
        before_count = OperatorSupplementReport.objects.count()
        before_with_equipment = OperatorSupplementReport.objects.filter(equipment__isnull=False).count()
        self.stdout.write(f'匯入前總記錄: {before_count}')
        self.stdout.write(f'匯入前有設備記錄: {before_with_equipment}')
        
        # 2. 檢查必要資料
        self.stdout.write('\n2. 檢查必要資料...')
        operators = Operator.objects.all()
        processes = ProcessName.objects.all()
        equipment_list = Equipment.objects.all()
        
        if not operators.exists():
            self.stdout.write(self.style.ERROR('錯誤: 沒有作業員資料'))
            return
        
        if not processes.exists():
            self.stdout.write(self.style.ERROR('錯誤: 沒有工序資料'))
            return
        
        if not equipment_list.exists():
            self.stdout.write(self.style.ERROR('錯誤: 沒有設備資料'))
            return
        
        operator = operators.first()
        process = processes.first()
        equipment = equipment_list.first()
        
        self.stdout.write(f'使用作業員: {operator.name}')
        self.stdout.write(f'使用工序: {process.name}')
        self.stdout.write(f'使用設備: {equipment.name} (ID: {equipment.id})')
        
        # 3. 建立測試資料
        self.stdout.write('\n3. 建立測試資料...')
        
        # 建立唯一的測試資料，避免與現有資料衝突
        test_date = date.today()
        test_start_time = time(14, 0)  # 14:00
        test_end_time = time(18, 0)    # 18:00
        
        test_data = [
            {
                '作業員名稱': operator.name,
                '公司代號': '01',
                '報工日期': test_date.strftime('%Y-%m-%d'),
                '開始時間': test_start_time.strftime('%H:%M'),
                '結束時間': test_end_time.strftime('%H:%M'),
                '工單號': 'TEST-EQUIPMENT-001',
                '產品編號': 'TEST-PROD-EQUIPMENT',
                '工序名稱': process.name,
                '設備名稱': equipment.name,  # 確保有設備名稱
                '報工數量': 150,
                '不良品數量': 3,
                '備註': '測試設備匯入功能',
                '異常紀錄': '',
            }
        ]
        
        # 建立DataFrame
        df = pd.DataFrame(test_data)
        
        # 儲存測試檔案
        test_file_path = '/tmp/actual_test_equipment_import.xlsx'
        df.to_excel(test_file_path, index=False)
        
        self.stdout.write(f'測試檔案已建立: {test_file_path}')
        self.stdout.write(f'測試資料:')
        for key, value in test_data[0].items():
            self.stdout.write(f'  {key}: {value}')
        
        # 4. 實際執行匯入邏輯
        self.stdout.write('\n4. 實際執行匯入邏輯...')
        
        success_count = 0
        error_count = 0
        skip_count = 0
        errors = []
        skips = []
        
        for index, row in df.iterrows():
            try:
                self.stdout.write(f'處理第 {index+1} 行...')
                
                # 檢查設備名稱欄位
                equipment_found = None
                if '設備名稱' in df.columns and pd.notna(row['設備名稱']):
                    equipment_name = str(row['設備名稱']).strip()
                    self.stdout.write(f'  設備名稱: "{equipment_name}"')
                    
                    if equipment_name:
                        # 查找設備
                        try:
                            equipment_found = Equipment.objects.get(name=equipment_name)
                            self.stdout.write(f'  找到設備: {equipment_found.name} (ID: {equipment_found.id})')
                        except Equipment.DoesNotExist:
                            try:
                                equipment_found = Equipment.objects.get(name__iexact=equipment_name)
                                self.stdout.write(f'  大小寫不匹配: "{equipment_name}" -> "{equipment_found.name}"')
                                skips.append(f'第 {index+1} 行：設備名稱大小寫不匹配 "{equipment_name}" -> "{equipment_found.name}"')
                            except Equipment.DoesNotExist:
                                self.stdout.write(f'  找不到設備: "{equipment_name}"')
                                errors.append(f'第 {index+1} 行：找不到設備 "{equipment_name}"')
                                error_count += 1
                                continue
                    else:
                        self.stdout.write(f'  設備名稱為空')
                else:
                    self.stdout.write(f'  沒有設備名稱欄位或欄位為空')
                
                # 檢查是否已存在相同記錄
                existing_report = OperatorSupplementReport.objects.filter(
                    operator=operator,
                    process=process,
                    work_date=test_date,
                    start_time=test_start_time,
                    end_time=test_end_time
                ).first()
                
                if existing_report:
                    self.stdout.write(f'  已存在相同記錄，跳過')
                    skips.append(f'第 {index+1} 行：已存在相同記錄，跳過匯入')
                    skip_count += 1
                    continue
                
                # 建立報工記錄
                report_data = {
                    'operator': operator,
                    'process': process,
                    'equipment': equipment_found,  # 這裡是關鍵！
                    'work_date': test_date,
                    'start_time': test_start_time,
                    'end_time': test_end_time,
                    'work_quantity': row['報工數量'],
                    'defect_quantity': row['不良品數量'],
                    'remarks': row['備註'],
                    'abnormal_notes': row['異常紀錄'],
                    'created_by': 'test_user'
                }
                
                self.stdout.write(f'  準備建立記錄:')
                self.stdout.write(f'    作業員: {report_data["operator"].name}')
                self.stdout.write(f'    工序: {report_data["process"].name}')
                self.stdout.write(f'    設備: {report_data["equipment"].name if report_data["equipment"] else "無"}')
                self.stdout.write(f'    數量: {report_data["work_quantity"]}')
                
                # 實際建立記錄
                report = OperatorSupplementReport.objects.create(**report_data)
                
                # 自動計算工時
                report.calculate_work_hours()
                report.save()
                
                self.stdout.write(f'  記錄建立成功，ID: {report.id}')
                self.stdout.write(f'  設備欄位值: {report.equipment.name if report.equipment else "無"}')
                
                success_count += 1
                
            except Exception as e:
                self.stdout.write(f'  錯誤: {str(e)}')
                errors.append(f'第 {index+1} 行：處理失敗 - {str(e)}')
                error_count += 1
        
        # 5. 檢查匯入結果
        self.stdout.write('\n5. 檢查匯入結果...')
        
        after_count = OperatorSupplementReport.objects.count()
        after_with_equipment = OperatorSupplementReport.objects.filter(equipment__isnull=False).count()
        
        self.stdout.write(f'匯入後總記錄: {after_count}')
        self.stdout.write(f'匯入後有設備記錄: {after_with_equipment}')
        self.stdout.write(f'新增記錄數: {after_count - before_count}')
        self.stdout.write(f'新增有設備記錄數: {after_with_equipment - before_with_equipment}')
        
        # 檢查剛建立的記錄
        if success_count > 0:
            latest_report = OperatorSupplementReport.objects.filter(
                operator=operator,
                process=process,
                work_date=test_date,
                start_time=test_start_time,
                end_time=test_end_time
            ).first()
            
            if latest_report:
                self.stdout.write(f'\n最新建立的記錄:')
                self.stdout.write(f'  ID: {latest_report.id}')
                self.stdout.write(f'  作業員: {latest_report.operator.name}')
                self.stdout.write(f'  工序: {latest_report.process.name}')
                self.stdout.write(f'  設備: {latest_report.equipment.name if latest_report.equipment else "無"}')
                self.stdout.write(f'  數量: {latest_report.work_quantity}')
                self.stdout.write(f'  建立時間: {latest_report.created_at}')
                
                # 檢查設備欄位是否真的寫入了
                if latest_report.equipment:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ 設備欄位成功寫入: {latest_report.equipment.name}'))
                else:
                    self.stdout.write(self.style.ERROR(f'  ✗ 設備欄位為空'))
        
        # 6. 顯示匯入統計
        self.stdout.write(f'\n匯入統計:')
        self.stdout.write(f'  成功: {success_count} 筆')
        self.stdout.write(f'  錯誤: {error_count} 筆')
        self.stdout.write(f'  跳過: {skip_count} 筆')
        
        if errors:
            self.stdout.write(f'\n錯誤詳情:')
            for error in errors:
                self.stdout.write(f'  {error}')
        
        if skips:
            self.stdout.write(f'\n跳過詳情:')
            for skip in skips:
                self.stdout.write(f'  {skip}')
        
        # 7. 清理測試檔案
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            self.stdout.write('\n測試檔案已清理')
        
        self.stdout.write(self.style.SUCCESS('\n=== 測試完成 ===')) 