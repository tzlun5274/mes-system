"""
評分週期管理服務
提供評分週期的建立、關閉、摘要等功能
"""

import logging
from datetime import datetime, timedelta
from calendar import monthrange
from django.utils import timezone
from django.db.models import Count, Sum, Avg

logger = logging.getLogger(__name__)


class ScorePeriodService:
    """評分週期管理服務"""
    
    @staticmethod
    def get_current_period_dates(period_type='monthly'):
        """取得當前評分週期的日期範圍"""
        today = datetime.now().date()
        
        if period_type == 'monthly':
            # 當月第一天到最後一天
            start_date = today.replace(day=1)
            _, last_day = monthrange(today.year, today.month)
            end_date = today.replace(day=last_day)
            
        elif period_type == 'quarterly':
            # 當前季度
            quarter = (today.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            
            start_date = today.replace(month=start_month, day=1)
            _, last_day = monthrange(today.year, end_month)
            end_date = today.replace(month=end_month, day=last_day)
            
        elif period_type == 'yearly':
            # 當年
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            
        else:
            raise ValueError(f"不支援的評分週期類型: {period_type}")
        
        return start_date, end_date
    
    @staticmethod
    def get_period_name(period_type, start_date, end_date):
        """取得評分週期名稱"""
        if period_type == 'monthly':
            return f"{start_date.year}年{start_date.month}月評分"
        elif period_type == 'quarterly':
            quarter = (start_date.month - 1) // 3 + 1
            return f"{start_date.year}年第{quarter}季評分"
        elif period_type == 'yearly':
            return f"{start_date.year}年度評分"
        else:
            return f"{start_date}至{end_date}評分"
    
    @staticmethod
    def create_period_score_records(company_code, period_type='monthly', force=False):
        """建立評分週期記錄"""
        from .models import OperatorProcessCapacityScore
        from .operator_capacity_service import OperatorCapacityService
        
        start_date, end_date = ScorePeriodService.get_current_period_dates(period_type)
        
        # 檢查是否已存在該週期的記錄
        existing_records = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            score_period=period_type,
            period_start_date=start_date,
            period_end_date=end_date
        )
        
        if existing_records.exists() and not force:
            return existing_records
        
        # 取得該週期內的所有作業員工作記錄
        from workorder.fill_work.models import FillWork
        from workorder.onsite_reporting.models import OnsiteReport
        
        # 從填報資料建立評分記錄
        fill_works = FillWork.objects.filter(
            company_name=company_code,
            work_date__range=[start_date, end_date]
        )
        
        created_records = []
        for fill_work in fill_works:
            # 計算作業員評分
            score_record = OperatorCapacityService.calculate_operator_process_score(
                operator_name=fill_work.operator,
                operator_id=fill_work.operator,  # 使用 operator 作為 operator_id
                company_code=company_code,
                product_code=fill_work.product_id,  # 使用 product_id 作為 product_code
                process_name=fill_work.process_name,
                workorder_id=fill_work.workorder,
                work_date=fill_work.work_date,
                work_hours=fill_work.work_hours_calculated or 0,
                completed_quantity=fill_work.work_quantity or 0,
                defect_quantity=fill_work.defect_quantity or 0
            )
            
            if score_record:
                # 設定評分週期資訊
                score_record.score_period = period_type
                score_record.period_start_date = start_date
                score_record.period_end_date = end_date
                score_record.save()
                created_records.append(score_record)
        
        # 從現場報工資料建立評分記錄
        onsite_reports = OnsiteReport.objects.filter(
            company_code=company_code,
            work_date__range=[start_date, end_date]
        )
        
        for report in onsite_reports:
            score_record = OperatorCapacityService.calculate_operator_process_score(
                operator_name=report.operator_name,
                operator_id=report.operator_id,
                company_code=company_code,
                product_code=report.product_code,
                process_name=report.process_name,
                workorder_id=report.workorder_id,
                work_date=report.work_date,
                work_hours=report.work_hours or 0,
                completed_quantity=report.completed_quantity or 0,
                defect_quantity=report.defect_quantity or 0
            )
            
            if score_record:
                # 設定評分週期資訊
                score_record.score_period = period_type
                score_record.period_start_date = start_date
                score_record.period_end_date = end_date
                score_record.save()
                created_records.append(score_record)
        
        return created_records
    
    @staticmethod
    def close_period(company_code, period_type='monthly'):
        """關閉評分週期"""
        from .models import OperatorProcessCapacityScore
        
        start_date, end_date = ScorePeriodService.get_current_period_dates(period_type)
        
        # 更新該週期的所有記錄為已關閉
        updated_count = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            score_period=period_type,
            period_start_date=start_date,
            period_end_date=end_date
        ).update(
            is_period_closed=True,
            period_closed_date=datetime.now()
        )
        
        return updated_count
    
    @staticmethod
    def get_period_summary(company_code, period_type='monthly'):
        """取得評分週期摘要"""
        from .models import OperatorProcessCapacityScore
        
        start_date, end_date = ScorePeriodService.get_current_period_dates(period_type)
        
        records = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            score_period=period_type,
            period_start_date=start_date,
            period_end_date=end_date
        )
        
        if not records.exists():
            return None
        
        # 計算統計資料
        total_records = records.count()
        avg_capacity_score = records.aggregate(avg=Avg('capacity_score'))['avg'] or 0
        avg_quality_score = records.aggregate(avg=Avg('quality_score'))['avg'] or 0
        avg_total_score = records.aggregate(avg=Avg('total_score'))['avg'] or 0
        
        # 等級分布
        grade_distribution = records.values('overall_grade').annotate(
            count=Count('id')
        ).order_by('overall_grade')
        
        # 主管評分統計
        supervisor_scored_count = records.filter(is_supervisor_scored=True).count()
        supervisor_score_rate = (supervisor_scored_count / total_records * 100) if total_records > 0 else 0
        
        return {
            'period_name': ScorePeriodService.get_period_name(period_type, start_date, end_date),
            'start_date': start_date,
            'end_date': end_date,
            'total_records': total_records,
            'avg_capacity_score': avg_capacity_score,
            'avg_quality_score': avg_quality_score,
            'avg_total_score': avg_total_score,
            'grade_distribution': grade_distribution,
            'supervisor_scored_count': supervisor_scored_count,
            'supervisor_score_rate': supervisor_score_rate,
            'is_closed': records.filter(is_period_closed=True).exists(),
        }
