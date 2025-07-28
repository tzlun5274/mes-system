# 智能分配算法基礎類別
# 本檔案定義了所有智能分配算法的基礎類別和共用方法

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta


class BaseAllocator:
    """智能分配算法基礎類別 - 所有分配算法的基礎類別"""
    
    def __init__(self):
        """初始化分配器"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def allocate_quantities(self, reports: List[Dict[str, Any]], total_quantity: int, **kwargs) -> List[Dict[str, Any]]:
        """
        分配數量（抽象方法）
        
        Args:
            reports: 報表記錄列表
            total_quantity: 總數量
            **kwargs: 其他參數
            
        Returns:
            List[Dict[str, Any]]: 分配後的報表記錄
        """
        raise NotImplementedError("子類別必須實作此方法")
    
    def validate_input(self, reports: List[Dict[str, Any]], total_quantity: int) -> bool:
        """
        驗證輸入參數
        
        Args:
            reports: 報表記錄列表
            total_quantity: 總數量
            
        Returns:
            bool: 驗證結果
        """
        try:
            if not reports:
                self.logger.error("報表記錄列表不能為空")
                return False
            
            if total_quantity <= 0:
                self.logger.error("總數量必須大於0")
                return False
            
            # 檢查必要欄位
            required_fields = ['work_hours', 'completed_quantity']
            for report in reports:
                for field in required_fields:
                    if field not in report:
                        self.logger.error(f"缺少必要欄位: {field}")
                        return False
            
            return True
        except Exception as e:
            self.logger.error(f"輸入驗證失敗: {str(e)}")
            return False
    
    def calculate_allocation_weights(self, reports: List[Dict[str, Any]], weight_type: str = 'time') -> Dict[int, float]:
        """
        計算分配權重
        
        Args:
            reports: 報表記錄列表
            weight_type: 權重類型 (time, efficiency, process)
            
        Returns:
            Dict[int, float]: 索引到權重的映射
        """
        try:
            weights = {}
            total_weight = 0.0
            
            for i, report in enumerate(reports):
                if weight_type == 'time':
                    # 按工作時數分配
                    weight = report.get('work_hours', 0)
                elif weight_type == 'efficiency':
                    # 按效率分配
                    weight = report.get('efficiency_rate', 0)
                elif weight_type == 'process':
                    # 按工序複雜度分配
                    weight = self._calculate_process_weight(report)
                else:
                    # 預設按工作時數分配
                    weight = report.get('work_hours', 0)
                
                weights[i] = max(weight, 0)  # 確保權重非負
                total_weight += weights[i]
            
            # 正規化權重
            if total_weight > 0:
                for i in weights:
                    weights[i] = weights[i] / total_weight
            
            return weights
        except Exception as e:
            self.logger.error(f"計算分配權重失敗: {str(e)}")
            return {}
    
    def _calculate_process_weight(self, report: Dict[str, Any]) -> float:
        """
        計算工序權重
        
        Args:
            report: 報表記錄
            
        Returns:
            float: 工序權重
        """
        try:
            process_name = report.get('process_name', '')
            
            # 根據工序名稱判斷複雜度
            process_weights = {
                'SMT': 1.5,  # SMT工序較複雜
                'TEST': 1.2,  # 測試工序中等複雜度
                'ASSEMBLY': 1.0,  # 組裝工序標準複雜度
                'PACKAGING': 0.8,  # 包裝工序較簡單
            }
            
            for process_type, weight in process_weights.items():
                if process_type in process_name.upper():
                    return weight
            
            return 1.0  # 預設權重
        except Exception as e:
            self.logger.error(f"計算工序權重失敗: {str(e)}")
            return 1.0
    
    def distribute_quantities(self, weights: Dict[int, float], total_quantity: int) -> Dict[int, int]:
        """
        根據權重分配數量
        
        Args:
            weights: 權重字典
            total_quantity: 總數量
            
        Returns:
            Dict[int, int]: 索引到分配數量的映射
        """
        try:
            allocations = {}
            remaining_quantity = total_quantity
            
            # 按權重比例分配
            for i, weight in weights.items():
                allocated = int(total_quantity * weight)
                allocations[i] = allocated
                remaining_quantity -= allocated
            
            # 處理剩餘數量（四捨五入造成的誤差）
            if remaining_quantity > 0:
                # 將剩餘數量分配給權重最大的記錄
                max_weight_index = max(weights.keys(), key=lambda k: weights[k])
                allocations[max_weight_index] += remaining_quantity
            
            return allocations
        except Exception as e:
            self.logger.error(f"分配數量失敗: {str(e)}")
            return {}
    
    def apply_allocation(self, reports: List[Dict[str, Any]], allocations: Dict[int, int]) -> List[Dict[str, Any]]:
        """
        應用分配結果到報表記錄
        
        Args:
            reports: 原始報表記錄
            allocations: 分配結果
            
        Returns:
            List[Dict[str, Any]]: 更新後的報表記錄
        """
        try:
            updated_reports = []
            
            for i, report in enumerate(reports):
                updated_report = report.copy()
                
                if i in allocations:
                    allocated_quantity = allocations[i]
                    original_quantity = report.get('completed_quantity', 0)
                    
                    updated_report.update({
                        'original_quantity': original_quantity,
                        'allocated_quantity': allocated_quantity,
                        'quantity_source': 'allocated',
                        'allocation_notes': f'智能分配: 原始數量 {original_quantity}, 分配數量 {allocated_quantity}'
                    })
                else:
                    # 沒有分配到數量的記錄
                    updated_report.update({
                        'original_quantity': report.get('completed_quantity', 0),
                        'allocated_quantity': 0,
                        'quantity_source': 'original',
                        'allocation_notes': '未分配到數量'
                    })
                
                updated_reports.append(updated_report)
            
            return updated_reports
        except Exception as e:
            self.logger.error(f"應用分配結果失敗: {str(e)}")
            return reports
    
    def calculate_allocation_accuracy(self, original_quantities: List[int], allocated_quantities: List[int]) -> Dict[str, float]:
        """
        計算分配準確度
        
        Args:
            original_quantities: 原始數量列表
            allocated_quantities: 分配數量列表
            
        Returns:
            Dict[str, float]: 準確度指標
        """
        try:
            if len(original_quantities) != len(allocated_quantities):
                return {'error': '數量列表長度不一致'}
            
            total_original = sum(original_quantities)
            total_allocated = sum(allocated_quantities)
            
            if total_original == 0:
                return {'error': '原始總數量為0'}
            
            # 計算各種準確度指標
            quantity_accuracy = abs(total_allocated - total_original) / total_original * 100
            
            # 計算各記錄的分配誤差
            individual_errors = []
            for orig, alloc in zip(original_quantities, allocated_quantities):
                if orig > 0:
                    error = abs(alloc - orig) / orig * 100
                    individual_errors.append(error)
            
            avg_error = sum(individual_errors) / len(individual_errors) if individual_errors else 0
            max_error = max(individual_errors) if individual_errors else 0
            
            return {
                'quantity_accuracy': round(100 - quantity_accuracy, 2),
                'average_error': round(avg_error, 2),
                'max_error': round(max_error, 2),
                'total_original': total_original,
                'total_allocated': total_allocated
            }
        except Exception as e:
            self.logger.error(f"計算分配準確度失敗: {str(e)}")
            return {'error': str(e)}
    
    def log_allocation(self, allocation_type: str, reports_count: int, total_quantity: int, accuracy: Dict[str, float]) -> None:
        """
        記錄分配過程
        
        Args:
            allocation_type: 分配類型
            reports_count: 報表記錄數量
            total_quantity: 總數量
            accuracy: 準確度指標
        """
        try:
            log_message = (
                f"分配類型: {allocation_type}, "
                f"記錄數量: {reports_count}, "
                f"總數量: {total_quantity}, "
                f"準確度: {accuracy}"
            )
            self.logger.info(log_message)
        except Exception as e:
            self.logger.error(f"記錄分配過程失敗: {str(e)}")
    
    def get_allocation_summary(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        取得分配摘要
        
        Args:
            reports: 報表記錄列表
            
        Returns:
            Dict[str, Any]: 分配摘要
        """
        try:
            total_original = sum(report.get('original_quantity', 0) for report in reports)
            total_allocated = sum(report.get('allocated_quantity', 0) for report in reports)
            
            # 統計分配來源
            source_counts = {}
            for report in reports:
                source = report.get('quantity_source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            summary = {
                'total_original_quantity': total_original,
                'total_allocated_quantity': total_allocated,
                'allocation_difference': total_allocated - total_original,
                'source_distribution': source_counts,
                'reports_count': len(reports),
                'allocation_ratio': total_allocated / total_original if total_original > 0 else 0
            }
            
            return summary
        except Exception as e:
            self.logger.error(f"取得分配摘要失敗: {str(e)}")
            return {} 