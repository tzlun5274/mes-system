# 混合智能分配器
# 專門處理作業員報工數量分配問題

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.db.models import Q, Sum
from django.utils import timezone

from .base_allocator import BaseAllocator


class HybridAllocator(BaseAllocator):
    """
    混合智能分配器
    專門處理作業員報工數量分配問題，支援多種分配策略
    """
    
    def __init__(self):
        """初始化混合分配器"""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 包裝工序關鍵字（用於識別最後工序）
        self.packaging_keywords = [
            '包裝', 'packaging', '出貨', 'shipping', 'final', '最後'
        ]
        
        # 分配策略權重
        self.strategy_weights = {
            'time': 0.4,      # 時間比例
            'efficiency': 0.3, # 效率比例
            'process': 0.2,   # 工序複雜度
            'operator': 0.1   # 作業員等級
        }
    
    def allocate_workorder_quantities(self, workorder_id: str, date_range: Dict[str, datetime]) -> Dict[str, Any]:
        """
        為指定工單分配數量
        
        Args:
            workorder_id: 工單號碼
            date_range: 日期範圍 {'start': datetime, 'end': datetime}
            
        Returns:
            Dict[str, Any]: 分配結果
        """
        try:
            self.logger.info(f"開始為工單 {workorder_id} 分配數量")
            
            # 步驟1: 獲取工單所有報工記錄
            all_reports = self._get_workorder_reports(workorder_id, date_range)
            if not all_reports:
                return {
                    'success': False,
                    'message': f'工單 {workorder_id} 在指定日期範圍內沒有報工記錄',
                    'allocated_reports': []
                }
            
            # 步驟2: 識別包裝工序和包裝人員
            packaging_reports = self._identify_packaging_reports(all_reports)
            
            # 步驟3: 計算最終總產出
            final_total_quantity = self._calculate_final_quantity(packaging_reports)
            if final_total_quantity <= 0:
                return {
                    'success': False,
                    'message': f'工單 {workorder_id} 沒有有效的包裝數量，無法進行分配',
                    'allocated_reports': all_reports
                }
            
            # 步驟4: 分離已填寫和未填寫數量的報工
            filled_reports, unfilled_reports = self._separate_filled_unfilled_reports(all_reports, packaging_reports)
            
            # 步驟5: 計算已填寫數量總和
            filled_quantity_sum = sum(report.work_quantity for report in filled_reports)
            
            # 步驟6: 計算需要分配的剩餘數量
            remaining_quantity = max(0, final_total_quantity - filled_quantity_sum)
            
            # 步驟7: 執行智能分配
            allocated_reports = self._execute_allocation(
                unfilled_reports, 
                remaining_quantity, 
                final_total_quantity
            )
            
            # 步驟8: 整合所有報工記錄
            final_reports = self._merge_all_reports(filled_reports, packaging_reports, allocated_reports)
            
            # 步驟9: 計算分配統計
            allocation_stats = self._calculate_allocation_statistics(
                final_reports, final_total_quantity, filled_quantity_sum, remaining_quantity
            )
            
            self.logger.info(f"工單 {workorder_id} 數量分配完成，總分配數量: {remaining_quantity}")
            
            return {
                'success': True,
                'message': f'工單 {workorder_id} 數量分配完成',
                'allocated_reports': final_reports,
                'statistics': allocation_stats
            }
            
        except Exception as e:
            self.logger.error(f"工單 {workorder_id} 數量分配失敗: {str(e)}")
            return {
                'success': False,
                'message': f'分配失敗: {str(e)}',
                'allocated_reports': []
            }
    
    def _get_workorder_reports(self, workorder_id: str, date_range: Dict[str, datetime]) -> List[Any]:
        """
        獲取工單所有報工記錄
        
        Args:
            workorder_id: 工單號碼
            date_range: 日期範圍
            
        Returns:
            List[Any]: 報工記錄列表
        """
        try:
            from workorder.models import OperatorSupplementReport
            
            reports = OperatorSupplementReport.objects.filter(
                workorder__order_number=workorder_id,
                work_date__range=[date_range['start'].date(), date_range['end'].date()],
                approval_status='approved'
            ).select_related(
                'operator', 'workorder', 'process', 'equipment'
            ).order_by('work_date', 'start_time')
            
            return list(reports)
            
        except Exception as e:
            self.logger.error(f"獲取工單報工記錄失敗: {str(e)}")
            return []
    
    def _identify_packaging_reports(self, reports: List[Any]) -> List[Any]:
        """
        識別包裝工序報工記錄
        
        Args:
            reports: 所有報工記錄
            
        Returns:
            List[Any]: 包裝工序報工記錄
        """
        packaging_reports = []
        
        for report in reports:
            process_name = report.process.name if report.process else report.operation
            
            # 檢查是否為包裝工序
            if self._is_packaging_process(process_name):
                packaging_reports.append(report)
        
        return packaging_reports
    
    def _is_packaging_process(self, process_name: str) -> bool:
        """
        判斷是否為包裝工序
        
        Args:
            process_name: 工序名稱
            
        Returns:
            bool: 是否為包裝工序
        """
        if not process_name:
            return False
        
        process_name_lower = process_name.lower()
        
        # 檢查是否包含包裝關鍵字
        for keyword in self.packaging_keywords:
            if keyword.lower() in process_name_lower:
                return True
        
        return False
    
    def _calculate_final_quantity(self, packaging_reports: List[Any]) -> int:
        """
        計算最終總產出數量
        
        Args:
            packaging_reports: 包裝工序報工記錄
            
        Returns:
            int: 最終總產出數量
        """
        total_quantity = 0
        
        for report in packaging_reports:
            if report.work_quantity and report.work_quantity > 0:
                total_quantity += report.work_quantity
        
        return total_quantity
    
    def _separate_filled_unfilled_reports(self, all_reports: List[Any], packaging_reports: List[Any]) -> Tuple[List[Any], List[Any]]:
        """
        分離已填寫和未填寫數量的報工記錄
        
        Args:
            all_reports: 所有報工記錄
            packaging_reports: 包裝工序報工記錄
            
        Returns:
            Tuple[List[Any], List[Any]]: (已填寫記錄, 未填寫記錄)
        """
        filled_reports = []
        unfilled_reports = []
        
        # 排除包裝工序記錄
        non_packaging_reports = [r for r in all_reports if r not in packaging_reports]
        
        for report in non_packaging_reports:
            if report.work_quantity and report.work_quantity > 0:
                filled_reports.append(report)
            else:
                unfilled_reports.append(report)
        
        return filled_reports, unfilled_reports
    
    def _execute_allocation(self, unfilled_reports: List[Any], remaining_quantity: int, total_quantity: int) -> List[Any]:
        """
        執行智能分配
        
        Args:
            unfilled_reports: 未填寫數量的報工記錄
            remaining_quantity: 需要分配的剩餘數量
            total_quantity: 總數量
            
        Returns:
            List[Any]: 分配後的報工記錄
        """
        if not unfilled_reports or remaining_quantity <= 0:
            return unfilled_reports
        
        # 計算每個作業員的分配權重
        operator_weights = self._calculate_operator_weights(unfilled_reports)
        
        # 按權重分配數量
        allocated_reports = []
        total_weight = sum(operator_weights.values())
        
        if total_weight <= 0:
            # 如果沒有權重，平均分配
            avg_quantity = remaining_quantity // len(unfilled_reports)
            remainder = remaining_quantity % len(unfilled_reports)
            
            for i, report in enumerate(unfilled_reports):
                allocated_qty = avg_quantity + (1 if i < remainder else 0)
                allocated_reports.append(self._create_allocated_report(report, allocated_qty, '平均分配'))
        else:
            # 按權重分配
            allocated_quantities = {}
            distributed_qty = 0
            
            for operator_id, weight in operator_weights.items():
                allocated_qty = int(remaining_quantity * weight / total_weight)
                allocated_quantities[operator_id] = allocated_qty
                distributed_qty += allocated_qty
            
            # 處理剩餘數量（四捨五入造成的誤差）
            remaining_qty = remaining_quantity - distributed_qty
            if remaining_qty > 0:
                # 將剩餘數量分配給權重最大的作業員
                max_weight_operator = max(operator_weights.items(), key=lambda x: x[1])[0]
                allocated_quantities[max_weight_operator] += remaining_qty
            
            # 應用分配結果
            for report in unfilled_reports:
                operator_id = report.operator.id if report.operator else 0
                allocated_qty = allocated_quantities.get(operator_id, 0)
                weight_percentage = (operator_weights.get(operator_id, 0) / total_weight * 100) if total_weight > 0 else 0
                
                allocation_note = f'基於工作時間比例分配 (佔比: {weight_percentage:.1f}%)'
                allocated_reports.append(self._create_allocated_report(report, allocated_qty, allocation_note))
        
        return allocated_reports
    
    def _calculate_operator_weights(self, reports: List[Any]) -> Dict[int, float]:
        """
        計算作業員分配權重
        
        Args:
            reports: 報工記錄列表
            
        Returns:
            Dict[int, float]: 作業員ID到權重的映射
        """
        operator_weights = {}
        
        for report in reports:
            operator_id = report.operator.id if report.operator else 0
            
            # 計算工作時數
            work_hours = self._calculate_work_hours(report)
            
            # 計算效率（如果有歷史數據）
            efficiency = self._calculate_efficiency(report)
            
            # 計算工序複雜度
            process_complexity = self._calculate_process_complexity(report)
            
            # 計算作業員等級
            operator_level = self._calculate_operator_level(report)
            
            # 綜合權重計算
            total_weight = (
                work_hours * self.strategy_weights['time'] +
                efficiency * self.strategy_weights['efficiency'] +
                process_complexity * self.strategy_weights['process'] +
                operator_level * self.strategy_weights['operator']
            )
            
            operator_weights[operator_id] = max(total_weight, 0)
        
        return operator_weights
    
    def _calculate_work_hours(self, report: Any) -> float:
        """
        計算工作時數
        
        Args:
            report: 報工記錄
            
        Returns:
            float: 工作時數
        """
        try:
            if report.start_time and report.end_time and report.work_date:
                start_dt = datetime.combine(report.work_date, report.start_time)
                end_dt = datetime.combine(report.work_date, report.end_time)
                
                # 處理跨日的情況
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                
                duration = end_dt - start_dt
                return duration.total_seconds() / 3600
        except Exception as e:
            self.logger.warning(f"計算工作時數失敗: {str(e)}")
        
        return 0.0
    
    def _calculate_efficiency(self, report: Any) -> float:
        """
        計算作業員效率（基於歷史數據）
        
        Args:
            report: 報工記錄
            
        Returns:
            float: 效率值
        """
        try:
            from workorder.models import OperatorSupplementReport
            
            if not report.operator or not report.process:
                return 1.0
            
            # 查詢該作業員在該工序的歷史效率
            historical_reports = OperatorSupplementReport.objects.filter(
                operator=report.operator,
                process=report.process,
                work_quantity__gt=0,
                approval_status='approved'
            ).exclude(id=report.id)[:10]  # 最近10筆記錄
            
            if not historical_reports:
                return 1.0
            
            total_efficiency = 0
            count = 0
            
            for hist_report in historical_reports:
                work_hours = self._calculate_work_hours(hist_report)
                if work_hours > 0:
                    efficiency = hist_report.work_quantity / work_hours
                    total_efficiency += efficiency
                    count += 1
            
            return total_efficiency / count if count > 0 else 1.0
            
        except Exception as e:
            self.logger.warning(f"計算效率失敗: {str(e)}")
            return 1.0
    
    def _calculate_process_complexity(self, report: Any) -> float:
        """
        計算工序複雜度
        
        Args:
            report: 報工記錄
            
        Returns:
            float: 複雜度值
        """
        # 這裡可以根據工序名稱或工序設定來計算複雜度
        # 暫時使用簡單的邏輯
        process_name = report.process.name if report.process else report.operation
        
        if not process_name:
            return 1.0
        
        # 根據工序名稱判斷複雜度
        complexity_map = {
            '測試': 1.2,
            '檢驗': 1.1,
            '包裝': 1.0,
            '組裝': 1.3,
            '焊接': 1.4,
            '測試': 1.2,
        }
        
        for keyword, complexity in complexity_map.items():
            if keyword in process_name:
                return complexity
        
        return 1.0
    
    def _calculate_operator_level(self, report: Any) -> float:
        """
        計算作業員等級
        
        Args:
            report: 報工記錄
            
        Returns:
            float: 等級值
        """
        # 這裡可以根據作業員的歷史表現來計算等級
        # 暫時使用固定值
        return 1.0
    
    def _create_allocated_report(self, original_report: Any, allocated_quantity: int, allocation_note: str) -> Any:
        """
        創建分配後的報工記錄
        
        Args:
            original_report: 原始報工記錄
            allocated_quantity: 分配數量
            allocation_note: 分配說明
            
        Returns:
            Any: 分配後的報工記錄
        """
        # 創建一個新的報工記錄物件，包含分配資訊
        allocated_report = type(original_report)()
        
        # 複製原始記錄的所有屬性
        for field in original_report._meta.fields:
            if field.name != 'id':
                setattr(allocated_report, field.name, getattr(original_report, field.name))
        
        # 設定分配相關屬性
        allocated_report.work_quantity = allocated_quantity
        allocated_report.allocated_quantity = allocated_quantity
        allocated_report.quantity_source = 'allocated'
        allocated_report.allocation_notes = allocation_note
        
        return allocated_report
    
    def _merge_all_reports(self, filled_reports: List[Any], packaging_reports: List[Any], allocated_reports: List[Any]) -> List[Any]:
        """
        合併所有報工記錄
        
        Args:
            filled_reports: 已填寫數量的報工記錄
            packaging_reports: 包裝工序報工記錄
            allocated_reports: 分配後的報工記錄
            
        Returns:
            List[Any]: 合併後的報工記錄
        """
        merged_reports = []
        
        # 添加已填寫數量的記錄
        for report in filled_reports:
            report.quantity_source = 'original'
            report.allocation_notes = '原始填寫數量'
            merged_reports.append(report)
        
        # 添加包裝工序記錄
        for report in packaging_reports:
            report.quantity_source = 'packaging'
            report.allocation_notes = '包裝工序最終數量'
            merged_reports.append(report)
        
        # 添加分配後的記錄
        merged_reports.extend(allocated_reports)
        
        # 按日期和時間排序
        merged_reports.sort(key=lambda x: (x.work_date, x.start_time))
        
        return merged_reports
    
    def _calculate_allocation_statistics(self, reports: List[Any], total_quantity: int, filled_quantity: int, allocated_quantity: int) -> Dict[str, Any]:
        """
        計算分配統計資訊
        
        Args:
            reports: 報工記錄列表
            total_quantity: 總數量
            filled_quantity: 已填寫數量
            allocated_quantity: 分配數量
            
        Returns:
            Dict[str, Any]: 統計資訊
        """
        # 統計各來源的記錄數量
        source_counts = {}
        for report in reports:
            source = getattr(report, 'quantity_source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # 統計各作業員的分配數量
        operator_allocations = {}
        for report in reports:
            if hasattr(report, 'allocated_quantity') and report.allocated_quantity > 0:
                operator_name = report.operator.name if report.operator else '未知'
                operator_allocations[operator_name] = operator_allocations.get(operator_name, 0) + report.allocated_quantity
        
        return {
            'total_quantity': total_quantity,
            'filled_quantity': filled_quantity,
            'allocated_quantity': allocated_quantity,
            'allocation_ratio': (allocated_quantity / total_quantity * 100) if total_quantity > 0 else 0,
            'source_distribution': source_counts,
            'operator_allocations': operator_allocations,
            'total_reports': len(reports)
        } 