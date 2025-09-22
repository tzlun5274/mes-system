"""
排程調度器
只負責調度邏輯，不包含具體的業務邏輯
"""

import logging
from django.utils import timezone
from .models import ReportSchedule, ReportExecutionLog

logger = logging.getLogger(__name__)


class ReportScheduler:
    """報表排程調度器 - 只負責調度邏輯"""
    
    def __init__(self):
        # 動態導入避免循環依賴
        self._report_generator = None
        self._email_service = None
        self._data_sync = None
    
    @property
    def report_generator(self):
        """延遲載入報表生成器"""
        if self._report_generator is None:
            from .report_generator import ReportGenerator
            self._report_generator = ReportGenerator()
        return self._report_generator
    
    @property
    def email_service(self):
        """延遲載入郵件服務"""
        if self._email_service is None:
            from .email_service import EmailService
            self._email_service = EmailService()
        return self._email_service
    
    @property
    def data_sync(self):
        """延遲載入資料同步服務"""
        if self._data_sync is None:
            from .data_sync import DataSyncService
            self._data_sync = DataSyncService()
        return self._data_sync
    
    def execute_single_schedule(self, schedule):
        """執行單一排程"""
        try:
            # 檢查是否該執行
            if self._should_execute_schedule(schedule):
                return self._execute_schedule(schedule)
            else:
                return {
                    'success': False,
                    'message': '當前時間未到執行時間，跳過執行'
                }
        except Exception as e:
            logger.error(f"執行排程 {schedule.name} 失敗: {str(e)}")
            self._log_execution(schedule, 'failed', str(e))
            return {
                'success': False,
                'message': f'執行排程失敗: {str(e)}'
            }
    
    def execute_scheduled_reports(self):
        """執行所有排程報表"""
        try:
            # 取得所有啟用的排程
            schedules = ReportSchedule.objects.filter(status='active')
            
            for schedule in schedules:
                try:
                    # 檢查是否該執行
                    if self._should_execute_schedule(schedule):
                        self._execute_schedule(schedule)
                        
                except Exception as e:
                    logger.error(f"執行排程 {schedule.name} 失敗: {str(e)}")
                    self._log_execution(schedule, 'failed', str(e))
                    
        except Exception as e:
            logger.error(f"執行排程報表失敗: {str(e)}")
    
    def _execute_schedule(self, schedule):
        """執行指定的排程"""
        try:
            # 根據報表類型調用對應的服務
            if schedule.report_type == 'data_sync':
                result = self.data_sync.execute_sync(schedule)
            elif schedule.report_type == 'previous_workday':
                result = self.report_generator.execute_previous_workday_report(schedule)
            elif schedule.report_type in ['current_week', 'previous_week']:
                result = self.report_generator.execute_weekly_report(schedule)
            elif schedule.report_type in ['current_month', 'previous_month']:
                result = self.report_generator.execute_monthly_report(schedule)
            elif schedule.report_type in ['current_quarter', 'previous_quarter']:
                result = self.report_generator.execute_quarterly_report(schedule)
            elif schedule.report_type in ['current_year', 'previous_year']:
                result = self.report_generator.execute_yearly_report(schedule)
            else:
                raise ValueError(f"不支援的報表類型: {schedule.report_type}")
            
            if result['success']:
                # 記錄成功執行
                self._log_execution(schedule, 'success', f'報表生成成功: {result["filename"]}', result['file_path'])
            
            return result
                    
        except Exception as e:
            logger.error(f"執行排程 {schedule.name} 失敗: {str(e)}")
            self._log_execution(schedule, 'failed', str(e))
            return {
                'success': False,
                'message': f'執行排程失敗: {str(e)}'
            }
    
    def _should_execute_schedule(self, schedule):
        """判斷是否應該執行排程"""
        now = timezone.localtime(timezone.now())
        
        if schedule.report_type == 'data_sync':
            return self._should_execute_data_sync(schedule)
        elif schedule.report_type == 'previous_workday':
            # 每天早上10點後執行前一個工作日報表
            return now.hour >= 10
        elif schedule.report_type in ['current_week', 'previous_week']:
            return self._should_execute_weekly_schedule(schedule, now)
        elif schedule.report_type in ['current_month', 'previous_month']:
            return self._should_execute_monthly_schedule(schedule, now)
        elif schedule.report_type in ['current_quarter', 'previous_quarter']:
            return self._should_execute_quarterly_schedule(schedule, now)
        elif schedule.report_type in ['current_year', 'previous_year']:
            return self._should_execute_yearly_schedule(schedule, now)
        else:
            raise ValueError(f"不支援的報表類型: {schedule.report_type}")
    
    def _log_execution(self, schedule, status, message, file_path=None):
        """記錄執行日誌"""
        try:
            ReportExecutionLog.objects.create(
                schedule=schedule,
                status=status,
                message=message,
                file_path=file_path or '',
                executed_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"記錄執行日誌失敗: {str(e)}")
    
    # 時間檢查方法
    def _should_execute_data_sync(self, schedule):
        """判斷填報與現場記錄資料同步是否應該執行"""
        now = timezone.localtime(timezone.now())
        
        if schedule.sync_execution_type == 'interval':
            # 間隔執行：根據設定的分鐘數判斷
            sync_minutes = schedule.sync_interval_minutes
            if sync_minutes and sync_minutes > 0:
                # 檢查上次執行時間
                last_log = ReportExecutionLog.objects.filter(
                    schedule=schedule,
                    status='success'
                ).order_by('-executed_at').first()
                
                if last_log:
                    time_diff = now - last_log.executed_at
                    return time_diff.total_seconds() >= (sync_minutes * 60)
                else:
                    # 第一次執行
                    return True
            return False
        elif schedule.sync_execution_type == 'fixed_time':
            # 固定時間執行：檢查是否到了指定時間
            if schedule.schedule_time:
                schedule_hour = schedule.schedule_time.hour
                schedule_minute = schedule.schedule_time.minute
                return now.hour == schedule_hour and now.minute == schedule_minute
            return True
        else:
            return True
    
    def _should_execute_weekly_schedule(self, schedule, now):
        """判斷週報表是否應該執行"""
        if schedule.schedule_day:
            # 如果設定了週幾，檢查今天是否是指定的週幾
            target_weekday = schedule.schedule_day - 1
            if target_weekday == 7:  # 週日
                target_weekday = 6
            
            if now.weekday() == target_weekday:
                if schedule.schedule_time:
                    schedule_hour = schedule.schedule_time.hour
                    schedule_minute = schedule.schedule_time.minute
                    return now.hour > schedule_hour or (now.hour == schedule_hour and now.minute >= schedule_minute)
                else:
                    return now.hour >= 9
        else:
            # 預設每週一執行
            if now.weekday() == 0:  # 週一
                if schedule.schedule_time:
                    schedule_hour = schedule.schedule_time.hour
                    schedule_minute = schedule.schedule_time.minute
                    return now.hour > schedule_hour or (now.hour == schedule_hour and now.minute >= schedule_minute)
                else:
                    return now.hour >= 9
        return False
    
    def _should_execute_monthly_schedule(self, schedule, now):
        """判斷月報表是否應該執行"""
        if schedule.schedule_day:
            # 如果設定了日期，檢查今天是否是指定的日期
            if now.day == schedule.schedule_day:
                if schedule.schedule_time:
                    schedule_hour = schedule.schedule_time.hour
                    schedule_minute = schedule.schedule_time.minute
                    return now.hour > schedule_hour or (now.hour == schedule_hour and now.minute >= schedule_minute)
                else:
                    return now.hour >= 9
        else:
            # 預設每月1號執行
            if now.day == 1:
                if schedule.schedule_time:
                    schedule_hour = schedule.schedule_time.hour
                    schedule_minute = schedule.schedule_time.minute
                    return now.hour > schedule_hour or (now.hour == schedule_hour and now.minute >= schedule_minute)
                else:
                    return now.hour >= 9
        return False
    
    def _should_execute_quarterly_schedule(self, schedule, now):
        """判斷季報表是否應該執行"""
        # 季報表在每季的第一個月執行
        current_month = now.month
        if current_month in [1, 4, 7, 10]:  # 每季的第一個月
            if schedule.schedule_day:
                if now.day == schedule.schedule_day:
                    if schedule.schedule_time:
                        schedule_hour = schedule.schedule_time.hour
                        schedule_minute = schedule.schedule_time.minute
                        return now.hour > schedule_hour or (now.hour == schedule_hour and now.minute >= schedule_minute)
                    else:
                        return now.hour >= 9
            else:
                # 預設每季第一個月1號執行
                if now.day == 1:
                    if schedule.schedule_time:
                        schedule_hour = schedule.schedule_time.hour
                        schedule_minute = schedule.schedule_time.minute
                        return now.hour > schedule_hour or (now.hour == schedule_hour and now.minute >= schedule_minute)
                    else:
                        return now.hour >= 9
        return False
    
    def _should_execute_yearly_schedule(self, schedule, now):
        """判斷年報表是否應該執行"""
        # 年報表在每年1月執行
        if now.month == 1:
            if schedule.schedule_day:
                if now.day == schedule.schedule_day:
                    if schedule.schedule_time:
                        schedule_hour = schedule.schedule_time.hour
                        schedule_minute = schedule.schedule_time.minute
                        return now.hour > schedule_hour or (now.hour == schedule_hour and now.minute >= schedule_minute)
                    else:
                        return now.hour >= 9
            else:
                # 預設每年1月1號執行
                if now.day == 1:
                    if schedule.schedule_time:
                        schedule_hour = schedule.schedule_time.hour
                        schedule_minute = schedule.schedule_time.minute
                        return now.hour > schedule_hour or (now.hour == schedule_hour and now.minute >= schedule_minute)
                    else:
                        return now.hour >= 9
        return False
    
    def get_report_date(self):
        """取得前一個工作日的日期"""
        from .workday_calendar import WorkdayCalendarService
        calendar_service = WorkdayCalendarService()
        return calendar_service.get_previous_workday(timezone.now().date())
    
    def should_execute(self):
        """判斷是否應該執行前一個工作日報表"""
        now = timezone.localtime(timezone.now())
        # 每天早上10點後執行前一個工作日報表
        return now.hour >= 10
    
    def collect_data(self, report_date):
        """收集前一個工作日的資料"""
        from .report_generator import ReportGenerator
        generator = ReportGenerator()
        return generator._collect_previous_workday_data(report_date)
