"""
派工單管理視圖
提供派工單的列表、新增、編輯、刪除等功能
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import WorkOrderDispatch
from .forms import WorkOrderDispatchForm
from workorder.models import WorkOrder
from workorder.workorder_erp.models import SystemConfig


@method_decorator(csrf_exempt, name='dispatch')
class DispatchListView(LoginRequiredMixin, ListView):
    """
    派工單列表視圖
    顯示所有派工單，支援搜尋、篩選和分頁
    """
    model = WorkOrderDispatch
    template_name = 'workorder_dispatch/dispatch_list.html'
    context_object_name = 'dispatches'
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        """取得查詢集，支援搜尋和篩選功能"""
        queryset = super().get_queryset()
        
        # 搜尋功能
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(work_order__order_number__icontains=search) |
                Q(operator__icontains=search) |
                Q(process__icontains=search)
            )
        
        # 狀態篩選
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # 日期範圍篩選
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=end_date_obj)
            except ValueError:
                pass
        
        return queryset

    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 統計資料
        context['total_dispatches'] = WorkOrderDispatch.objects.count()
        context['pending_dispatches'] = WorkOrderDispatch.objects.filter(status='pending').count()
        context['in_progress_dispatches'] = WorkOrderDispatch.objects.filter(status='in_progress').count()
        context['completed_dispatches'] = WorkOrderDispatch.objects.filter(status='completed').count()
        
        # 搜尋參數
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        return context


class DispatchCreateView(LoginRequiredMixin, CreateView):
    """
    派工單新增視圖
    建立新的派工單
    """
    model = WorkOrderDispatch
    form_class = WorkOrderDispatchForm
    template_name = 'workorder_dispatch/dispatch_form.html'
    success_url = reverse_lazy('workorder_dispatch:dispatch_list')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user
        form.instance.status = 'pending'
        response = super().form_valid(form)
        messages.success(self.request, '派工單建立成功！')
        return response

    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        context['title'] = '新增派工單'
        context['submit_text'] = '建立派工單'
        return context


class DispatchUpdateView(LoginRequiredMixin, UpdateView):
    """
    派工單編輯視圖
    編輯現有的派工單
    """
    model = WorkOrderDispatch
    form_class = WorkOrderDispatchForm
    template_name = 'workorder_dispatch/dispatch_form.html'
    success_url = reverse_lazy('workorder_dispatch:dispatch_list')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.updated_by = self.request.user
        form.instance.updated_at = timezone.now()
        response = super().form_valid(form)
        messages.success(self.request, '派工單更新成功！')
        return response

    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        context['title'] = '編輯派工單'
        context['submit_text'] = '更新派工單'
        return context


class DispatchDetailView(LoginRequiredMixin, DetailView):
    """
    派工單詳情視圖
    顯示派工單的詳細資訊
    """
    model = WorkOrderDispatch
    template_name = 'workorder_dispatch/dispatch_detail.html'
    context_object_name = 'dispatch'


class DispatchDeleteView(LoginRequiredMixin, DeleteView):
    """
    派工單刪除視圖
    刪除派工單
    """
    model = WorkOrderDispatch
    template_name = 'workorder_dispatch/dispatch_confirm_delete.html'
    success_url = reverse_lazy('workorder_dispatch:dispatch_list')

    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        response = super().delete(request, *args, **kwargs)
        messages.success(request, '派工單刪除成功！')
        return response


@login_required
def dispatch_dashboard(request):
    """
    派工單儀表板
    顯示派工單的統計資訊和圖表
    """
    # 統計資料
    total_dispatches = WorkOrderDispatch.objects.count()
    pending_dispatches = WorkOrderDispatch.objects.filter(status='pending').count()
    in_progress_dispatches = WorkOrderDispatch.objects.filter(status='in_progress').count()
    completed_dispatches = WorkOrderDispatch.objects.filter(status='completed').count()
    
    # 今日派工單
    today = timezone.now().date()
    today_dispatches = WorkOrderDispatch.objects.filter(created_at__date=today).count()
    
    # 本週派工單
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_dispatches = WorkOrderDispatch.objects.filter(
        created_at__date__range=[week_start, week_end]
    ).count()
    
    # 最近派工單
    recent_dispatches = WorkOrderDispatch.objects.select_related(
        'work_order'
    ).order_by('-created_at')[:10]
    
    context = {
        'total_dispatches': total_dispatches,
        'pending_dispatches': pending_dispatches,
        'in_progress_dispatches': in_progress_dispatches,
        'completed_dispatches': completed_dispatches,
        'today_dispatches': today_dispatches,
        'week_dispatches': week_dispatches,
        'recent_dispatches': recent_dispatches,
    }
    
    return render(request, 'workorder_dispatch/dispatch_dashboard.html', context)


@login_required
def get_work_order_info(request):
    """
    取得工單資訊的 AJAX 端點
    用於派工單表單中的動態載入
    """
    work_order_no = request.GET.get('work_order_no', '')
    
    if not work_order_no:
        return JsonResponse({'error': '工單號不能為空'}, status=400)
    
    try:
        work_order = WorkOrder.objects.get(order_number=work_order_no)
        data = {
            'product_code': work_order.product_code,
            'quantity': work_order.quantity,
            'status': work_order.status,
        }
        return JsonResponse(data)
    except WorkOrder.DoesNotExist:
        return JsonResponse({'error': '找不到指定的工單'}, status=404)


@login_required
def bulk_dispatch(request):
    """
    批量派工功能
    一次為多個工單建立派工單
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            work_order_nos = data.get('work_order_nos', [])
            operator_id = data.get('operator_id')
            process = data.get('process')
            
            if not work_order_nos or not operator_id or not process:
                return JsonResponse({'error': '缺少必要參數'}, status=400)
            
            created_count = 0
            for work_order_no in work_order_nos:
                try:
                    work_order = WorkOrder.objects.get(order_number=work_order_no)
                    WorkOrderDispatch.objects.create(
                        work_order=work_order,
                        operator=operator_id,
                        process=process,
                        status='pending',
                        created_by=request.user
                    )
                    created_count += 1
                except WorkOrder.DoesNotExist:
                    continue
            
            return JsonResponse({
                'success': True,
                'message': f'成功建立 {created_count} 個派工單',
                'created_count': created_count
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': '無效的 JSON 格式'}, status=400)
    
    return JsonResponse({'error': '只支援 POST 請求'}, status=405) 