"""
評分報表服務
提供生產效率、品質管理、交期管理等各項評分計算功能
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Avg

logger = logging.getLogger(__name__)


class ScoringService:
    """評分報表服務類別"""
    
    @staticmethod
    def calculate_production_score(company_code, start_date, end_date):
        """計算生產效率分數 - 以工序標準產能為基準"""
        from .models import OperatorProcessCapacityScore
        
        # 取得期間內的作業員工序產能評分資料
        capacity_scores = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            work_date__range=[start_date, end_date]
        )
        
        if not capacity_scores.exists():
            return Decimal('0.00')
        
        # 計算平均產能評分
        avg_capacity_score = capacity_scores.aggregate(
            avg=Avg('capacity_score')
        )['avg'] or Decimal('0.00')
        
        return avg_capacity_score
    
    @staticmethod
    def calculate_quality_score(company_code, start_date, end_date):
        """計算品質管理分數 - 基於作業員工序產能評分"""
        from .models import OperatorProcessCapacityScore
        
        # 取得期間內的作業員工序產能評分資料
        capacity_scores = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            work_date__range=[start_date, end_date]
        )
        
        if not capacity_scores.exists():
            return Decimal('0.00')
        
        # 計算品質指標
        total_quantity = capacity_scores.aggregate(
            total=Sum('completed_quantity')
        )['total'] or 0
        
        total_defect = capacity_scores.aggregate(
            total=Sum('defect_quantity')
        )['total'] or 0
        
        # 計算不良率
        defect_rate = (total_defect / total_quantity * 100) if total_quantity > 0 else 0
        
        # 計算平均品質評分
        avg_quality_score = capacity_scores.aggregate(
            avg=Avg('quality_score')
        )['avg'] or Decimal('0.00')
        
        # 品質分數 = 平均品質評分 (70%) + 不良率評分 (30%)
        defect_score = max(Decimal('100.00') - Decimal(str(defect_rate)), Decimal('0.00'))
        quality_score = (avg_quality_score * Decimal('0.7') + defect_score * Decimal('0.3'))
        
        return quality_score
    
    @staticmethod
    def calculate_delivery_score(company_code, start_date, end_date):
        """計算交期管理分數"""
        from .models import CompletedWorkOrderAnalysis
        
        # 取得期間內的工單資料，排除 RD樣品工單
        workorder_data = CompletedWorkOrderAnalysis.objects.exclude(workorder_id__icontains='RD樣品').filter(
            company_code=company_code,
            completion_date__range=[start_date, end_date]
        )
        
        if not workorder_data.exists():
            return Decimal('0.00')
        
        # 計算準時完工率 (假設所有工單都準時完工)
        # 實際應用中需要比對計劃完工日期和實際完工日期
        on_time_count = workorder_data.count()  # 簡化計算
        total_count = workorder_data.count()
        
        on_time_rate = (on_time_count / total_count * 100) if total_count > 0 else 0
        
        return Decimal(str(on_time_rate))
    
    @staticmethod
    def calculate_equipment_score(company_code, start_date, end_date):
        """計算設備管理分數"""
        from .models import CompletedWorkOrderAnalysis
        
        # 取得期間內的工單資料，排除 RD樣品工單
        workorder_data = CompletedWorkOrderAnalysis.objects.exclude(workorder_id__icontains='RD樣品').filter(
            company_code=company_code,
            completion_date__range=[start_date, end_date]
        )
        
        if not workorder_data.exists():
            return Decimal('0.00')
        
        # 計算設備利用率
        total_equipment_hours = workorder_data.aggregate(
            total=Sum('total_work_hours')
        )['total'] or Decimal('0.00')
        
        # 假設標準工作時數為8小時/天，工作天數為期間天數
        work_days = (end_date - start_date).days + 1
        standard_hours = work_days * Decimal('8.00')
        
        # 設備利用率 (簡化計算)
        equipment_utilization = min((total_equipment_hours / standard_hours * 100), Decimal('100.00'))
        
        return equipment_utilization
    
    @staticmethod
    def calculate_cost_score(company_code, start_date, end_date):
        """計算成本控制分數"""
        from .models import CompletedWorkOrderAnalysis
        
        # 取得期間內的工單資料，排除 RD樣品工單
        workorder_data = CompletedWorkOrderAnalysis.objects.exclude(workorder_id__icontains='RD樣品').filter(
            company_code=company_code,
            completion_date__range=[start_date, end_date]
        )
        
        if not workorder_data.exists():
            return Decimal('0.00')
        
        # 計算加班時數比例
        total_work_hours = workorder_data.aggregate(
            total=Sum('total_work_hours')
        )['total'] or Decimal('0.00')
        
        total_overtime_hours = workorder_data.aggregate(
            total=Sum('total_overtime_hours')
        )['total'] or Decimal('0.00')
        
        # 加班比例越低分數越高
        overtime_rate = (total_overtime_hours / total_work_hours * 100) if total_work_hours > 0 else 0
        cost_score = max(Decimal('100.00') - Decimal(str(overtime_rate)), Decimal('0.00'))
        
        return cost_score
    
    @staticmethod
    def calculate_safety_score(company_code, start_date, end_date):
        """計算安全管理分數"""
        # 這裡可以整合安全事件資料
        # 目前簡化為固定分數
        safety_score = Decimal('95.00')  # 假設安全狀況良好
        
        return safety_score
    
    @staticmethod
    def calculate_personnel_score(company_code, start_date, end_date):
        """計算人員管理分數"""
        from .models import CompletedWorkOrderAnalysis
        
        # 取得期間內的工單資料，排除 RD樣品工單
        workorder_data = CompletedWorkOrderAnalysis.objects.exclude(workorder_id__icontains='RD樣品').filter(
            company_code=company_code,
            completion_date__range=[start_date, end_date]
        )
        
        if not workorder_data.exists():
            return Decimal('0.00')
        
        # 計算人員效率
        total_operators = workorder_data.aggregate(
            total=Sum('unique_operators_count')
        )['total'] or 0
        
        total_work_hours = workorder_data.aggregate(
            total=Sum('total_work_hours')
        )['total'] or Decimal('0.00')
        
        # 人員效率 = 總工作時數 / 總人員數 (簡化計算)
        if total_operators > 0:
            personnel_efficiency = (total_work_hours / total_operators) / Decimal('8.00') * 100
            personnel_score = min(personnel_efficiency, Decimal('100.00'))
        else:
            personnel_score = Decimal('0.00')
        
        return personnel_score
    
    @staticmethod
    def generate_scoring_report(company_code, start_date, end_date, report_period='monthly'):
        """生成評分報表"""
        # 計算生產效率分數
        production_score = ScoringService.calculate_production_score(company_code, start_date, end_date)
        
        # 生產效率佔100%權重
        total_score = production_score
        
        # 計算得分百分比
        score_percentage = total_score
        
        # 計算總體等級
        if score_percentage >= 90:
            overall_grade = '優秀'
        elif score_percentage >= 80:
            overall_grade = '良好'
        elif score_percentage >= 70:
            overall_grade = '及格'
        else:
            overall_grade = '不及格'
        
        # 統計各等級項目數
        scores = [production_score]
        
        excellent_count = sum(1 for score in scores if score >= 90)
        good_count = sum(1 for score in scores if 80 <= score < 90)
        pass_count = sum(1 for score in scores if 70 <= score < 80)
        fail_count = sum(1 for score in scores if score < 70)
        
        # 建立報表名稱
        report_name = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%Y年%m月%d日')} 評分報表"
        
        # 取得公司名稱
        from erp_integration.models import CompanyConfig
        try:
            company = CompanyConfig.objects.get(company_code=company_code)
            company_name = company.company_name
        except CompanyConfig.DoesNotExist:
            company_name = company_code
        
        # 暫時返回一個字典，因為ScoringReport模型已移除
        return {
            'id': None,
            'report_name': report_name,
            'company_name': company_name,
            'total_score': total_score,
            'score_percentage': score_percentage,
            'overall_grade': overall_grade,
            'production_score': production_score,
            'excellent_count': excellent_count,
            'good_count': good_count,
            'pass_count': pass_count,
            'fail_count': fail_count,
        }
    
    @staticmethod
    def generate_improvement_suggestions(scoring_report):
        """生成改善建議"""
        # 暫時返回空列表，因為ScoringImprovement模型已移除
        return []
