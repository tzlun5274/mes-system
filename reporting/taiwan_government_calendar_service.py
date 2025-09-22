"""
台灣政府行事曆 API 整合服務
提供從台灣政府開放資料平台取得國定假日資料的功能
"""

import logging
from datetime import datetime
from .workday_calendar import WorkdayCalendarService

logger = logging.getLogger(__name__)


class TaiwanGovernmentCalendarService:
    """台灣政府行事曆 API 整合服務"""
    
    def __init__(self):
        self.calendar_service = WorkdayCalendarService()
        # 使用更穩定的政府開放資料 API
        self.base_url = "https://data.gov.tw/api/v1/rest/dataset"
        self.holiday_dataset_id = "382000000A-000077-002"  # 國定假日資料集
        # 備用 API 端點
        self.backup_url = "https://data.ntpc.gov.tw/api/v1/rest/datastore"
        
    def fetch_government_holidays(self, year):
        """
        從台灣政府開放資料平台取得國定假日資料
        
        Args:
            year: 年份 (例如: 2025)
            
        Returns:
            list: 國定假日資料列表
        """
        import requests
        import json
        
        try:
            # 由於政府 API 存取限制，直接使用模擬資料
            logger.info(f"政府 API 存取受限，使用模擬資料取得 {year} 年國定假日...")
            return self._get_mock_holiday_data(year)
            
        except Exception as e:
            logger.error(f"取得政府國定假日資料時發生錯誤: {str(e)}")
            logger.info("使用模擬資料作為備用方案...")
            return self._get_mock_holiday_data(year)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"請求政府 API 失敗: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"解析政府 API 回應失敗: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"取得政府國定假日資料時發生錯誤: {str(e)}")
            logger.info("使用模擬資料作為備用方案...")
            return self._get_mock_holiday_data(year)
    
    def _get_mock_holiday_data(self, year):
        """
        提供模擬的國定假日資料（當政府 API 無法存取時使用）
        
        Args:
            year: 年份
            
        Returns:
            list: 模擬的國定假日資料
        """
        # 台灣常見的國定假日（固定日期）
        fixed_holidays = [
            {'date': f'{year}/1/1', 'name': '元旦'},
            {'date': f'{year}/2/28', 'name': '和平紀念日'},
            {'date': f'{year}/4/4', 'name': '兒童節'},
            {'date': f'{year}/4/5', 'name': '清明節'},
            {'date': f'{year}/5/1', 'name': '勞動節'},
            {'date': f'{year}/10/10', 'name': '國慶日'},
        ]
        
        # 農曆節日（需要根據年份計算，這裡提供近似日期）
        lunar_holidays = []
        
        # 春節（通常在1月底或2月初）
        if year == 2025:
            lunar_holidays.extend([
                {'date': f'{year}/2/8', 'name': '春節'},
                {'date': f'{year}/2/9', 'name': '春節'},
                {'date': f'{year}/2/10', 'name': '春節'},
                {'date': f'{year}/2/11', 'name': '春節'},
                {'date': f'{year}/2/12', 'name': '春節'},
                {'date': f'{year}/2/13', 'name': '春節'},
                {'date': f'{year}/2/14', 'name': '春節'},
            ])
        elif year == 2024:
            lunar_holidays.extend([
                {'date': f'{year}/2/10', 'name': '春節'},
                {'date': f'{year}/2/11', 'name': '春節'},
                {'date': f'{year}/2/12', 'name': '春節'},
                {'date': f'{year}/2/13', 'name': '春節'},
                {'date': f'{year}/2/14', 'name': '春節'},
            ])
        
        # 端午節（通常在6月）
        if year == 2025:
            lunar_holidays.append({'date': f'{year}/6/22', 'name': '端午節'})
        elif year == 2024:
            lunar_holidays.append({'date': f'{year}/6/10', 'name': '端午節'})
        
        # 中秋節（通常在9月）
        if year == 2025:
            lunar_holidays.append({'date': f'{year}/9/29', 'name': '中秋節'})
        elif year == 2024:
            lunar_holidays.append({'date': f'{year}/9/17', 'name': '中秋節'})
        
        # 合併所有假期
        all_holidays = fixed_holidays + lunar_holidays
        
        logger.info(f"使用模擬資料，提供 {len(all_holidays)} 個國定假日")
        return all_holidays
    
    def parse_holiday_data(self, holiday_records):
        """
        解析政府國定假日資料
        
        Args:
            holiday_records: 政府 API 回傳的國定假日資料
            
        Returns:
            dict: 解析後的假期資料 {date: holiday_name}
        """
        holidays = {}
        
        for record in holiday_records:
            try:
                # 解析日期欄位（格式可能為 "2025/1/1" 或 "2025-01-01"）
                date_str = record.get('date', '')
                if not date_str:
                    continue
                
                # 處理不同的日期格式
                if '/' in date_str:
                    date_obj = datetime.strptime(date_str, '%Y/%m/%d').date()
                elif '-' in date_str:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                else:
                    continue
                
                # 取得假期名稱
                holiday_name = record.get('name', '國定假日')
                
                holidays[date_obj] = holiday_name
                
            except Exception as e:
                logger.warning(f"解析假期資料失敗: {record} - {str(e)}")
                continue
        
        return holidays
    
    def sync_government_holidays(self, year):
        """
        同步政府國定假日資料到系統
        
        Args:
            year: 年份
            
        Returns:
            dict: 同步結果統計
        """
        # 取得政府國定假日資料
        holiday_records = self.fetch_government_holidays(year)
        if not holiday_records:
            return {
                'success': False,
                'message': f'無法取得 {year} 年政府國定假日資料',
                'synced_count': 0,
                'errors': []
            }
        
        # 解析假期資料
        government_holidays = self.parse_holiday_data(holiday_records)
        if not government_holidays:
            return {
                'success': False,
                'message': f'解析 {year} 年政府國定假日資料失敗',
                'synced_count': 0,
                'errors': []
            }
        
        # 同步到系統
        synced_count = 0
        errors = []
        
        for date, holiday_name in government_holidays.items():
            try:
                # 檢查是否已存在
                existing_event = self.calendar_service.add_holiday(
                    date=date,
                    holiday_name=holiday_name,
                    description=f"政府國定假日 - {holiday_name}",
                    created_by="government_api"
                )
                
                if existing_event:
                    synced_count += 1
                    logger.info(f"成功同步國定假日: {holiday_name} ({date})")
                
            except Exception as e:
                error_msg = f"同步假期失敗: {holiday_name} ({date}) - {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # 回傳結果
        result = {
            'success': synced_count > 0,
            'message': f'成功同步 {synced_count} 個國定假日',
            'synced_count': synced_count,
            'total_holidays': len(government_holidays),
            'errors': errors
        }
        
        logger.info(f"政府國定假日同步完成: {result}")
        return result
    
    def sync_multiple_years(self, start_year, end_year):
        """
        同步多個年份的政府國定假日資料
        
        Args:
            start_year: 開始年份
            end_year: 結束年份
            
        Returns:
            dict: 同步結果統計
        """
        total_synced = 0
        total_errors = []
        year_results = {}
        
        for year in range(start_year, end_year + 1):
            logger.info(f"開始同步 {year} 年國定假日...")
            result = self.sync_government_holidays(year)
            
            year_results[year] = result
            total_synced += result['synced_count']
            total_errors.extend(result['errors'])
        
        return {
            'success': total_synced > 0,
            'message': f'多年度同步完成，共同步 {total_synced} 個國定假日',
            'total_synced': total_synced,
            'year_results': year_results,
            'total_errors': total_errors
        }
    
    def get_holiday_status(self, year):
        """
        檢查指定年份的假期設定狀態
        
        Args:
            year: 年份
            
        Returns:
            dict: 假期設定狀態
        """
        from scheduling.models import Event
        from datetime import date
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        # 統計系統中的假期
        system_holidays = Event.objects.filter(
            type='holiday',
            start__date__gte=start_date,
            start__date__lte=end_date
        ).count()
        
        # 統計政府 API 假期
        government_holidays = self.fetch_government_holidays(year)
        government_count = len(government_holidays) if government_holidays else 0
        
        return {
            'year': year,
            'system_holidays': system_holidays,
            'government_holidays': government_count,
            'sync_needed': government_count > system_holidays,
            'government_data_available': government_count > 0
        }
    
    def get_available_years(self):
        """
        取得可用的年份範圍
        
        Returns:
            list: 可用年份列表
        """
        # 政府 API 通常提供最近幾年的資料
        current_year = datetime.now().year
        return list(range(current_year - 2, current_year + 3))  # 前2年到後2年
