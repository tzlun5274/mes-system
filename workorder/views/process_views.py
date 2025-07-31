"""
工序管理視圖
包含工序的建立、編輯、刪除、移動等功能
使用 Django 類別視圖，符合設計規範
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone

from ..models import WorkOrder, WorkOrderProcess, WorkOrderProcessLog
from ..forms import WorkOrderProcessForm
from process.models import ProcessName, ProductProcessRoute
from equip.models import Equipment
from process.models import Operator


class WorkOrderProcessListView(LoginRequiredMixin, ListView):
    """
    工單工序列表視圖
    顯示指定工單的所有工序
    """
    model = WorkOrderProcess
    template_name = 'workorder/process/process_list.html'
    context_object_name = 'processes'
    paginate_by = 20

    def get_queryset(self):
        """取得查詢集，根據工單ID篩選"""
        workorder_id = self.kwargs.get('workorder_id')
        self.workorder = get_object_or_404(WorkOrder, pk=workorder_id)
        return WorkOrderProcess.objects.filter(workorder=self.workorder).order_by('step_order')

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context['workorder'] = self.workorder
        context['total_planned'] = sum(p.planned_quantity for p in context['processes'])
        context['total_completed'] = sum(p.completed_quantity for p in context['processes'])
        return context


class WorkOrderProcessDetailView(LoginRequiredMixin, DetailView):
    """
    工單工序詳情視圖
    顯示單一工序的詳細資訊
    """
    model = WorkOrderProcess
    template_name = 'workorder/process/process_detail.html'
    context_object_name = 'process'

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context['logs'] = self.object.logs.all().order_by('-created_at')[:10]
        context['completion_rate'] = self.object.completion_rate
        return context


class WorkOrderProcessCreateView(LoginRequiredMixin, CreateView):
    """
    工單工序新增視圖
    用於建立新的工序
    """
    model = WorkOrderProcess
    form_class = WorkOrderProcessForm
    template_name = 'workorder/process/process_form.html'

    def get_success_url(self):
        """取得成功後的URL"""
        return reverse('workorder:process_list', kwargs={'workorder_id': self.object.workorder.id})

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        workorder_id = self.kwargs.get('workorder_id')
        workorder = get_object_or_404(WorkOrder, pk=workorder_id)
        form.instance.workorder = workorder
        
        # 自動設定工序順序
        if not form.instance.step_order:
            last_process = WorkOrderProcess.objects.filter(workorder=workorder).order_by('-step_order').first()
            form.instance.step_order = (last_process.step_order + 1) if last_process else 1
        
        messages.success(self.request, '工序建立成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '工序建立失敗，請檢查輸入資料！')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context['workorder'] = get_object_or_404(WorkOrder, pk=self.kwargs.get('workorder_id'))
        return context


class WorkOrderProcessUpdateView(LoginRequiredMixin, UpdateView):
    """
    工單工序編輯視圖
    用於編輯現有工序
    """
    model = WorkOrderProcess
    form_class = WorkOrderProcessForm
    template_name = 'workorder/process/process_form.html'

    def get_success_url(self):
        """取得成功後的URL"""
        return reverse('workorder:process_list', kwargs={'workorder_id': self.object.workorder.id})

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, '工序更新成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '工序更新失敗，請檢查輸入資料！')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context['workorder'] = self.object.workorder
        return context


class WorkOrderProcessDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    工單工序刪除視圖
    用於刪除工序，僅限管理員使用
    """
    model = WorkOrderProcess
    template_name = 'workorder/process/process_confirm_delete.html'

    def test_func(self):
        """檢查用戶是否有刪除權限"""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_success_url(self):
        """取得成功後的URL"""
        return reverse('workorder:process_list', kwargs={'workorder_id': self.object.workorder.id})

    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        messages.success(request, '工序刪除成功！')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context['workorder'] = self.object.workorder
        return context


@method_decorator(ensure_csrf_cookie, name='dispatch')
class ProcessCapacityView(LoginRequiredMixin, DetailView):
    """
    工序產能設定視圖
    用於設定和查看工序的產能參數
    """
    model = WorkOrderProcess
    template_name = 'workorder/process/process_capacity.html'
    context_object_name = 'process'

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context['workorder'] = self.object.workorder
        context['operators'] = Operator.objects.filter(is_active=True)
        context['equipments'] = Equipment.objects.filter(is_active=True)
        return context


@method_decorator(ensure_csrf_cookie, name='dispatch')
class ProcessStatisticsView(LoginRequiredMixin, ListView):
    """
    工序統計視圖
    顯示工序的統計資訊
    """
    model = WorkOrderProcess
    template_name = 'workorder/process/process_statistics.html'
    context_object_name = 'processes'

    def get_queryset(self):
        """取得查詢集"""
        workorder_id = self.kwargs.get('workorder_id')
        self.workorder = get_object_or_404(WorkOrder, pk=workorder_id)
        return WorkOrderProcess.objects.filter(workorder=self.workorder).order_by('step_order')

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context['workorder'] = self.workorder
        
        # 計算統計資料
        processes = context['processes']
        context['total_processes'] = processes.count()
        context['completed_processes'] = processes.filter(status='completed').count()
        context['in_progress_processes'] = processes.filter(status='in_progress').count()
        context['pending_processes'] = processes.filter(status='pending').count()
        
        # 計算總進度
        total_planned = sum(p.planned_quantity for p in processes)
        total_completed = sum(p.completed_quantity for p in processes)
        context['total_progress'] = (total_completed / total_planned * 100) if total_planned > 0 else 0
        
        return context


# API 視圖函數
@require_POST
def move_process(request, process_id):
    """
    移動工序順序的 API 端點
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': '未登入'}, status=401)
    
    try:
        process = get_object_or_404(WorkOrderProcess, pk=process_id)
        direction = request.POST.get('direction')
        
        if direction == 'up':
            # 向上移動
            prev_process = WorkOrderProcess.objects.filter(
                workorder=process.workorder,
                step_order__lt=process.step_order
            ).order_by('-step_order').first()
            
            if prev_process:
                with transaction.atomic():
                    prev_process.step_order, process.step_order = process.step_order, prev_process.step_order
                    prev_process.save()
                    process.save()
                return JsonResponse({'success': True, 'message': '工序順序已更新'})
            else:
                return JsonResponse({'error': '已是第一個工序'}, status=400)
                
        elif direction == 'down':
            # 向下移動
            next_process = WorkOrderProcess.objects.filter(
                workorder=process.workorder,
                step_order__gt=process.step_order
            ).order_by('step_order').first()
            
            if next_process:
                with transaction.atomic():
                    next_process.step_order, process.step_order = process.step_order, next_process.step_order
                    next_process.save()
                    process.save()
                return JsonResponse({'success': True, 'message': '工序順序已更新'})
            else:
                return JsonResponse({'error': '已是最後一個工序'}, status=400)
        else:
            return JsonResponse({'error': '無效的移動方向'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': f'操作失敗：{str(e)}'}, status=500)


@require_POST
def update_process_capacity(request, process_id):
    """
    更新工序產能的 API 端點
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': '未登入'}, status=401)
    
    try:
        process = get_object_or_404(WorkOrderProcess, pk=process_id)
        
        # 取得表單資料
        capacity_multiplier = request.POST.get('capacity_multiplier', 1)
        target_hourly_output = request.POST.get('target_hourly_output', 0)
        additional_operators = request.POST.get('additional_operators', '[]')
        additional_equipments = request.POST.get('additional_equipments', '[]')
        
        # 更新工序產能設定
        process.capacity_multiplier = int(capacity_multiplier)
        process.target_hourly_output = int(target_hourly_output)
        process.additional_operators = additional_operators
        process.additional_equipments = additional_equipments
        
        # 重新計算預計工時
        process.calculate_estimated_hours()
        process.save()
        
        return JsonResponse({
            'success': True, 
            'message': '產能設定已更新',
            'estimated_hours': float(process.estimated_hours)
        })
        
    except Exception as e:
        return JsonResponse({'error': f'更新失敗：{str(e)}'}, status=500)


@require_POST
def update_process_status(request, process_id):
    """
    更新工序狀態的 API 端點
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': '未登入'}, status=401)
    
    try:
        process = get_object_or_404(WorkOrderProcess, pk=process_id)
        new_status = request.POST.get('status')
        
        if new_status not in ['pending', 'in_progress', 'completed', 'paused', 'cancelled']:
            return JsonResponse({'error': '無效的狀態'}, status=400)
        
        old_status = process.status
        process.status = new_status
        
        # 記錄狀態變更
        WorkOrderProcessLog.objects.create(
            workorder_process=process,
            action='status_change',
            operator=request.user.username,
            notes=f'狀態從 {old_status} 變更為 {new_status}'
        )
        
        process.save()
        
        return JsonResponse({
            'success': True, 
            'message': '工序狀態已更新',
            'new_status': new_status
        })
        
    except Exception as e:
        return JsonResponse({'error': f'更新失敗：{str(e)}'}, status=500) 