"""
CSV 國定假日匯入服務
提供從 CSV 檔案匯入國定假日資料的功能
"""

import logging
import csv
import io
from datetime import datetime
from .workday_calendar import WorkdayCalendarService

logger = logging.getLogger(__name__)


class CSVHolidayImportService:
    """CSV 國定假日匯入服務"""
    
    def __init__(self):
        self.calendar_service = WorkdayCalendarService()
    
    def parse_csv_holidays(self, csv_file):
        """
        解析 CSV 檔案中的國定假日資料
        
        Args:
            csv_file: 上傳的 CSV 檔案
            
        Returns:
            dict: 解析結果 {success: bool, data: list, errors: list}
        """
        holidays = []
        errors = []
        
        try:
            # 讀取 CSV 檔案 - 修正檔案處理邏輯
            if hasattr(csv_file, 'read'):
                # 如果是 Django 上傳的檔案，直接讀取 bytes 並解碼
                content = csv_file.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8-sig')  # 使用 utf-8-sig 處理 BOM
                elif isinstance(content, str):
                    pass  # 已經是字串
                else:
                    content = str(content)
            else:
                content = str(csv_file)
            
            # 處理 BOM 問題
            if content.startswith('\ufeff'):
                content = content[1:]
            
            csv_reader = csv.DictReader(io.StringIO(content))
            
            for row_num, row in enumerate(csv_reader, start=2):  # 從第2行開始（跳過標題）
                try:
                    # 檢查是否為空行或無效行（所有欄位都為空，或只有逗號）
                    if all(not value.strip() for value in row.values()):
                        continue  # 跳過空行
                    
                    # 檢查是否有必要的欄位值
                    subject = row.get('Subject', '').strip()
                    date_str = row.get('Start Date', '').strip()
                    
                    # 如果沒有主題和日期，跳過這行
                    if not subject and not date_str:
                        continue  # 跳過無效行
                    
                    # 檢查是否有假期名稱
                    if not subject:
                        errors.append(f"第 {row_num} 行：缺少假期名稱")
                        continue
                    
                    # 解析日期欄位
                    if not date_str:
                        errors.append(f"第 {row_num} 行：缺少開始日期")
                        continue
                    
                    # 處理不同的日期格式
                    date_obj = self._parse_date(date_str)
                    if not date_obj:
                        errors.append(f"第 {row_num} 行：日期格式錯誤 '{date_str}'")
                        continue
                    
                    # 取得假期名稱
                    subject = row.get('Subject', '').strip()
                    if not subject:
                        errors.append(f"第 {row_num} 行：缺少假期名稱")
                        continue
                    
                    # 檢查是否為全天事件（支援多種欄位名稱）
                    all_day_ev = row.get('All Day Ev', '').strip()
                    all_day_event = row.get('All Day Event', '').strip()
                    all_day = (all_day_ev.upper() in ['TRUE', 'YES', '1', '是'] or 
                              all_day_event.upper() in ['TRUE', 'YES', '1', '是'])
                    
                    # 取得描述
                    description = row.get('Description', '').strip()
                    
                    holidays.append({
                        'date': date_obj,
                        'name': subject,
                        'description': description,
                        'all_day': all_day,
                        'row_num': row_num
                    })
                    
                except Exception as e:
                    errors.append(f"第 {row_num} 行：解析錯誤 - {str(e)}")
                    continue
            
            return {
                'success': len(holidays) > 0,
                'data': holidays,
                'errors': errors,
                'total_rows': len(holidays) + len(errors)
            }
            
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'errors': [f"CSV 檔案解析失敗：{str(e)}"],
                'total_rows': 0
            }
    
    def _parse_date(self, date_str):
        """
        解析日期字串
        
        Args:
            date_str: 日期字串
            
        Returns:
            date: 解析後的日期物件，失敗則返回 None
        """
        # 支援多種日期格式
        date_formats = [
            '%Y/%m/%d',    # 2026/1/1
            '%Y-%m-%d',    # 2026-01-01
            '%Y/%m/%d',    # 2026/01/01
            '%Y-%m-%d',    # 2026-1-1
            '%d/%m/%Y',    # 1/1/2026
            '%d-%m-%Y',    # 1-1-2026
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def import_holidays_from_csv(self, csv_file):
        """
        從 CSV 檔案匯入國定假日
        
        Args:
            csv_file: 上傳的 CSV 檔案
            
        Returns:
            dict: 匯入結果統計
        """
        # 解析 CSV 檔案
        parse_result = self.parse_csv_holidays(csv_file)
        
        if not parse_result['success']:
            return {
                'success': False,
                'message': f"CSV 檔案解析失敗，共 {len(parse_result['errors'])} 個錯誤",
                'imported_count': 0,
                'errors': parse_result['errors']
            }
        
        # 匯入假期資料
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for holiday in parse_result['data']:
            try:
                # 檢查是否已存在
                existing_event = self.calendar_service.add_holiday(
                    date=holiday['date'],
                    holiday_name=holiday['name'],
                    description=holiday['description'],
                    created_by="csv_import"
                )
                
                if existing_event:
                    imported_count += 1
                    logger.info(f"成功匯入假期: {holiday['name']} ({holiday['date']})")
                else:
                    skipped_count += 1
                    logger.info(f"跳過已存在的假期: {holiday['name']} ({holiday['date']})")
                
            except Exception as e:
                error_msg = f"匯入假期失敗: {holiday['name']} ({holiday['date']}) - {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # 回傳結果
        result = {
            'success': imported_count > 0,
            'message': f'CSV 匯入完成！成功匯入 {imported_count} 個假期，跳過 {skipped_count} 個已存在的假期',
            'imported_count': imported_count,
            'skipped_count': skipped_count,
            'total_parsed': len(parse_result['data']),
            'errors': errors + parse_result['errors']
        }
        
        logger.info(f"CSV 假期匯入完成: {result}")
        return result
    
    def generate_sample_csv(self):
        """
        生成範例 CSV 檔案內容
        
        Returns:
            str: CSV 檔案內容
        """
        sample_data = [
            {
                'Subject': '中華民國開國紀念日',
                'Start Date': '2026/1/1',
                'Start Time': '',
                'End Date': '2026/1/1',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/3',
                'Start Time': '',
                'End Date': '2026/1/3',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/4',
                'Start Time': '',
                'End Date': '2026/1/4',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/10',
                'Start Time': '',
                'End Date': '2026/1/10',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/11',
                'Start Time': '',
                'End Date': '2026/1/11',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/17',
                'Start Time': '',
                'End Date': '2026/1/17',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/18',
                'Start Time': '',
                'End Date': '2026/1/18',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/24',
                'Start Time': '',
                'End Date': '2026/1/24',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/25',
                'Start Time': '',
                'End Date': '2026/1/25',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/1/31',
                'Start Time': '',
                'End Date': '2026/1/31',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            },
            {
                'Subject': '例假日',
                'Start Date': '2026/2/1',
                'Start Time': '',
                'End Date': '2026/2/1',
                'End Time': '',
                'All Day Event': 'TRUE',
                'Description': '',
                'Location': ''
            }
        ]
        
        # 生成 CSV 內容
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'Subject', 'Start Date', 'Start Time', 'End Date', 'End Time', 
            'All Day Event', 'Description', 'Location'
        ])
        
        writer.writeheader()
        writer.writerows(sample_data)
        
        return output.getvalue()
