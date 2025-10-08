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
        self._email_service = None
    
    
    @property
    def email_service(self):
        """延遲載入郵件服務"""
        if self._email_service is None:
            from .email_service import EmailService
            self._email_service = EmailService()
        return self._email_service
    
    
    def execute_single_schedule(self, schedule):
        """執行單一排程 - 使用統一執行器"""
        try:
            logger.info(f"開始執行排程: {schedule.name} ({schedule.report_type})")
            
            # 使用統一執行器
            from .unified_report_executor import UnifiedReportExecutor
            executor = UnifiedReportExecutor()
            
            # 根據報表類型執行對應的任務
            if schedule.report_type == 'data_sync':
                # 資料同步
                result = executor.execute_data_sync()
            else:
                # 報表生成
                result = executor.execute_report(schedule)
            
            # 記錄執行結果
            if result['success']:
                self._log_execution(schedule, 'success', result.get('message', '執行成功'), result.get('file_path'))
            else:
                self._log_execution(schedule, 'failed', result.get('message', '執行失敗'))
            
            return result
            
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
                    # 使用統一的執行方法
                    self.execute_single_schedule(schedule)
                        
                except Exception as e:
                    logger.error(f"執行排程 {schedule.name} 失敗: {str(e)}")
                    self._log_execution(schedule, 'failed', str(e))
                    
        except Exception as e:
            logger.error(f"執行排程報表失敗: {str(e)}")
    
    
    def _log_execution(self, schedule, status, message, file_path=None):
        """記錄執行日誌"""
        try:
            ReportExecutionLog.objects.create(
                report_schedule_id=str(schedule.id),
                report_schedule_name=schedule.name,
                status=status,
                message=message,
                file_path=file_path or ''
            )
        except Exception as e:
            logger.error(f"記錄執行日誌失敗: {str(e)}")
    
    
    def get_report_date(self):
        """取得前一個工作日的日期"""
        from .workday_calendar import WorkdayCalendarService
        calendar_service = WorkdayCalendarService()
        return calendar_service.get_previous_workday(timezone.now().date())
    
    def should_execute(self):
        """判斷是否應該執行前一個工作日報表 - 移除時間檢查，直接執行"""
        return True
    
    
