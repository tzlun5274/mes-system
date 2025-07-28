# 基於效率的分配器模組
# 本檔案負責根據歷史效率進行數量分配

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from .base_allocator import BaseAllocator


class EfficiencyBasedAllocator(BaseAllocator):
    """基於效率的分配器 - 根據歷史效率分配數量"""
    
    def __init__(self):
        """初始化效率分配器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def allocate_quantities(self, reports: List[Dict[str, Any]], total_quantity: int, **kwargs) -> List[Dict[str, Any]]:
        """
        根據歷史效率分配數量
        
        Args:
            reports: 報表記錄列表
            total_quantity: 總數量
            **kwargs: 其他參數
            
        Returns:
            List[Dict[str, Any]]: 分配後的報表記錄
        """
        try:
            if not self.validate_input(reports, total_quantity):
                return reports
            
            # 計算效率權重
            weights = self.calculate_efficiency_weights(reports)
            
            # 分配數量
            allocations = self.distribute_quantities(weights, total_quantity)
            
            # 應用分配結果
            allocated_reports = self.apply_allocation(reports, allocations)
            
            # 記錄分配過程
            self.log_allocation('efficiency_based', len(reports), total_quantity, {})
            
            return allocated_reports
        except Exception as e:
            self.logger.error(f"效率分配失敗: {str(e)}")
            return reports
    
    def calculate_efficiency_weights(self, reports: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        計算效率權重
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[int, float]: 索引到效率權重的映射
        """
        try:
            weights = {}
            total_efficiency = 0.0
            
            for i, report in enumerate(reports):
                # 獲取效率指標
                efficiency_rate = report.get('efficiency_rate', 0)
                historical_efficiency = report.get('historical_efficiency', 0)
                operator_efficiency = report.get('operator_efficiency', 0)
                
                # 綜合效率計算
                if efficiency_rate > 0:
                    efficiency = efficiency_rate
                elif historical_efficiency > 0:
                    efficiency = historical_efficiency
                elif operator_efficiency > 0:
                    efficiency = operator_efficiency
                else:
                    # 如果沒有效率數據，使用預設值
                    efficiency = 1.0
                
                weights[i] = max(efficiency, 0)
                total_efficiency += weights[i]
            
            # 正規化權重
            if total_efficiency > 0:
                for i in weights:
                    weights[i] = weights[i] / total_efficiency
            else:
                # 如果總效率為0，平均分配
                equal_weight = 1.0 / len(reports) if reports else 0
                for i in weights:
                    weights[i] = equal_weight
            
            return weights
        except Exception as e:
            self.logger.error(f"計算效率權重失敗: {str(e)}")
            return {}
    
    def calculate_historical_efficiency_weights(self, reports: List[Dict[str, Any]], 
                                              historical_data: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        根據歷史數據計算效率權重
        
        Args:
            reports: 報表記錄列表
            historical_data: 歷史數據列表
            
        Returns:
            Dict[int, float]: 索引到歷史效率權重的映射
        """
        try:
            weights = {}
            total_efficiency = 0.0
            
            # 建立歷史效率字典
            historical_efficiency = {}
            for data in historical_data:
                operator_id = data.get('operator_id')
                efficiency = data.get('efficiency_rate', 0)
                if operator_id:
                    if operator_id in historical_efficiency:
                        historical_efficiency[operator_id].append(efficiency)
                    else:
                        historical_efficiency[operator_id] = [efficiency]
            
            # 計算平均歷史效率
            avg_historical_efficiency = {}
            for operator_id, efficiencies in historical_efficiency.items():
                avg_historical_efficiency[operator_id] = sum(efficiencies) / len(efficiencies)
            
            for i, report in enumerate(reports):
                operator_id = report.get('operator_id')
                
                # 獲取歷史效率
                if operator_id in avg_historical_efficiency:
                    efficiency = avg_historical_efficiency[operator_id]
                else:
                    efficiency = 1.0  # 預設效率
                
                weights[i] = max(efficiency, 0)
                total_efficiency += weights[i]
            
            # 正規化權重
            if total_efficiency > 0:
                for i in weights:
                    weights[i] = weights[i] / total_efficiency
            else:
                # 如果總效率為0，平均分配
                equal_weight = 1.0 / len(reports) if reports else 0
                for i in weights:
                    weights[i] = equal_weight
            
            return weights
        except Exception as e:
            self.logger.error(f"計算歷史效率權重失敗: {str(e)}")
            return {}
    
    def calculate_performance_based_weights(self, reports: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        計算基於績效的權重
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[int, float]: 索引到績效權重的映射
        """
        try:
            weights = {}
            total_performance = 0.0
            
            for i, report in enumerate(reports):
                # 獲取績效指標
                quality_rate = report.get('quality_rate', 100) / 100  # 轉換為0-1
                productivity_rate = report.get('productivity_rate', 100) / 100
                attendance_rate = report.get('attendance_rate', 100) / 100
                
                # 綜合績效計算
                performance = (quality_rate + productivity_rate + attendance_rate) / 3
                
                weights[i] = max(performance, 0)
                total_performance += weights[i]
            
            # 正規化權重
            if total_performance > 0:
                for i in weights:
                    weights[i] = weights[i] / total_performance
            else:
                # 如果總績效為0，平均分配
                equal_weight = 1.0 / len(reports) if reports else 0
                for i in weights:
                    weights[i] = equal_weight
            
            return weights
        except Exception as e:
            self.logger.error(f"計算績效權重失敗: {str(e)}")
            return {}
    
    def calculate_skill_based_weights(self, reports: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        計算基於技能的權重
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[int, float]: 索引到技能權重的映射
        """
        try:
            weights = {}
            total_skill = 0.0
            
            for i, report in enumerate(reports):
                # 獲取技能指標
                skill_level = report.get('skill_level', 1)  # 1-5級
                experience_years = report.get('experience_years', 0)
                certification_count = report.get('certification_count', 0)
                
                # 技能綜合評分
                skill_score = (skill_level / 5.0) * 0.5 + \
                             min(experience_years / 10.0, 1.0) * 0.3 + \
                             min(certification_count / 5.0, 1.0) * 0.2
                
                weights[i] = max(skill_score, 0)
                total_skill += weights[i]
            
            # 正規化權重
            if total_skill > 0:
                for i in weights:
                    weights[i] = weights[i] / total_skill
            else:
                # 如果總技能為0，平均分配
                equal_weight = 1.0 / len(reports) if reports else 0
                for i in weights:
                    weights[i] = equal_weight
            
            return weights
        except Exception as e:
            self.logger.error(f"計算技能權重失敗: {str(e)}")
            return {}
    
    def allocate_with_efficiency_threshold(self, reports: List[Dict[str, Any]], 
                                         total_quantity: int,
                                         min_efficiency: float = 0.5,
                                         max_efficiency: float = 2.0) -> List[Dict[str, Any]]:
        """
        根據效率閾值分配數量
        
        Args:
            reports: 報表記錄列表
            total_quantity: 總數量
            min_efficiency: 最小效率閾值
            max_efficiency: 最大效率閾值
            
        Returns:
            List[Dict[str, Any]]: 分配後的報表記錄
        """
        try:
            if not self.validate_input(reports, total_quantity):
                return reports
            
            # 篩選符合效率閾值的記錄
            filtered_reports = []
            filtered_indices = []
            
            for i, report in enumerate(reports):
                efficiency_rate = report.get('efficiency_rate', 1.0)
                if min_efficiency <= efficiency_rate <= max_efficiency:
                    filtered_reports.append(report)
                    filtered_indices.append(i)
            
            if not filtered_reports:
                self.logger.warning("沒有符合效率閾值的記錄")
                return reports
            
            # 計算效率權重
            weights = self.calculate_efficiency_weights(filtered_reports)
            
            # 分配數量
            allocations = self.distribute_quantities(weights, total_quantity)
            
            # 應用分配結果到原始記錄
            result_reports = reports.copy()
            for i, allocation in allocations.items():
                original_index = filtered_indices[i]
                result_reports[original_index]['allocated_quantity'] = allocation
                result_reports[original_index]['allocation_method'] = 'efficiency_threshold'
            
            return result_reports
        except Exception as e:
            self.logger.error(f"效率閾值分配失敗: {str(e)}")
            return reports
    
    def allocate_with_learning_curve(self, reports: List[Dict[str, Any]], 
                                   total_quantity: int,
                                   learning_factor: float = 0.1) -> List[Dict[str, Any]]:
        """
        根據學習曲線分配數量
        
        Args:
            reports: 報表記錄列表
            total_quantity: 總數量
            learning_factor: 學習因子
            
        Returns:
            List[Dict[str, Any]]: 分配後的報表記錄
        """
        try:
            if not self.validate_input(reports, total_quantity):
                return reports
            
            weights = {}
            total_weight = 0.0
            
            for i, report in enumerate(reports):
                base_efficiency = report.get('efficiency_rate', 1.0)
                experience_years = report.get('experience_years', 0)
                
                # 學習曲線公式：效率 = 基礎效率 * (1 + 學習因子 * 經驗年數)
                learning_efficiency = base_efficiency * (1 + learning_factor * experience_years)
                
                weights[i] = max(learning_efficiency, 0)
                total_weight += weights[i]
            
            # 正規化權重
            if total_weight > 0:
                for i in weights:
                    weights[i] = weights[i] / total_weight
            else:
                # 如果總權重為0，平均分配
                equal_weight = 1.0 / len(reports) if reports else 0
                for i in weights:
                    weights[i] = equal_weight
            
            # 分配數量
            allocations = self.distribute_quantities(weights, total_quantity)
            
            # 應用分配結果
            allocated_reports = self.apply_allocation(reports, allocations)
            
            return allocated_reports
        except Exception as e:
            self.logger.error(f"學習曲線分配失敗: {str(e)}")
            return reports
    
    def get_efficiency_allocation_summary(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        獲取效率分配摘要
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[str, Any]: 效率分配摘要
        """
        try:
            efficiency_distribution = {}
            total_allocated_quantity = 0
            total_efficiency = 0.0
            
            for report in reports:
                efficiency_rate = report.get('efficiency_rate', 1.0)
                allocated_quantity = report.get('allocated_quantity', 0)
                
                total_allocated_quantity += allocated_quantity
                total_efficiency += efficiency_rate
                
                # 按效率區間統計
                efficiency_range = self._get_efficiency_range(efficiency_rate)
                if efficiency_range in efficiency_distribution:
                    efficiency_distribution[efficiency_range]['count'] += 1
                    efficiency_distribution[efficiency_range]['quantity'] += allocated_quantity
                else:
                    efficiency_distribution[efficiency_range] = {
                        'count': 1,
                        'quantity': allocated_quantity
                    }
            
            avg_efficiency = total_efficiency / len(reports) if reports else 0
            
            return {
                'total_allocated_quantity': total_allocated_quantity,
                'average_efficiency': avg_efficiency,
                'efficiency_distribution': efficiency_distribution
            }
        except Exception as e:
            self.logger.error(f"獲取效率分配摘要失敗: {str(e)}")
            return {}
    
    def _get_efficiency_range(self, efficiency: float) -> str:
        """
        獲取效率區間標籤
        
        Args:
            efficiency: 效率值
            
        Returns:
            str: 效率區間標籤
        """
        if efficiency < 0.5:
            return "低效率 (<50%)"
        elif efficiency < 0.8:
            return "中低效率 (50-80%)"
        elif efficiency < 1.0:
            return "中效率 (80-100%)"
        elif efficiency < 1.2:
            return "中高效率 (100-120%)"
        else:
            return "高效率 (>120%)" 