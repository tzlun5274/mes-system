# 基於工序的分配器模組
# 本檔案負責根據工序複雜度進行數量分配

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from .base_allocator import BaseAllocator


class ProcessBasedAllocator(BaseAllocator):
    """基於工序的分配器 - 根據工序複雜度分配數量"""
    
    def __init__(self):
        """初始化工序分配器"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        # 工序複雜度權重定義
        self.process_complexity_weights = {
            'packaging': 1.0,      # 包裝工序（最簡單）
            'assembly': 1.2,       # 組裝工序
            'testing': 1.5,        # 測試工序
            'inspection': 1.8,     # 檢驗工序
            'machining': 2.0,      # 加工工序
            'welding': 2.5,        # 焊接工序
            'painting': 1.3,       # 噴漆工序
            'heat_treatment': 3.0, # 熱處理工序
            'default': 1.0         # 預設權重
        }
    
    def allocate_quantities(self, reports: List[Dict[str, Any]], total_quantity: int, **kwargs) -> List[Dict[str, Any]]:
        """
        根據工序複雜度分配數量
        
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
            
            # 計算工序權重
            weights = self.calculate_process_weights(reports)
            
            # 分配數量
            allocations = self.distribute_quantities(weights, total_quantity)
            
            # 應用分配結果
            allocated_reports = self.apply_allocation(reports, allocations)
            
            # 記錄分配過程
            self.log_allocation('process_based', len(reports), total_quantity, {})
            
            return allocated_reports
        except Exception as e:
            self.logger.error(f"工序分配失敗: {str(e)}")
            return reports
    
    def calculate_process_weights(self, reports: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        計算工序權重
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[int, float]: 索引到工序權重的映射
        """
        try:
            weights = {}
            total_weight = 0.0
            
            for i, report in enumerate(reports):
                process_name = report.get('process_name', '').lower()
                process_type = report.get('process_type', '').lower()
                
                # 獲取工序複雜度權重
                complexity_weight = self.get_process_complexity_weight(process_name, process_type)
                
                # 考慮工作時間
                work_hours = report.get('work_hours', 0)
                
                # 計算綜合權重
                weight = complexity_weight * work_hours
                weights[i] = max(weight, 0)
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
            
            return weights
        except Exception as e:
            self.logger.error(f"計算工序權重失敗: {str(e)}")
            return {}
    
    def get_process_complexity_weight(self, process_name: str, process_type: str) -> float:
        """
        獲取工序複雜度權重
        
        Args:
            process_name: 工序名稱
            process_type: 工序類型
            
        Returns:
            float: 複雜度權重
        """
        try:
            # 根據工序名稱判斷複雜度
            if 'packaging' in process_name or '包裝' in process_name:
                return self.process_complexity_weights['packaging']
            elif 'assembly' in process_name or '組裝' in process_name:
                return self.process_complexity_weights['assembly']
            elif 'testing' in process_name or '測試' in process_name:
                return self.process_complexity_weights['testing']
            elif 'inspection' in process_name or '檢驗' in process_name:
                return self.process_complexity_weights['inspection']
            elif 'machining' in process_name or '加工' in process_name:
                return self.process_complexity_weights['machining']
            elif 'welding' in process_name or '焊接' in process_name:
                return self.process_complexity_weights['welding']
            elif 'painting' in process_name or '噴漆' in process_name:
                return self.process_complexity_weights['painting']
            elif 'heat_treatment' in process_name or '熱處理' in process_name:
                return self.process_complexity_weights['heat_treatment']
            
            # 根據工序類型判斷複雜度
            if process_type in self.process_complexity_weights:
                return self.process_complexity_weights[process_type]
            
            # 預設權重
            return self.process_complexity_weights['default']
        except Exception as e:
            self.logger.error(f"獲取工序複雜度權重失敗: {str(e)}")
            return self.process_complexity_weights['default']
    
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
            total_weight = 0.0
            
            for i, report in enumerate(reports):
                operator_skill_level = report.get('operator_skill_level', 1)
                process_complexity = self.get_process_complexity_weight(
                    report.get('process_name', ''),
                    report.get('process_type', '')
                )
                work_hours = report.get('work_hours', 0)
                
                # 技能等級權重（1-5級）
                skill_weight = min(operator_skill_level / 5.0, 1.0)
                
                # 綜合權重 = 技能權重 * 工序複雜度 * 工作時間
                weight = skill_weight * process_complexity * work_hours
                weights[i] = max(weight, 0)
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
            
            return weights
        except Exception as e:
            self.logger.error(f"計算技能權重失敗: {str(e)}")
            return {}
    
    def calculate_equipment_based_weights(self, reports: List[Dict[str, Any]]) -> Dict[int, float]:
        """
        計算基於設備的權重
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[int, float]: 索引到設備權重的映射
        """
        try:
            weights = {}
            total_weight = 0.0
            
            for i, report in enumerate(reports):
                equipment_efficiency = report.get('equipment_efficiency', 1.0)
                equipment_capacity = report.get('equipment_capacity', 1.0)
                work_hours = report.get('work_hours', 0)
                
                # 設備綜合權重
                equipment_weight = equipment_efficiency * equipment_capacity
                
                # 綜合權重 = 設備權重 * 工作時間
                weight = equipment_weight * work_hours
                weights[i] = max(weight, 0)
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
            
            return weights
        except Exception as e:
            self.logger.error(f"計算設備權重失敗: {str(e)}")
            return {}
    
    def allocate_by_process_priority(self, reports: List[Dict[str, Any]], 
                                   total_quantity: int,
                                   priority_processes: List[str] = None) -> List[Dict[str, Any]]:
        """
        根據工序優先級分配數量
        
        Args:
            reports: 報表記錄列表
            total_quantity: 總數量
            priority_processes: 優先工序列表
            
        Returns:
            List[Dict[str, Any]]: 分配後的報表記錄
        """
        try:
            if not self.validate_input(reports, total_quantity):
                return reports
            
            if not priority_processes:
                priority_processes = ['packaging', 'assembly', 'testing']
            
            # 按優先級分組
            priority_reports = []
            normal_reports = []
            priority_indices = []
            normal_indices = []
            
            for i, report in enumerate(reports):
                process_name = report.get('process_name', '').lower()
                if any(priority in process_name for priority in priority_processes):
                    priority_reports.append(report)
                    priority_indices.append(i)
                else:
                    normal_reports.append(report)
                    normal_indices.append(i)
            
            # 優先分配給優先工序（70%）
            priority_quantity = int(total_quantity * 0.7)
            normal_quantity = total_quantity - priority_quantity
            
            result_reports = reports.copy()
            
            # 分配優先工序
            if priority_reports and priority_quantity > 0:
                priority_weights = self.calculate_process_weights(priority_reports)
                priority_allocations = self.distribute_quantities(priority_weights, priority_quantity)
                
                for i, allocation in priority_allocations.items():
                    original_index = priority_indices[i]
                    result_reports[original_index]['allocated_quantity'] = allocation
                    result_reports[original_index]['allocation_method'] = 'process_priority'
            
            # 分配一般工序
            if normal_reports and normal_quantity > 0:
                normal_weights = self.calculate_process_weights(normal_reports)
                normal_allocations = self.distribute_quantities(normal_weights, normal_quantity)
                
                for i, allocation in normal_allocations.items():
                    original_index = normal_indices[i]
                    result_reports[original_index]['allocated_quantity'] = allocation
                    result_reports[original_index]['allocation_method'] = 'process_normal'
            
            return result_reports
        except Exception as e:
            self.logger.error(f"工序優先級分配失敗: {str(e)}")
            return reports
    
    def get_process_allocation_summary(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        獲取工序分配摘要
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[str, Any]: 工序分配摘要
        """
        try:
            process_distribution = {}
            total_allocated_quantity = 0
            
            for report in reports:
                process_name = report.get('process_name', '未知工序')
                allocated_quantity = report.get('allocated_quantity', 0)
                work_hours = report.get('work_hours', 0)
                
                total_allocated_quantity += allocated_quantity
                
                if process_name in process_distribution:
                    process_distribution[process_name]['quantity'] += allocated_quantity
                    process_distribution[process_name]['hours'] += work_hours
                    process_distribution[process_name]['count'] += 1
                else:
                    process_distribution[process_name] = {
                        'quantity': allocated_quantity,
                        'hours': work_hours,
                        'count': 1
                    }
            
            # 計算每個工序的平均效率
            for process_name, data in process_distribution.items():
                if data['hours'] > 0:
                    data['efficiency'] = data['quantity'] / data['hours']
                else:
                    data['efficiency'] = 0
            
            return {
                'total_allocated_quantity': total_allocated_quantity,
                'process_distribution': process_distribution,
                'process_count': len(process_distribution)
            }
        except Exception as e:
            self.logger.error(f"獲取工序分配摘要失敗: {str(e)}")
            return {}
    
    def set_process_complexity_weights(self, weights: Dict[str, float]) -> None:
        """
        設定工序複雜度權重
        
        Args:
            weights: 工序複雜度權重字典
        """
        try:
            self.process_complexity_weights.update(weights)
            self.logger.info(f"更新工序複雜度權重: {weights}")
        except Exception as e:
            self.logger.error(f"設定工序複雜度權重失敗: {str(e)}")
    
    def get_process_complexity_weights(self) -> Dict[str, float]:
        """
        獲取工序複雜度權重
        
        Returns:
            Dict[str, float]: 工序複雜度權重字典
        """
        return self.process_complexity_weights.copy() 