"""
報表服務模組
提供各種報表功能的業務邏輯
採用彙總+詳細分離策略，解決資料增長問題
"""

from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
from decimal import Decimal
import logging

from .models import WorkTimeReportSummary, WorkTimeReportDetail, ReportArchive

logger = logging.getLogger(__name__)


class WorkTimeReportService:
    """工作時數報表服務"""
    
    def __init__(self, company_code=None):
        self.company_code = company_code
    
    def generate_daily_work_time_report(self, report_date, company_code=None):
        """
        生成日工作時數報表
        
        Args:
            report_date: 報表日期
            company_code: 公司代號
            
        Returns:
            DailyReportSummary: 彙總資料
        """
        company_code = company_code or self.company_code
        if not company_code:
            raise ValueError("公司代號不能為空")
        
        try:
            # 從填報作業獲取資料
            from workorder.fill_work.models import FillWork
            fill_works = FillWork.objects.filter(
                work_date=report_date,
                company_name=company_code,
                approval_status='approved'
            )
            
            # 從現場報工獲取資料
            from workorder.onsite_reporting.models import OnsiteReport
            onsite_reports = OnsiteReport.objects.filter(
                work_date=report_date,
                company_code=company_code,
                status='completed'
            )
            
            # 計算統計資料
            total_work_hours = Decimal('0.00')
            total_overtime_hours = Decimal('0.00')
            total_work_quantity = 0
            total_defect_quantity = 0
            total_good_quantity = 0
            unique_operators = set()
            unique_equipment = set()
            unique_workorders = set()
            
            # 處理填報作業資料
            for fill_work in fill_works:
                work_hours = fill_work.work_hours_calculated or Decimal('0')
                total_work_hours += work_hours
                
                # 計算加班時數（超過8小時的部分）
                if work_hours > 8:
                    total_overtime_hours += work_hours - 8
                
                total_work_quantity += fill_work.work_quantity or 0
                total_defect_quantity += fill_work.defect_quantity or 0
                total_good_quantity += (fill_work.work_quantity or 0) - (fill_work.defect_quantity or 0)
                
                unique_operators.add(fill_work.operator)
                unique_workorders.add(fill_work.workorder)
            
            # 處理現場報工資料
            for onsite_report in onsite_reports:
                work_minutes = onsite_report.work_minutes or 0
                work_hours = Decimal(str(work_minutes / 60)).quantize(Decimal('0.01'))
                total_work_hours += work_hours
                
                # 計算加班時數
                if work_hours > 8:
                    total_overtime_hours += work_hours - 8
                
                unique_operators.add(onsite_report.operator)
                unique_workorders.add(onsite_report.workorder)
            
            # 計算效率指標
            efficiency_rate = self._calculate_efficiency_rate(total_work_hours, total_work_quantity)
            defect_rate = self._calculate_defect_rate(total_good_quantity, total_defect_quantity)
            completion_rate = self._calculate_completion_rate(unique_workorders)
            
            # 建立或更新彙總資料
            summary, created = WorkTimeReportSummary.objects.get_or_create(
                report_date=report_date,
                company_code=company_code,
                report_type='work_time',
                time_dimension='daily',
                defaults={
                    'company_name': self._get_company_name(company_code),
                    'total_work_hours': total_work_hours,
                    'total_overtime_hours': total_overtime_hours,
                    'total_work_quantity': total_work_quantity,
                    'total_defect_quantity': total_defect_quantity,
                    'total_good_quantity': total_good_quantity,
                    'efficiency_rate': efficiency_rate,
                    'defect_rate': defect_rate,
                    'completion_rate': completion_rate,
                    'unique_operators_count': len(unique_operators),
                    'unique_equipment_count': len(unique_equipment),
                    'total_workorders_count': len(unique_workorders),
                }
            )
            
            if not created:
                # 更新現有記錄
                summary.total_work_hours = total_work_hours
                summary.total_overtime_hours = total_overtime_hours
                summary.total_work_quantity = total_work_quantity
                summary.total_defect_quantity = total_defect_quantity
                summary.total_good_quantity = total_good_quantity
                summary.efficiency_rate = efficiency_rate
                summary.defect_rate = defect_rate
                summary.completion_rate = completion_rate
                summary.unique_operators_count = len(unique_operators)
                summary.unique_equipment_count = len(unique_equipment)
                summary.total_workorders_count = len(unique_workorders)
                summary.save()
            
            # 建立詳細資料
            self._create_work_time_detail(summary, fill_works, onsite_reports)
            
            return summary
            
        except Exception as e:
            logger.error(f"生成日工作時數報表失敗: {str(e)}")
            raise
    
    def generate_weekly_work_time_report(self, week_start_date, company_code=None):
        """
        生成週工作時數報表
        
        Args:
            week_start_date: 週開始日期
            company_code: 公司代號
            
        Returns:
            DailyReportSummary: 彙總資料
        """
        company_code = company_code or self.company_code
        week_end_date = week_start_date + timedelta(days=6)
        
        # 獲取週內所有日報表資料
        daily_summaries = WorkTimeReportSummary.objects.filter(
            report_date__range=[week_start_date, week_end_date],
            company_code=company_code,
            report_type='work_time',
            time_dimension='daily'
        )
        
        # 彙總週資料
        total_work_hours = sum(s.total_work_hours for s in daily_summaries)
        total_overtime_hours = sum(s.total_overtime_hours for s in daily_summaries)
        total_work_quantity = sum(s.total_work_quantity for s in daily_summaries)
        total_defect_quantity = sum(s.total_defect_quantity for s in daily_summaries)
        total_good_quantity = sum(s.total_good_quantity for s in daily_summaries)
        
        # 計算週效率指標
        efficiency_rate = self._calculate_efficiency_rate(total_work_hours, total_work_quantity)
        defect_rate = self._calculate_defect_rate(total_good_quantity, total_defect_quantity)
        
        # 統計人員和設備
        unique_operators_count = self._get_unique_operators_count(week_start_date, week_end_date, company_code)
        unique_equipment_count = self._get_unique_equipment_count(week_start_date, week_end_date, company_code)
        total_workorders_count = self._get_unique_workorders_count(week_start_date, week_end_date, company_code)
        
        # 建立或更新週報表
        summary, created = WorkTimeReportSummary.objects.get_or_create(
            report_date=week_start_date,
            company_code=company_code,
            report_type='work_time',
            time_dimension='weekly',
            defaults={
                'company_name': self._get_company_name(company_code),
                'total_work_hours': total_work_hours,
                'total_overtime_hours': total_overtime_hours,
                'total_work_quantity': total_work_quantity,
                'total_defect_quantity': total_defect_quantity,
                'total_good_quantity': total_good_quantity,
                'efficiency_rate': efficiency_rate,
                'defect_rate': defect_rate,
                'completion_rate': Decimal('100.00'),  # 週報表完工率設為100%
                'unique_operators_count': unique_operators_count,
                'unique_equipment_count': unique_equipment_count,
                'total_workorders_count': total_workorders_count,
            }
        )
        
        if not created:
            # 更新現有記錄
            summary.total_work_hours = total_work_hours
            summary.total_overtime_hours = total_overtime_hours
            summary.total_work_quantity = total_work_quantity
            summary.total_defect_quantity = total_defect_quantity
            summary.total_good_quantity = total_good_quantity
            summary.efficiency_rate = efficiency_rate
            summary.defect_rate = defect_rate
            summary.unique_operators_count = unique_operators_count
            summary.unique_equipment_count = unique_equipment_count
            summary.total_workorders_count = total_workorders_count
            summary.save()
        
        return summary
    
    def generate_monthly_work_time_report(self, year, month, company_code=None):
        """
        生成月工作時數報表
        
        Args:
            year: 年份
            month: 月份
            company_code: 公司代號
            
        Returns:
            DailyReportSummary: 彙總資料
        """
        company_code = company_code or self.company_code
        
        # 計算月份開始和結束日期
        month_start = datetime(year, month, 1).date()
        if month == 12:
            month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # 獲取月內所有日報表資料
        daily_summaries = WorkTimeReportSummary.objects.filter(
            report_date__range=[month_start, month_end],
            company_code=company_code,
            report_type='work_time',
            time_dimension='daily'
        )
        
        # 彙總月資料
        total_work_hours = sum(s.total_work_hours for s in daily_summaries)
        total_overtime_hours = sum(s.total_overtime_hours for s in daily_summaries)
        total_work_quantity = sum(s.total_work_quantity for s in daily_summaries)
        total_defect_quantity = sum(s.total_defect_quantity for s in daily_summaries)
        total_good_quantity = sum(s.total_good_quantity for s in daily_summaries)
        
        # 計算月效率指標
        efficiency_rate = self._calculate_efficiency_rate(total_work_hours, total_work_quantity)
        defect_rate = self._calculate_defect_rate(total_good_quantity, total_defect_quantity)
        
        # 統計人員和設備
        unique_operators_count = self._get_unique_operators_count(month_start, month_end, company_code)
        unique_equipment_count = self._get_unique_equipment_count(month_start, month_end, company_code)
        total_workorders_count = self._get_unique_workorders_count(month_start, month_end, company_code)
        
        # 建立或更新月報表
        summary, created = WorkTimeReportSummary.objects.get_or_create(
            report_date=month_start,
            company_code=company_code,
            report_type='work_time',
            time_dimension='monthly',
            defaults={
                'company_name': self._get_company_name(company_code),
                'total_work_hours': total_work_hours,
                'total_overtime_hours': total_overtime_hours,
                'total_work_quantity': total_work_quantity,
                'total_defect_quantity': total_defect_quantity,
                'total_good_quantity': total_good_quantity,
                'efficiency_rate': efficiency_rate,
                'defect_rate': defect_rate,
                'completion_rate': Decimal('100.00'),  # 月報表完工率設為100%
                'unique_operators_count': unique_operators_count,
                'unique_equipment_count': unique_equipment_count,
                'total_workorders_count': total_workorders_count,
            }
        )
        
        if not created:
            # 更新現有記錄
            summary.total_work_hours = total_work_hours
            summary.total_overtime_hours = total_overtime_hours
            summary.total_work_quantity = total_work_quantity
            summary.total_defect_quantity = total_defect_quantity
            summary.total_good_quantity = total_good_quantity
            summary.efficiency_rate = efficiency_rate
            summary.defect_rate = defect_rate
            summary.unique_operators_count = unique_operators_count
            summary.unique_equipment_count = unique_equipment_count
            summary.total_workorders_count = total_workorders_count
            summary.save()
        
        return summary
    
    def get_work_time_report_data(self, start_date, end_date, company_code=None, time_dimension='daily'):
        """
        獲取工作時數報表資料
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            company_code: 公司代號
            time_dimension: 時間維度
            
        Returns:
            list: 報表資料列表
        """
        company_code = company_code or self.company_code
        
        summaries = WorkTimeReportSummary.objects.filter(
            report_date__range=[start_date, end_date],
            company_code=company_code,
            report_type='work_time',
            time_dimension=time_dimension
        ).order_by('report_date')
        
        data = []
        for summary in summaries:
            data.append({
                'report_date': summary.report_date.strftime('%Y-%m-%d'),
                'total_work_hours': float(summary.total_work_hours),
                'total_overtime_hours': float(summary.total_overtime_hours),
                'total_work_quantity': summary.total_work_quantity,
                'total_defect_quantity': summary.total_defect_quantity,
                'total_good_quantity': summary.total_good_quantity,
                'efficiency_rate': float(summary.efficiency_rate),
                'defect_rate': float(summary.defect_rate),
                'completion_rate': float(summary.completion_rate),
                'unique_operators_count': summary.unique_operators_count,
                'unique_equipment_count': summary.unique_equipment_count,
                'total_workorders_count': summary.total_workorders_count,
                'yield_rate': float(summary.yield_rate),
            })
        
        return data
    
    def get_work_time_summary(self, start_date, end_date, company_code=None, time_dimension='daily'):
        """
        獲取工作時數報表摘要
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            company_code: 公司代號
            time_dimension: 時間維度
            
        Returns:
            dict: 摘要資料
        """
        company_code = company_code or self.company_code
        
        summaries = WorkTimeReportSummary.objects.filter(
            report_date__range=[start_date, end_date],
            company_code=company_code,
            report_type='work_time',
            time_dimension=time_dimension
        )
        
        if not summaries.exists():
            return {
                'total_work_hours': 0,
                'total_overtime_hours': 0,
                'total_work_quantity': 0,
                'total_defect_quantity': 0,
                'total_good_quantity': 0,
                'avg_efficiency_rate': 0,
                'avg_defect_rate': 0,
                'avg_completion_rate': 0,
                'total_operators': 0,
                'total_equipment': 0,
                'total_workorders': 0,
                'avg_yield_rate': 0,
            }
        
        # 計算總計
        total_work_hours = sum(s.total_work_hours for s in summaries)
        total_overtime_hours = sum(s.total_overtime_hours for s in summaries)
        total_work_quantity = sum(s.total_work_quantity for s in summaries)
        total_defect_quantity = sum(s.total_defect_quantity for s in summaries)
        total_good_quantity = sum(s.total_good_quantity for s in summaries)
        
        # 計算平均值
        count = summaries.count()
        avg_efficiency_rate = sum(s.efficiency_rate for s in summaries) / count
        avg_defect_rate = sum(s.defect_rate for s in summaries) / count
        avg_completion_rate = sum(s.completion_rate for s in summaries) / count
        avg_yield_rate = sum(s.yield_rate for s in summaries) / count
        
        # 統計人員和設備
        total_operators = max(s.unique_operators_count for s in summaries)
        total_equipment = max(s.unique_equipment_count for s in summaries)
        total_workorders = sum(s.total_workorders_count for s in summaries)
        
        return {
            'total_work_hours': float(total_work_hours),
            'total_overtime_hours': float(total_overtime_hours),
            'total_work_quantity': total_work_quantity,
            'total_defect_quantity': total_defect_quantity,
            'total_good_quantity': total_good_quantity,
            'avg_efficiency_rate': float(avg_efficiency_rate),
            'avg_defect_rate': float(avg_defect_rate),
            'avg_completion_rate': float(avg_completion_rate),
            'total_operators': total_operators,
            'total_equipment': total_equipment,
            'total_workorders': total_workorders,
            'avg_yield_rate': float(avg_yield_rate),
        }
    
    def _create_work_time_detail(self, summary, fill_works, onsite_reports):
        """建立工作時數報表詳細資料"""
        try:
            # 準備詳細資料
            detail_data = {
                'fill_works': [],
                'onsite_reports': [],
                'operator_summary': {},
                'workorder_summary': {},
            }
            
            # 處理填報作業詳細資料
            for fill_work in fill_works:
                detail_data['fill_works'].append({
                    'operator': fill_work.operator,
                    'workorder': fill_work.workorder,
                    'product_id': fill_work.product_id,
                    'process': fill_work.process,
                    'work_quantity': fill_work.work_quantity,
                    'defect_quantity': fill_work.defect_quantity,
                    'work_hours': float(fill_work.work_hours_calculated or 0),
                    'start_time': fill_work.start_time.strftime('%H:%M') if fill_work.start_time else '',
                    'end_time': fill_work.end_time.strftime('%H:%M') if fill_work.end_time else '',
                })
            
            # 處理現場報工詳細資料
            for onsite_report in onsite_reports:
                detail_data['onsite_reports'].append({
                    'operator': onsite_report.operator,
                    'workorder': onsite_report.workorder,
                    'product_id': onsite_report.product_id,
                    'process': onsite_report.process,
                    'work_minutes': onsite_report.work_minutes,
                    'work_hours': float((onsite_report.work_minutes or 0) / 60),
                    'start_datetime': onsite_report.start_datetime.strftime('%Y-%m-%d %H:%M') if onsite_report.start_datetime else '',
                    'end_datetime': onsite_report.end_datetime.strftime('%Y-%m-%d %H:%M') if onsite_report.end_datetime else '',
                })
            
            # 建立或更新詳細資料
            detail, created = WorkTimeReportDetail.objects.get_or_create(
                summary=summary,
                defaults={
                    'detailed_data': detail_data,
                    'data_source': 'fill_work_and_onsite_report',
                    'calculation_method': 'aggregation',
                }
            )
            
            if not created:
                detail.detailed_data = detail_data
                detail.save()
            
            return detail
            
        except Exception as e:
            logger.error(f"建立日報表詳細資料失敗: {str(e)}")
            return None
    
    def _calculate_efficiency_rate(self, work_hours, work_quantity):
        """計算效率率"""
        if work_hours > 0 and work_quantity > 0:
            # 假設標準效率為每小時10件
            standard_quantity = work_hours * 10
            efficiency = (work_quantity / standard_quantity) * 100
            return min(Decimal('100.00'), max(Decimal('0.00'), Decimal(str(efficiency)).quantize(Decimal('0.01'))))
        return Decimal('0.00')
    
    def _calculate_defect_rate(self, good_quantity, defect_quantity):
        """計算不良率"""
        total_quantity = good_quantity + defect_quantity
        if total_quantity > 0:
            defect_rate = (defect_quantity / total_quantity) * 100
            return Decimal(str(defect_rate)).quantize(Decimal('0.01'))
        return Decimal('0.00')
    
    def _calculate_completion_rate(self, workorders):
        """計算完工率"""
        # 這裡簡化為100%，實際應該根據工單完成情況計算
        return Decimal('100.00')
    
    def _get_company_name(self, company_code):
        """獲取公司名稱"""
        # 從ERP整合模組獲取公司名稱
        try:
            from erp_integration.models import CompanyConfig
            company = CompanyConfig.objects.filter(company_code=company_code).first()
            return company.company_name if company else company_code
        except:
            return company_code
    
    def _get_unique_operators_count(self, start_date, end_date, company_code):
        """獲取期間內唯一作業員數量"""
        from workorder.fill_work.models import FillWork
        from workorder.onsite_reporting.models import OnsiteReport
        
        fill_work_operators = FillWork.objects.filter(
            work_date__range=[start_date, end_date],
            company_name=company_code,
            approval_status='approved'
        ).values_list('operator', flat=True).distinct()
        
        onsite_operators = OnsiteReport.objects.filter(
            work_date__range=[start_date, end_date],
            company_code=company_code,
            status='completed'
        ).values_list('operator', flat=True).distinct()
        
        all_operators = set(list(fill_work_operators) + list(onsite_operators))
        return len(all_operators)
    
    def _get_unique_equipment_count(self, start_date, end_date, company_code):
        """獲取期間內唯一設備數量"""
        # 這裡簡化為0，實際應該從設備相關資料表獲取
        return 0
    
    def _get_unique_workorders_count(self, start_date, end_date, company_code):
        """獲取期間內唯一工單數量"""
        from workorder.fill_work.models import FillWork
        from workorder.onsite_reporting.models import OnsiteReport
        
        fill_work_workorders = FillWork.objects.filter(
            work_date__range=[start_date, end_date],
            company_name=company_code,
            approval_status='approved'
        ).values_list('workorder', flat=True).distinct()
        
        onsite_workorders = OnsiteReport.objects.filter(
            work_date__range=[start_date, end_date],
            company_code=company_code,
            status='completed'
        ).values_list('workorder', flat=True).distinct()
        
        all_workorders = set(list(fill_work_workorders) + list(onsite_workorders))
        return len(all_workorders)


# 保留原有的服務類別
class WorkHourReportService:
    """工作時數報表服務 - 保留原有功能"""
    
    def __init__(self, company_code=None):
        self.company_code = company_code
    
    def get_daily_report(self, company_code, year, month, day):
        """日報表"""
        from .models import WorkTimeReportSummary
        return WorkTimeReportSummary.objects.filter(
            company_code=company_code,
            report_date__year=year,
            report_date__month=month,
            report_date__day=day,
            report_type='work_time',
            time_dimension='daily'
        )
    
    def get_weekly_report(self, company_code, year, week):
        """週報表"""
        from .models import WorkTimeReportSummary
        return WorkTimeReportSummary.objects.filter(
            company_code=company_code,
            report_date__year=year,
            report_type='work_time',
            time_dimension='weekly'
        )
    
    def get_monthly_report(self, company_code, year, month):
        """月報表"""
        from .models import WorkTimeReportSummary
        return WorkTimeReportSummary.objects.filter(
            company_code=company_code,
            report_date__year=year,
            report_date__month=month,
            report_type='work_time',
            time_dimension='monthly'
        )
    
    def get_quarterly_report(self, company_code, year, quarter):
        """季報表"""
        from .models import WorkTimeReportSummary
        return WorkTimeReportSummary.objects.filter(
            company_code=company_code,
            report_date__year=year,
            report_type='work_time',
            time_dimension='quarterly'
        )
    
    def get_yearly_report(self, company_code, year):
        """年報表"""
        from .models import WorkTimeReportSummary
        return WorkTimeReportSummary.objects.filter(
            company_code=company_code,
            report_date__year=year,
            report_type='work_time',
            time_dimension='yearly'
        )
    
    def get_daily_summary(self, company_code, year, month, day):
        """日報表摘要"""
        from .models import WorkTimeReportSummary
        reports = WorkTimeReportSummary.objects.filter(
            company_code=company_code,
            report_date__year=year,
            report_date__month=month,
            report_date__day=day,
            report_type='work_time',
            time_dimension='daily'
        )
        
        if not reports.exists():
            return {
                'total_work_hours': 0,
                'total_overtime_hours': 0,
                'total_work_quantity': 0,
                'total_defect_quantity': 0,
                'avg_efficiency_rate': 0,
            }
        
        report = reports.first()
        return {
            'total_work_hours': float(report.total_work_hours),
            'total_overtime_hours': float(report.total_overtime_hours),
            'total_work_quantity': report.total_work_quantity,
            'total_defect_quantity': report.total_defect_quantity,
            'avg_efficiency_rate': float(report.efficiency_rate),
        }


class ReportGeneratorService:
    """報表生成服務"""
    
    def __init__(self):
        self.work_time_service = WorkTimeReportService()
    
    def generate_work_time_report(self, company_code, start_date, end_date, time_dimension='daily', format='excel'):
        """生成工作時數報表"""
        try:
            # 根據時間維度生成報表
            if time_dimension == 'daily':
                for date in self._get_date_range(start_date, end_date):
                    self.work_time_service.generate_daily_work_time_report(date, company_code)
            elif time_dimension == 'weekly':
                for week_start in self._get_week_starts(start_date, end_date):
                    self.work_time_service.generate_weekly_work_time_report(week_start, company_code)
            elif time_dimension == 'monthly':
                for year, month in self._get_month_range(start_date, end_date):
                    self.work_time_service.generate_monthly_work_time_report(year, month, company_code)
            
            # 獲取報表資料
            data = self.work_time_service.get_work_time_report_data(start_date, end_date, company_code, time_dimension)
            summary = self.work_time_service.get_work_time_summary(start_date, end_date, company_code, time_dimension)
            
            # 生成檔案
            if format == 'excel':
                return self._export_to_excel(data, summary, f'工作時數報表_{company_code}_{start_date}_{end_date}')
            elif format == 'csv':
                return self._export_to_csv(data, summary, f'工作時數報表_{company_code}_{start_date}_{end_date}')
            else:
                return {
                    'data': data,
                    'summary': summary,
                }
                
        except Exception as e:
            logger.error(f"生成工作時數報表失敗: {str(e)}")
            raise
    
    def _get_date_range(self, start_date, end_date):
        """獲取日期範圍"""
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        return dates
    
    def _get_week_starts(self, start_date, end_date):
        """獲取週開始日期"""
        week_starts = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() == 0:  # 週一
                week_starts.append(current_date)
            current_date += timedelta(days=1)
        return week_starts
    
    def _get_month_range(self, start_date, end_date):
        """獲取月份範圍"""
        months = []
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            months.append((current_date.year, current_date.month))
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        return months
    
    def _export_to_excel(self, data, summary, filename):
        """匯出到Excel"""
        # 這裡實作Excel匯出邏輯
        return {
            'file_path': f'/tmp/{filename}.xlsx',
            'filename': f'{filename}.xlsx',
        }
    
    def _export_to_csv(self, data, summary, filename):
        """匯出到CSV"""
        # 這裡實作CSV匯出邏輯
        return {
            'file_path': f'/tmp/{filename}.csv',
            'filename': f'{filename}.csv',
        } 