"""
時間計算器
提供作業員及設備工時的計算功能，考慮產線設定
"""

from datetime import timedelta, datetime, time
from typing import List, Dict, Any, Optional


class TimeCalculator:
    """用於計算作業員及設備工時的計算器，考慮產線設定"""
    
    def calculate_raw_duration(self, start_time: Optional[datetime], end_time: Optional[datetime]) -> float:
        """計算兩個時間點之間的原始時長（秒）"""
        if start_time and end_time and end_time > start_time:
            return (end_time - start_time).total_seconds()
        return 0

    def calculate_operator_total_work_time(self, reports: List[Any]) -> float:
        """
        工作報表專用 - 作業員
        根據報工記錄計算作業員的總工作時數 (以小時為單位)。
        此計算只統計報工時間段的原始時長，不考慮休息時間，也不區分正常與加班。
        """
        total_duration_seconds = 0
        for report in reports:
            if hasattr(report, 'start_time') and hasattr(report, 'end_time'):
                total_duration_seconds += self.calculate_raw_duration(report.start_time, report.end_time)
        return total_duration_seconds / 3600.0

    def calculate_smt_total_run_time(self, smt_reports: List[Any]) -> float:
        """
        工作報表專用 - SMT設備
        根據SMT報工記錄計算設備的總運行時數 (以小時為單位)。
        """
        total_run_seconds = 0
        for report in smt_reports:
            if hasattr(report, 'start_time') and hasattr(report, 'end_time'):
                total_run_seconds += self.calculate_raw_duration(report.start_time, report.end_time)
        return total_run_seconds / 3600.0

    def calculate_actual_work_and_overtime(self, reports: List[Any], 
                                         line_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        工時報表 - 作業員
        計算作業員在指定報工記錄集合中的正常工時和加班工時。
        會考慮產線的上班時間、休息時間和加班規則。
        """
        if not reports:
            return {
                'total_hours_raw': 0.0, 
                'normal_hours': 0.0, 
                'overtime_hours': 0.0, 
                'break_deduction_hours': 0.0, 
                'details': "無有效報工記錄"
            }
            
        report_date = reports[0].report_date if hasattr(reports[0], 'report_date') else datetime.now().date()

        total_seconds_raw = 0
        normal_seconds = 0
        overtime_seconds = 0
        break_seconds_deducted = 0
        
        details = []

        # 合併並排序報工時間段，處理重疊
        time_intervals = []
        for report in reports:
            if hasattr(report, 'start_time') and hasattr(report, 'end_time'):
                if report.start_time and report.end_time and report.end_time > report.start_time:
                    time_intervals.append((report.start_time, report.end_time))
        
        # 對時間區間進行合併
        merged_intervals = self._merge_time_intervals(time_intervals)

        # 計算原始總時長 (合併後的區間)
        for start_dt, end_dt in merged_intervals:
            total_seconds_raw += (end_dt - start_dt).total_seconds()

        # 如果沒有產線設定，則無法區分正常/加班/休息
        if not line_settings:
            return {
                'total_hours_raw': total_seconds_raw / 3600.0,
                'normal_hours': total_seconds_raw / 3600.0,
                'overtime_hours': 0.0,
                'break_deduction_hours': 0.0,
                'details': "無產線設定，無法精確區分正常/加班/休息"
            }

        # 根據產線設定，定義當天的班次和休息時間
        shift_start_time = line_settings.get('shift_start', time(8, 0))
        shift_end_time = line_settings.get('shift_end', time(17, 0))
        break_start_time = line_settings.get('break_start')
        break_end_time = line_settings.get('break_end')
        overtime_start_time = line_settings.get('overtime_start', shift_end_time)

        shift_start_dt = datetime.combine(report_date, shift_start_time)
        shift_end_dt = datetime.combine(report_date, shift_end_time)
        overtime_start_dt = datetime.combine(report_date, overtime_start_time)

        break_start_dt = datetime.combine(report_date, break_start_time) if break_start_time else None
        break_end_dt = datetime.combine(report_date, break_end_time) if break_end_time else None

        for start_dt, end_dt in merged_intervals:
            # 1. 計算休息時間的扣除
            if break_start_dt and break_end_dt and break_start_dt < break_end_dt:
                overlap_break_start = max(start_dt, break_start_dt)
                overlap_break_end = min(end_dt, break_end_dt)
                if overlap_break_start < overlap_break_end:
                    deducted = (overlap_break_end - overlap_break_start).total_seconds()
                    break_seconds_deducted += deducted
                    details.append(f"從 {start_dt.time()}-{end_dt.time()} 報工中扣除休息時間 ({break_start_dt.time()}-{break_end_dt.time()}): {round(deducted/60, 2)} 分鐘")
            
            # 2. 計算正常工時
            normal_overlap_start = max(start_dt, shift_start_dt)
            normal_overlap_end = min(end_dt, overtime_start_dt)
            
            if normal_overlap_start < normal_overlap_end:
                normal_segment_duration = (normal_overlap_end - normal_overlap_start).total_seconds()
                # 從正常段中扣除休息時間
                normal_segment_deducted_break = self._get_overlap_duration(
                    normal_overlap_start, normal_overlap_end, break_start_dt, break_end_dt
                )
                normal_seconds += (normal_segment_duration - normal_segment_deducted_break)
                details.append(f"從 {start_dt.time()}-{end_dt.time()} 報工中計算正常工時段 ({normal_overlap_start.time()}-{normal_overlap_end.time()})：{round((normal_segment_duration - normal_segment_deducted_break)/3600, 2)} 小時")

            # 3. 計算加班工時
            overtime_overlap_start = max(start_dt, overtime_start_dt)
            overtime_overlap_end = end_dt
            
            if overtime_overlap_start < overtime_overlap_end:
                overtime_segment_duration = (overtime_overlap_end - overtime_overlap_start).total_seconds()
                # 從加班段中扣除休息時間
                overtime_segment_deducted_break = self._get_overlap_duration(
                    overtime_overlap_start, overtime_overlap_end, break_start_dt, break_end_dt
                )
                overtime_seconds += (overtime_segment_duration - overtime_segment_deducted_break)
                details.append(f"從 {start_dt.time()}-{end_dt.time()} 報工中計算加班工時段 ({overtime_overlap_start.time()}-{overtime_overlap_end.time()}): {round((overtime_segment_duration - overtime_segment_deducted_break)/3600, 2)} 小時")

        return {
            'total_hours_raw': total_seconds_raw / 3600.0,
            'normal_hours': normal_seconds / 3600.0,
            'overtime_hours': overtime_seconds / 3600.0,
            'break_deduction_hours': break_seconds_deducted / 3600.0,
            'details': "\n".join(details)
        }

    def calculate_smt_equipment_work_hours(self, smt_reports: List[Any], 
                                         line_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        工時報表 - SMT設備
        計算 SMT 設備的正常運行時數和超時運行時數。
        考慮產線設定中的班次時間。
        """
        if not smt_reports:
            return {
                'total_run_hours_raw': 0.0, 
                'normal_run_hours': 0.0, 
                'overtime_run_hours': 0.0, 
                'down_time_hours': 0.0, 
                'details': "無有效SMT報表記錄"
            }

        report_date = smt_reports[0].report_date if hasattr(smt_reports[0], 'report_date') else datetime.now().date()
        total_run_seconds_raw = 0
        total_down_seconds = 0
        
        details = []

        # 合併並排序設備運行時間段
        time_intervals = []
        for report in smt_reports:
            if hasattr(report, 'start_time') and hasattr(report, 'end_time'):
                if report.start_time and report.end_time and report.end_time > report.start_time:
                    time_intervals.append((report.start_time, report.end_time))
            # 假設 report 還有 down_time_minutes 可以直接從原始報工中獲取停機時間
            if hasattr(report, 'down_time_minutes') and report.down_time_minutes is not None:
                total_down_seconds += report.down_time_minutes * 60

        merged_intervals = self._merge_time_intervals(time_intervals)

        for start_dt, end_dt in merged_intervals:
            total_run_seconds_raw += (end_dt - start_dt).total_seconds()

        total_run_hours_raw = total_run_seconds_raw / 3600.0
        down_time_hours = total_down_seconds / 3600.0

        if not line_settings:
            return {
                'total_run_hours_raw': total_run_hours_raw,
                'normal_run_hours': total_run_hours_raw,
                'overtime_run_hours': 0.0,
                'down_time_hours': down_time_hours,
                'details': "無產線設定，無法精確區分正常/超時運行"
            }
        
        shift_start_time = line_settings.get('shift_start', time(8, 0))
        shift_end_time = line_settings.get('shift_end', time(17, 0))
        overtime_start_time = line_settings.get('overtime_start', shift_end_time)

        shift_start_dt = datetime.combine(report_date, shift_start_time)
        shift_end_dt = datetime.combine(report_date, shift_end_time)
        overtime_start_dt = datetime.combine(report_date, overtime_start_time)

        normal_run_seconds = 0
        overtime_run_seconds = 0

        for start_dt, end_dt in merged_intervals:
            # 計算與正常班次的重疊
            normal_overlap_start = max(start_dt, shift_start_dt)
            normal_overlap_end = min(end_dt, overtime_start_dt)
            
            if normal_overlap_start < normal_overlap_end:
                normal_run_seconds += (normal_overlap_end - normal_overlap_start).total_seconds()
                details.append(f"設備從 {start_dt.time()}-{end_dt.time()} 在正常班次內運行 ({normal_overlap_start.time()}-{normal_overlap_end.time()}): {round((normal_overlap_end - normal_overlap_start).total_seconds()/3600, 2)} 小時")
            
            # 計算與加班時段的重疊
            if end_dt > overtime_start_dt:
                overtime_overlap_start = max(start_dt, overtime_start_dt)
                overtime_overlap_end = end_dt
                
                if overtime_overlap_start < overtime_overlap_end:
                    overtime_run_seconds += (overtime_overlap_end - overtime_overlap_start).total_seconds()
                    details.append(f"設備從 {start_dt.time()}-{end_dt.time()} 超出正常班次運行 (加班) ({overtime_overlap_start.time()}-{overtime_overlap_end.time()}): {round((overtime_overlap_end - overtime_overlap_start).total_seconds()/3600, 2)} 小時")

        return {
            'total_run_hours_raw': total_run_hours_raw,
            'normal_run_hours': normal_run_seconds / 3600.0,
            'overtime_run_hours': overtime_run_seconds / 3600.0,
            'down_time_hours': down_time_hours,
            'details': "\n".join(details)
        }

    def _merge_time_intervals(self, time_intervals: List[tuple]) -> List[tuple]:
        """合併重疊的時間區間"""
        if not time_intervals:
            return []
        
        time_intervals.sort()
        merged_intervals = []
        current_start, current_end = time_intervals[0]
        
        for i in range(1, len(time_intervals)):
            next_start, next_end = time_intervals[i]
            if next_start <= current_end:  # 有重疊或緊密連接
                current_end = max(current_end, next_end)
            else:
                merged_intervals.append((current_start, current_end))
                current_start, current_end = next_start, next_end
        
        merged_intervals.append((current_start, current_end))
        return merged_intervals

    def _get_overlap_duration(self, interval1_start: datetime, interval1_end: datetime, 
                             interval2_start: Optional[datetime], interval2_end: Optional[datetime]) -> float:
        """計算兩個時間區間的重疊時長（秒）"""
        if not interval1_start or not interval1_end or not interval2_start or not interval2_end:
            return 0
        
        overlap_start = max(interval1_start, interval2_start)
        overlap_end = min(interval1_end, interval2_end)
        
        if overlap_start < overlap_end:
            return (overlap_end - overlap_start).total_seconds()
        return 0 