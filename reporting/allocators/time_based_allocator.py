# 基於時間的分配器模組
# 本檔案負責根據工作時間進行數量分配

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from .base_allocator import BaseAllocator


class TimeBasedAllocator(BaseAllocator):
    """基於時間的分配器 - 根據工作時間分配數量"""
    
    def __init__(self):
        """初始化時間分配器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def allocate_quantities(self, reports: List[Dict[str, Any]], total_quantity: int, **kwargs) -> List[Dict[str, Any]]:
        """
        根據工作時間分配數量
        
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
            
            # 計算時間權重
            weights = self.calculate_time_weights(reports)
            
            # 分配數量
            allocations = self.distribute_quantities(weights, total_quantity)
            
            # 應用分配結果
            allocated_reports = self.apply_allocation(reports, allocations)
            
            # 記錄分配過程
            self.log_allocation('time_based', len(reports), total_quantity, {})
            
            return allocated_reports
        except Exception as e:
            self.logger.error(f"時間分配失敗: {str(e)}")
            return reports
    
    def calculate_time_weights(self, reports: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        計算時間權重
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[int, float]: 索引到時間權重的映射
        """
        try:
            weights = {}
            total_time = 0.0
            
            for i, report in enumerate(reports):
                # 獲取工作時間
                work_hours = report.get('work_hours', 0)
                start_time = report.get('start_time')
                end_time = report.get('end_time')
                
                # 如果沒有工作時數，嘗試從時間計算
                if work_hours <= 0 and start_time and end_time:
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    if isinstance(end_time, str):
                        end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    
                    time_diff = end_time - start_time
                    work_hours = time_diff.total_seconds() / 3600
                
                weights[i] = max(work_hours, 0)
                total_time += weights[i]
            
            # 正規化權重
            if total_time > 0:
                for i in weights:
                    weights[i] = weights[i] / total_time
            else:
                # 如果總時間為0，平均分配
                equal_weight = 1.0 / len(reports) if reports else 0
                for i in weights:
                    weights[i] = equal_weight
            
            return weights
        except Exception as e:
            self.logger.error(f"計算時間權重失敗: {str(e)}")
            return {}
    
    def calculate_effective_time_weights(self, reports: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        計算有效時間權重（扣除休息時間）
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[int, float]: 索引到有效時間權重的映射
        """
        try:
            weights = {}
            total_effective_time = 0.0
            
            for i, report in enumerate(reports):
                work_hours = report.get('work_hours', 0)
                break_time = report.get('break_time', 0)
                
                # 計算有效工作時間
                effective_hours = max(work_hours - break_time, 0)
                weights[i] = effective_hours
                total_effective_time += effective_hours
            
            # 正規化權重
            if total_effective_time > 0:
                for i in weights:
                    weights[i] = weights[i] / total_effective_time
            else:
                # 如果總有效時間為0，平均分配
                equal_weight = 1.0 / len(reports) if reports else 0
                for i in weights:
                    weights[i] = equal_weight
            
            return weights
        except Exception as e:
            self.logger.error(f"計算有效時間權重失敗: {str(e)}")
            return {}
    
    def calculate_overtime_weights(self, reports: List[Dict[str, Any]], 
                                 regular_hours: float = 8.0) -> Dict[int, float]:
        """
        計算加班時間權重
        
        Args:
            reports: 報表記錄列表
            regular_hours: 正常工時
            
        Returns:
            Dict[int, float]: 索引到加班時間權重的映射
        """
        try:
            weights = {}
            total_overtime = 0.0
            
            for i, report in enumerate(reports):
                work_hours = report.get('work_hours', 0)
                
                # 計算加班時間
                overtime_hours = max(work_hours - regular_hours, 0)
                weights[i] = overtime_hours
                total_overtime += overtime_hours
            
            # 正規化權重
            if total_overtime > 0:
                for i in weights:
                    weights[i] = weights[i] / total_overtime
            else:
                # 如果沒有加班時間，使用正常時間權重
                return self.calculate_time_weights(reports)
            
            return weights
        except Exception as e:
            self.logger.error(f"計算加班時間權重失敗: {str(e)}")
            return {}
    
    def allocate_with_time_constraints(self, reports: List[Dict[str, Any]], 
                                     total_quantity: int,
                                     min_time_threshold: float = 0.5,
                                     max_time_threshold: float = 12.0) -> List[Dict[str, Any]]:
        """
        根據時間約束分配數量
        
        Args:
            reports: 報表記錄列表
            total_quantity: 總數量
            min_time_threshold: 最小時間閾值
            max_time_threshold: 最大時間閾值
            
        Returns:
            List[Dict[str, Any]]: 分配後的報表記錄
        """
        try:
            if not self.validate_input(reports, total_quantity):
                return reports
            
            # 篩選符合時間約束的記錄
            filtered_reports = []
            filtered_indices = []
            
            for i, report in enumerate(reports):
                work_hours = report.get('work_hours', 0)
                if min_time_threshold <= work_hours <= max_time_threshold:
                    filtered_reports.append(report)
                    filtered_indices.append(i)
            
            if not filtered_reports:
                self.logger.warning("沒有符合時間約束的記錄")
                return reports
            
            # 計算時間權重
            weights = self.calculate_time_weights(filtered_reports)
            
            # 分配數量
            allocations = self.distribute_quantities(weights, total_quantity)
            
            # 應用分配結果到原始記錄
            result_reports = reports.copy()
            for i, allocation in allocations.items():
                original_index = filtered_indices[i]
                result_reports[original_index]['allocated_quantity'] = allocation
                result_reports[original_index]['allocation_method'] = 'time_constrained'
            
            return result_reports
        except Exception as e:
            self.logger.error(f"時間約束分配失敗: {str(e)}")
            return reports
    
    def allocate_with_time_efficiency(self, reports: List[Dict[str, Any]], 
                                    total_quantity: int) -> List[Dict[str, Any]]:
        """
        根據時間效率分配數量
        
        Args:
            reports: 報表記錄列表
            total_quantity: 總數量
            
        Returns:
            List[Dict[str, Any]]: 分配後的報表記錄
        """
        try:
            if not self.validate_input(reports, total_quantity):
                return reports
            
            # 計算時間效率權重
            weights = {}
            total_efficiency = 0.0
            
            for i, report in enumerate(reports):
                work_hours = report.get('work_hours', 0)
                completed_quantity = report.get('completed_quantity', 0)
                
                # 計算時間效率（每小時完成數量）
                if work_hours > 0:
                    efficiency = completed_quantity / work_hours
                else:
                    efficiency = 0
                
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
            
            # 分配數量
            allocations = self.distribute_quantities(weights, total_quantity)
            
            # 應用分配結果
            allocated_reports = self.apply_allocation(reports, allocations)
            
            return allocated_reports
        except Exception as e:
            self.logger.error(f"時間效率分配失敗: {str(e)}")
            return reports
    
    def get_time_allocation_summary(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        獲取時間分配摘要
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[str, Any]: 時間分配摘要
        """
        try:
            total_work_hours = 0.0
            total_allocated_quantity = 0
            time_distribution = {}
            
            for report in reports:
                work_hours = report.get('work_hours', 0)
                allocated_quantity = report.get('allocated_quantity', 0)
                
                total_work_hours += work_hours
                total_allocated_quantity += allocated_quantity
                
                # 按時間區間統計
                time_range = self._get_time_range(work_hours)
                if time_range in time_distribution:
                    time_distribution[time_range]['count'] += 1
                    time_distribution[time_range]['quantity'] += allocated_quantity
                else:
                    time_distribution[time_range] = {
                        'count': 1,
                        'quantity': allocated_quantity
                    }
            
            return {
                'total_work_hours': total_work_hours,
                'total_allocated_quantity': total_allocated_quantity,
                'average_hours_per_unit': total_work_hours / total_allocated_quantity if total_allocated_quantity > 0 else 0,
                'time_distribution': time_distribution
            }
        except Exception as e:
            self.logger.error(f"獲取時間分配摘要失敗: {str(e)}")
            return {}
    
    def _get_time_range(self, hours: float) -> str:
        """
        獲取時間區間標籤
        
        Args:
            hours: 小時數
            
        Returns:
            str: 時間區間標籤
        """
        if hours < 2:
            return "0-2小時"
        elif hours < 4:
            return "2-4小時"
        elif hours < 6:
            return "4-6小時"
        elif hours < 8:
            return "6-8小時"
        elif hours < 10:
            return "8-10小時"
        else:
            return "10小時以上" 