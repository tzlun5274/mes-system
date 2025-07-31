"""
報工管理視圖
包含作業員報工、SMT報工、主管報工等相關功能
使用 Django 類別視圖，符合設計規範
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required

from ..models import (
    OperatorSupplementReport, 
    SMTProductionReport, 
    SupervisorProductionReport
)
from ..forms import (
    OperatorSupplementReportForm, 
    SMTProductionReportForm, 
    SupervisorProductionReportForm
)


class ReportIndexView(LoginRequiredMixin, ListView):
    """
    報工管理首頁視圖
    顯示報工功能的總覽
    """
    template_name = 'workorder/report/index.html'
    context_object_name = 'reports'
    
    def get_queryset(self):
        """取得最近的報工記錄"""
        return OperatorSupplementReport.objects.all()[:10]
    
    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        
        from datetime import date
        from django.db.models import Q
        from ..models import OperatorSupplementReport, SMTProductionReport
        
        today = date.today()
        month_start = today.replace(day=1)
        
        # 從補登報工記錄中取得真實統計資料
        # 作業員補登報工統計
        operator_today = OperatorSupplementReport.objects.filter(created_at__date=today).count()
        operator_month = OperatorSupplementReport.objects.filter(created_at__date__gte=month_start).count()
        operator_pending = OperatorSupplementReport.objects.filter(approval_status='pending').count()
        operator_abnormal = OperatorSupplementReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
        ).count()
        
        # SMT補登報工統計
        smt_today = SMTProductionReport.objects.filter(created_at__date=today).count()
        smt_month = SMTProductionReport.objects.filter(created_at__date__gte=month_start).count()
        smt_pending = SMTProductionReport.objects.filter(approval_status='pending').count()
        smt_abnormal = SMTProductionReport.objects.filter(
            Q(abnormal_notes__isnull=False) & ~Q(abnormal_notes='')
        ).count()
        
        # 計算總計
        total_today = operator_today + smt_today
        total_month = operator_month + smt_month
        total_pending = operator_pending + smt_pending
        total_abnormal = operator_abnormal + smt_abnormal
        
        context.update({
            'today_reports': total_today,
            'month_reports': total_month,
            'pending_reports': total_pending,
            'abnormal_reports': total_abnormal,
            'stats': {
                'total_pending': total_pending,
                'total_today': total_today,
                'total_month': total_month,
                'total_abnormal': total_abnormal,
                'pending_operator': operator_pending,
                'pending_smt': smt_pending,
                'today_operator': operator_today,
                'today_smt': smt_today,
                'month_operator': operator_month,
                'month_smt': smt_month,
                'abnormal_operator': operator_abnormal,
                'abnormal_smt': smt_abnormal,
            }
        })
        
        return context


class OperatorSupplementReportListView(LoginRequiredMixin, ListView):
    """
    作業員補登報工列表視圖
    顯示所有作業員補登報工記錄
    """
    model = OperatorSupplementReport
    template_name = 'workorder/report/operator/supplement/index.html'
    context_object_name = 'supplement_reports'
    paginate_by = 20
    ordering = ['-work_date', '-start_time']

    def get_queryset(self):
        """取得查詢集，支援搜尋功能"""
        queryset = super().get_queryset()
        
        # 篩選條件
        operator_id = self.request.GET.get('operator')
        if operator_id:
            queryset = queryset.filter(operator_id=operator_id)
        
        workorder_number = self.request.GET.get('workorder')
        if workorder_number:
            queryset = queryset.filter(workorder__order_number__icontains=workorder_number)
        
        process_id = self.request.GET.get('process')
        if process_id:
            queryset = queryset.filter(process_id=process_id)
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(approval_status=status)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(work_date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(work_date__lte=date_to)
        
        # 搜尋功能
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(operator__name__icontains=search) |
                Q(workorder__order_number__icontains=search) |
                Q(process__name__icontains=search)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        
        # 取得選項資料
        from process.models import Operator, ProcessName
        operator_list = Operator.objects.all().order_by('name')
        process_list = ProcessName.objects.all().order_by('name')
        
        # 統計資料
        queryset = self.get_queryset()
        total_reports = queryset.count()
        pending_reports = queryset.filter(approval_status='pending').count()
        approved_reports = queryset.filter(approval_status='approved').count()
        rejected_reports = queryset.filter(approval_status='rejected').count()
        
        # 添加額外的上下文數據
        context.update({
            'search': self.request.GET.get('search', ''),
            'total_count': total_reports,
            'pending_count': pending_reports,
            'approved_count': approved_reports,
            'rejected_count': rejected_reports,
            'operator_list': operator_list,
            'process_list': process_list,
            'selected_operator': self.request.GET.get('operator'),
            'selected_workorder': self.request.GET.get('workorder'),
            'selected_process': self.request.GET.get('process'),
            'selected_status': self.request.GET.get('status'),
            'selected_date_from': self.request.GET.get('date_from'),
            'selected_date_to': self.request.GET.get('date_to'),
        })
        
        return context


class OperatorSupplementReportCreateView(LoginRequiredMixin, CreateView):
    """
    作業員補登報工新增視圖
    用於建立新的作業員補登報工記錄
    """
    model = OperatorSupplementReport
    form_class = OperatorSupplementReportForm
    template_name = 'workorder/report/operator/supplement/form.html'
    success_url = reverse_lazy('workorder:operator_supplement_report_index')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        messages.success(self.request, '作業員補登報工記錄建立成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '作業員補登報工記錄建立失敗，請檢查輸入資料！')
        return super().form_invalid(form)


class OperatorSupplementReportUpdateView(LoginRequiredMixin, UpdateView):
    """
    作業員補登報工編輯視圖
    用於編輯現有作業員補登報工記錄
    """
    model = OperatorSupplementReport
    form_class = OperatorSupplementReportForm
    template_name = 'workorder/report/operator/supplement/form.html'
    success_url = reverse_lazy('workorder:operator_supplement_report_index')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, '作業員補登報工記錄更新成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, '作業員補登報工記錄更新失敗，請檢查輸入資料！')
        return super().form_invalid(form)


class OperatorSupplementReportDetailView(LoginRequiredMixin, DetailView):
    """
    作業員補登報工詳情視圖
    顯示單一作業員補登報工記錄的詳細資訊
    """
    model = OperatorSupplementReport
    template_name = 'workorder/report/operator/supplement/detail.html'
    context_object_name = 'report'


class OperatorSupplementReportDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    作業員補登報工刪除視圖
    用於刪除作業員補登報工記錄，僅限管理員使用
    """
    model = OperatorSupplementReport
    template_name = 'workorder/report/operator/supplement/delete_confirm.html'
    success_url = reverse_lazy('workorder:operator_supplement_report_index')

    def test_func(self):
        """檢查用戶是否有刪除權限"""
        return self.request.user.is_staff or self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        messages.success(request, '作業員補登報工記錄刪除成功！')
        return super().delete(request, *args, **kwargs)


class SMTProductionReportListView(LoginRequiredMixin, ListView):
    """
    SMT生產報工列表視圖
    顯示所有SMT生產報工記錄
    """
    model = SMTProductionReport
    template_name = 'workorder/report/smt/supplement/index.html'
    context_object_name = 'reports'
    paginate_by = 20
    ordering = ['-work_date', '-start_time']

    def get_queryset(self):
        """取得查詢集，支援搜尋功能"""
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        equipment = self.request.GET.get('equipment', '')
        
        if search:
            queryset = queryset.filter(
                Q(workorder__order_number__icontains=search) |
                Q(product_id__icontains=search) |
                Q(equipment__name__icontains=search)
            )
        
        if equipment:
            queryset = queryset.filter(equipment_id=equipment)
            
        return queryset


class SMTProductionReportCreateView(LoginRequiredMixin, CreateView):
    """
    SMT生產報工新增視圖
    用於建立新的SMT生產報工記錄
    """
    model = SMTProductionReport
    form_class = SMTProductionReportForm
    template_name = 'workorder/report/smt/supplement/form.html'
    success_url = reverse_lazy('workorder:smt_supplement_report_index')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        messages.success(self.request, 'SMT生產報工記錄建立成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, 'SMT生產報工記錄建立失敗，請檢查輸入資料！')
        return super().form_invalid(form)


class SMTProductionReportUpdateView(LoginRequiredMixin, UpdateView):
    """
    SMT生產報工編輯視圖
    用於編輯現有SMT生產報工記錄
    """
    model = SMTProductionReport
    form_class = SMTProductionReportForm
    template_name = 'workorder/report/smt/supplement/form.html'
    success_url = reverse_lazy('workorder:smt_supplement_report_index')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, 'SMT生產報工記錄更新成功！')
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, 'SMT生產報工記錄更新失敗，請檢查輸入資料！')
        return super().form_invalid(form)


class SMTProductionReportDetailView(LoginRequiredMixin, DetailView):
    """
    SMT生產報工詳情視圖
    顯示單一SMT生產報工記錄的詳細資訊
    """
    model = SMTProductionReport
    template_name = 'workorder/report/smt/supplement/detail.html'
    context_object_name = 'report'


class SMTProductionReportDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    SMT生產報工刪除視圖
    用於刪除SMT生產報工記錄，僅限管理員使用
    """
    model = SMTProductionReport
    template_name = 'workorder/report/smt/supplement/delete_confirm.html'
    success_url = reverse_lazy('workorder:smt_supplement_report_index')

    def test_func(self):
        """檢查用戶是否有刪除權限"""
        return self.request.user.is_staff or self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        messages.success(request, 'SMT生產報工記錄刪除成功！')
        return super().delete(request, *args, **kwargs)


@require_POST
@login_required
def approve_report(request, report_id):
    """
    核准報工記錄
    用於核准作業員補登報工或SMT生產報工記錄
    """
    try:
        report_type = request.POST.get('report_type')
        if report_type == 'operator':
            report = get_object_or_404(OperatorSupplementReport, id=report_id)
        elif report_type == 'smt':
            report = get_object_or_404(SMTProductionReport, id=report_id)
        else:
            messages.error(request, '無效的報工記錄類型！')
            return redirect('workorder:report_index')
        
        if report.can_approve(request.user):
            report.approve(request.user, request.POST.get('remarks', ''))
            messages.success(request, '報工記錄核准成功！')
        else:
            messages.error(request, '您沒有權限核准此報工記錄！')
            
    except Exception as e:
        messages.error(request, f'核准失敗：{str(e)}')
    
    return redirect('workorder:report_index')


@require_POST
@login_required
def reject_report(request, report_id):
    """
    駁回報工記錄
    用於駁回作業員補登報工或SMT生產報工記錄
    """
    try:
        report_type = request.POST.get('report_type')
        if report_type == 'operator':
            report = get_object_or_404(OperatorSupplementReport, id=report_id)
        elif report_type == 'smt':
            report = get_object_or_404(SMTProductionReport, id=report_id)
        else:
            messages.error(request, '無效的報工記錄類型！')
            return redirect('workorder:report_index')
        
        if report.can_approve(request.user):
            report.reject(request.user, request.POST.get('reason', ''))
            messages.success(request, '報工記錄駁回成功！')
        else:
            messages.error(request, '您沒有權限駁回此報工記錄！')
            
    except Exception as e:
        messages.error(request, f'駁回失敗：{str(e)}')
    
    return redirect('workorder:report_index') 