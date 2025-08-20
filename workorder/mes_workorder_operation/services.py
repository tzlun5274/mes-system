"""
MES 工單作業子模組 - 服務層
"""

from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import MesWorkorderOperation, MesWorkorderOperationDetail, MesWorkorderOperationHistory


class MesWorkorderOperationService:
    """
    MES 工單作業服務類
    """
    
    @staticmethod
    def create_operation(company_code, workorder_number, product_code, operation_name, **kwargs):
        """
        建立 MES 工單作業
        
        Args:
            company_code (str): 公司代號
            workorder_number (str): 工單號碼
            product_code (str): 產品編號
            operation_name (str): 作業名稱
            **kwargs: 其他參數
            
        Returns:
            MesWorkorderOperation: 建立的作業實例
        """
        # 檢查是否已存在相同的作業
        existing = MesWorkorderOperation.objects.filter(
            company_code=company_code,
            workorder_number=workorder_number,
            product_code=product_code,
            operation_name=operation_name
        ).first()
        
        if existing:
            raise ValidationError(f'已存在相同的作業：{operation_name}')
        
        # 建立新作業
        operation = MesWorkorderOperation.objects.create(
            company_code=company_code,
            workorder_number=workorder_number,
            product_code=product_code,
            operation_name=operation_name,
            **kwargs
        )
        
        return operation
    
    @staticmethod
    def get_operation_by_id(operation_id):
        """
        根據ID取得作業
        
        Args:
            operation_id (int): 作業ID
            
        Returns:
            MesWorkorderOperation: 作業實例
        """
        try:
            return MesWorkorderOperation.objects.get(id=operation_id)
        except MesWorkorderOperation.DoesNotExist:
            raise ValidationError(f'找不到ID為 {operation_id} 的作業')
    
    @staticmethod
    def get_operations_by_workorder(company_code, workorder_number, product_code):
        """
        根據工單資訊取得所有作業
        
        Args:
            company_code (str): 公司代號
            workorder_number (str): 工單號碼
            product_code (str): 產品編號
            
        Returns:
            QuerySet: 作業查詢集
        """
        return MesWorkorderOperation.objects.filter(
            company_code=company_code,
            workorder_number=workorder_number,
            product_code=product_code
        ).order_by('created_at')
    
    @staticmethod
    def search_operations(filters=None):
        """
        搜尋作業
        
        Args:
            filters (dict): 搜尋條件
            
        Returns:
            QuerySet: 作業查詢集
        """
        queryset = MesWorkorderOperation.objects.all()
        
        if not filters:
            return queryset
        
        # 公司代號
        if filters.get('company_code'):
            queryset = queryset.filter(company_code__icontains=filters['company_code'])
        
        # 工單號碼
        if filters.get('workorder_number'):
            queryset = queryset.filter(workorder_number__icontains=filters['workorder_number'])
        
        # 產品編號
        if filters.get('product_code'):
            queryset = queryset.filter(product_code__icontains=filters['product_code'])
        
        # 作業類型
        if filters.get('operation_type'):
            queryset = queryset.filter(operation_type=filters['operation_type'])
        
        # 作業狀態
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        # 分配作業員
        if filters.get('assigned_operator'):
            queryset = queryset.filter(assigned_operator__icontains=filters['assigned_operator'])
        
        # 日期範圍
        if filters.get('date_from'):
            queryset = queryset.filter(planned_start_date__gte=filters['date_from'])
        
        if filters.get('date_to'):
            queryset = queryset.filter(planned_start_date__lte=filters['date_to'])
        
        # 完成率範圍
        if filters.get('completion_rate_min') is not None:
            # 這裡需要計算完成率，可能需要額外的邏輯
            pass
        
        if filters.get('completion_rate_max') is not None:
            # 這裡需要計算完成率，可能需要額外的邏輯
            pass
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def update_operation_status(operation_id, new_status, operator=None):
        """
        更新作業狀態
        
        Args:
            operation_id (int): 作業ID
            new_status (str): 新狀態
            operator (str): 操作者
            
        Returns:
            MesWorkorderOperation: 更新的作業實例
        """
        operation = MesWorkorderOperationService.get_operation_by_id(operation_id)
        
        old_status = operation.status
        operation.status = new_status
        
        # 根據狀態更新時間
        if new_status == 'in_progress' and old_status == 'pending':
            operation.actual_start_date = timezone.now()
        elif new_status == 'completed':
            operation.actual_end_date = timezone.now()
        
        operation.save()
        
        # 記錄歷史
        MesWorkorderOperationHistory.objects.create(
            operation=operation,
            history_type='updated',
            history_description=f'狀態變更：{operation.get_status_display()} → {operation.get_status_display()}',
            operator=operator or 'system',
            old_values={'status': old_status},
            new_values={'status': new_status}
        )
        
        return operation
    
    @staticmethod
    def bulk_update_status(operation_ids, new_status, operator=None):
        """
        批量更新作業狀態
        
        Args:
            operation_ids (list): 作業ID列表
            new_status (str): 新狀態
            operator (str): 操作者
            
        Returns:
            dict: 更新結果
        """
        success_count = 0
        error_count = 0
        errors = []
        
        for operation_id in operation_ids:
            try:
                MesWorkorderOperationService.update_operation_status(
                    operation_id, new_status, operator
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f'作業ID {operation_id}: {str(e)}')
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
    
    @staticmethod
    def get_operation_statistics(company_code=None):
        """
        取得作業統計資訊
        
        Args:
            company_code (str): 公司代號（可選）
            
        Returns:
            dict: 統計資訊
        """
        queryset = MesWorkorderOperation.objects.all()
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        total_operations = queryset.count()
        pending_operations = queryset.filter(status='pending').count()
        in_progress_operations = queryset.filter(status='in_progress').count()
        completed_operations = queryset.filter(status='completed').count()
        cancelled_operations = queryset.filter(status='cancelled').count()
        
        # 計算平均完成率
        operations_with_quantity = queryset.filter(planned_quantity__gt=0)
        if operations_with_quantity.exists():
            total_completion_rate = sum(
                op.get_completion_rate() for op in operations_with_quantity
            )
            avg_completion_rate = total_completion_rate / operations_with_quantity.count()
        else:
            avg_completion_rate = 0
        
        return {
            'total_operations': total_operations,
            'pending_operations': pending_operations,
            'in_progress_operations': in_progress_operations,
            'completed_operations': completed_operations,
            'cancelled_operations': cancelled_operations,
            'avg_completion_rate': round(avg_completion_rate, 2)
        }


class MesWorkorderOperationDetailService:
    """
    MES 工單作業明細服務類
    """
    
    @staticmethod
    def create_detail(operation_id, detail_name, detail_type='process', **kwargs):
        """
        建立作業明細
        
        Args:
            operation_id (int): 作業ID
            detail_name (str): 明細名稱
            detail_type (str): 明細類型
            **kwargs: 其他參數
            
        Returns:
            MesWorkorderOperationDetail: 建立的明細實例
        """
        operation = MesWorkorderOperationService.get_operation_by_id(operation_id)
        
        detail = MesWorkorderOperationDetail.objects.create(
            operation=operation,
            detail_name=detail_name,
            detail_type=detail_type,
            **kwargs
        )
        
        return detail
    
    @staticmethod
    def update_detail_completion(detail_id, actual_quantity, is_completed=None):
        """
        更新明細完成情況
        
        Args:
            detail_id (int): 明細ID
            actual_quantity (int): 實際數量
            is_completed (bool): 是否完成
            
        Returns:
            MesWorkorderOperationDetail: 更新的明細實例
        """
        try:
            detail = MesWorkorderOperationDetail.objects.get(id=detail_id)
        except MesWorkorderOperationDetail.DoesNotExist:
            raise ValidationError(f'找不到ID為 {detail_id} 的明細')
        
        detail.actual_quantity = actual_quantity
        
        if is_completed is not None:
            detail.is_completed = is_completed
        
        detail.save()
        
        return detail
    
    @staticmethod
    def get_operation_details(operation_id):
        """
        取得作業的所有明細
        
        Args:
            operation_id (int): 作業ID
            
        Returns:
            QuerySet: 明細查詢集
        """
        operation = MesWorkorderOperationService.get_operation_by_id(operation_id)
        return operation.details.all().order_by('created_at')


class MesWorkorderOperationHistoryService:
    """
    MES 工單作業歷史服務類
    """
    
    @staticmethod
    def get_operation_history(operation_id, limit=None):
        """
        取得作業歷史記錄
        
        Args:
            operation_id (int): 作業ID
            limit (int): 限制數量
            
        Returns:
            QuerySet: 歷史記錄查詢集
        """
        operation = MesWorkorderOperationService.get_operation_by_id(operation_id)
        queryset = operation.history.all().order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @staticmethod
    def get_recent_activities(company_code=None, limit=50):
        """
        取得最近的活動記錄
        
        Args:
            company_code (str): 公司代號（可選）
            limit (int): 限制數量
            
        Returns:
            QuerySet: 歷史記錄查詢集
        """
        queryset = MesWorkorderOperationHistory.objects.all()
        
        if company_code:
            queryset = queryset.filter(operation__company_code=company_code)
        
        return queryset.order_by('-created_at')[:limit] 