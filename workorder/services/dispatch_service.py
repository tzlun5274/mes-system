"""
派工服務模組
處理工單派工的業務邏輯
"""

from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction
from ..models import WorkOrder
from ..workorder_dispatch.models import WorkOrderDispatch
import logging

logger = logging.getLogger(__name__)


class DispatchService:
    """派工服務類別"""
    
    def __init__(self):
        self.logger = logger
    
    def dispatch_workorder(self, workorder_id, user=None):
        """
        為指定工單建立派工單
        
        Args:
            workorder_id (int): 工單ID
            user (User): 執行派工的使用者
            
        Returns:
            dict: 包含成功狀態和訊息的字典
        """
        try:
            with transaction.atomic():
                # 查詢工單
                workorder = WorkOrder.objects.get(id=workorder_id)
                
                # 檢查是否已有派工單
                existing_dispatch = WorkOrderDispatch.objects.filter(
                    company_code=workorder.company_code,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code
                ).first()
                
                if existing_dispatch:
                    return {
                        'success': False,
                        'error': f'工單 {workorder.order_number} 已有派工單',
                        'dispatch_id': existing_dispatch.id
                    }
                
                # 建立派工單
                dispatch = WorkOrderDispatch.objects.create(
                    company_code=workorder.company_code,
                    company_name=workorder.company_name,
                    order_number=workorder.order_number,
                    product_code=workorder.product_code,
                    product_name=workorder.product_name,
                    planned_quantity=workorder.quantity,
                    status="in_production",  # 直接設定為生產中
                    dispatch_date=timezone.now().date(),
                    created_by=str(user) if user else "system",
                )
                
                # 記錄日誌
                self.logger.info(f'成功建立派工單: {dispatch.id} - 工單: {workorder.order_number}')
                
                return {
                    'success': True,
                    'message': f'派工單建立成功，已設定為生產中狀態',
                    'dispatch_id': dispatch.id,
                    'workorder': {
                        'id': workorder.id,
                        'company_code': workorder.company_code,
                        'company_name': workorder.company_name,
                        'order_number': workorder.order_number,
                        'product_code': workorder.product_code,
                        'product_name': workorder.product_name,
                        'quantity': workorder.quantity
                    }
                }
                
        except WorkOrder.DoesNotExist:
            return {
                'success': False,
                'error': '工單不存在'
            }
        except Exception as e:
            self.logger.error(f'派工失敗: {str(e)}')
            return {
                'success': False,
                'error': f'派工失敗: {str(e)}'
            }
    
    def dispatch_workorder_by_identifier(self, company_code, order_number, product_code, user=None):
        """
        根據唯一識別符建立派工單
        
        Args:
            company_code (str): 公司代號
            order_number (str): 工單號碼
            product_code (str): 產品編號
            user (User): 執行派工的使用者
            
        Returns:
            dict: 包含成功狀態和訊息的字典
        """
        try:
            with transaction.atomic():
                # 查詢工單
                workorder = WorkOrder.objects.get(
                    company_code=company_code,
                    order_number=order_number,
                    product_code=product_code
                )
                
                return self.dispatch_workorder(workorder.id, user)
                
        except WorkOrder.DoesNotExist:
            return {
                'success': False,
                'error': f'工單不存在: {company_code}-{order_number}-{product_code}'
            }
        except Exception as e:
            self.logger.error(f'派工失敗: {str(e)}')
            return {
                'success': False,
                'error': f'派工失敗: {str(e)}'
            }
    
    def get_workorders_by_order_number(self, order_number):
        """
        根據工單號碼查詢所有匹配的工單
        
        Args:
            order_number (str): 工單號碼
            
        Returns:
            list: 工單列表
        """
        workorders = WorkOrder.objects.filter(order_number=order_number)
        return [
            {
                'id': wo.id,
                'company_code': wo.company_code,
                'company_name': wo.company_name,
                'order_number': wo.order_number,
                'product_code': wo.product_code,
                'product_name': wo.product_name,
                'quantity': wo.quantity,
                'status': wo.status,
                'created_at': wo.created_at
            }
            for wo in workorders
        ]
    
    def check_dispatch_status(self, company_code, order_number, product_code):
        """
        檢查工單的派工狀態
        
        Args:
            company_code (str): 公司代號
            order_number (str): 工單號碼
            product_code (str): 產品編號
            
        Returns:
            dict: 派工狀態資訊
        """
        try:
            dispatch = WorkOrderDispatch.objects.get(
                company_code=company_code,
                order_number=order_number,
                product_code=product_code
            )
            
            return {
                'has_dispatch': True,
                'dispatch_id': dispatch.id,
                'status': dispatch.status,
                'dispatch_date': dispatch.dispatch_date,
                'created_by': dispatch.created_by
            }
        except WorkOrderDispatch.DoesNotExist:
            return {
                'has_dispatch': False
            }
    
    def batch_dispatch_workorders(self, workorder_ids, user=None):
        """
        批量派工
        
        Args:
            workorder_ids (list): 工單ID列表
            user (User): 執行派工的使用者
            
        Returns:
            dict: 批量派工結果
        """
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        for workorder_id in workorder_ids:
            result = self.dispatch_workorder(workorder_id, user)
            
            if result['success']:
                results['success'].append(result)
            elif '已有派工單' in result.get('error', ''):
                results['skipped'].append(result)
            else:
                results['failed'].append(result)
        
        return results

