"""
測試匯入成功率
檢查為什麼100筆資料只寫入60筆
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from workorder.workorder_reporting.models import OperatorSupplementReport
from process.models import Operator, ProcessName
from equip.models import Equipment
from erp_integration.models import CompanyConfig
import pandas as pd
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '測試匯入成功率'

    def handle(self, *args, **options):
        self.stdout.write('=== 開始測試匯入成功率 ===')
        
        # 1. 準備測試資料
        self.stdout.write('\n1. 準備測試資料...')
        
        # 獲取測試資料
        operators = list(Operator.objects.all()[:3])
        processes = list(ProcessName.objects.all()[:3])
        equipments = list(Equipment.objects.all()[:3])
        companies = list(CompanyConfig.objects.all()[:1])
        
        if not all([operators, processes, equipments, companies]):
            self.stdout.write(self.style.ERROR('測試資料不足'))
            return
        
        test_operator = operators[0]
        test_process = processes[0]
        test_equipment = equipments[0]
        test_company = companies[0]
        
        self.stdout.write(f'使用作業員: {test_operator.name}')
        self.stdout.write(f'使用工序: {test_process.name}')
        self.stdout.write(f'使用設備: {test_equipment.name}')
        self.stdout.write(f'使用公司: {test_company.company_name}')
        
        # 2. 創建100筆測試資料
        self.stdout.write('\n2. 創建100筆測試資料...')
        
        test_data = []
        for i in range(100):
            # 隨機選擇設備（有些記錄沒有設備）
            equipment_name = test_equipment.name if i % 3 != 0 else ""  # 每3筆中有1筆沒有設備
            
            row_data = {
                '作業員名稱': test_operator.name,
                '公司代號': test_company.company_code,
                '報工日期': '2024-01-15',
                '開始時間': '08:00',
                '結束時間': '17:00',
                '工單號': f'TEST{i:03d}',
                '產品編號': f'PROD{i:03d}',
                '工序名稱': test_process.name,
                '設備名稱': equipment_name,  # 有些記錄沒有設備
                '報工數量': 100 + i,
                '不良品數量': i % 5,
                '備註': f'測試記錄 {i+1}',
                '異常紀錄': '' if i % 10 != 0 else f'異常記錄 {i+1}'
            }
            test_data.append(row_data)
        
        df = pd.DataFrame(test_data)
        self.stdout.write(f'創建了 {len(df)} 筆測試資料')
        self.stdout.write(f'有設備名稱的記錄: {len(df[df["設備名稱"] != ""])} 筆')
        self.stdout.write(f'無設備名稱的記錄: {len(df[df["設備名稱"] == ""])} 筆')
        
        # 3. 模擬匯入過程
        self.stdout.write('\n3. 模擬匯入過程...')
        
        success_count = 0
        error_count = 0
        skip_count = 0
        errors = []
        skips = []
        
        for index, row in df.iterrows():
            try:
                # 模擬匯入邏輯
                operator_name = str(row['作業員名稱']).strip()
                operator = Operator.objects.filter(name=operator_name).first()
                if not operator:
                    errors.append(f'第 {index+1} 行：找不到作業員 "{operator_name}"')
                    error_count += 1
                    continue
                
                # 檢查公司代號
                company_code_raw = row['公司代號']
                if pd.isna(company_code_raw):
                    errors.append(f'第 {index+1} 行：公司代號為空')
                    error_count += 1
                    continue
                
                if isinstance(company_code_raw, (int, float)):
                    company_code = str(int(company_code_raw))
                else:
                    company_code = str(company_code_raw).strip()
                
                if company_code.isdigit():
                    company_code = company_code.zfill(2)
                
                company = CompanyConfig.objects.filter(company_code=company_code).first()
                if not company:
                    errors.append(f'第 {index+1} 行：找不到公司代號 "{company_code}"')
                    error_count += 1
                    continue
                
                # 解析日期
                try:
                    date_str = str(row['報工日期']).strip()
                    work_date = pd.to_datetime(date_str).date()
                except Exception as e:
                    errors.append(f'第 {index+1} 行：報工日期格式錯誤 "{row["報工日期"]}"')
                    error_count += 1
                    continue
                
                # 解析時間
                try:
                    start_time_str = str(row['開始時間']).strip()
                    if ':' in start_time_str:
                        if start_time_str.count(':') == 2:
                            start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
                        else:
                            start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    else:
                        start_time = datetime.strptime(start_time_str.zfill(4), '%H%M').time()
                except Exception as e:
                    errors.append(f'第 {index+1} 行：開始時間格式錯誤 "{row["開始時間"]}"')
                    error_count += 1
                    continue
                
                try:
                    end_time_str = str(row['結束時間']).strip()
                    if ':' in end_time_str:
                        if end_time_str.count(':') == 2:
                            end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
                        else:
                            end_time = datetime.strptime(end_time_str, '%H:%M').time()
                    else:
                        end_time = datetime.strptime(end_time_str.zfill(4), '%H%M').time()
                except Exception as e:
                    errors.append(f'第 {index+1} 行：結束時間格式錯誤 "{row["結束時間"]}"')
                    error_count += 1
                    continue
                
                # 檢查工單號
                workorder_number = str(row['工單號']).strip()
                if not workorder_number:
                    errors.append(f'第 {index+1} 行：工單號為空')
                    error_count += 1
                    continue
                
                # 檢查產品編號
                product_code = str(row['產品編號']).strip()
                if not product_code:
                    errors.append(f'第 {index+1} 行：產品編號為空')
                    error_count += 1
                    continue
                
                # 檢查工序名稱
                process_name = str(row['工序名稱']).strip()
                if not process_name:
                    errors.append(f'第 {index+1} 行：工序名稱為空')
                    error_count += 1
                    continue
                
                process = ProcessName.objects.filter(name=process_name).first()
                if not process:
                    errors.append(f'第 {index+1} 行：找不到工序 "{process_name}"')
                    error_count += 1
                    continue
                
                # 檢查報工數量
                try:
                    work_quantity = int(row['報工數量'])
                    if work_quantity < 0:
                        errors.append(f'第 {index+1} 行：報工數量不能為負數')
                        error_count += 1
                        continue
                except (ValueError, TypeError):
                    errors.append(f'第 {index+1} 行：報工數量格式錯誤 "{row["報工數量"]}"')
                    error_count += 1
                    continue
                
                # 處理不良品數量
                defect_quantity = 0
                if '不良品數量' in df.columns and pd.notna(row['不良品數量']):
                    try:
                        defect_quantity = int(row['不良品數量'])
                        if defect_quantity < 0:
                            errors.append(f'第 {index+1} 行：不良品數量不能為負數')
                            error_count += 1
                            continue
                    except (ValueError, TypeError):
                        errors.append(f'第 {index+1} 行：不良品數量格式錯誤 "{row["不良品數量"]}"')
                        error_count += 1
                        continue
                
                # 處理設備名稱
                equipment = None
                if '設備名稱' in df.columns and pd.notna(row['設備名稱']):
                    equipment_name = str(row['設備名稱']).strip()
                    if equipment_name:
                        equipment = Equipment.objects.filter(name=equipment_name).first()
                        if not equipment:
                            equipment = Equipment.objects.filter(name__iexact=equipment_name).first()
                
                # 處理備註
                remarks = ""
                if '備註' in df.columns and pd.notna(row['備註']):
                    remarks = str(row['備註']).strip()
                
                # 處理異常紀錄
                abnormal_notes = ""
                if '異常紀錄' in df.columns and pd.notna(row['異常紀錄']):
                    abnormal_notes = str(row['異常紀錄']).strip()
                
                # 檢查重複記錄
                existing_query = OperatorSupplementReport.objects.filter(
                    operator=operator,
                    process=process,
                    work_date=work_date,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if workorder_number.startswith('TEST'):
                    # 測試資料，檢查是否有相同工單號
                    existing_query = existing_query.filter(original_workorder_number=workorder_number)
                else:
                    # 實際資料，檢查工單關聯
                    from workorder.models import WorkOrder
                    workorder = WorkOrder.objects.filter(
                        company_code=company_code,
                        order_number=workorder_number
                    ).first()
                    if workorder:
                        existing_query = existing_query.filter(workorder=workorder)
                    else:
                        existing_query = existing_query.filter(original_workorder_number=workorder_number)
                
                if equipment:
                    existing_query = existing_query.filter(equipment=equipment)
                else:
                    existing_query = existing_query.filter(equipment__isnull=True)
                
                existing_report = existing_query.first()
                if existing_report:
                    skips.append(f'第 {index+1} 行：已存在相同記錄，跳過匯入')
                    skip_count += 1
                    continue
                
                # 建立記錄
                report_data = {
                    'operator': operator,
                    'process': process,
                    'operation': process.name,
                    'equipment': equipment,
                    'product_id': product_code,
                    'work_date': work_date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'work_quantity': work_quantity,
                    'defect_quantity': defect_quantity,
                    'remarks': remarks,
                    'abnormal_notes': abnormal_notes,
                    'created_by': 'test_user'
                }
                
                if workorder_number.startswith('TEST'):
                    report_data['original_workorder_number'] = workorder_number
                
                report = OperatorSupplementReport.objects.create(**report_data)
                report.calculate_work_hours()
                report.save()
                
                success_count += 1
                
            except Exception as e:
                errors.append(f'第 {index+1} 行：處理失敗 - {str(e)}')
                error_count += 1
        
        # 4. 顯示結果
        self.stdout.write('\n4. 匯入結果...')
        self.stdout.write(f'總處理筆數: {len(df)}')
        self.stdout.write(f'成功筆數: {success_count}')
        self.stdout.write(f'錯誤筆數: {error_count}')
        self.stdout.write(f'跳過筆數: {skip_count}')
        self.stdout.write(f'成功率: {success_count/len(df)*100:.1f}%')
        
        if errors:
            self.stdout.write(f'\n錯誤詳情（前5個）:')
            for error in errors[:5]:
                self.stdout.write(f'  {error}')
            if len(errors) > 5:
                self.stdout.write(f'  ... 還有 {len(errors) - 5} 個錯誤')
        
        if skips:
            self.stdout.write(f'\n跳過詳情（前5個）:')
            for skip in skips[:5]:
                self.stdout.write(f'  {skip}')
            if len(skips) > 5:
                self.stdout.write(f'  ... 還有 {len(skips) - 5} 個跳過')
        
        self.stdout.write('\n=== 測試完成 ===') 