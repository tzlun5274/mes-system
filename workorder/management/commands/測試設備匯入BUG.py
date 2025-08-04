#!/usr/bin/env python3
"""
測試和修復設備匯入BUG
"""

from django.core.management.base import BaseCommand
from workorder.workorder_reporting.models import OperatorSupplementReport
from equip.models import Equipment
from process.models import Operator, ProcessName
from workorder.models import WorkOrder
from datetime import date
import pandas as pd
import os


class Command(BaseCommand):
    help = '測試和修復設備匯入BUG'

    def handle(self, *args, **options):
        self.stdout.write('=== 測試設備匯入BUG ===')
        
        # 1. 檢查現有資料
        self.stdout.write('\n1. 檢查現有資料...')
        total_reports = OperatorSupplementReport.objects.count()
        reports_with_equipment = OperatorSupplementReport.objects.filter(equipment__isnull=False).count()
        self.stdout.write(f'總報工記錄: {total_reports}')
        self.stdout.write(f'有設備記錄: {reports_with_equipment}')
        self.stdout.write(f'無設備記錄: {total_reports - reports_with_equipment}')
        
        # 2. 檢查設備資料
        self.stdout.write('\n2. 檢查設備資料...')
        equipment_list = Equipment.objects.all()
        self.stdout.write(f'總設備數: {equipment_list.count()}')
        
        if equipment_list.exists():
            self.stdout.write('設備清單:')
            for equipment in equipment_list[:10]:  # 顯示前10個
                self.stdout.write(f'  {equipment.id}: {equipment.name}')
        
        # 3. 建立測試資料
        self.stdout.write('\n3. 建立測試資料...')
        
        # 檢查必要資料
        operators = Operator.objects.all()
        processes = ProcessName.objects.all()
        
        if not operators.exists():
            self.stdout.write(self.style.ERROR('錯誤: 沒有作業員資料'))
            return
        
        if not processes.exists():
            self.stdout.write(self.style.ERROR('錯誤: 沒有工序資料'))
            return
        
        if not equipment_list.exists():
            self.stdout.write(self.style.ERROR('錯誤: 沒有設備資料'))
            return
        
        # 建立測試Excel檔案
        test_data = []
        operator = operators.first()
        process = processes.first()
        equipment = equipment_list.first()
        
        # 建立3筆測試資料，包含設備名稱
        for i in range(3):
            test_data.append({
                '作業員名稱': operator.name,
                '公司代號': '01',
                '報工日期': date.today().strftime('%Y-%m-%d'),
                '開始時間': f'0{8+i}:00',
                '結束時間': f'{12+i}:00',
                '工單號': f'TEST-WO-{i+1:03d}',
                '產品編號': f'TEST-PROD-{i+1:03d}',
                '工序名稱': process.name,
                '設備名稱': equipment.name,  # 確保有設備名稱
                '報工數量': 100 + (i * 10),
                '不良品數量': i,
                '備註': f'測試設備匯入 {i+1}',
                '異常紀錄': '',
            })
        
        # 建立DataFrame
        df = pd.DataFrame(test_data)
        
        # 儲存測試檔案
        test_file_path = '/tmp/test_equipment_import.xlsx'
        df.to_excel(test_file_path, index=False)
        
        self.stdout.write(f'測試檔案已建立: {test_file_path}')
        self.stdout.write(f'測試資料筆數: {len(test_data)}')
        self.stdout.write(f'設備名稱: {equipment.name}')
        
        # 4. 模擬匯入邏輯
        self.stdout.write('\n4. 模擬匯入邏輯...')
        
        success_count = 0
        error_count = 0
        
        for index, row in df.iterrows():
            try:
                self.stdout.write(f'處理第 {index+1} 行...')
                
                # 檢查設備名稱欄位
                if '設備名稱' in df.columns:
                    self.stdout.write(f'  設備名稱欄位存在')
                    if pd.notna(row['設備名稱']):
                        equipment_name = str(row['設備名稱']).strip()
                        self.stdout.write(f'  設備名稱值: "{equipment_name}"')
                        
                        if equipment_name:
                            # 查找設備
                            try:
                                found_equipment = Equipment.objects.get(name=equipment_name)
                                self.stdout.write(f'  找到設備: {found_equipment.name} (ID: {found_equipment.id})')
                                equipment = found_equipment
                            except Equipment.DoesNotExist:
                                try:
                                    found_equipment = Equipment.objects.get(name__iexact=equipment_name)
                                    self.stdout.write(f'  大小寫不匹配: "{equipment_name}" -> "{found_equipment.name}"')
                                    equipment = found_equipment
                                except Equipment.DoesNotExist:
                                    self.stdout.write(f'  找不到設備: "{equipment_name}"')
                                    equipment = None
                        else:
                            self.stdout.write(f'  設備名稱為空')
                            equipment = None
                    else:
                        self.stdout.write(f'  設備名稱欄位為空')
                        equipment = None
                else:
                    self.stdout.write(f'  設備名稱欄位不存在')
                    equipment = None
                
                # 模擬建立記錄
                report_data = {
                    'operator': operator,
                    'process': process,
                    'equipment': equipment,  # 這裡應該有設備資料
                    'work_date': date.today(),
                    'start_time': f'0{8+index}:00',
                    'end_time': f'{12+index}:00',
                    'work_quantity': 100 + (index * 10),
                    'defect_quantity': index,
                    'remarks': f'測試設備匯入 {index+1}',
                    'abnormal_notes': '',
                    'created_by': 'test_user'
                }
                
                self.stdout.write(f'  準備建立的資料:')
                self.stdout.write(f'    作業員: {report_data["operator"].name}')
                self.stdout.write(f'    工序: {report_data["process"].name}')
                self.stdout.write(f'    設備: {report_data["equipment"].name if report_data["equipment"] else "無"}')
                self.stdout.write(f'    數量: {report_data["work_quantity"]}')
                
                success_count += 1
                
            except Exception as e:
                self.stdout.write(f'  錯誤: {str(e)}')
                error_count += 1
        
        self.stdout.write(f'\n模擬結果: 成功 {success_count} 筆，錯誤 {error_count} 筆')
        
        # 5. 實際測試匯入
        self.stdout.write('\n5. 實際測試匯入...')
        
        # 檢查匯入前的記錄數
        before_count = OperatorSupplementReport.objects.count()
        self.stdout.write(f'匯入前記錄數: {before_count}')
        
        # 模擬實際匯入（不真正建立記錄，只檢查邏輯）
        for index, row in df.iterrows():
            try:
                # 檢查是否會建立記錄
                existing_report = OperatorSupplementReport.objects.filter(
                    operator=operator,
                    process=process,
                    work_date=date.today(),
                    start_time=f'0{8+index}:00',
                    end_time=f'{12+index}:00'
                ).first()
                
                if existing_report:
                    self.stdout.write(f'第 {index+1} 行: 已存在記錄，會跳過')
                else:
                    self.stdout.write(f'第 {index+1} 行: 會建立新記錄')
                    
                    # 檢查設備處理
                    equipment_name = str(row['設備名稱']).strip()
                    if equipment_name:
                        try:
                            found_equipment = Equipment.objects.get(name=equipment_name)
                            self.stdout.write(f'  設備會正確設定為: {found_equipment.name}')
                        except Equipment.DoesNotExist:
                            self.stdout.write(f'  設備查找失敗: {equipment_name}')
                    
            except Exception as e:
                self.stdout.write(f'第 {index+1} 行: 處理錯誤 - {str(e)}')
        
        # 6. 清理測試檔案
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            self.stdout.write('\n測試檔案已清理')
        
        self.stdout.write(self.style.SUCCESS('\n=== 測試完成 ==='))
        
        # 7. 提供修復建議
        self.stdout.write('\n=== 修復建議 ===')
        self.stdout.write('1. 檢查匯入模板是否包含「設備名稱」欄位')
        self.stdout.write('2. 確認設備名稱在系統中是否存在')
        self.stdout.write('3. 檢查匯入邏輯中的設備查找是否正確')
        self.stdout.write('4. 確認設備欄位在建立記錄時有正確傳遞') 