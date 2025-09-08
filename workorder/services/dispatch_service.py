# -*- coding: utf-8 -*-
"""
派工服務模組
提供統一的派工邏輯，支援個別、批量、自動批次派工功能
"""

import logging
from typing import List, Dict, Optional, Tuple
from django.db import transaction
from django.utils import timezone

from workorder.models import WorkOrder
from workorder.workorder_dispatch.models import WorkOrderDispatch

logger = logging.getLogger(__name__)


class WorkOrderDispatchService:
    """工單派工服務"""
    
    @classmethod
    def dispatch_single_workorder(cls, order_number: str, company_code: str = None) -> Dict:
        """
        派工單一工單
        
        Args:
            order_number: 工單編號
            company_code: 公司代號（可選）
            
        Returns:
            Dict: 包含 success, message, dispatch_id 等資訊
        """
        try:
            with transaction.atomic():
                # 查找工單
                workorder = cls._find_workorder(order_number, company_code)
                if not workorder:
                    return {
                        'success': False,
                        'message': f'工單 {order_number} 不存在',
                        'dispatch_id': None
                    }
                
                # 檢查是否已有派工單
                existing_dispatch = cls._check_existing_dispatch(workorder)
                if existing_dispatch:
                    return {
                        'success': False,
                        'message': f'工單 {order_number} 已有派工單',
                        'dispatch_id': existing_dispatch.id
                    }
                
                # 建立派工單
                dispatch = cls._create_dispatch(workorder)
                
                logger.info(f"成功為工單 {order_number} 建立派工單，派工單ID: {dispatch.id}")
                
                return {
                    'success': True,
                    'message': f'成功為工單 {order_number} 建立派工單',
                    'dispatch_id': dispatch.id,
                    'workorder': workorder,
                    'dispatch': dispatch
                }
                
        except Exception as e:
            logger.error(f"派工單一工單失敗：{str(e)}")
            return {
                'success': False,
                'message': f'派工失敗：{str(e)}',
                'dispatch_id': None
            }
    
    @classmethod
    def dispatch_multiple_workorders(cls, order_numbers: List[str], company_code: str = None) -> Dict:
        """
        批量派工多個工單
        
        Args:
            order_numbers: 工單編號列表
            company_code: 公司代號（可選）
            
        Returns:
            Dict: 包含 success, created_count, skipped_count, results 等資訊
        """
        try:
            with transaction.atomic():
                created_count = 0
                skipped_count = 0
                results = []
                
                for order_number in order_numbers:
                    result = cls.dispatch_single_workorder(order_number, company_code)
                    results.append(result)
                    
                    if result['success']:
                        created_count += 1
                    else:
                        skipped_count += 1
                
                logger.info(f"批量派工完成：成功 {created_count} 筆，跳過 {skipped_count} 筆")
                
                return {
                    'success': True,
                    'message': f'批量派工完成：成功 {created_count} 筆，跳過 {skipped_count} 筆',
                    'created_count': created_count,
                    'skipped_count': skipped_count,
                    'results': results
                }
                
        except Exception as e:
            logger.error(f"批量派工失敗：{str(e)}")
            return {
                'success': False,
                'message': f'批量派工失敗：{str(e)}',
                'created_count': 0,
                'skipped_count': 0,
                'results': []
            }
    
    @classmethod
    def auto_dispatch_all_workorders(cls, company_code: str = None) -> Dict:
        """
        自動批次派工所有未派工的工單
        
        Args:
            company_code: 公司代號（可選，如果提供則只派工該公司的工單）
            
        Returns:
            Dict: 包含 success, created_count, skipped_count, results 等資訊
        """
        try:
            with transaction.atomic():
                # 取得所有工單
                workorders_query = WorkOrder.objects.all()
                if company_code:
                    workorders_query = workorders_query.filter(company_code=company_code)
                
                all_workorders = workorders_query.all()
                
                # 找出真正未派工的工單
                undispatched_workorders = []
                for workorder in all_workorders:
                    if not cls._check_existing_dispatch(workorder):
                        undispatched_workorders.append(workorder)
                
                created_count = 0
                skipped_count = 0
                results = []
                
                # 為每個未派工工單建立派工單
                for workorder in undispatched_workorders:
                    result = cls.dispatch_single_workorder(workorder.order_number, workorder.company_code)
                    results.append(result)
                    
                    if result['success']:
                        created_count += 1
                    else:
                        skipped_count += 1
                
                logger.info(f"自動批次派工完成：成功 {created_count} 筆，跳過 {skipped_count} 筆")
                
                return {
                    'success': True,
                    'message': f'自動批次派工完成：成功 {created_count} 筆，跳過 {skipped_count} 筆',
                    'created_count': created_count,
                    'skipped_count': skipped_count,
                    'results': results
                }
                
        except Exception as e:
            logger.error(f"自動批次派工失敗：{str(e)}")
            return {
                'success': False,
                'message': f'自動批次派工失敗：{str(e)}',
                'created_count': 0,
                'skipped_count': 0,
                'results': []
            }
    
    @classmethod
    def _find_workorder(cls, order_number: str, company_code: str = None) -> Optional[WorkOrder]:
        """
        查找工單
        
        Args:
            order_number: 工單編號
            company_code: 公司代號（可選）
            
        Returns:
            WorkOrder 或 None
        """
        query = WorkOrder.objects.filter(order_number=order_number)
        if company_code:
            query = query.filter(company_code=company_code)
        
        return query.first()
    
    @classmethod
    def _check_existing_dispatch(cls, workorder: WorkOrder) -> Optional[WorkOrderDispatch]:
        """
        檢查工單是否已有派工單
        
        Args:
            workorder: 工單物件
            
        Returns:
            WorkOrderDispatch 或 None
        """
        return WorkOrderDispatch.objects.filter(
            order_number=workorder.order_number,
            product_code=workorder.product_code
        ).first()
    
    @classmethod
    def _create_dispatch(cls, workorder: WorkOrder) -> WorkOrderDispatch:
        """
        建立派工單
        
        Args:
            workorder: 工單物件
            
        Returns:
            WorkOrderDispatch 物件
        """
        return WorkOrderDispatch.objects.create(
            order_number=workorder.order_number,
            product_code=workorder.product_code,
            product_name=workorder.product_name or '',
            quantity=workorder.quantity,
            company_code=workorder.company_code,
            company_name=workorder.company_name or '',
            status='in_production',  # 直接設定為生產中狀態
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
    
    @classmethod
    def get_dispatch_status(cls, order_number: str, company_code: str = None) -> Dict:
        """
        取得工單的派工狀態
        
        Args:
            order_number: 工單編號
            company_code: 公司代號（可選）
            
        Returns:
            Dict: 包含派工狀態資訊
        """
        workorder = cls._find_workorder(order_number, company_code)
        if not workorder:
            return {
                'success': False,
                'message': f'工單 {order_number} 不存在',
                'has_dispatch': False
            }
        
        dispatch = cls._check_existing_dispatch(workorder)
        
        return {
            'success': True,
            'message': '查詢成功',
            'has_dispatch': dispatch is not None,
            'dispatch': dispatch,
            'workorder': workorder
        }
