"""
系統管理工具函數
提供權限檢查等通用功能
"""

from .models import UserWorkPermission


def check_user_work_permission(user, operator_code=None, process_name=None, permission_type='both'):
    """
    檢查使用者是否有權限進行填報報工或現場報工
    
    Args:
        user: 使用者物件
        operator_code: 作業員編號（可選）
        process_name: 工序名稱（可選）
        permission_type: 權限類型（'fill_work', 'onsite_reporting', 'both'）
    
    Returns:
        dict: 權限檢查結果
        {
            'has_permission': bool,
            'message': str,
            'permission': UserWorkPermission or None
        }
    """
    try:
        # 檢查使用者是否有工作權限設定
        permission = UserWorkPermission.get_user_permission(user, permission_type)
        
        if not permission:
            return {
                'has_permission': False,
                'message': f'使用者 {user.username} 沒有 {permission_type} 權限設定',
                'permission': None
            }
        
        # 檢查作業員權限
        if operator_code and not permission.can_operate_operator(operator_code):
            return {
                'has_permission': False,
                'message': f'使用者 {user.username} 沒有權限操作作業員 {operator_code}',
                'permission': permission
            }
        
        # 檢查工序權限
        if process_name and not permission.can_operate_process(process_name):
            return {
                'has_permission': False,
                'message': f'使用者 {user.username} 沒有權限操作工序 {process_name}',
                'permission': permission
            }
        
        return {
            'has_permission': True,
            'message': '權限檢查通過',
            'permission': permission
        }
        
    except Exception as e:
        return {
            'has_permission': False,
            'message': f'權限檢查發生錯誤: {str(e)}',
            'permission': None
        }


def get_user_allowed_operators(user, permission_type='both'):
    """
    獲取使用者可以操作的作業員列表
    
    Args:
        user: 使用者物件
        permission_type: 權限類型
    
    Returns:
        list: 可操作的作業員編號列表，空列表表示可以操作所有作業員
    """
    try:
        permission = UserWorkPermission.get_user_permission(user, permission_type)
        if permission:
            return permission.get_operator_codes_list()
        return []
    except Exception:
        return []


def get_user_allowed_processes(user, permission_type='both'):
    """
    獲取使用者可以操作的工序列表
    
    Args:
        user: 使用者物件
        permission_type: 權限類型
    
    Returns:
        list: 可操作的工序名稱列表，空列表表示可以操作所有工序
    """
    try:
        permission = UserWorkPermission.get_user_permission(user, permission_type)
        if permission:
            return permission.get_process_names_list()
        return []
    except Exception:
        return []


def can_user_fill_work(user):
    """
    檢查使用者是否可以進行填報報工
    
    Args:
        user: 使用者物件
    
    Returns:
        bool: 是否可以進行填報報工
    """
    try:
        permission = UserWorkPermission.get_user_permission(user, 'fill_work')
        if permission:
            return permission.can_fill_work()
        
        # 檢查是否有通用權限
        permission = UserWorkPermission.get_user_permission(user, 'both')
        if permission:
            return permission.can_fill_work()
        
        return False
    except Exception:
        return False


def can_user_onsite_reporting(user):
    """
    檢查使用者是否可以進行現場報工
    
    Args:
        user: 使用者物件
    
    Returns:
        bool: 是否可以進行現場報工
    """
    try:
        permission = UserWorkPermission.get_user_permission(user, 'onsite_reporting')
        if permission:
            return permission.can_onsite_reporting()
        
        # 檢查是否有通用權限
        permission = UserWorkPermission.get_user_permission(user, 'both')
        if permission:
            return permission.can_onsite_reporting()
        
        return False
    except Exception:
        return False 