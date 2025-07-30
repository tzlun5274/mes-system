"""
報表模組測試
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta

from .models import WorkReport, WorkOrderReport, WorkHourReport, ReportExportLog
from .services.work_report_service import WorkReportService
from .services.workorder_report_service import WorkOrderReportService
from .services.work_hour_report_service import WorkHourReportService
from .calculators.time_calculator import TimeCalculator


class ReportingModelsTest(TestCase):
    """報表模型測試"""
    
    def setUp(self):
        """測試前準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.today = date.today()
    
    def test_work_report_creation(self):
        """測試工作報表建立"""
        work_report = WorkReport.objects.create(
            report_type='WORK_REPORT',
            report_date=self.today,
            operator=self.user,
            work_order_no='WO001',
            product_sn='PROD001',
            process='測試工序',
            work_quantity=100,
            defect_quantity=5
        )
        
        self.assertEqual(work_report.operator.username, 'testuser')
        self.assertEqual(work_report.work_order_no, 'WO001')
        self.assertEqual(work_report.work_quantity, 100)
        self.assertEqual(work_report.defect_quantity, 5)
    
    def test_workorder_report_creation(self):
        """測試工單報表建立"""
        workorder_report = WorkOrderReport.objects.create(
            report_type='WORKORDER_REPORT',
            report_date=self.today,
            work_order_no='WO001',
            product_sn='PROD001',
            product_name='測試產品',
            total_quantity=1000,
            completed_quantity=800,
            defect_quantity=20,
            status='IN_PROGRESS'
        )
        
        self.assertEqual(workorder_report.work_order_no, 'WO001')
        self.assertEqual(workorder_report.total_quantity, 1000)
        self.assertEqual(workorder_report.completed_quantity, 800)
    
    def test_work_hour_report_creation(self):
        """測試工時報表建立"""
        work_hour_report = WorkHourReport.objects.create(
            report_type='WORK_HOUR_REPORT',
            report_date=self.today,
            operator=self.user,
            total_hours=8.5,
            normal_hours=8.0,
            overtime_hours=0.5,
            break_hours=1.0
        )
        
        self.assertEqual(work_hour_report.operator.username, 'testuser')
        self.assertEqual(work_hour_report.total_hours, 8.5)
        self.assertEqual(work_hour_report.normal_hours, 8.0)
    
    def test_export_log_creation(self):
        """測試匯出日誌建立"""
        export_log = ReportExportLog.objects.create(
            report_type='WORK_REPORT',
            export_format='EXCEL',
            date_range='TODAY',
            export_status='SUCCESS',
            created_by=self.user
        )
        
        self.assertEqual(export_log.report_type, 'WORK_REPORT')
        self.assertEqual(export_log.export_format, 'EXCEL')
        self.assertEqual(export_log.export_status, 'SUCCESS')


class TimeCalculatorTest(TestCase):
    """時間計算器測試"""
    
    def setUp(self):
        """測試前準備"""
        self.calculator = TimeCalculator()
        self.start_time = timezone.now()
        self.end_time = self.start_time + timedelta(hours=2)
    
    def test_calculate_raw_duration(self):
        """測試原始時長計算"""
        duration = self.calculator.calculate_raw_duration(self.start_time, self.end_time)
        self.assertEqual(duration, 7200)  # 2小時 = 7200秒
    
    def test_calculate_raw_duration_invalid(self):
        """測試無效時間計算"""
        duration = self.calculator.calculate_raw_duration(self.end_time, self.start_time)
        self.assertEqual(duration, 0)
    
    def test_get_date_range(self):
        """測試日期範圍獲取"""
        # 測試今日
        today_range = self.calculator.get_date_range('TODAY')
        self.assertEqual(today_range['start_date'], date.today())
        self.assertEqual(today_range['end_date'], date.today())
        
        # 測試自訂範圍
        custom_start = date.today() - timedelta(days=7)
        custom_end = date.today()
        custom_range = self.calculator.get_date_range('CUSTOM', custom_start, custom_end)
        self.assertEqual(custom_range['start_date'], custom_start)
        self.assertEqual(custom_range['end_date'], custom_end)


class ReportServiceTest(TestCase):
    """報表服務測試"""
    
    def setUp(self):
        """測試前準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.work_service = WorkReportService()
        self.workorder_service = WorkOrderReportService()
        self.work_hour_service = WorkHourReportService()
    
    def test_work_report_service_validation(self):
        """測試工作報表服務參數驗證"""
        # 測試有效參數
        valid_params = {
            'date_range': {
                'start_date': date.today(),
                'end_date': date.today()
            }
        }
        self.assertTrue(self.work_service.validate_params(valid_params))
        
        # 測試無效參數
        invalid_params = {
            'date_range': {
                'start_date': date.today(),
                'end_date': date.today() - timedelta(days=1)
            }
        }
        self.assertFalse(self.work_service.validate_params(invalid_params))
    
    def test_get_date_range_methods(self):
        """測試日期範圍方法"""
        # 測試各種日期範圍類型
        date_ranges = ['TODAY', 'YESTERDAY', 'THIS_WEEK', 'LAST_WEEK', 'THIS_MONTH', 'LAST_MONTH']
        
        for range_type in date_ranges:
            try:
                date_range = self.work_service.get_date_range(range_type)
                self.assertIn('start_date', date_range)
                self.assertIn('end_date', date_range)
                self.assertLessEqual(date_range['start_date'], date_range['end_date'])
            except Exception as e:
                self.fail(f"日期範圍 {range_type} 測試失敗: {str(e)}")


class ExportUtilsTest(TestCase):
    """匯出工具測試"""
    
    def test_export_format_validation(self):
        """測試匯出格式驗證"""
        from .utils.export_utils import ExportUtils
        
        export_utils = ExportUtils()
        
        # 測試支援的格式
        supported_formats = ['EXCEL', 'CSV', 'PDF']
        for format_type in supported_formats:
            try:
                # 這裡只是測試格式驗證，不實際匯出
                pass
            except ValueError:
                self.fail(f"格式 {format_type} 應該被支援")
        
        # 測試不支援的格式
        with self.assertRaises(ValueError):
            export_utils.export_report({}, 'WORK_REPORT', 'INVALID_FORMAT', {}) 