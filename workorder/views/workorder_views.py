"""
工單基本管理視圖
包含工單的列表、新增、編輯、刪除、詳情等功能
使用 Django 類別視圖，符合設計規範
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from ..models import WorkOrder
from ..workorder_erp.models import CompanyOrder
from ..forms import WorkOrderForm


class WorkOrderListView(LoginRequiredMixin, ListView):
    """
    工單列表視圖
    顯示所有工單，支援搜尋和分頁功能
    """
    model = WorkOrder
    template_name = 'workorder/workorder/workorder_list.html'
    context_object_name = 'workorders'
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        """取得查詢集，支援搜尋功能"""
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(product_code__icontains=search) |
                Q(company_code__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context['is_debug'] = self.request.settings.DEBUG if hasattr(self.request, 'settings') else False
        return context


class WorkOrderDetailView(LoginRequiredMixin, DetailView):
    """
    工單詳情視圖
    顯示單一工單的詳細資訊
    """
    model = WorkOrder
    template_name = 'workorder/workorder/workorder_detail.html'
    context_object_name = 'workorder'


class WorkOrderCreateView(LoginRequiredMixin, CreateView):
    """
    工單新增視圖
    用於建立新的工單
    """
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'workorder/workorder/workorder_form.html'
    success_url = reverse_lazy('workorder:workorder_list')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, '工單建立成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '工單建立失敗，請檢查輸入資料！')
        return super().form_invalid(form)


class WorkOrderUpdateView(LoginRequiredMixin, UpdateView):
    """
    工單編輯視圖
    用於編輯現有工單
    """
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'workorder/workorder/workorder_form.html'
    success_url = reverse_lazy('workorder:workorder_list')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, '工單更新成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '工單更新失敗，請檢查輸入資料！')
        return super().form_invalid(form)


class WorkOrderDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    工單刪除視圖
    用於刪除工單，僅限管理員使用
    """
    model = WorkOrder
    template_name = 'workorder/workorder/workorder_confirm_delete.html'
    success_url = reverse_lazy('workorder:workorder_list')

    def test_func(self):
        """檢查用戶是否有刪除權限"""
        return self.request.user.is_staff or self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        messages.success(request, '工單刪除成功！')
        return super().delete(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CompanyOrderListView(LoginRequiredMixin, ListView):
    """
    公司製令單列表視圖
    顯示從 ERP 同步的公司製令單
    """
    model = CompanyOrder
    template_name = 'workorder/company_order_list.html'
    context_object_name = 'company_orders'
    paginate_by = 20
    ordering = ['-sync_time']

    def get_queryset(self):
        """取得查詢集，支援搜尋功能"""
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        company_code = self.request.GET.get('company_code', '')
        
        if search:
            queryset = queryset.filter(
                Q(mkordno__icontains=search) |
                Q(product_id__icontains=search)
            )
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
            
        return queryset

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        # 取得所有公司代號供篩選使用
        context['company_codes'] = CompanyOrder.objects.values_list(
            'company_code', flat=True
        ).distinct().order_by('company_code')
        return context


@require_GET
def get_company_order_info(request):
    """
    取得公司製令單資訊的 API 端點
    用於 AJAX 請求
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': '未登入'}, status=401)
    
    try:
        company_code = request.GET.get('company_code')
        if not company_code:
            return JsonResponse({'error': '缺少公司代號參數'}, status=400)
        
        # 取得該公司的製令單數量統計
        total_orders = CompanyOrder.objects.filter(company_code=company_code).count()
        converted_orders = CompanyOrder.objects.filter(
            company_code=company_code, 
            is_converted=True
        ).count()
        pending_orders = total_orders - converted_orders
        
        return JsonResponse({
            'total_orders': total_orders,
            'converted_orders': converted_orders,
            'pending_orders': pending_orders,
            'company_code': company_code
        })
        
    except Exception as e:
        return JsonResponse({'error': f'查詢失敗：{str(e)}'}, status=500) 