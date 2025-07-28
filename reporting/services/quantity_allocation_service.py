# 數量分配服務
# 整合智能分配功能到報表系統

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone

from ..allocators.hybrid_allocator import HybridAllocator


class QuantityAllocationService:
    """
    數量分配服務
    提供作業員報工數量智能分配功能
    """
    
    def __init__(self):
        """初始化服務"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.allocator = HybridAllocator()
    
    def allocate_workorder_quantities(self, workorder_id: str, date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """
        為指定工單分配數量
        
        Args:
            workorder_id: 工單號碼
            date_range: 日期範圍，如果為None則使用最近30天
            
        Returns:
            Dict[str, Any]: 分配結果
        """
        try:
            # 設定預設日期範圍
            if date_range is None:
                end_date = timezone.now()
                start_date = end_date - timedelta(days=30)
                date_range = {'start': start_date, 'end': end_date}
            
            self.logger.info(f"開始為工單 {workorder_id} 分配數量，日期範圍: {date_range['start']} 到 {date_range['end']}")
            
            # 執行分配
            result = self.allocator.allocate_workorder_quantities(workorder_id, date_range)
            
            if result['success']:
                # 可選：將分配結果儲存到資料庫
                # self._save_allocation_results(result['allocated_reports'])
                pass
            
            return result
            
        except Exception as e:
            self.logger.error(f"工單 {workorder_id} 數量分配服務失敗: {str(e)}")
            return {
                'success': False,
                'message': f'分配服務失敗: {str(e)}',
                'allocated_reports': []
            }
    
    def allocate_multiple_workorders(self, workorder_ids: List[str], date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """
        為多個工單批量分配數量
        
        Args:
            workorder_ids: 工單號碼列表
            date_range: 日期範圍
            
        Returns:
            Dict[str, Any]: 批量分配結果
        """
        try:
            results = {
                'success': True,
                'total_workorders': len(workorder_ids),
                'successful_allocations': 0,
                'failed_allocations': 0,
                'workorder_results': []
            }
            
            for workorder_id in workorder_ids:
                result = self.allocate_workorder_quantities(workorder_id, date_range)
                
                workorder_result = {
                    'workorder_id': workorder_id,
                    'success': result['success'],
                    'message': result.get('message', ''),
                    'statistics': result.get('statistics', {})
                }
                
                results['workorder_results'].append(workorder_result)
                
                if result['success']:
                    results['successful_allocations'] += 1
                else:
                    results['failed_allocations'] += 1
            
            self.logger.info(f"批量分配完成: 成功 {results['successful_allocations']} 個，失敗 {results['failed_allocations']} 個")
            
            return results
            
        except Exception as e:
            self.logger.error(f"批量分配失敗: {str(e)}")
            return {
                'success': False,
                'message': f'批量分配失敗: {str(e)}',
                'total_workorders': len(workorder_ids),
                'successful_allocations': 0,
                'failed_allocations': len(workorder_ids),
                'workorder_results': []
            }
    
    def get_allocation_summary(self, date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """
        取得分配摘要統計
        
        Args:
            date_range: 日期範圍
            
        Returns:
            Dict[str, Any]: 分配摘要
        """
        try:
            from workorder.models import OperatorSupplementReport
            
            # 設定預設日期範圍
            if date_range is None:
                end_date = timezone.now()
                start_date = end_date - timedelta(days=30)
                date_range = {'start': start_date, 'end': end_date}
            
            # 查詢分配相關的報工記錄
            reports = OperatorSupplementReport.objects.filter(
                work_date__range=[date_range['start'].date(), date_range['end'].date()],
                approval_status='approved'
            )
            
            # 統計各來源的數量
            source_stats = {}
            total_original = 0
            total_allocated = 0
            
            for report in reports:
                source = report.quantity_source
                if source not in source_stats:
                    source_stats[source] = {
                        'count': 0,
                        'total_quantity': 0,
                        'total_allocated': 0
                    }
                
                source_stats[source]['count'] += 1
                source_stats[source]['total_quantity'] += report.work_quantity
                source_stats[source]['total_allocated'] += report.allocated_quantity
                
                total_original += report.work_quantity
                total_allocated += report.allocated_quantity
            
            # 統計作業員分配情況
            operator_stats = {}
            for report in reports:
                if report.allocated_quantity > 0:
                    operator_name = report.operator.name if report.operator else '未知'
                    if operator_name not in operator_stats:
                        operator_stats[operator_name] = {
                            'total_allocated': 0,
                            'allocation_count': 0
                        }
                    
                    operator_stats[operator_name]['total_allocated'] += report.allocated_quantity
                    operator_stats[operator_name]['allocation_count'] += 1
            
            return {
                'date_range': {
                    'start': date_range['start'].date(),
                    'end': date_range['end'].date()
                },
                'total_reports': reports.count(),
                'total_original_quantity': total_original,
                'total_allocated_quantity': total_allocated,
                'allocation_ratio': (total_allocated / total_original * 100) if total_original > 0 else 0,
                'source_distribution': source_stats,
                'operator_distribution': operator_stats
            }
            
        except Exception as e:
            self.logger.error(f"取得分配摘要失敗: {str(e)}")
            return {
                'error': str(e),
                'date_range': date_range,
                'total_reports': 0,
                'total_original_quantity': 0,
                'total_allocated_quantity': 0,
                'allocation_ratio': 0,
                'source_distribution': {},
                'operator_distribution': {}
            }
    
    def _save_allocation_results(self, allocated_reports: List[Any]) -> bool:
        """
        將分配結果儲存到資料庫
        
        Args:
            allocated_reports: 分配後的報工記錄
            
        Returns:
            bool: 儲存是否成功
        """
        try:
            with transaction.atomic():
                for report in allocated_reports:
                    if hasattr(report, 'id') and report.id:
                        # 更新現有記錄
                        original_report = report.__class__.objects.get(id=report.id)
                        original_report.allocated_quantity = report.allocated_quantity
                        original_report.quantity_source = report.quantity_source
                        original_report.allocation_notes = report.allocation_notes
                        original_report.save()
                    else:
                        # 創建新記錄（如果需要）
                        report.save()
            
            self.logger.info(f"成功儲存 {len(allocated_reports)} 筆分配結果")
            return True
            
        except Exception as e:
            self.logger.error(f"儲存分配結果失敗: {str(e)}")
            return False
    
    def validate_allocation_data(self, workorder_id: str, date_range: Dict[str, datetime]) -> Dict[str, Any]:
        """
        驗證分配數據的完整性
        
        Args:
            workorder_id: 工單號碼
            date_range: 日期範圍
            
        Returns:
            Dict[str, Any]: 驗證結果
        """
        try:
            from workorder.models import OperatorSupplementReport
            
            # 檢查是否有報工記錄
            reports = OperatorSupplementReport.objects.filter(
                workorder__order_number=workorder_id,
                work_date__range=[date_range['start'].date(), date_range['end'].date()],
                approval_status='approved'
            )
            
            if not reports.exists():
                return {
                    'valid': False,
                    'message': f'工單 {workorder_id} 在指定日期範圍內沒有報工記錄',
                    'issues': ['no_reports']
                }
            
            # 檢查是否有包裝工序記錄
            packaging_reports = reports.filter(
                process__name__icontains='包裝'
            )
            
            if not packaging_reports.exists():
                return {
                    'valid': False,
                    'message': f'工單 {workorder_id} 沒有包裝工序記錄',
                    'issues': ['no_packaging_reports']
                }
            
            # 檢查包裝工序是否有數量
            packaging_with_quantity = packaging_reports.filter(work_quantity__gt=0)
            
            if not packaging_with_quantity.exists():
                return {
                    'valid': False,
                    'message': f'工單 {workorder_id} 包裝工序沒有有效數量',
                    'issues': ['no_packaging_quantity']
                }
            
            # 檢查是否有需要分配的記錄
            unfilled_reports = reports.exclude(
                process__name__icontains='包裝'
            ).filter(
                work_quantity=0
            )
            
            if not unfilled_reports.exists():
                return {
                    'valid': False,
                    'message': f'工單 {workorder_id} 沒有需要分配數量的記錄',
                    'issues': ['no_unfilled_reports']
                }
            
            return {
                'valid': True,
                'message': f'工單 {workorder_id} 數據驗證通過',
                'total_reports': reports.count(),
                'packaging_reports': packaging_reports.count(),
                'unfilled_reports': unfilled_reports.count()
            }
            
        except Exception as e:
            self.logger.error(f"驗證分配數據失敗: {str(e)}")
            return {
                'valid': False,
                'message': f'驗證失敗: {str(e)}',
                'issues': ['validation_error']
            } 