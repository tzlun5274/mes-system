"""
公司製造命令管理子模組 - 服務層
負責公司製造命令的同步、轉換和業務邏輯
"""

import logging
from datetime import datetime
from django.utils import timezone
from .models import ManufacturingOrder

logger = logging.getLogger(__name__)



class ManufacturingOrderConvertService:
    """公司製造命令轉換服務"""
    
    @classmethod
    def convert_to_workorder(cls, manufacturing_order_ids=None):
        """
        將製令單轉換成 MES 工單
        """
        try:
            if manufacturing_order_ids:
                orders = ManufacturingOrder.objects.filter(
                    id__in=manufacturing_order_ids,
                    is_converted=False
                )
            else:
                orders = ManufacturingOrder.objects.filter(
                    is_converted=False
                )
            
            converted_count = 0
            
            for order in orders:
                if cls._create_workorder_from_order(order):
                    converted_count += 1
            
            logger.info(f"轉換完成：成功轉換 {converted_count} 筆製令單")
            return {
                'success': True,
                'converted': converted_count
            }
            
        except Exception as e:
            logger.error(f"轉換製令單失敗：{str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def _create_workorder_from_order(cls, manufacturing_order):
        """從製令單創建工單"""
        try:
            from workorder.models import WorkOrder, WorkOrderProcess
            
            # 創建工單
            workorder = WorkOrder.objects.create(
                order_number=manufacturing_order.mkordno,
                product_code=manufacturing_order.product_id,
                quantity=manufacturing_order.prodt_qty,
                company_code=manufacturing_order.company_code,
                status='pending',
                order_source='erp'
            )
            
            # 創建預設工序
            WorkOrderProcess.objects.create(
                workorder_id=workorder.id,
                process_name='預設工序',
                step_order=1,
                planned_quantity=manufacturing_order.prodt_qty,
                status='pending'
            )
            
            # 標記為已轉換
            manufacturing_order.is_converted = True
            manufacturing_order.save()
            
            return True
            
        except Exception as e:
            logger.error(f"創建工單失敗：{str(e)}")
            return False
    
    @classmethod
    def _parse_date(cls, date_str):
        """解析日期字串"""
        if not date_str:
            return timezone.now().date()
        
        try:
            # 嘗試解析不同格式的日期
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return timezone.now().date()
        except:
            return timezone.now().date()


class ManufacturingOrderQueryService:
    """公司製造命令查詢服務"""
    
    @classmethod
    def get_company_statistics(cls):
        """取得各公司製造命令統計"""
        from django.db.models import Count, Q
        
        stats = ManufacturingOrder.objects.values('company_code').annotate(
            total_orders=Count('id'),
            converted_orders=Count('id', filter=Q(is_converted=True)),
            pending_orders=Count('id', filter=Q(is_converted=False))
        ).order_by('company_code')
        
        return stats
    
    @classmethod
    def get_order_by_product(cls, product_id, company_code=None):
        """根據產品編號取得製令單資訊"""
        queryset = ManufacturingOrder.objects.filter(product_id=product_id)
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        return queryset.order_by('-est_stock_out_date')
    
    @classmethod
    def search_orders(cls, company_code=None, mkordno=None, product_id=None):
        """搜尋製令單"""
        queryset = ManufacturingOrder.objects.all()
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        if mkordno:
            queryset = queryset.filter(mkordno__icontains=mkordno)
        
        if product_id:
            queryset = queryset.filter(product_id__icontains=product_id)
        
        return queryset.order_by('-est_stock_out_date')
