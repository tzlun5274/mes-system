"""
報表模組測試
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport
from process.models import Operator, ProcessName
from equip.models import Equipment
from workorder.models import WorkOrder
from datetime import date, time


class ReportingViewsTestCase(TestCase):
    """報表模組視圖測試"""

    def setUp(self):
        """設定測試環境"""
        # 創建超級管理員用戶
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        
        # 創建一般用戶
        self.normal_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='user123'
        )
        
        # 創建測試客戶端
        self.client = Client()
        
        # 創建測試資料
        self.create_test_data()

    def create_test_data(self):
        """創建測試資料"""
        # 創建工序
        self.process = ProcessName.objects.create(
            name='測試工序',
            description='測試用工序'
        )
        
        # 創建作業員
        self.operator = Operator.objects.create(
            name='測試作業員',
            employee_id='TEST001'
        )
        
        # 創建設備
        self.equipment = Equipment.objects.create(
            name='測試設備',
            equipment_id='EQ001'
        )
        
        # 創建工單
        self.workorder = WorkOrder.objects.create(
            order_number='WO001',
            product_id='PROD001',
            total_order_quantity=100
        )
        
        # 創建待核准的作業員報工記錄
        self.operator_report = OperatorSupplementReport.objects.create(
            operator=self.operator,
            workorder=self.workorder,
            process=self.process,
            work_date=date.today(),
            start_time=time(8, 0),
            end_time=time(17, 0),
            work_quantity=50,
            defect_quantity=2,
            approval_status='pending',
            created_by='test_user'
        )
        
        # 創建待核准的SMT報工記錄
        self.smt_report = SMTProductionReport.objects.create(
            workorder=self.workorder,
            equipment=self.equipment,
            operation='SMT測試工序',
            work_date=date.today(),
            start_time=time(8, 0),
            end_time=time(17, 0),
            work_quantity=80,
            defect_quantity=1,
            approval_status='pending',
            created_by='test_user'
        )

    def test_superuser_can_access_batch_delete_confirm(self):
        """測試超級管理員可以訪問批次刪除確認頁面"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('reporting:batch_delete_pending_confirm'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '批次刪除待核准報工記錄')

    def test_normal_user_cannot_access_batch_delete_confirm(self):
        """測試一般用戶無法訪問批次刪除確認頁面"""
        self.client.login(username='user', password='user123')
        response = self.client.get(reverse('reporting:batch_delete_pending_confirm'))
        self.assertEqual(response.status_code, 302)  # 重定向到登入頁面

    def test_superuser_can_execute_batch_delete(self):
        """測試超級管理員可以執行批次刪除"""
        self.client.login(username='admin', password='admin123')
        
        # 確認刪除前有記錄
        self.assertEqual(OperatorSupplementReport.objects.filter(approval_status='pending').count(), 1)
        self.assertEqual(SMTProductionReport.objects.filter(approval_status='pending').count(), 1)
        
        # 執行批次刪除
        response = self.client.post(reverse('reporting:batch_delete_pending_reports'))
        self.assertEqual(response.status_code, 302)  # 重定向
        
        # 確認記錄已被刪除
        self.assertEqual(OperatorSupplementReport.objects.filter(approval_status='pending').count(), 0)
        self.assertEqual(SMTProductionReport.objects.filter(approval_status='pending').count(), 0)

    def test_normal_user_cannot_execute_batch_delete(self):
        """測試一般用戶無法執行批次刪除"""
        self.client.login(username='user', password='user123')
        
        # 嘗試執行批次刪除
        response = self.client.post(reverse('reporting:batch_delete_pending_reports'))
        self.assertEqual(response.status_code, 302)  # 重定向到登入頁面
        
        # 確認記錄未被刪除
        self.assertEqual(OperatorSupplementReport.objects.filter(approval_status='pending').count(), 1)
        self.assertEqual(SMTProductionReport.objects.filter(approval_status='pending').count(), 1)

    def test_pending_approval_list_shows_superuser_buttons(self):
        """測試待審核清單頁面對超級管理員顯示批次刪除按鈕"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('reporting:pending_approval_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '批次刪除')

    def test_pending_approval_list_hides_buttons_from_normal_user(self):
        """測試待審核清單頁面對一般用戶隱藏批次刪除按鈕"""
        self.client.login(username='user', password='user123')
        response = self.client.get(reverse('reporting:pending_approval_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '批次刪除')

    def test_get_pending_reports_count_api(self):
        """測試取得待核准報工記錄數量的API"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('reporting:get_pending_reports_count'))
        self.assertEqual(response.status_code, 200)
        
        # 解析JSON回應
        import json
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['operator_count'], 1)
        self.assertEqual(data['smt_count'], 1)
        self.assertEqual(data['total_count'], 2) 