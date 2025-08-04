#!/usr/bin/env python3
"""
測試作業員報工匯入功能
驗證匯入邏輯是否正常工作
"""

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth.models import User
from workorder.views_import import operator_report_import_file
import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '測試作業員報工匯入功能'

    def handle(self, *args, **options):
        self.stdout.write('開始測試匯入功能...')
        
        # 創建測試用戶
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'is_superuser': True, 'is_staff': True}
        )
        
        # 創建測試數據
        test_data = [
            ['張小明', '01', '2025-01-15', '08:00', '12:00', 'WO-01-202501001', 'PROD-001', 'SMT', 'SMT-001', 100, 2, '正常生產', ''],
            ['李小華', '01', '2025-01-15', '13:00', '17:00', 'WO-01-202501001', 'PROD-001', 'DIP', 'DIP-001', 95, 5, '設備調整', '設備故障30分鐘'],
        ]
        
        # 創建DataFrame
        columns = ['作業員名稱', '公司代號', '報工日期', '開始時間', '結束時間', 
                  '工單號', '產品編號', '工序名稱', '設備名稱', '報工數量', 
                  '不良品數量', '備註', '異常紀錄']
        df = pd.DataFrame(test_data, columns=columns)
        
        # 保存為Excel文件
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        excel_buffer.seek(0)
        
        # 創建模擬請求
        factory = RequestFactory()
        request = factory.post('/workorder/report/operator/supplement/batch/file/')
        request.user = user
        
        # 創建模擬文件對象
        class MockFile:
            def __init__(self, name, content):
                self.name = name
                self.content = content
                self.position = 0
            
            def read(self, size=None):
                return self.content
            
            def seek(self, position, whence=0):
                self.position = position
            
            def tell(self):
                return self.position
        
        # 設置FILES
        request._files = {'file': MockFile('test_import.xlsx', excel_buffer.getvalue())}
        
        try:
            # 調用匯入函數
            response = operator_report_import_file(request)
            
            self.stdout.write(f'匯入函數返回: {response}')
            self.stdout.write(f'回應內容: {response.content.decode()}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'匯入測試失敗: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(f'錯誤詳情: {traceback.format_exc()}'))
        
        self.stdout.write(self.style.SUCCESS('測試完成')) 