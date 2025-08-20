"""
MES 工單作業子模組 - 信號處理
"""

from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
from .models import MesWorkorderOperation, MesWorkorderOperationDetail, MesWorkorderOperationHistory
from django.db import models


@receiver(pre_save, sender=MesWorkorderOperation)
def mes_workorder_operation_pre_save(sender, instance, **kwargs):
    """
    MES 工單作業儲存前的處理
    """
    # 自動更新完成率
    if instance.planned_quantity > 0:
        completion_rate = (instance.completed_quantity / instance.planned_quantity) * 100
        if completion_rate >= 100 and instance.status != 'completed':
            instance.status = 'completed'
            instance.actual_end_date = timezone.now()
        elif completion_rate > 0 and instance.status == 'pending':
            instance.status = 'in_progress'
            if not instance.actual_start_date:
                instance.actual_start_date = timezone.now()


@receiver(post_save, sender=MesWorkorderOperation)
def mes_workorder_operation_post_save(sender, instance, created, **kwargs):
    """
    MES 工單作業儲存後的處理
    """
    # 記錄歷史
    if created:
        history_type = 'created'
        history_description = f'建立 MES 工單作業：{instance.operation_name}'
    else:
        history_type = 'updated'
        history_description = f'更新 MES 工單作業：{instance.operation_name}'
    
    # 這裡可以添加獲取當前用戶的邏輯
    operator = 'system'  # 預設值
    
    MesWorkorderOperationHistory.objects.create(
        operation=instance,
        history_type=history_type,
        history_description=history_description,
        operator=operator,
        new_values={
            'status': instance.status,
            'completed_quantity': instance.completed_quantity,
            'defect_quantity': instance.defect_quantity,
            'assigned_operator': instance.assigned_operator,
            'assigned_equipment': instance.assigned_equipment,
        }
    )


@receiver(pre_save, sender=MesWorkorderOperationDetail)
def mes_workorder_operation_detail_pre_save(sender, instance, **kwargs):
    """
    MES 工單作業明細儲存前的處理
    """
    # 自動更新完成率
    if instance.planned_quantity > 0:
        instance.completion_rate = (instance.actual_quantity / instance.planned_quantity) * 100
        
        # 自動設定完成狀態
        if instance.completion_rate >= 100:
            instance.is_completed = True
        elif instance.actual_quantity > 0:
            instance.is_completed = False


@receiver(post_save, sender=MesWorkorderOperationDetail)
def mes_workorder_operation_detail_post_save(sender, instance, created, **kwargs):
    """
    MES 工單作業明細儲存後的處理
    """
    # 更新主表的完成數量
    operation = instance.operation
    total_completed = operation.details.filter(is_completed=True).aggregate(
        total=models.Sum('actual_quantity')
    )['total'] or 0
    
    if operation.completed_quantity != total_completed:
        operation.completed_quantity = total_completed
        operation.save(update_fields=['completed_quantity'])


@receiver(pre_delete, sender=MesWorkorderOperation)
def mes_workorder_operation_pre_delete(sender, instance, **kwargs):
    """
    MES 工單作業刪除前的處理
    """
    # 記錄刪除歷史
    operator = 'system'  # 預設值
    
    MesWorkorderOperationHistory.objects.create(
        operation=instance,
        history_type='deleted',
        history_description=f'刪除 MES 工單作業：{instance.operation_name}',
        operator=operator,
        old_values={
            'status': instance.status,
            'completed_quantity': instance.completed_quantity,
            'defect_quantity': instance.defect_quantity,
            'assigned_operator': instance.assigned_operator,
            'assigned_equipment': instance.assigned_equipment,
        }
    ) 