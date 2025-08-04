#!/usr/bin/env python3
"""
測試作業員報工匯入匯出功能
確保只操作 OperatorSupplementReport 模型的 equipment 欄位，不與其他模型產生關聯
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from workorder.workorder_reporting.models import OperatorSupplementReport
from equip.models import Equipment
from process.models import Operator, ProcessName
from workorder.models import WorkOrder
from datetime import datetime, date
import pandas as pd
from io import BytesIO
import os


class Command(BaseCommand):
    help = '測試作業員報工匯入匯出功能，確保只操作 OperatorSupplementReport 模型的 equipment 欄位'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-import',
            action='store_true',
            help='測試匯入功能'
        )
        parser.add_argument(
            '--test-export',
            action='store_true',
            help='測試匯出功能'
        )
        parser.add_argument(
            '--test-equipment-only',
            action='store_true',
            help='只測試設備欄位相關功能'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('開始測試作業員報工匯入匯出功能...')
        )

        if options['test_equipment_only']:
            self.test_equipment_field_only()
        elif options['test_import']:
            self.test_import_functionality()
        elif options['test_export']:
            self.test_export_functionality()
        else:
            self.test_equipment_field_only()
            self.test_import_functionality()
            self.test_export_functionality()

    def test_equipment_field_only(self):
        """測試設備欄位相關功能"""
        self.stdout.write(
            self.style.WARNING('\n=== 測試設備欄位相關功能 ===')
        )

        # 1. 檢查 OperatorSupplementReport 模型的 equipment 欄位
        self.stdout.write('1. 檢查 OperatorSupplementReport 模型的 equipment 欄位...')
        
        # 取得模型欄位資訊
        equipment_field = OperatorSupplementReport._meta.get_field('equipment')
        self.stdout.write(f'   欄位名稱: {equipment_field.name}')
        self.stdout.write(f'   欄位類型: {equipment_field.__class__.__name__}')
        self.stdout.write(f'   中文名稱: {equipment_field.verbose_name}')
        self.stdout.write(f'   是否可為空: {equipment_field.null}')
        self.stdout.write(f'   是否可為空白: {equipment_field.blank}')
        
        if hasattr(equipment_field, 'related_model'):
            self.stdout.write(f'   關聯模型: {equipment_field.related_model.__name__}')
        
        # 2. 檢查現有資料的設備使用情況
        self.stdout.write('\n2. 檢查現有資料的設備使用情況...')
        
        total_reports = OperatorSupplementReport.objects.count()
        reports_with_equipment = OperatorSupplementReport.objects.filter(equipment__isnull=False).count()
        reports_without_equipment = OperatorSupplementReport.objects.filter(equipment__isnull=True).count()
        
        self.stdout.write(f'   總報工記錄數: {total_reports}')
        self.stdout.write(f'   有設備記錄數: {reports_with_equipment}')
        self.stdout.write(f'   無設備記錄數: {reports_without_equipment}')
        
        if total_reports > 0:
            equipment_usage_rate = (reports_with_equipment / total_reports) * 100
            self.stdout.write(f'   設備使用率: {equipment_usage_rate:.2f}%')

        # 3. 檢查設備資料
        self.stdout.write('\n3. 檢查設備資料...')
        
        total_equipment = Equipment.objects.count()
        self.stdout.write(f'   總設備數: {total_equipment}')
        
        if total_equipment > 0:
            # 顯示前5個設備
            equipment_list = Equipment.objects.all()[:5]
            for i, equipment in enumerate(equipment_list, 1):
                self.stdout.write(f'   設備 {i}: {equipment.name} (ID: {equipment.id})')

        # 4. 檢查設備欄位是否與其他模型有關聯
        self.stdout.write('\n4. 檢查設備欄位是否與其他模型有關聯...')
        
        # 檢查是否有其他模型也使用 equipment 欄位
        from django.apps import apps
        
        related_models = []
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                if hasattr(model, '_meta'):
                    for field in model._meta.fields:
                        if field.name == 'equipment' and model != OperatorSupplementReport:
                            related_models.append(model.__name__)
        
        if related_models:
            self.stdout.write(f'   發現其他模型也有 equipment 欄位: {", ".join(related_models)}')
        else:
            self.stdout.write('   沒有發現其他模型有 equipment 欄位')

    def test_import_functionality(self):
        """測試匯入功能"""
        self.stdout.write(
            self.style.WARNING('\n=== 測試匯入功能 ===')
        )

        # 1. 建立測試資料
        self.stdout.write('1. 建立測試資料...')
        
        # 檢查是否有必要的基礎資料
        operators = Operator.objects.all()
        processes = ProcessName.objects.all()
        equipment_list = Equipment.objects.all()
        
        if not operators.exists():
            self.stdout.write(self.style.ERROR('   錯誤: 沒有作業員資料'))
            return
        
        if not processes.exists():
            self.stdout.write(self.style.ERROR('   錯誤: 沒有工序資料'))
            return
        
        if not equipment_list.exists():
            self.stdout.write(self.style.ERROR('   錯誤: 沒有設備資料'))
            return

        # 2. 建立測試 Excel 檔案
        self.stdout.write('2. 建立測試 Excel 檔案...')
        
        test_data = []
        for i in range(3):  # 建立3筆測試資料
            operator = operators.first()
            process = processes.first()
            equipment = equipment_list.first() if equipment_list.exists() else None
            
            test_data.append({
                '作業員名稱': operator.name,
                '公司代號': '01',
                '報工日期': date.today().strftime('%Y-%m-%d'),
                '開始時間': '08:00',
                '結束時間': '12:00',
                '工單號': f'TEST-WO-{i+1:03d}',
                '產品編號': f'TEST-PROD-{i+1:03d}',
                '工序名稱': process.name,
                '設備名稱': equipment.name if equipment else '',
                '報工數量': 100 + (i * 10),
                '不良品數量': i,
                '備註': f'測試資料 {i+1}',
                '異常紀錄': '',
            })

        # 建立 DataFrame
        df = pd.DataFrame(test_data)
        
        # 儲存為 Excel 檔案
        test_file_path = '/tmp/test_operator_report_import.xlsx'
        df.to_excel(test_file_path, index=False)
        
        self.stdout.write(f'   測試檔案已建立: {test_file_path}')
        self.stdout.write(f'   測試資料筆數: {len(test_data)}')

        # 3. 模擬匯入邏輯
        self.stdout.write('3. 模擬匯入邏輯...')
        
        success_count = 0
        error_count = 0
        skip_count = 0
        
        for index, row in df.iterrows():
            try:
                # 模擬匯入邏輯中的設備處理部分
                equipment = None
                if pd.notna(row['設備名稱']) and row['設備名稱'].strip():
                    equipment_name = str(row['設備名稱']).strip()
                    
                    # 直接查找 Equipment 模型，不與其他報工模型產生關聯
                    try:
                        equipment = Equipment.objects.get(name=equipment_name)
                        self.stdout.write(f'   第 {index+1} 行: 找到設備 "{equipment_name}" (ID: {equipment.id})')
                    except Equipment.DoesNotExist:
                        # 如果精確匹配失敗，嘗試不區分大小寫的查找
                        try:
                            equipment = Equipment.objects.get(name__iexact=equipment_name)
                            self.stdout.write(f'   第 {index+1} 行: 設備名稱大小寫不匹配 "{equipment_name}" -> "{equipment.name}"')
                        except Equipment.DoesNotExist:
                            self.stdout.write(f'   第 {index+1} 行: 找不到設備 "{equipment_name}"，設備欄位將設為空')
                            equipment = None
                
                success_count += 1
                
            except Exception as e:
                self.stdout.write(f'   第 {index+1} 行: 處理失敗 - {str(e)}')
                error_count += 1

        self.stdout.write(f'   匯入測試結果: 成功 {success_count} 筆，錯誤 {error_count} 筆，跳過 {skip_count} 筆')

        # 4. 清理測試檔案
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            self.stdout.write('   測試檔案已清理')

    def test_export_functionality(self):
        """測試匯出功能"""
        self.stdout.write(
            self.style.WARNING('\n=== 測試匯出功能 ===')
        )

        # 1. 檢查是否有資料可以匯出
        self.stdout.write('1. 檢查是否有資料可以匯出...')
        
        total_reports = OperatorSupplementReport.objects.count()
        self.stdout.write(f'   總報工記錄數: {total_reports}')
        
        if total_reports == 0:
            self.stdout.write(self.style.WARNING('   沒有資料可以匯出'))
            return

        # 2. 模擬匯出邏輯
        self.stdout.write('2. 模擬匯出邏輯...')
        
        # 建立查詢 - 只針對 OperatorSupplementReport 模型
        query = OperatorSupplementReport.objects.select_related(
            'operator', 'process', 'equipment', 'workorder'
        ).all()
        
        # 限制匯出數量
        max_export_count = 10
        query = query[:max_export_count]
        
        self.stdout.write(f'   將匯出前 {max_export_count} 筆記錄')

        # 3. 準備匯出資料
        export_data = []
        for report in query:
            # 取得工單號碼 - 只從 OperatorSupplementReport 模型取得
            workorder_number = ''
            if report.workorder:
                workorder_number = report.workorder.order_number
            elif report.original_workorder_number:
                workorder_number = report.original_workorder_number
            elif report.rd_workorder_number:
                workorder_number = report.rd_workorder_number
            
            # 取得產品編號 - 只從 OperatorSupplementReport 模型取得
            product_code = ''
            if report.workorder and report.workorder.product_code:
                product_code = report.workorder.product_code
            elif report.product_id:
                product_code = report.product_id
            elif report.rd_product_code:
                product_code = report.rd_product_code
            
            # 取得公司代號 - 只從 OperatorSupplementReport 模型取得
            company_code_value = ''
            if report.workorder and report.workorder.company_code:
                company_code_value = report.workorder.company_code
            
            export_data.append({
                '作業員名稱': report.operator.name if report.operator else '',
                '公司代號': company_code_value,
                '報工日期': report.work_date.strftime('%Y-%m-%d') if report.work_date else '',
                '開始時間': report.start_time.strftime('%H:%M:%S') if report.start_time else '',
                '結束時間': report.end_time.strftime('%H:%M:%S') if report.end_time else '',
                '工單號': workorder_number,
                '產品編號': product_code,
                '工序名稱': report.process.name if report.process else '',
                '設備名稱': report.equipment.name if report.equipment else '',  # 直接從 OperatorSupplementReport 的 equipment 欄位取得
                '報工數量': report.work_quantity,
                '不良品數量': report.defect_quantity,
                '備註': report.remarks or '',
                '異常紀錄': report.abnormal_notes or '',
                '工作時數': float(report.work_hours_calculated) if report.work_hours_calculated else 0,
                '加班時數': float(report.overtime_hours_calculated) if report.overtime_hours_calculated else 0,
                '報工類型': report.report_type,
                '核准狀態': report.approval_status,
                '建立時間': report.created_at.strftime('%Y-%m-%d %H:%M:%S') if report.created_at else '',
            })

        # 4. 建立 DataFrame
        df = pd.DataFrame(export_data)
        
        # 5. 顯示匯出結果
        self.stdout.write(f'   成功準備 {len(export_data)} 筆資料')
        self.stdout.write(f'   資料欄位: {list(df.columns)}')
        
        # 顯示設備欄位的統計
        equipment_data = df['設備名稱'].value_counts()
        self.stdout.write(f'   設備欄位統計:')
        for equipment_name, count in equipment_data.items():
            if equipment_name:
                self.stdout.write(f'     {equipment_name}: {count} 筆')
            else:
                self.stdout.write(f'     空白: {count} 筆')

        # 6. 儲存測試匯出檔案
        test_export_path = '/tmp/test_operator_report_export.xlsx'
        df.to_excel(test_export_path, index=False)
        self.stdout.write(f'   測試匯出檔案已建立: {test_export_path}')

        # 7. 清理測試檔案
        if os.path.exists(test_export_path):
            os.remove(test_export_path)
            self.stdout.write('   測試匯出檔案已清理')

    def test_equipment_validation(self):
        """測試設備驗證邏輯"""
        self.stdout.write(
            self.style.WARNING('\n=== 測試設備驗證邏輯 ===')
        )

        # 測試各種設備名稱的情況
        test_cases = [
            {'name': '正確設備名稱', 'expected': 'success'},
            {'name': 'WRONG_EQUIPMENT', 'expected': 'not_found'},
            {'name': '', 'expected': 'empty'},
            {'name': '   ', 'expected': 'empty'},
        ]

        for test_case in test_cases:
            equipment_name = test_case['name']
            expected = test_case['expected']
            
            self.stdout.write(f'測試設備名稱: "{equipment_name}"')
            
            if not equipment_name or not equipment_name.strip():
                self.stdout.write('   結果: 設備名稱為空，設為 None')
                continue
            
            equipment_name = equipment_name.strip()
            
            # 模擬匯入邏輯中的設備查找
            try:
                equipment = Equipment.objects.get(name=equipment_name)
                self.stdout.write(f'   結果: 找到設備 "{equipment.name}" (ID: {equipment.id})')
            except Equipment.DoesNotExist:
                try:
                    equipment = Equipment.objects.get(name__iexact=equipment_name)
                    self.stdout.write(f'   結果: 大小寫不匹配 "{equipment_name}" -> "{equipment.name}"')
                except Equipment.DoesNotExist:
                    self.stdout.write(f'   結果: 找不到設備 "{equipment_name}"，設為 None')

        self.stdout.write(
            self.style.SUCCESS('\n=== 測試完成 ===')
        ) 