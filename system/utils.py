# -*- coding: utf-8 -*-
"""
系統管理模組的工具函數
提供權限檢查、資料過濾等通用功能
"""

from django.contrib.auth.models import User
from django.db.models import Q
from .models import UserWorkPermission


def get_user_work_permissions(user):
    """
    獲取用戶的工作權限設定
    
    Args:
        user: Django User 實例
        
    Returns:
        UserWorkPermission 實例或 None
    """
    try:
        return UserWorkPermission.objects.get(user=user)
    except UserWorkPermission.DoesNotExist:
        return None


def check_user_operator_permission(user, operator_id):
    """
    檢查用戶是否有操作指定作業員的權限
    
    Args:
        user: Django User 實例
        operator_id: 作業員ID
        
    Returns:
        bool: 是否有權限
    """
    if user.is_superuser:
        return True
        
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return True  # 如果沒有設定，預設允許
        
    return work_permission.check_operator_permission(operator_id)


def check_user_process_permission(user, process_id):
    """
    檢查用戶是否有操作指定工序的權限
    
    Args:
        user: Django User 實例
        process_id: 工序ID
        
    Returns:
        bool: 是否有權限
    """
    if user.is_superuser:
        return True
        
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return True  # 如果沒有設定，預設允許
        
    return work_permission.check_process_permission(process_id)


def check_user_equipment_permission(user, equipment_id):
    """
    檢查用戶是否有操作指定設備的權限
    
    Args:
        user: Django User 實例
        equipment_id: 設備ID
        
    Returns:
        bool: 是否有權限
    """
    if user.is_superuser:
        return True
        
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return True  # 如果沒有設定，預設允許
        
    return work_permission.check_equipment_permission(equipment_id)


def filter_operators_by_user_permission(user, queryset):
    """
    根據用戶權限過濾作業員查詢集
    
    Args:
        user: Django User 實例
        queryset: 作業員查詢集
        
    Returns:
        QuerySet: 過濾後的查詢集
    """
    if user.is_superuser:
        return queryset
        
    work_permission = get_user_work_permissions(user)
    if not work_permission or work_permission.can_operate_all_operators:
        return queryset
        
    return queryset.filter(id__in=work_permission.allowed_operators)


def filter_processes_by_user_permission(user, queryset):
    """
    根據用戶權限過濾工序查詢集
    
    Args:
        user: Django User 實例
        queryset: 工序查詢集
        
    Returns:
        QuerySet: 過濾後的查詢集
    """
    if user.is_superuser:
        return queryset
        
    work_permission = get_user_work_permissions(user)
    if not work_permission or work_permission.can_operate_all_processes:
        return queryset
        
    return queryset.filter(id__in=work_permission.allowed_processes)


def filter_equipments_by_user_permission(user, queryset):
    """
    根據用戶權限過濾設備查詢集
    
    Args:
        user: Django User 實例
        queryset: 設備查詢集
        
    Returns:
        QuerySet: 過濾後的查詢集
    """
    if user.is_superuser:
        return queryset
        
    work_permission = get_user_work_permissions(user)
    if not work_permission or work_permission.can_operate_all_equipments:
        return queryset
        
    return queryset.filter(id__in=work_permission.allowed_equipments)


def check_user_reporting_permission(user, reporting_type):
    """
    檢查用戶是否有進行指定類型報工的權限
    
    Args:
        user: Django User 實例
        reporting_type: 報工類型 ('fill_work', 'onsite_reporting', 'smt_reporting')
        
    Returns:
        bool: 是否有權限
    """
    if user.is_superuser:
        return True
        
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return True  # 如果沒有設定，預設允許
        
    if reporting_type == 'fill_work':
        return work_permission.can_fill_work
    elif reporting_type == 'onsite_reporting':
        return work_permission.can_onsite_reporting
    elif reporting_type == 'smt_reporting':
        return work_permission.can_smt_reporting
    
    return False


def get_user_permission_summary(user):
    """
    獲取用戶權限摘要
    
    Args:
        user: Django User 實例
        
    Returns:
        dict: 權限摘要字典
    """
    if user.is_superuser:
        return {
            'summary': '超級用戶 - 擁有所有權限',
            'can_fill_work': True,
            'can_onsite_reporting': True,
            'can_smt_reporting': True,
            'operators_restricted': False,
            'processes_restricted': False,
            'equipments_restricted': False,
        }
    
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return {
            'summary': '未設定權限 - 使用預設權限',
            'can_fill_work': True,
            'can_onsite_reporting': True,
            'can_smt_reporting': True,
            'operators_restricted': False,
            'processes_restricted': False,
            'equipments_restricted': False,
        }
    
    return {
        'summary': work_permission.get_permission_summary(),
        'can_fill_work': work_permission.can_fill_work,
        'can_onsite_reporting': work_permission.can_onsite_reporting,
        'can_smt_reporting': work_permission.can_smt_reporting,
        'operators_restricted': not work_permission.can_operate_all_operators,
        'processes_restricted': not work_permission.can_operate_all_processes,
        'equipments_restricted': not work_permission.can_operate_all_equipments,
    }


def validate_work_permission_data(user, operator_id=None, process_id=None, equipment_id=None):
    """
    驗證用戶的報工權限資料
    
    Args:
        user: Django User 實例
        operator_id: 作業員ID（可選）
        process_id: 工序ID（可選）
        equipment_id: 設備ID（可選）
        
    Returns:
        dict: 驗證結果
        {
            'valid': bool,
            'errors': list,
            'warnings': list
        }
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # 檢查報工功能權限
    work_permission = get_user_work_permissions(user)
    if work_permission:
        if not any([
            work_permission.can_fill_work,
            work_permission.can_onsite_reporting,
            work_permission.can_smt_reporting
        ]):
            result['errors'].append('用戶沒有報工功能權限')
            result['valid'] = False
    
    # 檢查作業員權限
    if operator_id and not check_user_operator_permission(user, operator_id):
        result['errors'].append('用戶沒有操作指定作業員的權限')
        result['valid'] = False
    
    # 檢查工序權限
    if process_id and not check_user_process_permission(user, process_id):
        result['errors'].append('用戶沒有操作指定工序的權限')
        result['valid'] = False
    
    # 檢查設備權限
    if equipment_id and not check_user_equipment_permission(user, equipment_id):
        result['errors'].append('用戶沒有操作指定設備的權限')
        result['valid'] = False
    
    # 檢查是否有任何限制
    if work_permission:
        if not work_permission.can_operate_all_operators:
            result['warnings'].append('用戶的作業員操作權限受到限制')
        if not work_permission.can_operate_all_processes:
            result['warnings'].append('用戶的工序操作權限受到限制')
        if not work_permission.can_operate_all_equipments:
            result['warnings'].append('用戶的設備操作權限受到限制')
    
    return result


# 填報記錄過濾功能
def filter_fill_work_records_by_user_permission(user, queryset):
    """
    根據用戶權限過濾填報記錄查詢集
    
    Args:
        user: Django User 實例
        queryset: 填報記錄查詢集
        
    Returns:
        QuerySet: 過濾後的查詢集
    """
    if user.is_superuser:
        return queryset
    
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return queryset  # 如果沒有設定，預設允許所有
    
    # 檢查是否有填報權限
    if not work_permission.can_fill_work:
        return queryset.none()  # 沒有權限，返回空查詢集
    
    # 根據資料範圍過濾
    if work_permission.data_scope == 'own':
        # 只顯示自己的記錄
        queryset = queryset.filter(created_by=user)
    elif work_permission.data_scope == 'department':
        # 只顯示部門內的記錄（需要用戶有部門屬性）
        try:
            if hasattr(user, 'department'):
                queryset = queryset.filter(created_by__department=user.department)
        except:
            pass
    
    # 根據作業員權限過濾
    if not work_permission.can_operate_all_operators and work_permission.allowed_operators:
        queryset = queryset.filter(operator_id__in=work_permission.allowed_operators)
    
    # 根據工序權限過濾
    if not work_permission.can_operate_all_processes and work_permission.allowed_processes:
        queryset = queryset.filter(process_id__in=work_permission.allowed_processes)
    
    # 根據設備權限過濾
    if not work_permission.can_operate_all_equipments and work_permission.allowed_equipments:
        queryset = queryset.filter(equipment_id__in=work_permission.allowed_equipments)
    
    return queryset


# 現場報工記錄過濾功能
def filter_onsite_work_records_by_user_permission(user, queryset):
    """
    根據用戶權限過濾現場報工記錄查詢集
    
    Args:
        user: Django User 實例
        queryset: 現場報工記錄查詢集
        
    Returns:
        QuerySet: 過濾後的查詢集
    """
    if user.is_superuser:
        return queryset
    
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return queryset  # 如果沒有設定，預設允許所有
    
    # 檢查是否有現場報工權限
    if not work_permission.can_onsite_reporting:
        return queryset.none()  # 沒有權限，返回空查詢集
    
    # 根據資料範圍過濾
    if work_permission.data_scope == 'own':
        # 只顯示自己的記錄
        queryset = queryset.filter(created_by=user)
    elif work_permission.data_scope == 'department':
        # 只顯示部門內的記錄
        try:
            if hasattr(user, 'department'):
                queryset = queryset.filter(created_by__department=user.department)
        except:
            pass
    
    # 根據作業員權限過濾
    if not work_permission.can_operate_all_operators and work_permission.allowed_operators:
        queryset = queryset.filter(operator_id__in=work_permission.allowed_operators)
    
    # 根據工序權限過濾
    if not work_permission.can_operate_all_processes and work_permission.allowed_processes:
        queryset = queryset.filter(process_id__in=work_permission.allowed_processes)
    
    # 根據設備權限過濾
    if not work_permission.can_operate_all_equipments and work_permission.allowed_equipments:
        queryset = queryset.filter(equipment_id__in=work_permission.allowed_equipments)
    
    return queryset


# SMT報工記錄過濾功能
def filter_smt_work_records_by_user_permission(user, queryset):
    """
    根據用戶權限過濾SMT報工記錄查詢集
    
    Args:
        user: Django User 實例
        queryset: SMT報工記錄查詢集
        
    Returns:
        QuerySet: 過濾後的查詢集
    """
    if user.is_superuser:
        return queryset
    
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return queryset  # 如果沒有設定，預設允許所有
    
    # 檢查是否有SMT報工權限
    if not work_permission.can_smt_reporting:
        return queryset.none()  # 沒有權限，返回空查詢集
    
    # 根據資料範圍過濾
    if work_permission.data_scope == 'own':
        # 只顯示自己的記錄
        queryset = queryset.filter(created_by=user)
    elif work_permission.data_scope == 'department':
        # 只顯示部門內的記錄
        try:
            if hasattr(user, 'department'):
                queryset = queryset.filter(created_by__department=user.department)
        except:
            pass
    
    # 根據作業員權限過濾
    if not work_permission.can_operate_all_operators and work_permission.allowed_operators:
        queryset = queryset.filter(operator_id__in=work_permission.allowed_operators)
    
    # 根據工序權限過濾
    if not work_permission.can_operate_all_processes and work_permission.allowed_processes:
        queryset = queryset.filter(process_id__in=work_permission.allowed_processes)
    
    # 根據設備權限過濾
    if not work_permission.can_operate_all_equipments and work_permission.allowed_equipments:
        queryset = queryset.filter(equipment_id__in=work_permission.allowed_equipments)
    
    return queryset


# 工單過濾功能
def filter_workorders_by_user_permission(user, queryset):
    """
    根據用戶權限過濾工單查詢集
    
    Args:
        user: Django User 實例
        queryset: 工單查詢集
        
    Returns:
        QuerySet: 過濾後的查詢集
    """
    if user.is_superuser:
        return queryset
    
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return queryset  # 如果沒有設定，預設允許所有
    
    # 根據資料範圍過濾
    if work_permission.data_scope == 'own':
        # 只顯示自己創建的工單
        queryset = queryset.filter(created_by=user)
    elif work_permission.data_scope == 'department':
        # 只顯示部門內的工單
        try:
            if hasattr(user, 'department'):
                queryset = queryset.filter(created_by__department=user.department)
        except:
            pass
    
    # 根據工序權限過濾（如果工單有關聯的工序）
    if not work_permission.can_operate_all_processes and work_permission.allowed_processes:
        try:
            # 假設工單有關聯的工序，根據實際模型調整
            queryset = queryset.filter(process_id__in=work_permission.allowed_processes)
        except:
            pass
    
    # 根據設備權限過濾（如果工單有關聯的設備）
    if not work_permission.can_operate_all_equipments and work_permission.allowed_equipments:
        try:
            # 假設工單有關聯的設備，根據實際模型調整
            queryset = queryset.filter(equipment_id__in=work_permission.allowed_equipments)
        except:
            pass
    
    return queryset


# 通用報工記錄過濾功能
def filter_work_records_by_user_permission(user, queryset, record_type='all'):
    """
    根據用戶權限過濾報工記錄查詢集（通用版本）
    
    Args:
        user: Django User 實例
        queryset: 報工記錄查詢集
        record_type: 記錄類型 ('fill_work', 'onsite_reporting', 'smt_reporting', 'all')
        
    Returns:
        QuerySet: 過濾後的查詢集
    """
    if user.is_superuser:
        return queryset
    
    work_permission = get_user_work_permissions(user)
    if not work_permission:
        return queryset  # 如果沒有設定，預設允許所有
    
    # 根據記錄類型檢查權限
    if record_type == 'fill_work' and not work_permission.can_fill_work:
        return queryset.none()
    elif record_type == 'onsite_reporting' and not work_permission.can_onsite_reporting:
        return queryset.none()
    elif record_type == 'smt_reporting' and not work_permission.can_smt_reporting:
        return queryset.none()
    elif record_type == 'all':
        # 檢查是否有任何報工權限
        if not any([
            work_permission.can_fill_work,
            work_permission.can_onsite_reporting,
            work_permission.can_smt_reporting
        ]):
            return queryset.none()
    
    # 根據資料範圍過濾
    if work_permission.data_scope == 'own':
        queryset = queryset.filter(created_by=user)
    elif work_permission.data_scope == 'department':
        try:
            if hasattr(user, 'department'):
                queryset = queryset.filter(created_by__department=user.department)
        except:
            pass
    
    # 根據作業員權限過濾
    if not work_permission.can_operate_all_operators and work_permission.allowed_operators:
        queryset = queryset.filter(operator_id__in=work_permission.allowed_operators)
    
    # 根據工序權限過濾
    if not work_permission.can_operate_all_processes and work_permission.allowed_processes:
        queryset = queryset.filter(process_id__in=work_permission.allowed_processes)
    
    # 根據設備權限過濾
    if not work_permission.can_operate_all_equipments and work_permission.allowed_equipments:
        queryset = queryset.filter(equipment_id__in=work_permission.allowed_equipments)
    
    return queryset


# 裝飾器函數，用於視圖權限檢查
def require_work_permission(reporting_type=None, operator_check=True, process_check=True, equipment_check=True):
    """
    裝飾器：檢查用戶的工作權限
    
    Args:
        reporting_type: 報工類型檢查
        operator_check: 是否檢查作業員權限
        process_check: 是否檢查工序權限
        equipment_check: 是否檢查設備權限
        
    Returns:
        decorator: 裝飾器函數
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            # 檢查報工類型權限
            if reporting_type and not check_user_reporting_permission(user, reporting_type):
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("您沒有進行此類型報工的權限")
            
            # 檢查資料權限（如果請求中包含相關ID）
            if operator_check and 'operator_id' in kwargs:
                if not check_user_operator_permission(user, kwargs['operator_id']):
                    from django.http import HttpResponseForbidden
                    return HttpResponseForbidden("您沒有操作指定作業員的權限")
            
            if process_check and 'process_id' in kwargs:
                if not check_user_process_permission(user, kwargs['process_id']):
                    from django.http import HttpResponseForbidden
                    return HttpResponseForbidden("您沒有操作指定工序的權限")
            
            if equipment_check and 'equipment_id' in kwargs:
                if not check_user_equipment_permission(user, kwargs['equipment_id']):
                    from django.http import HttpResponseForbidden
                    return HttpResponseForbidden("您沒有操作指定設備的權限")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator 