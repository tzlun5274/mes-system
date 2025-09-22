"""
作業員工序產能評分服務
提供作業員工序產能評分計算、報表生成和分析功能
"""

import logging
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.db.models import Count, Sum, Avg, StdDev

logger = logging.getLogger(__name__)


class OperatorCapacityService:
    """作業員工序產能評分服務類別"""
    
    @staticmethod
    def calculate_operator_process_score(operator_name, operator_id, company_code, 
                                       product_code, process_name, workorder_id, 
                                       work_date, work_hours, completed_quantity, 
                                       defect_quantity=0, supervisor_name=None, 
                                       supervisor_score=None, supervisor_comment=None):
        """計算作業員工序評分"""
        from .models import OperatorProcessCapacityScore
        
        # 取得標準產能
        try:
            from process.models import ProductProcessStandardCapacity
            standard_capacity = ProductProcessStandardCapacity.objects.get(
                company_code=company_code,
                product_code=product_code,
                process_name=process_name
            )
            standard_capacity_per_hour = standard_capacity.standard_capacity_per_hour
        except ProductProcessStandardCapacity.DoesNotExist:
            # 如果沒有標準產能，使用預設值
            standard_capacity_per_hour = Decimal('1.00')
        
        # 計算實際產能
        if work_hours > 0:
            actual_capacity_per_hour = Decimal(str(completed_quantity)) / work_hours
        else:
            actual_capacity_per_hour = Decimal('0.00')
        
        # 計算產能比率
        if standard_capacity_per_hour > 0:
            capacity_ratio = actual_capacity_per_hour / standard_capacity_per_hour
        else:
            capacity_ratio = Decimal('0.00')
        
        # 計算效率因子和學習曲線因子
        efficiency_factor = min(Decimal('1.20'), capacity_ratio)
        learning_curve_factor = min(Decimal('1.10'), capacity_ratio)
        
        # 計算不良率
        if completed_quantity > 0:
            defect_rate = Decimal(str(defect_quantity)) / completed_quantity
        else:
            defect_rate = Decimal('0.00')
        
        # 建立或更新評分記錄
        score_record, created = OperatorProcessCapacityScore.objects.get_or_create(
            operator_id=operator_id,
            company_code=company_code,
            product_code=product_code,
            process_name=process_name,
            workorder_id=workorder_id,
            work_date=work_date,
            defaults={
                'operator_name': operator_name,
                'work_hours': work_hours,
                'standard_capacity_per_hour': standard_capacity_per_hour,
                'actual_capacity_per_hour': actual_capacity_per_hour,
                'completed_quantity': completed_quantity,
                'capacity_ratio': capacity_ratio,
                'efficiency_factor': efficiency_factor,
                'learning_curve_factor': learning_curve_factor,
                'defect_quantity': defect_quantity,
                'defect_rate': defect_rate,
                'supervisor_score': Decimal('80.00'),  # 預設80分
                'is_supervisor_scored': False,  # 預設未評分
            }
        )
        
        if not created:
            # 更新現有記錄
            score_record.operator_name = operator_name
            score_record.work_hours = work_hours
            score_record.standard_capacity_per_hour = standard_capacity_per_hour
            score_record.actual_capacity_per_hour = actual_capacity_per_hour
            score_record.completed_quantity = completed_quantity
            score_record.capacity_ratio = capacity_ratio
            score_record.efficiency_factor = efficiency_factor
            score_record.learning_curve_factor = learning_curve_factor
            score_record.defect_quantity = defect_quantity
            score_record.defect_rate = defect_rate
        
        # 如果提供了主管評分，更新主管評分資訊
        if supervisor_score is not None and supervisor_name:
            score_record.supervisor_score = supervisor_score
            score_record.supervisor_comment = supervisor_comment or ''
            score_record.supervisor_name = supervisor_name
            score_record.supervisor_date = datetime.now()
            score_record.is_supervisor_scored = True
        
        # 計算評分
        score_record.capacity_score = score_record.calculate_capacity_score()
        # 品質評分不再自動計算，由主管手動評分
        score_record.total_score = score_record.calculate_total_score()
        score_record.grade = score_record.get_grade(score_record.capacity_score)
        score_record.overall_grade = score_record.get_grade(score_record.total_score)
        
        score_record.save()
        return score_record
    
    @staticmethod
    def generate_operator_capacity_report(company_code, start_date, end_date, report_period='monthly'):
        """生成作業員產能評分報表"""
        from .models import OperatorProcessCapacityScore, OperatorCapacityReport
        
        # 取得期間內的評分資料
        scores = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            work_date__range=[start_date, end_date]
        )
        
        if not scores.exists():
            return None
        
        # 計算統計資料
        total_operators = scores.values('operator_id').distinct().count()
        total_processes = scores.values('process_name').distinct().count()
        total_work_hours = scores.aggregate(total=Sum('work_hours'))['total'] or Decimal('0.00')
        total_completed_quantity = scores.aggregate(total=Sum('completed_quantity'))['total'] or 0
        
        # 計算平均評分
        avg_capacity_score = scores.aggregate(avg=Avg('capacity_score'))['avg'] or Decimal('0.00')
        avg_quality_score = scores.aggregate(avg=Avg('quality_score'))['avg'] or Decimal('0.00')
        avg_total_score = scores.aggregate(avg=Avg('total_score'))['avg'] or Decimal('0.00')
        
        # 計算等級統計
        excellent_count = scores.filter(overall_grade='優秀').count()
        good_count = scores.filter(overall_grade='良好').count()
        pass_count = scores.filter(overall_grade='及格').count()
        fail_count = scores.filter(overall_grade='不及格').count()
        
        # 計算工序表現統計
        process_performance = {}
        process_stats = scores.values('process_name').annotate(
            avg_capacity=Avg('capacity_score'),
            avg_quality=Avg('quality_score'),
            avg_total=Avg('total_score'),
            operator_count=Count('operator_id', distinct=True),
            total_hours=Sum('work_hours'),
            total_quantity=Sum('completed_quantity')
        )
        
        for stat in process_stats:
            process_performance[stat['process_name']] = {
                'avg_capacity': float(stat['avg_capacity'] or 0),
                'avg_quality': float(stat['avg_quality'] or 0),
                'avg_total': float(stat['avg_total'] or 0),
                'operator_count': stat['operator_count'],
                'total_hours': float(stat['total_hours'] or 0),
                'total_quantity': stat['total_quantity'] or 0,
            }
        
        # 建立報表名稱
        report_name = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%Y年%m月%d日')} 作業員產能評分報表"
        
        # 建立或更新報表
        report, created = OperatorCapacityReport.objects.get_or_create(
            company_code=company_code,
            report_period=report_period,
            start_date=start_date,
            end_date=end_date,
            defaults={
                'report_name': report_name,
                'report_date': datetime.now().date(),
                'total_operators': total_operators,
                'total_processes': total_processes,
                'total_work_hours': total_work_hours,
                'total_completed_quantity': total_completed_quantity,
                'avg_capacity_score': avg_capacity_score,
                'avg_quality_score': avg_quality_score,
                'avg_total_score': avg_total_score,
                'excellent_count': excellent_count,
                'good_count': good_count,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'process_performance': process_performance,
            }
        )
        
        if not created:
            # 更新現有記錄
            report.report_name = report_name
            report.total_operators = total_operators
            report.total_processes = total_processes
            report.total_work_hours = total_work_hours
            report.total_completed_quantity = total_completed_quantity
            report.avg_capacity_score = avg_capacity_score
            report.avg_quality_score = avg_quality_score
            report.avg_total_score = avg_total_score
            report.excellent_count = excellent_count
            report.good_count = good_count
            report.pass_count = pass_count
            report.fail_count = fail_count
            report.process_performance = process_performance
            report.save()
        
        return report
    
    @staticmethod
    def get_operator_performance_summary(company_code, start_date, end_date, operator_id=None):
        """取得作業員表現摘要"""
        from .models import OperatorProcessCapacityScore
        
        # 建立查詢條件
        query = {
            'company_code': company_code,
            'work_date__range': [start_date, end_date]
        }
        
        if operator_id:
            query['operator_id'] = str(operator_id)
        
        scores = OperatorProcessCapacityScore.objects.filter(**query)
        
        if not scores.exists():
            return None
        
        # 計算摘要統計
        summary = scores.aggregate(
            total_records=Count('id'),
            avg_capacity_score=Avg('capacity_score'),
            avg_quality_score=Avg('quality_score'),
            avg_total_score=Avg('total_score'),
            total_work_hours=Sum('work_hours'),
            total_completed_quantity=Sum('completed_quantity'),
            total_defect_quantity=Sum('defect_quantity'),
        )
        
        # 計算等級分布
        grade_distribution = {
            'excellent': scores.filter(overall_grade='優秀').count(),
            'good': scores.filter(overall_grade='良好').count(),
            'pass': scores.filter(overall_grade='及格').count(),
            'fail': scores.filter(overall_grade='不及格').count(),
        }
        
        # 計算工序表現排名
        process_ranking = scores.values('process_name').annotate(
            avg_score=Avg('total_score'),
            record_count=Count('id')
        ).order_by('-avg_score')
        
        # 計算作業員表現排名
        operator_ranking = scores.values('operator_name', 'operator_id').annotate(
            avg_score=Avg('total_score'),
            total_hours=Sum('work_hours'),
            total_quantity=Sum('completed_quantity'),
            record_count=Count('id')
        ).order_by('-avg_score')
        
        return {
            'summary': summary,
            'grade_distribution': grade_distribution,
            'process_ranking': list(process_ranking),
            'operator_ranking': list(operator_ranking),
        }
    
    @staticmethod
    def get_operator_process_details(operator_id, start_date, end_date):
        """取得作業員工序詳細資料"""
        from .models import OperatorProcessCapacityScore
        
        scores = OperatorProcessCapacityScore.objects.filter(
            operator_id=str(operator_id),
            work_date__range=[start_date, end_date]
        ).order_by('work_date', 'process_name')
        
        return list(scores.values(
            'work_date', 'process_name', 'product_code', 'workorder_id',
            'work_hours', 'completed_quantity', 'defect_quantity',
            'standard_capacity_per_hour', 'actual_capacity_per_hour',
            'capacity_ratio', 'capacity_score', 'quality_score', 'total_score',
            'overall_grade'
        ))
    
    @staticmethod
    def get_process_capacity_analysis(company_code, start_date, end_date, process_name=None):
        """取得工序產能分析"""
        from .models import OperatorProcessCapacityScore
        
        query = {
            'company_code': company_code,
            'work_date__range': [start_date, end_date]
        }
        
        if process_name:
            query['process_name'] = process_name
        
        scores = OperatorProcessCapacityScore.objects.filter(**query)
        
        if not scores.exists():
            return None
        
        # 按工序分組統計
        process_stats = scores.values('process_name').annotate(
            operator_count=Count('operator_id', distinct=True),
            total_records=Count('id'),
            avg_capacity_score=Avg('capacity_score'),
            avg_quality_score=Avg('quality_score'),
            avg_total_score=Avg('total_score'),
            avg_capacity_ratio=Avg('capacity_ratio'),
            total_work_hours=Sum('work_hours'),
            total_completed_quantity=Sum('completed_quantity'),
            total_defect_quantity=Sum('defect_quantity'),
            capacity_score_std=StdDev('capacity_score'),
            quality_score_std=StdDev('quality_score'),
        )
        
        # 計算整體統計
        overall_stats = scores.aggregate(
            total_operators=Count('operator_id', distinct=True),
            total_processes=Count('process_name', distinct=True),
            avg_capacity_score=Avg('capacity_score'),
            avg_quality_score=Avg('quality_score'),
            avg_total_score=Avg('total_score'),
            avg_capacity_ratio=Avg('capacity_ratio'),
            total_work_hours=Sum('work_hours'),
            total_completed_quantity=Sum('completed_quantity'),
            total_defect_quantity=Sum('defect_quantity'),
        )
        
        return {
            'process_stats': list(process_stats),
            'overall_stats': overall_stats,
        }
