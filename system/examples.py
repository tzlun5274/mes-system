# -*- coding: utf-8 -*-
"""
系統管理模組的使用範例
展示如何在實際的視圖中使用權限過濾功能
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .utils import (
    # 權限檢查函數
    check_user_operator_permission,
    check_user_process_permission,
    check_user_equipment_permission,
    check_user_reporting_permission,
    
    # 資料過濾函數
    filter_operators_by_user_permission,
    filter_processes_by_user_permission,
    filter_equipments_by_user_permission,
    filter_fill_work_records_by_user_permission,
    filter_onsite_work_records_by_user_permission,
    filter_smt_work_records_by_user_permission,
    filter_workorders_by_user_permission,
    filter_work_records_by_user_permission,
    
    # 權限驗證函數
    validate_work_permission_data,
    get_user_permission_summary,
    
    # 裝飾器
    require_work_permission
)


# 範例 1: 填報記錄列表（帶權限過濾）
@login_required
def fill_work_list_example(request):
    """
    填報記錄列表範例 - 展示如何使用權限過濾
    """
    try:
        # 檢查用戶是否有填報權限
        if not check_user_reporting_permission(request.user, 'fill_work'):
            return render(request, 'error.html', {
                'message': '您沒有填報填報的權限'
            })
        
        # 假設有填報記錄模型
        from workorder.models import FillWorkRecord  # 根據實際模型調整
        queryset = FillWorkRecord.objects.all()
        
        # 根據用戶權限過濾記錄
        filtered_queryset = filter_fill_work_records_by_user_permission(
            request.user, 
            queryset
        )
        
        # 獲取用戶權限摘要（用於顯示權限狀態）
        permission_summary = get_user_permission_summary(request.user)
        
        context = {
            'records': filtered_queryset,
            'permission_summary': permission_summary,
            'total_count': filtered_queryset.count(),
            'title': '填報記錄列表'
        }
        
        return render(request, 'fill_work_list.html', context)
        
    except Exception as e:
        return render(request, 'error.html', {
            'message': f'載入填報記錄時發生錯誤：{str(e)}'
        })


# 範例 2: 現場報工記錄列表（帶權限過濾）
@login_required
def onsite_work_list_example(request):
    """
    現場報工記錄列表範例 - 展示如何使用權限過濾
    """
    try:
        # 檢查用戶是否有現場報工權限
        if not check_user_reporting_permission(request.user, 'onsite_reporting'):
            return render(request, 'error.html', {
                'message': '您沒有現場報工的權限'
            })
        
        # 假設有現場報工記錄模型
        from workorder.models import OnsiteWorkRecord  # 根據實際模型調整
        queryset = OnsiteWorkRecord.objects.all()
        
        # 根據用戶權限過濾記錄
        filtered_queryset = filter_onsite_work_records_by_user_permission(
            request.user, 
            queryset
        )
        
        context = {
            'records': filtered_queryset,
            'total_count': filtered_queryset.count(),
            'title': '現場報工記錄列表'
        }
        
        return render(request, 'onsite_work_list.html', context)
        
    except Exception as e:
        return render(request, 'error.html', {
            'message': f'載入現場報工記錄時發生錯誤：{str(e)}'
        })


# 範例 3: 使用裝飾器進行權限檢查
@login_required
@require_work_permission(reporting_type='fill_work')
def fill_work_create_example(request):
    """
    創建填報記錄範例 - 使用裝飾器進行權限檢查
    """
    if request.method == 'POST':
        # 獲取表單資料
        operator_id = request.POST.get('operator_id')
        process_id = request.POST.get('process_id')
        equipment_id = request.POST.get('equipment_id')
        
        # 驗證用戶權限
        validation_result = validate_work_permission_data(
            user=request.user,
            operator_id=operator_id,
            process_id=process_id,
            equipment_id=equipment_id
        )
        
        if not validation_result['valid']:
            return JsonResponse({
                'success': False,
                'errors': validation_result['errors']
            })
        
        # 如果有警告，記錄但不阻止操作
        if validation_result['warnings']:
            for warning in validation_result['warnings']:
                print(f"權限警告: {warning}")
        
        # 繼續處理表單提交...
        # 這裡是實際的業務邏輯
        
        return JsonResponse({'success': True})
    
    # GET 請求：顯示表單
    try:
        # 根據用戶權限過濾選項
        from process.models import Operator, ProcessName
        from equip.models import Equipment
        
        operators = filter_operators_by_user_permission(
            request.user, 
            Operator.objects.all()
        )
        processes = filter_processes_by_user_permission(
            request.user, 
            ProcessName.objects.all()
        )
        equipments = filter_equipments_by_user_permission(
            request.user, 
            Equipment.objects.all()
        )
        
        context = {
            'operators': operators,
            'processes': processes,
            'equipments': equipments,
            'title': '創建填報記錄'
        }
        
        return render(request, 'fill_work_create.html', context)
        
    except Exception as e:
        return render(request, 'error.html', {
            'message': f'載入表單時發生錯誤：{str(e)}'
        })


# 範例 4: 工單列表（帶權限過濾）
@login_required
def workorder_list_example(request):
    """
    工單列表範例 - 展示如何使用權限過濾
    """
    try:
        # 假設有工單模型
        from workorder.models import WorkOrder  # 根據實際模型調整
        queryset = WorkOrder.objects.all()
        
        # 根據用戶權限過濾工單
        filtered_queryset = filter_workorders_by_user_permission(
            request.user, 
            queryset
        )
        
        context = {
            'workorders': filtered_queryset,
            'total_count': filtered_queryset.count(),
            'title': '工單列表'
        }
        
        return render(request, 'workorder_list.html', context)
        
    except Exception as e:
        return render(request, 'error.html', {
            'message': f'載入工單時發生錯誤：{str(e)}'
        })


# 範例 5: 通用報工記錄過濾
@login_required
def work_records_list_example(request):
    """
    報工記錄列表範例 - 使用通用過濾函數
    """
    try:
        # 假設有報工記錄模型
        from workorder.models import WorkRecord  # 根據實際模型調整
        queryset = WorkRecord.objects.all()
        
        # 根據記錄類型過濾
        record_type = request.GET.get('type', 'all')
        filtered_queryset = filter_work_records_by_user_permission(
            request.user, 
            queryset, 
            record_type
        )
        
        # 獲取用戶權限摘要
        permission_summary = get_user_permission_summary(request.user)
        
        context = {
            'records': filtered_queryset,
            'record_type': record_type,
            'permission_summary': permission_summary,
            'total_count': filtered_queryset.count(),
            'title': '報工記錄列表'
        }
        
        return render(request, 'work_records_list.html', context)
        
    except Exception as e:
        return render(request, 'error.html', {
            'message': f'載入報工記錄時發生錯誤：{str(e)}'
        })


# 範例 6: API 端點權限檢查
@login_required
def api_work_permission_check_example(request):
    """
    API 端點權限檢查範例
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支援 POST 請求'})
    
    try:
        # 獲取請求資料
        data = request.POST
        operator_id = data.get('operator_id')
        process_id = data.get('process_id')
        equipment_id = data.get('equipment_id')
        action_type = data.get('action_type')  # 'fill_work', 'onsite_reporting', 'smt_reporting'
        
        # 檢查報工類型權限
        if action_type and not check_user_reporting_permission(request.user, action_type):
            return JsonResponse({
                'success': False,
                'message': f'您沒有進行{action_type}的權限'
            })
        
        # 驗證所有權限
        validation_result = validate_work_permission_data(
            user=request.user,
            operator_id=operator_id,
            process_id=process_id,
            equipment_id=equipment_id
        )
        
        if not validation_result['valid']:
            return JsonResponse({
                'success': False,
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings']
            })
        
        # 權限檢查通過，繼續處理業務邏輯
        return JsonResponse({
            'success': True,
            'message': '權限檢查通過',
            'warnings': validation_result['warnings']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'權限檢查時發生錯誤：{str(e)}'
        })


# 範例 7: 動態載入選項（根據用戶權限）
@login_required
def api_load_options_example(request):
    """
    動態載入選項範例 - 根據用戶權限過濾
    """
    try:
        option_type = request.GET.get('type')
        
        if option_type == 'operators':
            from process.models import Operator
            queryset = Operator.objects.all()
            filtered_queryset = filter_operators_by_user_permission(request.user, queryset)
            options = [{'id': op.id, 'name': op.name} for op in filtered_queryset]
            
        elif option_type == 'processes':
            from process.models import ProcessName
            queryset = ProcessName.objects.all()
            filtered_queryset = filter_processes_by_user_permission(request.user, queryset)
            options = [{'id': proc.id, 'name': proc.name} for proc in filtered_queryset]
            
        elif option_type == 'equipments':
            from equip.models import Equipment
            queryset = Equipment.objects.all()
            filtered_queryset = filter_equipments_by_user_permission(request.user, queryset)
            options = [{'id': eq.id, 'name': eq.name} for eq in filtered_queryset]
            
        else:
            return JsonResponse({
                'success': False,
                'message': '無效的選項類型'
            })
        
        return JsonResponse({
            'success': True,
            'options': options,
            'total_count': len(options)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'載入選項時發生錯誤：{str(e)}'
        })


# 範例 8: 權限狀態檢查
@login_required
def api_permission_status_example(request):
    """
    權限狀態檢查 API 範例
    """
    try:
        # 獲取用戶權限摘要
        permission_summary = get_user_permission_summary(request.user)
        
        # 檢查特定權限
        can_fill_work = check_user_reporting_permission(request.user, 'fill_work')
        can_onsite_reporting = check_user_reporting_permission(request.user, 'onsite_reporting')
        can_smt_reporting = check_user_reporting_permission(request.user, 'smt_reporting')
        
        return JsonResponse({
            'success': True,
            'permission_summary': permission_summary,
            'permissions': {
                'can_fill_work': can_fill_work,
                'can_onsite_reporting': can_onsite_reporting,
                'can_smt_reporting': can_smt_reporting,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'檢查權限狀態時發生錯誤：{str(e)}'
        })
