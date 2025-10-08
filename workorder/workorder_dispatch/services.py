"""
派工單管理服務
負責派工單的統計資料更新和狀態管理
"""

import logging
from django.db import transaction
from django.utils import timezone
from .models import WorkOrderDispatch

logger = logging.getLogger('workorder')

class WorkOrderDispatchService:
    """派工單服務類"""
    
    @staticmethod
    def update_dispatch_statistics(dispatch_id):
        """
        更新指定派工單的統計資料
        
        Args:
            dispatch_id (int): 派工單ID
            
        Returns:
            dict: 更新結果
        """
        try:
            dispatch = WorkOrderDispatch.objects.get(id=dispatch_id)
            # 使用新的統計服務
            from workorder.services.dispatch_statistics_service import DispatchStatisticsService
            result = DispatchStatisticsService.update_all_statistics(dispatch)
            
            if result:
                logger.info(f"派工單 {dispatch.order_number} 統計資料更新成功")
            else:
                logger.warning(f"派工單 {dispatch.order_number} 統計資料更新失敗")
            
            return {
                'success': True,
                'message': '統計資料更新成功',
                'dispatch_id': dispatch_id,
                'order_number': dispatch.order_number,
                'product_code': dispatch.product_code
            }
            
        except WorkOrderDispatch.DoesNotExist:
            logger.error(f"派工單 ID {dispatch_id} 不存在")
            return {
                'success': False,
                'message': f'派工單 ID {dispatch_id} 不存在'
            }
        except Exception as e:
            logger.error(f"更新派工單 {dispatch_id} 統計資料失敗: {str(e)}")
            return {
                'success': False,
                'message': f'更新統計資料失敗: {str(e)}'
            }
    
    @staticmethod
    def update_all_dispatches_statistics():
        """
        更新所有派工單的統計資料
        
        Returns:
            dict: 更新結果
        """
        try:
            dispatches = WorkOrderDispatch.objects.all()
            success_count = 0
            error_count = 0
            
            for dispatch in dispatches:
                try:
                    # 使用新的統計服務
                    from workorder.services.dispatch_statistics_service import DispatchStatisticsService
                    result = DispatchStatisticsService.update_all_statistics(dispatch)
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                        logger.error(f"更新派工單 {dispatch.order_number} 統計資料失敗")
                except Exception as e:
                    error_count += 1
                    logger.error(f"更新派工單 {dispatch.order_number} 統計資料失敗: {str(e)}")
            
            logger.info(f"批量更新完成: 成功 {success_count} 筆, 失敗 {error_count} 筆")
            
            return {
                'success': True,
                'message': f'批量更新完成: 成功 {success_count} 筆, 失敗 {error_count} 筆',
                'success_count': success_count,
                'error_count': error_count
            }
            
        except Exception as e:
            logger.error(f"批量更新派工單統計資料失敗: {str(e)}")
            return {
                'success': False,
                'message': f'批量更新失敗: {str(e)}'
            }
    
    @staticmethod
    def update_monitoring_data(dispatch):
        """
        更新派工單的監控資料
        
        Args:
            dispatch (WorkOrderDispatch): 派工單實例
            
        Returns:
            dict: 更新結果
        """
        try:
            # 使用新的統計服務
            from workorder.services.dispatch_statistics_service import DispatchStatisticsService
            result = DispatchStatisticsService.update_all_statistics(dispatch)
            
            if result:
                logger.info(f"派工單 {dispatch.order_number} 監控資料更新成功")
            else:
                logger.warning(f"派工單 {dispatch.order_number} 監控資料更新失敗")
            
            return {
                'success': True,
                'message': '監控資料更新成功',
                'order_number': dispatch.order_number,
                'product_code': dispatch.product_code
            }
            
        except Exception as e:
            logger.error(f"更新派工單 {dispatch.order_number} 監控資料失敗: {str(e)}")
            return {
                'success': False,
                'message': f'更新監控資料失敗: {str(e)}'
            }
    
    @staticmethod
    def update_dispatches_by_order_number(order_number):
        """
        根據工單號碼更新相關派工單的統計資料
        
        Args:
            order_number (str): 工單號碼
            
        Returns:
            dict: 更新結果
        """
        try:
            dispatches = WorkOrderDispatch.objects.filter(order_number=order_number)
            success_count = 0
            error_count = 0
            
            for dispatch in dispatches:
                try:
                    # 使用新的統計服務
                    from workorder.services.dispatch_statistics_service import DispatchStatisticsService
                    result = DispatchStatisticsService.update_all_statistics(dispatch)
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                        logger.error(f"更新派工單 {dispatch.order_number} 統計資料失敗")
                except Exception as e:
                    error_count += 1
                    logger.error(f"更新派工單 {dispatch.order_number} 統計資料失敗: {str(e)}")
            
            logger.info(f"工單 {order_number} 相關派工單更新完成: 成功 {success_count} 筆, 失敗 {error_count} 筆")
            
            return {
                'success': True,
                'message': f'工單 {order_number} 相關派工單更新完成: 成功 {success_count} 筆, 失敗 {error_count} 筆',
                'order_number': order_number,
                'success_count': success_count,
                'error_count': error_count
            }
            
        except Exception as e:
            logger.error(f"更新工單 {order_number} 相關派工單統計資料失敗: {str(e)}")
            return {
                'success': False,
                'message': f'更新失敗: {str(e)}'
            }
    
    @staticmethod
    def get_dispatch_summary(dispatch_id):
        """
        取得派工單摘要資訊
        
        Args:
            dispatch_id (int): 派工單ID
            
        Returns:
            dict: 派工單摘要資訊
        """
        try:
            dispatch = WorkOrderDispatch.objects.get(id=dispatch_id)
            
            return {
                'success': True,
                'dispatch_id': dispatch.id,
                'order_number': dispatch.order_number,
                'product_code': dispatch.product_code,
                'company_code': dispatch.company_code,
                'planned_quantity': dispatch.planned_quantity,
                'status': dispatch.status,
                'completion_rate': float(dispatch.completion_rate),
                'packaging_completion_rate': float(dispatch.packaging_completion_rate),
                'total_quantity': dispatch.total_quantity,
                'packaging_total_quantity': dispatch.packaging_total_quantity,
                'can_complete': dispatch.can_complete,
                'fillwork_approved_count': dispatch.fillwork_approved_count,
                'onsite_completed_count': dispatch.onsite_completed_count,
                'last_fillwork_update': dispatch.last_fillwork_update,
                'last_onsite_update': dispatch.last_onsite_update
            }
            
        except WorkOrderDispatch.DoesNotExist:
            return {
                'success': False,
                'message': f'派工單 ID {dispatch_id} 不存在'
            }
        except Exception as e:
            logger.error(f"取得派工單 {dispatch_id} 摘要資訊失敗: {str(e)}")
            return {
                'success': False,
                'message': f'取得摘要資訊失敗: {str(e)}'
            } 