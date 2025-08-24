#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
已完工工單工序紀錄數量分配視圖
提供網頁介面來管理已完工工單的數量分配功能
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from workorder.services.auto_allocation_service import AutoAllocationService
from workorder.models import CompletedWorkOrder
from erp_integration.models import CompanyConfig

logger = logging.getLogger(__name__)

@login_required
def completed_workorder_allocation_dashboard(request):
    """
    已完工工單數量分配儀表板
    """
    try:
        service = AutoAllocationService()
        
        # 獲取公司列表
        companies = CompanyConfig.objects.all().order_by('company_name')
        
        # 獲取選定的公司
        selected_company = request.GET.get('company')
        
        # 獲取待分配摘要
        summary = service.get_pending_allocation_summary(selected_company)
        
        # 統計資訊
        if 'error' in summary:
            total_pending = 0
            total_zero_reports = 0
            pending_workorders = []
        else:
            total_pending = summary.get('total_workorders', 0)
            total_zero_reports = summary.get('total_pending_reports', 0)
            pending_workorders = summary.get('workorders', {})
        
        context = {
            'companies': companies,
            'selected_company': selected_company,
            'pending_workorders': pending_workorders,
            'total_pending': total_pending,
            'total_zero_reports': total_zero_reports,
        }
        
        return render(request, 'workorder/completed_workorder_allocation_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"載入已完工工單數量分配儀表板時發生錯誤: {str(e)}")
        messages.error(request, f'載入儀表板失敗: {str(e)}')
        return redirect('workorder:workorder_list')

@login_required
def completed_workorder_allocation_detail(request, workorder_number):
    """
    已完工工單數量分配詳情頁面
    """
    try:
        service = AutoAllocationService()
        
        # 獲取分配摘要
        summary = service.get_allocation_summary(workorder_number)
        
        if 'error' in summary:
            messages.error(request, summary['error'])
            return redirect('workorder:completed_workorder_allocation_dashboard')
        
        # 獲取工單詳細資訊
        completed_workorder = CompletedWorkOrder.objects.filter(
            order_number=workorder_number
        ).first()
        
        context = {
            'summary': summary,
            'completed_workorder': completed_workorder,
        }
        
        return render(request, 'workorder/completed_workorder_allocation_detail.html', context)
        
    except Exception as e:
        logger.error(f"載入工單 {workorder_number} 分配詳情時發生錯誤: {str(e)}")
        messages.error(request, f'載入詳情失敗: {str(e)}')
        return redirect('workorder:completed_workorder_allocation_dashboard')

@login_required
@require_http_methods(["POST"])
def allocate_single_workorder(request, workorder_number):
    """
    為單一工單執行數量分配
    """
    try:
        service = AutoAllocationService()
        
        # 獲取公司代號
        company_code = request.POST.get('company_code')
        
        # 執行分配
        result = service.allocate_completed_workorder_quantities(
            workorder_number, company_code
        )
        
        if result['success']:
            messages.success(
                request, 
                f'分配成功！工單 {workorder_number} 共分配 {result["total_allocated_quantity"]} 件給 {result["total_allocated_reports"]} 筆紀錄'
            )
        else:
            messages.error(request, f'分配失敗: {result["message"]}')
        
        return redirect('workorder:completed_workorder_allocation_detail', workorder_number=workorder_number)
        
    except Exception as e:
        logger.error(f"為工單 {workorder_number} 執行分配時發生錯誤: {str(e)}")
        messages.error(request, f'執行分配失敗: {str(e)}')
        return redirect('workorder:completed_workorder_allocation_detail', workorder_number=workorder_number)

@login_required
@require_http_methods(["POST"])
def allocate_all_workorders(request):
    """
    為所有待分配工單執行批量分配
    """
    try:
        service = AutoAllocationService()
        
        # 獲取公司代號
        company_code = request.POST.get('company_code')
        
        # 執行批量分配
        result = service.allocate_all_pending_workorders(company_code)
        
        if result.get('success', False):
            messages.success(
                request,
                f'批量分配完成！處理 {result.get("total_allocated_workorders", 0)} 個工單，'
                f'分配 {result.get("total_allocated_quantity", 0)} 件給 {result.get("total_allocated_reports", 0)} 筆紀錄'
            )
        else:
            messages.error(request, f'批量分配失敗: {result.get("message", "未知錯誤")}')
        
        return redirect('workorder:completed_workorder_allocation_dashboard')
        
    except Exception as e:
        logger.error(f"執行批量分配時發生錯誤: {str(e)}")
        messages.error(request, f'執行批量分配失敗: {str(e)}')
        return redirect('workorder:completed_workorder_allocation_dashboard')

@login_required
@csrf_exempt
def get_allocation_summary_api(request, workorder_number):
    """
    獲取分配摘要的API端點
    """
    try:
        service = AutoAllocationService()
        summary = service.get_allocation_summary(workorder_number)
        
        return JsonResponse(summary)
        
    except Exception as e:
        logger.error(f"獲取工單 {workorder_number} 分配摘要API時發生錯誤: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def get_pending_workorders_api(request):
    """
    獲取待分配工單列表的API端點
    """
    try:
        service = AutoAllocationService()
        
        # 獲取公司代號
        company_code = request.GET.get('company')
        
        summary = service.get_pending_allocation_summary(company_code)
        
        return JsonResponse({
            'success': True,
            'pending_workorders': summary.get('workorders', {}),
            'total_count': summary.get('total_workorders', 0)
        })
        
    except Exception as e:
        logger.error(f"獲取待分配工單列表API時發生錯誤: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500) 