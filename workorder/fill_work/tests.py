"""
填報作業管理子模組 - 測試
負責填報作業的單元測試和整合測試
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, time
from decimal import Decimal

from .models import FillWork
from .forms import (
    OperatorFillWorkForm, OperatorRDFillWorkForm,
    SMTFillWorkForm, SMTRDFillWorkForm
)


class FillWorkModelTest(TestCase):
    """填報作業模型測試"""
    
    def setUp(self):
        """測試前準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 建立測試工序
        from process.models import ProcessName
        self.process = ProcessName.objects.create(
            name='測試工序',
            description='測試用工序'
        )
    
    def test_fill_work_creation(self):
        """測試填報作業建立"""
        fill_work = FillWork.objects.create(
            operator='測試作業員',
            company_name='測試公司',
            workorder='TEST-001',
            product_id='TEST-PRODUCT',
            planned_quantity=100,
            process_id=str(self.process.id),
            process_name=self.process.name,
            work_date=date.today(),
            start_time=time(8, 0),
            end_time=time(17, 0),
            work_quantity=50,
            defect_quantity=2,
            created_by=self.user.username
        )
        
        self.assertEqual(fill_work.operator, '測試作業員')
        self.assertEqual(fill_work.workorder, 'TEST-001')
        self.assertEqual(fill_work.approval_status, 'pending')
    
    def test_work_hours_calculation(self):
        """測試工時計算"""
        fill_work = FillWork.objects.create(
            operator='測試作業員',
            company_name='測試公司',
            workorder='TEST-001',
            product_id='TEST-PRODUCT',
            planned_quantity=100,
            process_id=str(self.process.id),
            process_name=self.process.name,
            work_date=date.today(),
            start_time=time(8, 0),
            end_time=time(17, 0),
            work_quantity=50,
            defect_quantity=2,
            has_break=True,
            break_start_time=time(12, 0),
            break_end_time=time(13, 0),
            created_by=self.user.username
        )
        
        # 驗證工時計算
        self.assertGreater(fill_work.work_hours_calculated, 0)
        self.assertGreaterEqual(fill_work.overtime_hours_calculated, 0)


class FillWorkFormTest(TestCase):
    """填報作業表單測試"""
    
    def setUp(self):
        """測試前準備"""
        # 建立測試工序
        from process.models import ProcessName
        self.process = ProcessName.objects.create(
            name='測試工序',
            description='測試用工序'
        )
    
    def test_operator_fill_work_form_valid(self):
        """測試作業員填報表單驗證"""
        form_data = {
            'operator': '測試作業員',
            'company_name': '測試公司',
            'workorder': 'TEST-001',
            'product_id': 'TEST-PRODUCT',
            'planned_quantity': 100,
            'process': self.process.id,
            'work_date': date.today(),
            'start_time': '08:00',
            'end_time': '17:00',
            'work_quantity': 50,
            'defect_quantity': 2,
        }
        
        form = OperatorFillWorkForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_time_validation(self):
        """測試時間驗證"""
        form_data = {
            'operator': '測試作業員',
            'company_name': '測試公司',
            'workorder': 'TEST-001',
            'product_id': 'TEST-PRODUCT',
            'planned_quantity': 100,
            'process': self.process.id,
            'work_date': date.today(),
            'start_time': '17:00',  # 結束時間早於開始時間
            'end_time': '08:00',
            'work_quantity': 50,
            'defect_quantity': 2,
        }
        
        form = OperatorFillWorkForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('結束時間必須晚於開始時間', str(form.errors))


class FillWorkViewTest(TestCase):
    """填報作業視圖測試"""
    
    def setUp(self):
        """測試前準備"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # 建立測試工序
        from process.models import ProcessName
        self.process = ProcessName.objects.create(
            name='測試工序',
            description='測試用工序'
        )
    
    def test_fill_work_index_view(self):
        """測試填報作業首頁視圖"""
        response = self.client.get(reverse('workorder:fill_work:fill_work_index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workorder/fill_work/fill_index.html')
    
    def test_operator_backfill_view(self):
        """測試作業員補登填報視圖"""
        response = self.client.get(reverse('workorder:fill_work:operator_backfill'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workorder/fill_work/operator_backfill.html')
    
    def test_smt_backfill_view(self):
        """測試SMT補登填報視圖"""
        response = self.client.get(reverse('workorder:fill_work:smt_backfill'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'workorder/fill_work/smt_backfill.html')


class FillWorkAPITest(TestCase):
    """填報作業API測試"""
    
    def setUp(self):
        """測試前準備"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_get_workorder_info_api(self):
        """測試獲取工單資訊API"""
        response = self.client.get(
            reverse('workorder:fill_work:get_workorder_info'),
            {'workorder_id': '1'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
    
    def test_get_workorder_by_product_api(self):
        """測試根據產品編號獲取工單API"""
        response = self.client.get(
            reverse('workorder:fill_work:get_workorder_by_product'),
            {'product_id': 'TEST-PRODUCT'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data) 