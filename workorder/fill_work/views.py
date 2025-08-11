"""
填報作業管理子模組 - 視圖定義
負責填報作業功能，包括作業員填報、SMT填報等
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from datetime import date

from .models import FillWork
from .forms import FillWorkForm


class FillWorkIndexView(LoginRequiredMixin, ListView):
    """
    填報作業管理首頁視圖
    顯示填報作業功能總覽
    """

    template_name = "workorder/fill_work/fill_index.html"
    context_object_name = "fill_works"

    def get_queryset(self):
        """取得最近的填報作業記錄"""
        return FillWork.objects.all()[:10]

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)

        # 統計數據 - 總計
        context['total_works'] = FillWork.objects.count()
        context['pending_works'] = FillWork.objects.filter(approval_status='pending').count()
        context['approved_works'] = FillWork.objects.filter(approval_status='approved').count()
        context['rejected_works'] = FillWork.objects.filter(approval_status='rejected').count()
        context['completed_works'] = FillWork.objects.filter(is_completed=True).count()

        # 為了模板相容性，提供相同的統計數據
        context['total_operator_works'] = FillWork.objects.count()
        context['pending_operator_works'] = FillWork.objects.filter(approval_status='pending').count()
        context['approved_operator_works'] = FillWork.objects.filter(approval_status='approved').count()
        context['rejected_operator_works'] = FillWork.objects.filter(approval_status='rejected').count()

        # SMT填報統計（所有填報都是正式填報）
        context['total_smt_works'] = FillWork.objects.count()
        context['pending_smt_works'] = FillWork.objects.filter(approval_status='pending').count()
        context['approved_smt_works'] = FillWork.objects.filter(approval_status='approved').count()
        context['rejected_smt_works'] = FillWork.objects.filter(approval_status='rejected').count()

        return context


class FillWorkListView(LoginRequiredMixin, ListView):
    """
    填報作業列表視圖
    """

    model = FillWork
    template_name = "workorder/fill_work/fill_list.html"
    context_object_name = "fill_works"
    paginate_by = 20

    def get_queryset(self):
        """取得填報作業記錄，支援搜尋"""
        queryset = FillWork.objects.select_related(
            'workorder', 'process', 'equipment'
        ).order_by('-created_at')

        # 搜尋條件
        workorder_number = self.request.GET.get('workorder_number')
        operator = self.request.GET.get('operator')
        process = self.request.GET.get('process')
        approval_status = self.request.GET.get('approval_status')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if workorder_number:
            queryset = queryset.filter(
                Q(workorder__workorder_number__icontains=workorder_number)
            )

        if operator:
            queryset = queryset.filter(operator__icontains=operator)

        if process:
            queryset = queryset.filter(process__name__icontains=process)

        if approval_status:
            queryset = queryset.filter(approval_status=approval_status)

        if start_date:
            queryset = queryset.filter(work_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(work_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        """提供額外的上下文數據"""
        context = super().get_context_data(**kwargs)
        context['today_date'] = date.today().isoformat()
        return context


class FillWorkCreateView(LoginRequiredMixin, CreateView):
    """
    填報作業建立視圖
    """

    model = FillWork
    template_name = "workorder/fill_work/fill_form.html"
    fields = ['operator', 'company_name', 'workorder', 'product_id', 'planned_quantity', 'process', 'operation', 'equipment', 'work_date', 'start_time', 'end_time', 'has_break', 'break_start_time', 'break_end_time', 'break_hours', 'work_quantity', 'defect_quantity', 'is_completed', 'remarks', 'abnormal_notes']
    success_url = reverse_lazy('workorder:fill_work:fill_work_list')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        form.instance.approval_status = 'pending'
        
        messages.success(self.request, "填報作業建立成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "請檢查輸入的資料是否正確！")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        
        # 提供工單、工序、設備選項
        from workorder.models import WorkOrder
        from process.models import ProcessName
        from equip.models import Equipment
        
        context['workorders'] = WorkOrder.objects.all().order_by('-created_at')[:100]
        context['processes'] = ProcessName.objects.all().order_by('name')
        context['equipments'] = Equipment.objects.all().order_by('name')
        context['today_date'] = date.today().isoformat()
        
        return context


class FillWorkUpdateView(LoginRequiredMixin, UpdateView):
    """
    填報作業更新視圖
    """

    model = FillWork
    template_name = "workorder/fill_work/fill_form.html"
    fields = ['operator', 'company_name', 'workorder', 'product_id', 'planned_quantity', 'process', 'operation', 'equipment', 'work_date', 'start_time', 'end_time', 'has_break', 'break_start_time', 'break_end_time', 'break_hours', 'work_quantity', 'defect_quantity', 'is_completed', 'remarks', 'abnormal_notes']
    success_url = reverse_lazy('workorder:fill_work:fill_work_list')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, "填報作業更新成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "請檢查輸入的資料是否正確！")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        
        # 提供工單、工序、設備選項
        from workorder.models import WorkOrder
        from process.models import ProcessName
        from equip.models import Equipment
        
        context['workorders'] = WorkOrder.objects.all().order_by('-created_at')[:100]
        context['processes'] = ProcessName.objects.all().order_by('name')
        context['equipments'] = Equipment.objects.all().order_by('name')
        context['today_date'] = date.today().isoformat()
        
        return context


class FillWorkDetailView(LoginRequiredMixin, DetailView):
    """
    填報作業詳情視圖
    """

    model = FillWork
    template_name = "workorder/fill_work/fill_detail.html"
    context_object_name = "fill_work"


class FillWorkDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    填報作業刪除視圖
    """

    model = FillWork
    template_name = "workorder/fill_work/fill_confirm_delete.html"
    success_url = reverse_lazy('workorder:fill_work:fill_work_list')

    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        messages.success(request, "填報作業刪除成功！")
        return super().delete(request, *args, **kwargs)


# 作業員填報首頁視圖
class OperatorFillWorkIndexView(LoginRequiredMixin, ListView):
    """作業員填報首頁視圖"""
    
    model = FillWork
    template_name = "workorder/fill_work/operator_fill_index.html"
    context_object_name = "fill_works"
    paginate_by = 10

    def get_queryset(self):
        """獲取作業員填報記錄"""
        return FillWork.objects.filter(
            operator__isnull=False
        ).exclude(
            operator=''
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        context['total_operator_reports'] = FillWork.objects.filter(
            operator__isnull=False
        ).exclude(
            operator=''
        ).count()
        context['pending_operator_reports'] = FillWork.objects.filter(
            operator__isnull=False
        ).exclude(
            operator=''
        ).filter(
            approval_status='pending'
        ).count()
        context['today_date'] = date.today().isoformat()
        return context


# 作業員補登填報視圖
class OperatorBackfillView(LoginRequiredMixin, CreateView):
    """作業員補登填報視圖"""
    
    model = FillWork
    template_name = "workorder/fill_work/operator_backfill.html"
    form_class = FillWorkForm
    success_url = reverse_lazy('workorder:fill_work:operator_fill_index')

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['today_date'] = date.today().isoformat()
        return context

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        form.instance.approval_status = 'pending'
        
        messages.success(self.request, "作業員補登填報建立成功！")
        return super().form_valid(form)


# 作業員RD樣品補登填報視圖
class OperatorRDBackfillView(LoginRequiredMixin, CreateView):
    """作業員RD樣品補登填報視圖"""
    
    model = FillWork
    template_name = "workorder/fill_work/operator_rd_backfill.html"
    form_class = FillWorkForm
    success_url = reverse_lazy('workorder:fill_work:fill_work_list')

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['today_date'] = date.today().isoformat()
        return context

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        form.instance.approval_status = 'pending'
        form.instance.workorder = None  # RD樣品不需要工單
        
        messages.success(self.request, "作業員RD樣品補登填報建立成功！")
        return super().form_valid(form)


# SMT補登填報視圖
class SMTBackfillView(LoginRequiredMixin, CreateView):
    """SMT補登填報視圖"""
    
    model = FillWork
    template_name = "workorder/fill_work/smt_backfill.html"
    fields = ['operator', 'company_name', 'workorder', 'product_id', 'planned_quantity', 'process', 'operation', 'equipment', 'work_date', 'start_time', 'end_time', 'has_break', 'break_start_time', 'break_end_time', 'break_hours', 'work_quantity', 'defect_quantity', 'is_completed', 'remarks', 'abnormal_notes']
    success_url = reverse_lazy('workorder:fill_work:fill_work_list')

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        from process.models import ProcessName
        from equip.models import Equipment
        
        # 只顯示SMT相關的工序和設備
        context['smt_processes'] = ProcessName.objects.filter(name__icontains='SMT')
        context['smt_equipments'] = Equipment.objects.filter(name__icontains='SMT')
        context['today_date'] = date.today().isoformat()
        return context

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        form.instance.approval_status = 'pending'
        
        messages.success(self.request, "SMT補登填報建立成功！")
        return super().form_valid(form)


# SMT_RD樣品補登填報視圖
class SMTRDBackfillView(LoginRequiredMixin, CreateView):
    """SMT_RD樣品補登填報視圖"""
    
    model = FillWork
    template_name = "workorder/fill_work/smt_rd_backfill.html"
    fields = ['operator', 'company_name', 'workorder', 'product_id', 'planned_quantity', 'process', 'operation', 'equipment', 'work_date', 'start_time', 'end_time', 'has_break', 'break_start_time', 'break_end_time', 'break_hours', 'work_quantity', 'defect_quantity', 'is_completed', 'remarks', 'abnormal_notes']
    success_url = reverse_lazy('workorder:fill_work:fill_work_list')

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        from process.models import ProcessName
        from equip.models import Equipment
        
        # 只顯示SMT相關的工序和設備
        context['smt_processes'] = ProcessName.objects.filter(name__icontains='SMT')
        context['smt_equipments'] = Equipment.objects.filter(name__icontains='SMT')
        context['today_date'] = date.today().isoformat()
        return context

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        form.instance.approval_status = 'pending'
        form.instance.workorder = None  # RD樣品不需要工單
        
        messages.success(self.request, "SMT_RD樣品補登填報建立成功！")
        return super().form_valid(form)


# 核准和駁回功能
@login_required
def approve_fill_work(request, work_id):
    """核准填報作業"""
    fill_work = get_object_or_404(FillWork, id=work_id)
    
    if request.method == 'POST':
        fill_work.approval_status = 'approved'
        fill_work.approved_by = request.user.username
        fill_work.approved_at = timezone.now()
        fill_work.approval_remarks = request.POST.get('approval_remarks', '')
        fill_work.save()
        
        messages.success(request, "填報作業已核准！")
        return redirect('workorder:fill_work:fill_work_list')
    
    return render(request, 'workorder/fill_work/approve_form.html', {'fill_work': fill_work})


@login_required
def reject_fill_work(request, work_id):
    """駁回填報作業"""
    fill_work = get_object_or_404(FillWork, id=work_id)
    
    if request.method == 'POST':
        fill_work.approval_status = 'rejected'
        fill_work.rejected_by = request.user.username
        fill_work.rejected_at = timezone.now()
        fill_work.rejection_reason = request.POST.get('rejection_reason', '')
        fill_work.save()
        
        messages.success(request, "填報作業已駁回！")
        return redirect('workorder:fill_work:fill_work_list')
    
    return render(request, 'workorder/fill_work/reject_form.html', {'fill_work': fill_work})


@require_GET
def get_workorder_info(request):
    """取得工單資訊的API - 當選擇工單號碼時自動帶出產品編號和公司名稱"""
    workorder_id = request.GET.get('workorder_id')
    if workorder_id:
        from workorder.models import WorkOrder
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 根據公司代號獲取公司名稱
            company_name = workorder.company_code
            try:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                if company_config:
                    company_name = company_config.company_name
            except:
                pass  # 如果無法獲取公司名稱，使用公司代號
            
            return JsonResponse({
                'success': True,
                'workorder_number': workorder.order_number,
                'product_id': workorder.product_code,  # 新增：產品編號
                'company_name': company_name,  # 新增：公司名稱
                'planned_quantity': workorder.quantity
            })
        except WorkOrder.DoesNotExist:
            return JsonResponse({'success': False, 'error': '找不到對應的工單'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '請提供工單ID'}) 