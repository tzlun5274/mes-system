"""
自動假期設定服務
提供台灣國定假日、補班日、週末假期的自動設定功能
"""

import logging
from datetime import datetime, date, timedelta
from .workday_calendar import WorkdayCalendarService

logger = logging.getLogger(__name__)


class HolidayAutoSetupService:
    """自動假期設定服務"""
    
    def __init__(self):
        self.calendar_service = WorkdayCalendarService()
    
    def setup_2025_holidays(self):
        """設定 2025 年台灣國定假日"""
        holidays_2025 = {
            '2025-01-01': '元旦',
            '2025-02-08': '春節',
            '2025-02-09': '春節',
            '2025-02-10': '春節',
            '2025-02-11': '春節',
            '2025-02-12': '春節',
            '2025-02-13': '春節',
            '2025-02-14': '春節',
            '2025-04-04': '清明節',
            '2025-04-05': '清明節',
            '2025-04-06': '清明節',
            '2025-05-01': '勞動節',
            '2025-06-22': '端午節',
            '2025-09-29': '中秋節',
            '2025-10-01': '國慶節',
            '2025-10-02': '國慶節',
            '2025-10-03': '國慶節',
            '2025-10-04': '國慶節',
            '2025-10-05': '國慶節',
            '2025-10-06': '國慶節',
            '2025-10-07': '國慶節',
        }
        
        setup_count = 0
        for date_str, holiday_name in holidays_2025.items():
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                self.calendar_service.add_holiday(
                    date=date_obj,
                    holiday_name=holiday_name,
                    description=f"2025年{holiday_name}",
                    created_by="system"
                )
                setup_count += 1
                logger.info(f"成功設定假期: {holiday_name} ({date_str})")
            except Exception as e:
                logger.error(f"設定假期失敗: {holiday_name} ({date_str}) - {str(e)}")
        
        logger.info(f"2025年假期設定完成，共設定 {setup_count} 個假期")
        return setup_count
    
    def setup_makeup_workdays_2025(self):
        """設定 2025 年補班日"""
        makeup_days_2025 = {
            '2025-02-15': '春節補班',
            '2025-02-16': '春節補班',
            '2025-04-06': '清明節補班',
            '2025-09-28': '中秋節補班',
            '2025-10-11': '國慶節補班',
            '2025-10-12': '國慶節補班',
        }
        
        setup_count = 0
        for date_str, description in makeup_days_2025.items():
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                self.calendar_service.add_workday(
                    date=date_obj,
                    description=description,
                    created_by="system"
                )
                setup_count += 1
                logger.info(f"成功設定補班日: {description} ({date_str})")
            except Exception as e:
                logger.error(f"設定補班日失敗: {description} ({date_str}) - {str(e)}")
        
        logger.info(f"2025年補班日設定完成，共設定 {setup_count} 個補班日")
        return setup_count
    
    def setup_weekly_holidays(self, year=2025):
        """設定週末假期（週六、週日）"""
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        weekend_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            # 週六和週日
            if current_date.weekday() >= 5:
                try:
                    self.calendar_service.add_holiday(
                        date=current_date,
                        holiday_name=f"週末",
                        description=f"{year}年週末",
                        created_by="system"
                    )
                    weekend_count += 1
                except Exception as e:
                    logger.error(f"設定週末假期失敗: {current_date} - {str(e)}")
            
            current_date += timedelta(days=1)
        
        logger.info(f"{year}年週末假期設定完成，共設定 {weekend_count} 個週末")
        return weekend_count
    
    def setup_all_2025(self):
        """設定 2025 年所有假期和補班日"""
        logger.info("開始設定 2025 年假期和補班日...")
        
        # 設定國定假日
        holiday_count = self.setup_2025_holidays()
        
        # 設定補班日
        makeup_count = self.setup_makeup_workdays_2025()
        
        # 設定週末（可選，因為預設邏輯已經處理週末）
        # weekend_count = self.setup_weekly_holidays(2025)
        
        total_count = holiday_count + makeup_count
        logger.info(f"2025年假期設定完成，總共設定 {total_count} 個事件")
        
        return {
            'holidays': holiday_count,
            'makeup_days': makeup_count,
            'total': total_count
        }
    
    def clear_all_holidays(self, year=2025):
        """清除指定年份的所有假期設定"""
        from scheduling.models import Event
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        # 刪除假期和補班日
        deleted_count = Event.objects.filter(
            type__in=['holiday', 'workday'],
            start__date__gte=start_date,
            start__date__lte=end_date,
            created_by='system'
        ).delete()[0]
        
        logger.info(f"清除 {year} 年假期設定完成，共刪除 {deleted_count} 個事件")
        return deleted_count
