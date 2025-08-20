"""
工單填報管理認證相關模板標籤庫
提供權限檢查和用戶組驗證功能
"""

from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.filter(name='has_group')
def has_group(user, group_name):
    """
    檢查用戶是否屬於指定群組
    
    Args:
        user: 用戶對象
        group_name: 群組名稱
        
    Returns:
        bool: 如果用戶屬於該群組則返回 True，否則返回 False
    """
    if user.is_authenticated:
        try:
            # 檢查用戶是否為超級用戶
            if user.is_superuser:
                return True
            
            # 檢查用戶是否屬於指定群組
            return user.groups.filter(name=group_name).exists()
        except (Group.DoesNotExist, AttributeError):
            return False
    return False


@register.filter(name='has_permission')
def has_permission(user, permission_name):
    """
    檢查用戶是否具有指定權限
    
    Args:
        user: 用戶對象
        permission_name: 權限名稱 (格式: app_label.permission_name)
        
    Returns:
        bool: 如果用戶具有該權限則返回 True，否則返回 False
    """
    if user.is_authenticated:
        try:
            # 檢查用戶是否為超級用戶
            if user.is_superuser:
                return True
            
            # 檢查用戶是否具有指定權限
            return user.has_perm(permission_name)
        except (AttributeError, ValueError):
            return False
    return False


@register.filter(name='is_operator')
def is_operator(user):
    """
    檢查用戶是否為作業員
    
    Args:
        user: 用戶對象
        
    Returns:
        bool: 如果用戶為作業員則返回 True，否則返回 False
    """
    return has_group(user, '作業員')


@register.filter(name='is_supervisor')
def is_supervisor(user):
    """
    檢查用戶是否為主管
    
    Args:
        user: 用戶對象
        
    Returns:
        bool: 如果用戶為主管理則返回 True，否則返回 False
    """
    return has_group(user, '主管')


@register.filter(name='is_admin')
def is_admin(user):
    """
    檢查用戶是否為管理員
    
    Args:
        user: 用戶對象
        
    Returns:
        bool: 如果用戶為管理員則返回 True，否則返回 False
    """
    return has_group(user, '管理員') or user.is_superuser 