# -*- coding: utf-8 -*-
"""
統一報表執行器
負責所有報表類型的統一執行邏輯
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


class UnifiedReportExecutor:
    """統一報表執行器 - 負責所有報表類型的統一執行邏輯"""
    
    def __init__(self):
        self._data_collector = None
        self._report_generator = None
        self._email_service = None
    
    @property
    def data_collector(self):
        """延遲載入資料收集器"""
        if self._data_collector is None:
            from .data_collector import DataCollector
            self._data_collector = DataCollector()
        return self._data_collector
    
    @property
    def report_generator(self):
        """延遲載入報表生成器"""
        if self._report_generator is None:
            from .report_formatter import ReportFormatter
            self._report_generator = ReportFormatter()
        return self._report_generator
    
    @property
    def email_service(self):
        """延遲載入郵件服務"""
        if self._email_service is None:
            from .email_service import EmailService
            self._email_service = EmailService()
        return self._email_service
    
    def execute_report(self, schedule) -> Dict[str, Any]:
        """
        執行報表生成 - 統一的報表執行入口
        
        Args:
            schedule: 報表排程物件
            
        Returns:
            執行結果字典
        """
        try:
            logger.info(f"開始執行報表: {schedule.name} ({schedule.report_type})")
            
            # 1. 建立 ReportConfig
            report_config = self._create_report_config(schedule)
            
            # 2. 計算日期範圍
            date_range = self._calculate_date_range(schedule.report_type)
            
            # 3. 收集資料
            data = self._collect_report_data(date_range, schedule.company)
            
            # 4. 生成檔案
            report_files = self._generate_report_files(data, schedule, report_config)
            
            # 5. 發送郵件（如果有設定收件人）
            if schedule.email_recipients and schedule.email_recipients.strip():
                self._send_report_email(schedule, report_files, data)
            
            # 6. 準備結果
            result = {
                'success': True,
                'message': f'{schedule.name} 執行成功',
                'filename': self._get_filename_from_files(report_files),
                'file_path': self._get_filepath_from_files(report_files),
                'excel_path': report_files.get('excel'),
                'html_path': report_files.get('html'),
                'data_summary': self._get_data_summary(data)
            }
            
            logger.info(f"報表執行成功: {schedule.name}")
            return result
            
        except Exception as e:
            logger.error(f"報表執行失敗: {schedule.name} - {str(e)}")
            return {
                'success': False,
                'message': f'報表執行失敗: {str(e)}',
                'filename': '',
                'file_path': '',
                'excel_path': None,
                'html_path': None
            }
    
    def execute_data_sync(self) -> Dict[str, Any]:
        """
        執行資料同步
        
        Returns:
            執行結果字典
        """
        try:
            from .data_sync import sync_data
            
            logger.info("開始執行資料同步")
            result = sync_data()
            
            if result['success']:
                logger.info(f"資料同步成功: {result['message']}")
                return {
                    'success': True,
                    'message': result['message'],
                    'filename': '',
                    'file_path': ''
                }
            else:
                logger.error(f"資料同步失敗: {result.get('error', '未知錯誤')}")
                return {
                    'success': False,
                    'message': f"資料同步失敗: {result.get('error', '未知錯誤')}",
                    'filename': '',
                    'file_path': ''
                }
                
        except Exception as e:
            logger.error(f"資料同步執行失敗: {str(e)}")
            return {
                'success': False,
                'message': f'資料同步執行失敗: {str(e)}',
                'filename': '',
                'file_path': ''
            }
    
    def _create_report_config(self, schedule):
        """建立報表配置"""
        from .report_config import ReportConfig
        
        return ReportConfig(
            report_type=schedule.report_type,
            company_code=schedule.company,
            recipients=schedule.email_recipients.split(',') if schedule.email_recipients else [],
            file_format=schedule.file_format
        )
    
    def _calculate_date_range(self, report_type: str) -> Dict[str, date]:
        """計算報表日期範圍"""
        from .workday_calendar import WorkdayCalendarService
        
        calendar_service = WorkdayCalendarService()
        today = date.today()
        
        if report_type == 'previous_workday':
            # 前一個工作日 - 如果沒有資料則使用最近有資料的日期
            start_date = end_date = calendar_service.get_previous_workday(today)
            
            # 檢查該日期是否有資料，如果沒有則使用最近有資料的日期
            from .models import WorkOrderReportData
            if not WorkOrderReportData.objects.filter(work_date=start_date).exists():
                # 往前找最近有資料的日期
                recent_dates = WorkOrderReportData.objects.values_list('work_date', flat=True).order_by('-work_date')[:1]
                if recent_dates:
                    start_date = end_date = recent_dates[0]
                    logger.info(f"前一個工作日 {calendar_service.get_previous_workday(today)} 無資料，使用最近有資料的日期 {start_date}")
            
        elif report_type == 'previous_week':
            # 上週報表
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            start_date = last_monday
            end_date = last_sunday
            
        elif report_type == 'previous_month':
            # 上月報表
            if today.month == 1:
                start_date = date(today.year - 1, 12, 1)
                end_date = date(today.year - 1, 12, 31)
            else:
                from calendar import monthrange
                start_date = date(today.year, today.month - 1, 1)
                # 取得上個月的實際最後一天
                last_day = monthrange(today.year, today.month - 1)[1]
                end_date = date(today.year, today.month - 1, last_day)
                
        elif report_type == 'previous_quarter':
            # 上季報表
            from calendar import monthrange
            current_quarter = (today.month - 1) // 3 + 1
            if current_quarter == 1:
                start_date = date(today.year - 1, 10, 1)
                end_date = date(today.year - 1, 12, 31)
            else:
                quarter_start_month = (current_quarter - 2) * 3 + 1
                quarter_end_month = quarter_start_month + 2
                start_date = date(today.year, quarter_start_month, 1)
                # 取得季末月份的實際最後一天
                last_day = monthrange(today.year, quarter_end_month)[1]
                end_date = date(today.year, quarter_end_month, last_day)
                
        elif report_type == 'previous_year':
            # 去年報表
            start_date = date(today.year - 1, 1, 1)
            end_date = date(today.year - 1, 12, 31)
            
        else:
            # 預設使用前一個工作日
            start_date = end_date = calendar_service.get_previous_workday(today)
        
        return {
            'start_date': start_date,
            'end_date': end_date
        }
    
    def _collect_report_data(self, date_range: Dict[str, date], company_code: str) -> Dict[str, Any]:
        """收集報表資料"""
        try:
            result = self.data_collector.collect_report_data(
                start_date=date_range['start_date'],
                end_date=date_range['end_date'],
                company_code=company_code
            )
            
            if not result.get('success', False):
                logger.error(f"資料收集失敗: {result.get('error', '未知錯誤')}")
                return {
                    'success': False,
                    'error': result.get('error', '資料收集失敗'),
                    'summary': {},
                    'detailed_data': []
                }
            
            # 在結果中添加報表日期資訊
            result['report_date'] = date_range['start_date']
            result['start_date'] = date_range['start_date']
            result['end_date'] = date_range['end_date']
            
            return result
            
        except Exception as e:
            logger.error(f"資料收集異常: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'summary': {},
                'detailed_data': []
            }
    
    def _generate_report_files(self, data: Dict[str, Any], schedule, report_config) -> Dict[str, str]:
        """生成報表檔案"""
        try:
            report_files = {}
            
            if schedule.file_format in ['html', 'both']:
                html_path = self._generate_html_report(data, schedule, report_config)
                if html_path:
                    report_files['html'] = html_path
            
            if schedule.file_format in ['excel', 'both']:
                excel_path = self._generate_excel_report(data, schedule, report_config)
                if excel_path:
                    report_files['excel'] = excel_path
            
            return report_files
            
        except Exception as e:
            logger.error(f"報表檔案生成失敗: {str(e)}")
            raise
    
    def _generate_html_report(self, data: Dict[str, Any], schedule, report_config) -> Optional[str]:
        """生成 HTML 報表"""
        try:
            # 根據報表類型生成正確的標題
            report_title = self._get_report_title(schedule.report_type, schedule.name)
            html_path = self.report_generator.generate_html_report(data, report_title, schedule)
            return html_path
            
        except Exception as e:
            logger.error(f"HTML 報表生成失敗: {str(e)}")
            raise
    
    def _generate_excel_report(self, data: Dict[str, Any], schedule, report_config) -> Optional[str]:
        """生成 Excel 報表"""
        try:
            # 根據報表類型生成正確的標題
            report_title = self._get_report_title(schedule.report_type, schedule.name)
            excel_path = self.report_generator.generate_excel_report(data, report_title, schedule)
            return excel_path
            
        except Exception as e:
            logger.error(f"Excel 報表生成失敗: {str(e)}")
            raise
    
    def _send_report_email(self, schedule, report_files: Dict[str, str], data: Dict[str, Any]):
        """發送報表郵件"""
        try:
            if not schedule.email_recipients or not schedule.email_recipients.strip():
                return
            
            # 檢查收件人
            recipients = [email.strip() for email in schedule.email_recipients.split(',') if email.strip()]
            if not recipients:
                logger.info(f"排程 {schedule.name} 沒有有效的收件人，跳過郵件發送")
                return
            
            # 準備郵件結果資料
            email_result = {
                'success': True,
                'message': f'{schedule.name} 執行成功',
                'filename': self._get_filename_from_files(report_files),
                'file_path': self._get_filepath_from_files(report_files),
                'excel_path': report_files.get('excel'),
                'html_path': report_files.get('html'),
                'data_summary': self._get_data_summary(data)
            }
            
            # 使用 EmailService 發送郵件
            success = self.email_service.send_report_email(schedule, email_result)
            
            if success:
                logger.info(f"報表郵件發送成功: {schedule.name}")
            else:
                logger.warning(f"報表郵件發送失敗: {schedule.name}")
            
        except Exception as e:
            logger.error(f"報表郵件發送失敗: {str(e)}")
            # 不拋出異常，避免影響報表生成
    
    def _generate_email_content(self, data: Dict[str, Any], schedule) -> str:
        """生成郵件內容"""
        summary = data.get('summary', {})
        
        html_content = f"""
        <html>
        <body>
            <h2>{schedule.name}</h2>
            <p>報表生成時間: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h3>資料摘要</h3>
            <ul>
                <li>總記錄數: {summary.get('total_records', 0)}</li>
                <li>總工作時數: {summary.get('total_work_hours', 0)}</li>
                <li>作業員數: {summary.get('operator_count', 0)}</li>
                <li>設備數: {summary.get('equipment_count', 0)}</li>
            </ul>
            
            <p>詳細報表請查看附件。</p>
        </body>
        </html>
        """
        
        return html_content
    
    def _get_filename_from_files(self, report_files: Dict[str, str]) -> str:
        """從檔案路徑中取得檔名"""
        if not report_files:
            return ''
        
        # 優先返回 Excel 檔案名，如果沒有則返回 HTML 檔案名
        if 'excel' in report_files and report_files['excel']:
            return report_files['excel'].split('/')[-1]
        elif 'html' in report_files and report_files['html']:
            return report_files['html'].split('/')[-1]
        
        return ''
    
    def _get_filepath_from_files(self, report_files: Dict[str, str]) -> str:
        """從檔案路徑中取得檔案路徑"""
        if not report_files:
            return ''
        
        # 優先返回 Excel 檔案路徑，如果沒有則返回 HTML 檔案路徑
        if 'excel' in report_files and report_files['excel']:
            return report_files['excel']
        elif 'html' in report_files and report_files['html']:
            return report_files['html']
        
        return ''
    
    def _get_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """取得資料摘要"""
        summary = data.get('summary', {})
        return {
            'total_records': summary.get('total_records', 0),
            'total_work_hours': summary.get('total_work_hours', 0),
            'operator_count': summary.get('operator_count', 0),
            'equipment_count': summary.get('equipment_count', 0)
        }
    
    def _get_report_title(self, report_type: str, schedule_name: str) -> str:
        """根據報表類型生成正確的標題"""
        from datetime import date
        from .workday_calendar import WorkdayCalendarService
        
        calendar_service = WorkdayCalendarService()
        today = date.today()
        
        if report_type == 'previous_workday':
            # 使用前一個工作日的實際日期
            previous_workday = calendar_service.get_previous_workday(today)
            return f"前一個工作日報表 ({previous_workday})"
        elif report_type == 'previous_week':
            # 計算上週的日期範圍
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            return f"上週報表 ({last_monday} 至 {last_sunday})"
        elif report_type == 'previous_month':
            # 計算上月的日期範圍
            from calendar import monthrange
            if today.month == 1:
                start_date = date(today.year - 1, 12, 1)
                end_date = date(today.year - 1, 12, 31)
            else:
                start_date = date(today.year, today.month - 1, 1)
                # 取得上個月的實際最後一天
                last_day = monthrange(today.year, today.month - 1)[1]
                end_date = date(today.year, today.month - 1, last_day)
            return f"上月報表 ({start_date} 至 {end_date})"
        elif report_type == 'previous_quarter':
            # 計算上季的日期範圍
            from calendar import monthrange
            current_quarter = (today.month - 1) // 3 + 1
            if current_quarter == 1:
                start_date = date(today.year - 1, 10, 1)
                end_date = date(today.year - 1, 12, 31)
            else:
                quarter_start_month = (current_quarter - 2) * 3 + 1
                quarter_end_month = quarter_start_month + 2
                start_date = date(today.year, quarter_start_month, 1)
                # 取得季末月份的實際最後一天
                last_day = monthrange(today.year, quarter_end_month)[1]
                end_date = date(today.year, quarter_end_month, last_day)
            return f"上季報表 ({start_date} 至 {end_date})"
        elif report_type == 'previous_year':
            # 去年報表
            start_date = date(today.year - 1, 1, 1)
            end_date = date(today.year - 1, 12, 31)
            return f"去年報表 ({start_date} 至 {end_date})"
        elif report_type == 'data_sync':
            return f"資料同步報表 ({today})"
        else:
            # 使用排程名稱作為標題
            return f"{schedule_name} ({today})"
