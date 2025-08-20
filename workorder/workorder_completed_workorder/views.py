"""
已完工工單管理子模組 - 視圖
負責處理已完工工單的顯示、查詢和管理功能
"""

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.db import transaction

from .models import (
    CompletedWorkOrder, CompletedWorkOrderProcess, 
    CompletedProductionReport, AutoAllocationSettings, AutoAllocationLog
)
from .forms import (
    CompletedWorkOrderForm, CompletedWorkOrderProcessForm,
    CompletedProductionReportForm, AutoAllocationSettingsForm
)

import logging

logger = logging.getLogger(__name__)


class CompletedWorkOrderListView(LoginRequiredMixin, ListView):
    """已完工工單列表視圖"""
    
    model = CompletedWorkOrder
    template_name = 'workorder_completed_workorder/completed_workorder_list.html'
    context_object_name = 'completed_workorders'
    paginate_by = 20
    
    def get_queryset(self):
        """取得查詢集，支援搜尋和篩選"""
        queryset = CompletedWorkOrder.objects.all()
        
        # 搜尋功能
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(company_code__icontains=search_query) |
                Q(order_number__icontains=search_query) |
                Q(product_code__icontains=search_query) |
                Q(product_name__icontains=search_query)
            )
        
        # 公司代號篩選
        company_code = self.request.GET.get('company_code', '')
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        # 狀態篩選
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # 日期範圍篩選
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        
        if start_date:
            queryset = queryset.filter(completion_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(completion_date__lte=end_date)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """增加額外的上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 統計資料
        context['total_completed'] = CompletedWorkOrder.objects.filter(status='completed').count()
        context['total_archived'] = CompletedWorkOrder.objects.filter(status='archived').count()
        
        # 公司代號列表（用於篩選）
        context['company_codes'] = CompletedWorkOrder.objects.values_list(
            'company_code', flat=True
        ).distinct().order_by('company_code')
        
        # 搜尋參數
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_company'] = self.request.GET.get('company_code', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        return context


class CompletedWorkOrderDetailView(LoginRequiredMixin, DetailView):
    """已完工工單詳情視圖"""
    
    model = CompletedWorkOrder
    template_name = 'workorder_completed_workorder/completed_workorder_detail.html'
    context_object_name = 'completed_workorder'
    
    def get_context_data(self, **kwargs):
        """增加額外的上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 取得相關的工序資料
        context['processes'] = self.object.processes.all()
        
        # 取得相關的生產報表
        context['production_reports'] = self.object.production_reports.all()
        
        # 計算統計資料
        context['total_processes'] = context['processes'].count()
        context['total_duration'] = sum(process.duration for process in context['processes'])
        context['avg_completion_rate'] = (
            sum(process.completion_rate for process in context['processes']) / 
            context['total_processes'] if context['total_processes'] > 0 else 0
        )
        
        return context


class CompletedWorkOrderCreateView(LoginRequiredMixin, CreateView):
    """已完工工單建立視圖"""
    
    model = CompletedWorkOrder
    form_class = CompletedWorkOrderForm
    template_name = 'workorder_completed_workorder/completed_workorder_form.html'
    success_url = reverse_lazy('workorder:completed_workorder_list')
    
    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, '已完工工單建立成功！')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '表單資料有誤，請檢查後重新提交。')
        return super().form_invalid(form)


class CompletedWorkOrderUpdateView(LoginRequiredMixin, UpdateView):
    """已完工工單更新視圖"""
    
    model = CompletedWorkOrder
    form_class = CompletedWorkOrderForm
    template_name = 'workorder_completed_workorder/completed_workorder_form.html'
    success_url = reverse_lazy('workorder:completed_workorder_list')
    
    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, '已完工工單更新成功！')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '表單資料有誤，請檢查後重新提交。')
        return super().form_invalid(form)


class CompletedWorkOrderDeleteView(LoginRequiredMixin, DeleteView):
    """已完工工單刪除視圖"""
    
    model = CompletedWorkOrder
    template_name = 'workorder_completed_workorder/completed_workorder_confirm_delete.html'
    success_url = reverse_lazy('workorder:completed_workorder_list')
    
    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        messages.success(request, '已完工工單刪除成功！')
        return super().delete(request, *args, **kwargs)


def transfer_workorder_to_completed(request, workorder_id):
    """將工單轉換為已完工狀態"""
    try:
        from workorder.models import WorkOrder
        
        with transaction.atomic():
            # 取得原始工單
            workorder = get_object_or_404(WorkOrder, id=workorder_id)
            
            # 檢查是否已經存在已完工工單
            existing_completed = CompletedWorkOrder.objects.filter(
                company_code=workorder.company_code,
                order_number=workorder.order_number,
                product_code=workorder.product_code
            ).first()
            
            if existing_completed:
                messages.warning(request, '此工單已經存在於已完工工單中！')
                return redirect('workorder:completed_workorder_detail', pk=existing_completed.id)
            
            # 建立已完工工單
            completed_workorder = CompletedWorkOrder.objects.create(
                company_code=workorder.company_code,
                order_number=workorder.order_number,
                product_code=workorder.product_code,
                product_name=workorder.product_name,
                order_quantity=workorder.order_quantity,
                completed_quantity=workorder.completed_quantity or 0,
                defective_quantity=workorder.defective_quantity or 0,
                start_date=workorder.start_date,
                completion_date=timezone.now().date(),
                status='completed',
                remarks=f'從工單 {workorder.id} 轉換而來'
            )
            
            # 轉換工序資料
            for process in workorder.processes.all():
                CompletedWorkOrderProcess.objects.create(
                    completed_workorder=completed_workorder,
                    process_name=process.process_name,
                    process_sequence=process.process_sequence,
                    planned_quantity=process.planned_quantity,
                    completed_quantity=process.completed_quantity or 0,
                    defective_quantity=process.defective_quantity or 0,
                    start_time=process.start_time or timezone.now(),
                    end_time=process.end_time or timezone.now(),
                    operator_name=process.operator_name,
                    equipment_name=process.equipment_name,
                    remarks=process.remarks
                )
            
            messages.success(request, f'工單 {workorder.order_number} 已成功轉換為已完工工單！')
            return redirect('workorder:completed_workorder_detail', pk=completed_workorder.id)
            
    except Exception as e:
        logger.error(f'轉換工單失敗: {str(e)}')
        messages.error(request, f'轉換工單失敗: {str(e)}')
        return redirect('workorder:list')


def batch_transfer_completed_workorders(request):
    """批次轉換工單為已完工狀態"""
    if request.method == 'POST':
        workorder_ids = request.POST.getlist('workorder_ids')
        
        if not workorder_ids:
            messages.warning(request, '請選擇要轉換的工單！')
            return redirect('workorder:list')
        
        success_count = 0
        error_count = 0
        
        for workorder_id in workorder_ids:
            try:
                transfer_workorder_to_completed(request, workorder_id)
                success_count += 1
            except Exception as e:
                logger.error(f'批次轉換工單 {workorder_id} 失敗: {str(e)}')
                error_count += 1
        
        if success_count > 0:
            messages.success(request, f'成功轉換 {success_count} 個工單為已完工狀態！')
        if error_count > 0:
            messages.error(request, f'轉換失敗 {error_count} 個工單！')
        
        return redirect('workorder:completed_workorder_list')
    
    return redirect('workorder:list')


# 自動分配設定相關視圖
class AutoAllocationSettingsListView(LoginRequiredMixin, ListView):
    """自動分配設定列表視圖"""
    
    model = AutoAllocationSettings
    template_name = 'workorder_completed_workorder/auto_allocation_settings_list.html'
    context_object_name = 'allocation_settings'
    paginate_by = 20


class AutoAllocationSettingsCreateView(LoginRequiredMixin, CreateView):
    """自動分配設定建立視圖"""
    
    model = AutoAllocationSettings
    form_class = AutoAllocationSettingsForm
    template_name = 'workorder_completed_workorder/auto_allocation_settings_form.html'
    success_url = reverse_lazy('workorder:auto_allocation_settings_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, '自動分配設定建立成功！')
        return super().form_valid(form)


class AutoAllocationSettingsUpdateView(LoginRequiredMixin, UpdateView):
    """自動分配設定更新視圖"""
    
    model = AutoAllocationSettings
    form_class = AutoAllocationSettingsForm
    template_name = 'workorder_completed_workorder/auto_allocation_settings_form.html'
    success_url = reverse_lazy('workorder:auto_allocation_settings_list')
    
    def form_valid(self, form):
        messages.success(self.request, '自動分配設定更新成功！')
        return super().form_valid(form)


class AutoAllocationSettingsDeleteView(LoginRequiredMixin, DeleteView):
    """自動分配設定刪除視圖"""
    
    model = AutoAllocationSettings
    template_name = 'workorder_completed_workorder/auto_allocation_settings_confirm_delete.html'
    success_url = reverse_lazy('workorder:auto_allocation_settings_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '自動分配設定刪除成功！')
        return super().delete(request, *args, **kwargs)


# API 視圖
def get_completed_workorder_list_api(request):
    """取得已完工工單列表的 API"""
    try:
        # 取得查詢參數
        search = request.GET.get('search', '')
        company_code = request.GET.get('company_code', '')
        status = request.GET.get('status', '')
        page = request.GET.get('page', 1)
        
        # 建立查詢集
        queryset = CompletedWorkOrder.objects.all()
        
        if search:
            queryset = queryset.filter(
                Q(company_code__icontains=search) |
                Q(order_number__icontains=search) |
                Q(product_code__icontains=search) |
                Q(product_name__icontains=search)
            )
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        if status:
            queryset = queryset.filter(status=status)
        
        # 分頁
        paginator = Paginator(queryset, 20)
        page_obj = paginator.get_page(page)
        
        # 準備回應資料
        data = {
            'success': True,
            'data': [
                {
                    'id': item.id,
                    'company_code': item.company_code,
                    'order_number': item.order_number,
                    'product_code': item.product_code,
                    'product_name': item.product_name,
                    'order_quantity': item.order_quantity,
                    'completed_quantity': item.completed_quantity,
                    'defective_quantity': item.defective_quantity,
                    'completion_rate': item.completion_rate,
                    'defect_rate': item.defect_rate,
                    'start_date': item.start_date.strftime('%Y-%m-%d'),
                    'completion_date': item.completion_date.strftime('%Y-%m-%d'),
                    'status': item.status,
                    'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for item in page_obj
            ],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': page_obj.paginator.num_pages,
                'total_count': page_obj.paginator.count,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f'取得已完工工單列表失敗: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_completed_workorder_detail_api(request, pk):
    """取得已完工工單詳情的 API"""
    try:
        completed_workorder = get_object_or_404(CompletedWorkOrder, pk=pk)
        
        data = {
            'success': True,
            'data': {
                'id': completed_workorder.id,
                'company_code': completed_workorder.company_code,
                'order_number': completed_workorder.order_number,
                'product_code': completed_workorder.product_code,
                'product_name': completed_workorder.product_name,
                'order_quantity': completed_workorder.order_quantity,
                'completed_quantity': completed_workorder.completed_quantity,
                'defective_quantity': completed_workorder.defective_quantity,
                'completion_rate': completed_workorder.completion_rate,
                'defect_rate': completed_workorder.defect_rate,
                'start_date': completed_workorder.start_date.strftime('%Y-%m-%d'),
                'completion_date': completed_workorder.completion_date.strftime('%Y-%m-%d'),
                'status': completed_workorder.status,
                'remarks': completed_workorder.remarks,
                'created_at': completed_workorder.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': completed_workorder.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'processes': [
                    {
                        'id': process.id,
                        'process_name': process.process_name,
                        'process_sequence': process.process_sequence,
                        'planned_quantity': process.planned_quantity,
                        'completed_quantity': process.completed_quantity,
                        'defective_quantity': process.defective_quantity,
                        'completion_rate': process.completion_rate,
                        'duration': process.duration,
                        'start_time': process.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'end_time': process.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'operator_name': process.operator_name,
                        'equipment_name': process.equipment_name,
                        'remarks': process.remarks,
                    }
                    for process in completed_workorder.processes.all()
                ]
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f'取得已完工工單詳情失敗: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500) 