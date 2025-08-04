#!/usr/bin/env python3
"""
測試作業員報工匯入邏輯
直接測試匯入函數的核心邏輯
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from process.models import Operator
from equip.models import Equipment
from process.models import ProcessName
from workorder.models import WorkOrder
from workorder.workorder_reporting.models import OperatorSupplementReport
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '測試作業員報工匯入邏輯'

    def handle(self, *args, **options):
        self.stdout.write('開始測試匯入邏輯...')
        
        # 創建測試數據（使用實際存在的作業員、工序和設備）
        test_data = [
            ['王 珍', '01', '2025-01-15', '08:00', '12:00', 'WO-01-202501001', 'PROD-001', '後焊', 'AOI-1', 100, 2, '正常生產', ''],
            ['蔡秉儒', '01', '2025-01-15', '13:00', '17:00', 'WO-01-202501001', 'PROD-001', '電測', 'AOI-2', 95, 5, '設備調整', '設備故障30分鐘'],
        ]
        
        # 創建DataFrame
        columns = ['作業員名稱', '公司代號', '報工日期', '開始時間', '結束時間', 
                  '工單號', '產品編號', '工序名稱', '設備名稱', '報工數量', 
                  '不良品數量', '備註', '異常紀錄']
        df = pd.DataFrame(test_data, columns=columns)
        
        self.stdout.write(f'DataFrame 欄位: {list(df.columns)}')
        self.stdout.write(f'是否有設備名稱欄位: {"設備名稱" in df.columns}')
        
        # 檢查必要欄位
        required_columns = [
            '作業員名稱', '公司代號', '報工日期', '開始時間', '結束時間', 
            '工單號', '產品編號', '工序名稱', '報工數量'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.stdout.write(self.style.ERROR(f'缺少必要欄位：{", ".join(missing_columns)}'))
            return
        
        # 處理每一行資料
        success_count = 0
        error_count = 0
        skip_count = 0
        errors = []
        skips = []
        
        for index, row in df.iterrows():
            try:
                self.stdout.write(f'處理第 {index+1} 行...')
                
                # 1. 驗證並取得作業員
                operator_name = str(row['作業員名稱']).strip()
                if not operator_name:
                    errors.append(f'第 {index+1} 行：作業員名稱為空')
                    error_count += 1
                    continue
                
                operator = Operator.objects.filter(name=operator_name).first()
                if not operator:
                    errors.append(f'第 {index+1} 行：找不到作業員 "{operator_name}"')
                    error_count += 1
                    continue
                
                self.stdout.write(f'找到作業員: {operator.name}')
                
                # 2. 驗證並取得公司代號
                company_code = str(row['公司代號']).strip()
                if not company_code:
                    errors.append(f'第 {index+1} 行：公司代號為空')
                    error_count += 1
                    continue
                
                # 3. 驗證並取得報工日期
                work_date_str = str(row['報工日期']).strip()
                try:
                    from datetime import datetime
                    work_date = datetime.strptime(work_date_str, '%Y-%m-%d').date()
                except ValueError:
                    errors.append(f'第 {index+1} 行：報工日期格式錯誤 "{work_date_str}"')
                    error_count += 1
                    continue
                
                # 4. 驗證並取得開始時間
                start_time_str = str(row['開始時間']).strip()
                try:
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                except ValueError:
                    errors.append(f'第 {index+1} 行：開始時間格式錯誤 "{start_time_str}"')
                    error_count += 1
                    continue
                
                # 5. 驗證並取得結束時間
                end_time_str = str(row['結束時間']).strip()
                try:
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                except ValueError:
                    errors.append(f'第 {index+1} 行：結束時間格式錯誤 "{end_time_str}"')
                    error_count += 1
                    continue
                
                # 6. 驗證並取得工單號
                workorder_number = str(row['工單號']).strip()
                if not workorder_number:
                    errors.append(f'第 {index+1} 行：工單號為空')
                    error_count += 1
                    continue
                
                workorder = WorkOrder.objects.filter(order_number=workorder_number).first()
                
                # 7. 驗證並取得產品編號
                product_id = str(row['產品編號']).strip()
                if not product_id:
                    errors.append(f'第 {index+1} 行：產品編號為空')
                    error_count += 1
                    continue
                
                # 8. 驗證並取得工序名稱
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
                
                self.stdout.write(f'找到工序: {process.name}')
                
                # 9. 驗證並取得報工數量
                work_quantity = row['報工數量']
                if pd.isna(work_quantity) or work_quantity <= 0:
                    errors.append(f'第 {index+1} 行：報工數量無效 "{work_quantity}"')
                    error_count += 1
                    continue
                
                work_quantity = int(work_quantity)
                
                # 10. 處理不良品數量（選填）
                defect_quantity = row['不良品數量']
                if pd.isna(defect_quantity):
                    defect_quantity = 0
                else:
                    defect_quantity = int(defect_quantity)
                
                # 11. 處理設備名稱（選填）
                equipment = None
                self.stdout.write(f'第 {index+1} 行：開始處理設備名稱欄位')
                self.stdout.write(f'第 {index+1} 行：DataFrame 欄位: {list(df.columns)}')
                self.stdout.write(f'第 {index+1} 行：是否有設備名稱欄位: {"設備名稱" in df.columns}')
                
                if '設備名稱' in df.columns:
                    self.stdout.write(f'第 {index+1} 行：設備名稱欄位存在')
                    equipment_value = row['設備名稱']
                    self.stdout.write(f'第 {index+1} 行：設備名稱原始值: "{equipment_value}" (類型: {type(equipment_value)})')
                    
                    if pd.notna(equipment_value):
                        equipment_name = str(equipment_value).strip()
                        self.stdout.write(f'第 {index+1} 行：設備名稱處理後: "{equipment_name}"')
                        
                        if equipment_name:
                            # 直接查找 Equipment 模型
                            try:
                                equipment = Equipment.objects.get(name=equipment_name)
                                self.stdout.write(f'第 {index+1} 行：成功找到設備 "{equipment_name}" (ID: {equipment.id})')
                            except Equipment.DoesNotExist:
                                # 如果精確匹配失敗，嘗試不區分大小寫的查找
                                try:
                                    equipment = Equipment.objects.get(name__iexact=equipment_name)
                                    skips.append(f'第 {index+1} 行：設備名稱大小寫不匹配 "{equipment_name}" -> "{equipment.name}"')
                                    self.stdout.write(f'第 {index+1} 行：設備名稱大小寫不匹配 "{equipment_name}" -> "{equipment.name}"')
                                except Equipment.DoesNotExist:
                                    errors.append(f'第 {index+1} 行：找不到設備 "{equipment_name}"，此記錄的設備欄位將設為空')
                                    self.stdout.write(f'第 {index+1} 行：找不到設備 "{equipment_name}"，設備欄位設為空')
                                    equipment = None
                        else:
                            self.stdout.write(f'第 {index+1} 行：設備名稱為空字串，設備欄位設為空')
                    else:
                        self.stdout.write(f'第 {index+1} 行：設備名稱欄位為空 (NaN/None)，設備欄位設為空')
                else:
                    self.stdout.write(f'第 {index+1} 行：DataFrame 中沒有「設備名稱」欄位')
                
                self.stdout.write(f'第 {index+1} 行：最終設備物件: {equipment}')
                
                # 12. 處理備註（選填）
                remarks = str(row['備註']).strip() if pd.notna(row['備註']) else ''
                
                # 13. 處理異常紀錄（選填）
                abnormal_notes = str(row['異常紀錄']).strip() if pd.notna(row['異常紀錄']) else ''
                
                # 14. 建立報工記錄
                report_data = {
                    'operator': operator,
                    'process': process,
                    'equipment': equipment,  # 確保設備欄位包含在內
                    'work_date': work_date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'work_quantity': work_quantity,
                    'defect_quantity': defect_quantity,
                    'remarks': remarks,
                    'abnormal_notes': abnormal_notes,
                    'created_by': 'test_user'
                }
                
                # 記錄設備資訊，用於除錯
                self.stdout.write(f'第 {index+1} 行：準備建立記錄，設備資訊: {equipment.name if equipment else "無設備"}')
                self.stdout.write(f'第 {index+1} 行：report_data 中的 equipment: {report_data["equipment"]}')
                
                if workorder:
                    # 如果工單存在，使用正常的 workorder 欄位
                    report_data['workorder'] = workorder
                else:
                    # 如果工單不存在，將工單號碼儲存到 original_workorder_number 欄位
                    report_data['original_workorder_number'] = workorder_number
                
                report = OperatorSupplementReport.objects.create(**report_data)
                
                # 記錄建立後的設備資訊，用於除錯
                self.stdout.write(f'第 {index+1} 行：記錄建立成功，ID: {report.id}')
                self.stdout.write(f'第 {index+1} 行：建立後的設備欄位: {report.equipment.name if report.equipment else "無設備"}')
                
                # 16. 自動計算工時
                report.calculate_work_hours()
                report.save()
                
                # 再次檢查保存後的設備資訊
                report.refresh_from_db()
                self.stdout.write(f'第 {index+1} 行：保存後的設備欄位: {report.equipment.name if report.equipment else "無設備"}')
                
                success_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"處理第 {index+1} 行時發生錯誤: {str(e)}"))
                import traceback
                self.stdout.write(self.style.ERROR(f"錯誤詳情: {traceback.format_exc()}"))
                errors.append(f'第 {index+1} 行：處理失敗 - {str(e)}')
                error_count += 1
        
        # 準備回應訊息
        result_message = f"匯入完成！成功：{success_count} 筆，錯誤：{error_count} 筆，跳過：{skip_count} 筆"
        
        if errors:
            result_message += f"\n錯誤詳情：\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                result_message += f"\n... 還有 {len(errors) - 10} 個錯誤"
        
        if skips:
            result_message += f"\n跳過詳情：\n" + "\n".join(skips[:5])
            if len(skips) > 5:
                result_message += f"\n... 還有 {len(skips) - 5} 個跳過"
        
        self.stdout.write(self.style.SUCCESS(result_message))
        self.stdout.write(self.style.SUCCESS('測試完成')) 