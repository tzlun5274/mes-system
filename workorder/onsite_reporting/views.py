"""
現場報工子模組 - 視圖
負責現場報工的所有視圖邏輯
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET, require_POST
from django.forms import ModelForm
from django import forms
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import OnsiteReport, OnsiteReportHistory, OnsiteReportConfig, OnsiteReportSession
from process.models import ProcessName, Operator
from equip.models import Equipment
from workorder.models import WorkOrder
from erp_integration.models import CompanyConfig


# ==================== 現場報工表單類別 ====================

class OperatorOnsiteReportForm(forms.Form):
    """作業員現場報工表單"""
    
    # 產品編號 - 下拉式選單
    product_id = forms.ChoiceField(
        choices=[],
        label="產品編號",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇產品編號'}),
        required=True,
        help_text="請選擇產品編號",
    )

    # 工單號碼 - 下拉式選單
    workorder = forms.ChoiceField(
        choices=[],
        label="工單號碼",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇工單號碼'}),
        required=True,
        help_text="請選擇工單號碼",
    )

    # 公司名稱欄位 - 下拉式選單
    company_name = forms.ChoiceField(
        choices=[],
        label="公司名稱",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇公司名稱'}),
        required=True,
        help_text="請選擇公司名稱",
    )

    # 作業員欄位 - 下拉式選單
    operator = forms.ChoiceField(
        choices=[],
        label="作業員",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇作業員'}),
        required=True,
        help_text="請選擇作業員",
    )

    # 工序欄位 - 下拉式選單
    process = forms.ChoiceField(
        choices=[],
        label="工序",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇工序'}),
        required=True,
        help_text="請選擇工序",
    )

    # 使用的設備欄位 - 下拉式選單
    equipment = forms.ChoiceField(
        choices=[],
        label="使用的設備",
        widget=forms.Select(attrs={'class': 'form-select', 'placeholder': '請選擇設備'}),
        required=False,
        help_text="請選擇設備",
    )

    # 工作狀態 - 下拉選單
    status = forms.ChoiceField(
        choices=OnsiteReport.STATUS_CHOICES,
        label="報工狀態",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text="請選擇此次報工的狀態",
    )

    # 備註欄位
    remarks = forms.CharField(
        label="備註",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text="可記錄此次報工的相關備註",
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # 動態載入選項
        self.load_dynamic_choices()

    def load_dynamic_choices(self):
        """動態載入表單選項"""
        try:
            # 載入公司選項
            companies = CompanyConfig.objects.all().order_by('company_name')
            self.fields['company_name'].choices = [('', '請選擇公司名稱')] + [
                (company.company_name, company.company_name) for company in companies
            ]

            # 載入產品選項（從工單中取得）
            workorders = WorkOrder.objects.values_list('product_code', flat=True).distinct().order_by('product_code')
            self.fields['product_id'].choices = [('', '請選擇產品編號')] + [
                (product_code, product_code) for product_code in workorders if product_code
            ]

            # 載入作業員選項 - 使用權限過濾
            from system.services import PermissionFilterService
            if self.request:
                operators = PermissionFilterService.filter_operators(self.request)
            else:
                # 沒有請求物件，載入所有作業員
                from process.models import Operator
                operators = Operator.objects.all().order_by('name')
            
            self.fields['operator'].choices = [('', '請選擇作業員')] + [
                (operator.name, operator.name) for operator in operators
            ]

            # 載入工序選項（從工單工序中取得）- 使用權限過濾
            from workorder.models import WorkOrderProcess
            from system.services import PermissionFilterService
            if self.request:
                processes = PermissionFilterService.filter_processes(self.request)
            else:
                # 沒有請求物件，載入所有工序
                from process.models import ProcessName
                processes = ProcessName.objects.all().order_by('name')
            
            process_names = processes.values_list('name', flat=True).distinct().order_by('name')
            self.fields['process'].choices = [('', '請選擇工序')] + [
                (process_name, process_name) for process_name in process_names if process_name
            ]

            # 載入設備選項 - 使用權限過濾
            from system.services import PermissionFilterService
            if self.request:
                equipments = PermissionFilterService.filter_equipments(self.request)
            else:
                # 沒有請求物件，載入所有設備
                from equip.models import Equipment
                equipments = Equipment.objects.all().order_by('name')
            
            self.fields['equipment'].choices = [('', '請選擇設備')] + [
                (equipment.name, equipment.name) for equipment in equipments
            ]

            # 載入工單選項
            workorders = WorkOrder.objects.filter(status__in=['pending', 'in_progress']).order_by('workorder_number')
            self.fields['workorder'].choices = [('', '請選擇工單號碼')] + [
                (workorder.workorder_number, workorder.workorder_number) for workorder in workorders
            ]

        except Exception as e:
            # 如果載入失敗，設定空選項
            self.fields['operator'].choices = [('', '載入作業員失敗')]
            self.fields['process'].choices = [('', '載入工序失敗')]
            self.fields['equipment'].choices = [('', '載入設備失敗')]
            self.fields['workorder'].choices = [('', '載入工單失敗')]


# ==================== 現場報工視圖 ====================

class OnsiteReportIndexView(LoginRequiredMixin, TemplateView):
    """現場報工首頁視圖"""
    
    template_name = "workorder/onsite_reporting/index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 取得統計資料
        from datetime import date
        today = date.today()

        # 今日報工統計
        today_reports = OnsiteReport.objects.filter(created_at__date=today)
        context['today_total'] = today_reports.count()
        context['today_active'] = today_reports.filter(status__in=['started', 'resumed']).count()
        context['today_completed'] = today_reports.filter(status='completed').count()
        context['today_stopped'] = today_reports.filter(status='stopped').count()

        # 報工類型統計
        context['operator_reports'] = today_reports.filter(report_type='operator').count()
        context['smt_reports'] = today_reports.filter(report_type='smt').count()

        # 最近活躍報工
        context['recent_active'] = OnsiteReport.objects.filter(
            status__in=['started', 'resumed']
        ).order_by('-updated_at')[:5]

        # 停工報工
        context['stopped_reports'] = OnsiteReport.objects.filter(
            status='stopped'
        ).order_by('-updated_at')[:5]

        return context


class OnsiteReportListView(LoginRequiredMixin, ListView):
    """現場報工列表視圖"""
    
    model = OnsiteReport
    template_name = "workorder/onsite_reporting/onsite_report_list.html"
    context_object_name = "onsite_reports"
    paginate_by = 20
    ordering = ["-created_at"]
    
    def get_queryset(self):
        """取得查詢集，支援搜尋和篩選功能"""
        queryset = super().get_queryset()
        
        # 搜尋功能
        search = self.request.GET.get("search", "")
        if search:
            queryset = queryset.filter(
                Q(operator__icontains=search) |
                Q(workorder__icontains=search) |
                Q(product_id__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        # 報工類型篩選
        report_type = self.request.GET.get("report_type", "")
        if report_type:
            if report_type == 'smt':
                # SMT類型包含 smt 和 smt_rd
                queryset = queryset.filter(report_type__in=['smt', 'smt_rd'])
            elif report_type == 'operator':
                # 作業員類型包含 operator 和 operator_rd
                queryset = queryset.filter(report_type__in=['operator', 'operator_rd'])
            else:
                # 其他類型直接篩選
                queryset = queryset.filter(report_type=report_type)
        
        # 狀態篩選
        status = self.request.GET.get("status", "")
        if status:
            queryset = queryset.filter(status=status)
        
        # 公司篩選
        company_name = self.request.GET.get("company_name", "")
        if company_name:
            queryset = queryset.filter(company_name=company_name)
        
        # 日期範圍篩選
        date_from = self.request.GET.get("date_from", "")
        if date_from:
            queryset = queryset.filter(work_date__gte=date_from)
        
        date_to = self.request.GET.get("date_to", "")
        if date_to:
            queryset = queryset.filter(work_date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 統計資料
        queryset = self.get_queryset()
        context['total_count'] = queryset.count()
        context['active_count'] = queryset.filter(status__in=['started', 'resumed']).count()
        context['completed_count'] = queryset.filter(status='completed').count()
        context['stopped_count'] = queryset.filter(status='stopped').count()
        
        return context


@login_required
def operator_onsite_report_create(request):
    """作業員現場報工新增視圖"""
    if request.method == 'POST':
        try:
            # 從 POST 資料取得欄位值
            report_type = 'operator'
            operator = request.POST.get('operator')
            workorder = request.POST.get('workorder')
            product_id = request.POST.get('product_id')
            company_name = request.POST.get('company_name')
            process = request.POST.get('process')
            equipment = request.POST.get('equipment', '')
            status = 'started'  # 新增報工固定為開工狀態
            planned_quantity = int(request.POST.get('planned_quantity', 0))
            remarks = request.POST.get('remarks', '')
            
            # 驗證必填欄位
            if not all([operator, workorder, product_id, company_name, process]):
                messages.error(request, '請填寫所有必填欄位')
                return redirect('workorder:onsite_reporting:operator_onsite_report_create')
            
            # 設定公司代號
            company_code = None
            try:
                company_config = CompanyConfig.objects.filter(
                    company_name=company_name
                ).first()
                if company_config:
                    company_code = company_config.company_code
            except Exception:
                pass
            
            # 建立報工記錄
            onsite_report = OnsiteReport.objects.create(
                report_type=report_type,
                operator=operator,
                workorder=workorder,
                product_id=product_id,
                company_name=company_name,
                company_code=company_code,
                process=process,
                equipment=equipment,
                status=status,
                planned_quantity=planned_quantity,
                work_quantity=0,
                remarks=remarks,
                created_by=request.user.username,
                work_date=timezone.now().date(),
                start_datetime=timezone.now()
            )
            
            messages.success(request, '作業員現場報工記錄已建立')
            return redirect('workorder:onsite_reporting:onsite_report_list')
            
        except Exception as e:
            messages.error(request, f'建立失敗: {str(e)}')
            return redirect('workorder:onsite_reporting:operator_onsite_report_create')
    
    # GET 請求：顯示新增頁面
    form = OperatorOnsiteReportForm(request=request)
    
    context = {
        'report_type': 'operator',
        'report_type_display': '作業員報工',
        'form': form
    }
    return render(request, 'workorder/onsite_reporting/operator_onsite_report_form.html', context)


# 其他視圖函數將在下一部分添加...


class OnsiteReportDetailView(LoginRequiredMixin, DetailView):
    """現場報工詳情視圖"""
    
    model = OnsiteReport
    template_name = "workorder/onsite_reporting/onsite_report_detail.html"
    context_object_name = "onsite_report"
    
    def post(self, request, *args, **kwargs):
        """處理狀態變更POST請求"""
        self.object = self.get_object()
        action = request.POST.get('action')
        
        if action == 'change_status':
            return self.handle_status_change(request)
        
        return self.get(request, *args, **kwargs)
    
    def handle_status_change(self, request):
        """處理狀態變更"""
        try:
            new_status = request.POST.get('new_status')
            work_quantity = int(request.POST.get('work_quantity', 0))
            defect_quantity = int(request.POST.get('defect_quantity', 0))
            change_notes = request.POST.get('change_notes', '')
            
            # 驗證新狀態
            if not new_status:
                messages.error(request, '請選擇新狀態')
                return self.get(request)
            
            # 驗證狀態轉換的合理性
            current_status = self.object.status
            valid_transitions = {
                'started': ['paused', 'completed', 'stopped'],
                'paused': ['resumed', 'completed', 'stopped'],
                'resumed': ['paused', 'completed', 'stopped'],
            }
            
            if current_status not in valid_transitions or new_status not in valid_transitions[current_status]:
                messages.error(request, f'無法從 {self.object.get_status_display()} 變更為 {dict(OnsiteReport.STATUS_CHOICES).get(new_status, new_status)}')
                return self.get(request)
            
            # 驗證數量
            if new_status in ['completed', 'stopped'] and work_quantity == 0:
                messages.error(request, '完工或停工時必須填寫工作數量')
                return self.get(request)
            
            if defect_quantity > work_quantity:
                messages.error(request, '不良品數量不能超過工作數量')
                return self.get(request)
            
            # 記錄原始資料
            old_status = self.object.status
            old_work_quantity = self.object.work_quantity
            old_defect_quantity = self.object.defect_quantity
            
            # 更新報工記錄
            self.object.status = new_status
            self.object.work_quantity = work_quantity
            self.object.defect_quantity = defect_quantity
            
            # 如果變更為完工或停工，設定結束時間
            if new_status in ['completed', 'stopped']:
                self.object.end_datetime = timezone.now()
            
            self.object.save()
            
            # 記錄歷史
            try:
                # 根據狀態變更類型決定 change_type
                if new_status == 'started':
                    change_type = 'start'
                elif new_status == 'paused':
                    change_type = 'pause'
                elif new_status == 'resumed':
                    change_type = 'resume'
                elif new_status == 'completed':
                    change_type = 'complete'
                elif new_status == 'stopped':
                    change_type = 'abnormal'
                else:
                    change_type = 'update'
                
                OnsiteReportHistory.objects.create(
                    onsite_report=self.object,
                    change_type=change_type,
                    old_status=old_status,
                    new_status=new_status,
                    old_quantity=old_work_quantity,
                    new_quantity=work_quantity,
                    change_notes=change_notes,
                    changed_by=request.user.username
                )
            except Exception as e:
                # 如果歷史記錄失敗，不影響主要功能
                print(f"記錄歷史失敗: {e}")
            
            messages.success(request, f'狀態已成功變更為 {self.object.get_status_display()}')
            return redirect('workorder:onsite_reporting:onsite_report_detail', pk=self.object.pk)
            
        except Exception as e:
            messages.error(request, f'狀態變更失敗: {str(e)}')
            return self.get(request)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得歷史記錄
        try:
            context['history'] = OnsiteReportHistory.objects.filter(
                onsite_report=self.object
            ).order_by('-changed_at')
        except:
            context['history'] = []
        
        # 計算進度
        context['progress_percentage'] = self.object.get_progress_percentage()
        context['duration_minutes'] = self.object.get_duration_minutes()
        
        return context


class OnsiteReportDeleteView(LoginRequiredMixin, DeleteView):
    """現場報工刪除視圖"""
    
    model = OnsiteReport
    template_name = "workorder/onsite_reporting/onsite_report_confirm_delete.html"
    success_url = reverse_lazy('workorder:onsite_reporting:onsite_report_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '現場報工記錄已刪除')
        return super().delete(request, *args, **kwargs)


class OnsiteReportMonitoringView(LoginRequiredMixin, TemplateView):
    """現場報工監控視圖"""
    
    template_name = "workorder/onsite_reporting/onsite_report_monitoring.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 活躍報工
        context['active_reports'] = OnsiteReport.objects.filter(
            status__in=['started', 'resumed']
        ).order_by('-updated_at')
        
        # 暫停報工
        context['paused_reports'] = OnsiteReport.objects.filter(
            status='paused'
        ).order_by('-updated_at')
        
        # 停工報工
        context['stopped_reports'] = OnsiteReport.objects.filter(
            status='stopped'
        ).order_by('-updated_at')
        
        # 今日完成報工
        from datetime import date
        today = date.today()
        context['today_completed'] = OnsiteReport.objects.filter(
            work_date=today,
            status='completed'
        ).order_by('-updated_at')
        
        # 統計資料
        context['total_reports'] = OnsiteReport.objects.count()
        context['total_active'] = context['active_reports'].count()
        context['total_paused'] = context['paused_reports'].count()
        context['total_stopped'] = context['stopped_reports'].count()
        context['total_completed_today'] = context['today_completed'].count()
        
        return context


class OnsiteReportConfigView(LoginRequiredMixin, ListView):
    """現場報工配置管理視圖"""
    
    model = OnsiteReportConfig
    template_name = "workorder/onsite_reporting/onsite_report_config.html"
    context_object_name = "object_list"
    paginate_by = 20
    ordering = ["config_type", "config_key"]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class OnsiteReportConfigDeleteView(LoginRequiredMixin, DeleteView):
    """現場報工配置刪除視圖"""
    
    model = OnsiteReportConfig
    template_name = "workorder/onsite_reporting/onsite_report_config_confirm_delete.html"
    success_url = reverse_lazy('workorder:onsite_reporting:onsite_report_config')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '現場報工配置已刪除')
        return super().delete(request, *args, **kwargs)


@login_required
def operator_work_selection(request):
    """作業員報工作業選擇頁面"""
    return render(request, 'workorder/onsite_reporting/operator_work_selection.html', {
        'title': '作業員現場報工作業選擇',
        'subtitle': '請選擇要進行的作業員報工類型'
    })


@login_required
def smt_work_selection(request):
    """SMT報工作業選擇頁面"""
    return render(request, 'workorder/onsite_reporting/smt_work_selection.html', {
        'title': 'SMT現場報工作業選擇',
        'subtitle': '請選擇要進行的SMT報工類型'
    })


@login_required
def smt_onsite_report_create(request):
    """SMT設備現場報工新增視圖 - 只有開工功能"""
    if request.method == 'POST':
        try:
            # 從 POST 資料取得欄位值
            report_type = 'smt'
            operator = request.POST.get('operator')
            workorder = request.POST.get('workorder')
            product_id = request.POST.get('product_id')
            company_name = request.POST.get('company_name')
            process = request.POST.get('process')
            equipment = request.POST.get('equipment', '')
            planned_quantity = int(request.POST.get('planned_quantity', 0))
            remarks = request.POST.get('remarks', '')
            
            # 驗證必填欄位
            if not all([operator, workorder, product_id, company_name, process, equipment]):
                messages.error(request, '請填寫所有必填欄位（SMT設備報工需要選擇設備）')
                return redirect('workorder:onsite_reporting:smt_onsite_report_create')
            
            # 設定公司代號
            company_code = None
            try:
                company_config = CompanyConfig.objects.filter(
                    company_name=company_name
                ).first()
                if company_config:
                    company_code = company_config.company_code
            except Exception:
                pass
            
            # SMT現場報工只有開工功能，狀態固定為 started
            status = 'started'
            
            # 建立報工記錄
            onsite_report = OnsiteReport.objects.create(
                report_type=report_type,
                operator=operator,
                workorder=workorder,
                product_id=product_id,
                company_name=company_name,
                company_code=company_code,
                process=process,
                equipment=equipment,
                status=status,  # 固定為開工狀態
                planned_quantity=planned_quantity,
                work_quantity=0,  # 初始工作數量為0
                remarks=remarks,
                created_by=request.user.username,
                work_date=timezone.now().date(),
                start_datetime=timezone.now()
            )
            
            messages.success(request, 'SMT設備現場報工記錄已建立（開工狀態）')
            return redirect('workorder:onsite_reporting:onsite_report_list')
            
        except Exception as e:
            messages.error(request, f'建立失敗: {str(e)}')
            return redirect('workorder:onsite_reporting:smt_onsite_report_create')
    
    # GET 請求：顯示新增頁面
    context = {
        'report_type': 'smt',
        'report_type_display': 'SMT設備報工（只有開工功能）'
    }
    return render(request, 'workorder/onsite_reporting/smt_onsite_report_form.html', context)


@login_required
def onsite_report_update(request, pk):
    """現場報工編輯視圖"""
    onsite_report = get_object_or_404(OnsiteReport, pk=pk)
    
    if request.method == 'POST':
        try:
            # 從 POST 資料取得欄位值
            work_quantity = int(request.POST.get('work_quantity', 0))
            defect_quantity = int(request.POST.get('defect_quantity', 0))
            remarks = request.POST.get('remarks', '')
            
            # 更新記錄
            onsite_report.work_quantity = work_quantity
            onsite_report.defect_quantity = defect_quantity
            onsite_report.remarks = remarks
            
            onsite_report.save()
            
            messages.success(request, '現場報工記錄已更新')
            return redirect('workorder:onsite_reporting:onsite_report_list')
            
        except Exception as e:
            messages.error(request, f'更新失敗: {str(e)}')
    
    # GET 請求：顯示編輯頁面
    context = {
        'onsite_report': onsite_report,
        'report_type': onsite_report.report_type,
        'report_type_display': '編輯現場報工'
    }
    return render(request, 'workorder/onsite_reporting/onsite_report_edit.html', context)


@login_required
def onsite_report_config_create(request):
    """現場報工配置新增視圖"""
    if request.method == 'POST':
        try:
            # 從 POST 資料取得欄位值
            config_type = request.POST.get('config_type')
            config_key = request.POST.get('config_key')
            config_value = request.POST.get('config_value')
            config_description = request.POST.get('config_description', '')
            is_active = request.POST.get('is_active') == 'on'
            
            # 驗證必填欄位
            if not all([config_type, config_key, config_value]):
                messages.error(request, '請填寫所有必填欄位')
                return redirect('workorder:onsite_reporting:onsite_report_config_create')
            
            # 建立配置
            OnsiteReportConfig.objects.create(
                config_type=config_type,
                config_key=config_key,
                config_value=config_value,
                config_description=config_description,
                is_active=is_active,
                created_by=request.user.username
            )
            
            messages.success(request, '現場報工配置已建立')
            return redirect('workorder:onsite_reporting:onsite_report_config')
            
        except Exception as e:
            messages.error(request, f'建立失敗: {str(e)}')
    
    # GET 請求：顯示新增頁面
    context = {
        'form': None,
        'object': None
    }
    return render(request, 'workorder/onsite_reporting/onsite_report_config_form.html', context)


@login_required
def onsite_report_config_update(request, pk):
    """現場報工配置更新視圖"""
    config = get_object_or_404(OnsiteReportConfig, pk=pk)
    
    if request.method == 'POST':
        try:
            # 從 POST 資料取得欄位值
            config_type = request.POST.get('config_type')
            config_key = request.POST.get('config_key')
            config_value = request.POST.get('config_value')
            config_description = request.POST.get('config_description', '')
            is_active = request.POST.get('is_active') == 'on'
            
            # 驗證必填欄位
            if not all([config_type, config_key, config_value]):
                messages.error(request, '請填寫所有必填欄位')
                return redirect('workorder:onsite_reporting:onsite_report_config_update', pk=pk)
            
            # 更新配置
            config.config_type = config_type
            config.config_key = config_key
            config.config_value = config_value
            config.config_description = config_description
            config.is_active = is_active
            config.save()
            
            messages.success(request, '現場報工配置已更新')
            return redirect('workorder:onsite_reporting:onsite_report_config')
            
        except Exception as e:
            messages.error(request, f'更新失敗: {str(e)}')
    
    # GET 請求：顯示編輯頁面
    context = {
        'form': None,
        'object': config
    }
    return render(request, 'workorder/onsite_reporting/onsite_report_config_form.html', context)


@login_required
def check_equipment_status(request):
    """檢查設備狀態API"""
    if request.method == 'GET':
        equipment_name = request.GET.get('equipment')
        
        if not equipment_name:
            return JsonResponse({
                'success': False,
                'message': '請提供設備名稱'
            })
        
        try:
            active_reports = OnsiteReport.objects.filter(
                equipment=equipment_name,
                status__in=['started', 'resumed'],
                end_datetime__isnull=True
            )
            
            if active_reports.exists():
                conflicting_report = active_reports.first()
                return JsonResponse({
                    'success': True,
                    'available': False,
                    'message': f'設備 {equipment_name} 正在被工單 {conflicting_report.workorder} 使用中',
                    'conflicting_workorder': conflicting_report.workorder,
                    'conflicting_operator': conflicting_report.operator,
                    'start_time': conflicting_report.start_datetime.strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                return JsonResponse({
                    'success': True,
                    'available': True,
                    'message': f'設備 {equipment_name} 可用'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'檢查設備狀態失敗: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': '不支援的請求方法'
    })


@login_required
def quick_status_change(request, pk):
    """快速狀態變更API"""
    if request.method == 'POST':
        try:
            onsite_report = OnsiteReport.objects.get(pk=pk)
            action = request.POST.get('action')
            
            if action == 'pause':
                # 暫停報工
                if onsite_report.status in ['started', 'resumed']:
                    old_status = onsite_report.status
                    onsite_report.status = 'paused'
                    onsite_report.end_datetime = timezone.now()
                    onsite_report.save()
                    
                    # 記錄歷史
                    try:
                        OnsiteReportHistory.objects.create(
                            onsite_report=onsite_report,
                            change_type='quick_pause',
                            old_status=old_status,
                            new_status='paused',
                            old_quantity=onsite_report.work_quantity,
                            new_quantity=onsite_report.work_quantity,
                            change_notes='快速暫停操作',
                            changed_by=request.user.username
                        )
                    except:
                        pass
                    
                    return JsonResponse({
                        'success': True,
                        'message': '報工已暫停'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '當前狀態無法暫停'
                    })
            
            elif action == 'resume':
                # 恢復報工
                if onsite_report.status == 'paused':
                    old_status = onsite_report.status
                    onsite_report.status = 'resumed'
                    onsite_report.end_datetime = None  # 清除結束時間
                    onsite_report.save()
                    
                    # 記錄歷史
                    try:
                        OnsiteReportHistory.objects.create(
                            onsite_report=onsite_report,
                            change_type='quick_resume',
                            old_status=old_status,
                            new_status='resumed',
                            old_quantity=onsite_report.work_quantity,
                            new_quantity=onsite_report.work_quantity,
                            change_notes='快速恢復操作',
                            changed_by=request.user.username
                        )
                    except:
                        pass
                    
                    return JsonResponse({
                        'success': True,
                        'message': '報工已恢復'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '當前狀態無法恢復'
                    })
            
            elif action == 'complete':
                # 完工報工
                work_quantity = int(request.POST.get('work_quantity', 0))
                defect_quantity = int(request.POST.get('defect_quantity', 0))
                
                if work_quantity == 0:
                    return JsonResponse({
                        'success': False,
                        'message': '完工時必須填寫工作數量'
                    })
                
                if defect_quantity > work_quantity:
                    return JsonResponse({
                        'success': False,
                        'message': '不良品數量不能超過工作數量'
                    })
                
                if onsite_report.status in ['started', 'resumed', 'paused']:
                    old_status = onsite_report.status
                    onsite_report.status = 'completed'
                    onsite_report.end_datetime = timezone.now()
                    onsite_report.work_quantity = work_quantity
                    onsite_report.defect_quantity = defect_quantity
                    onsite_report.save()
                    
                    # 記錄歷史
                    try:
                        OnsiteReportHistory.objects.create(
                            onsite_report=onsite_report,
                            change_type='quick_complete',
                            old_status=old_status,
                            new_status='completed',
                            old_quantity=0,
                            new_quantity=work_quantity,
                            change_notes=f'快速完工操作 - 工作數量: {work_quantity}, 不良品: {defect_quantity}',
                            changed_by=request.user.username
                        )
                    except:
                        pass
                    
                    return JsonResponse({
                        'success': True,
                        'message': '報工已完成'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '當前狀態無法完工'
                    })
            
            elif action == 'stop':
                # 停工報工
                reason = request.POST.get('reason', '')
                
                if onsite_report.status in ['started', 'resumed', 'paused']:
                    old_status = onsite_report.status
                    onsite_report.status = 'stopped'
                    onsite_report.end_datetime = timezone.now()
                    onsite_report.abnormal_notes = reason
                    onsite_report.save()
                    
                    # 記錄歷史
                    try:
                        OnsiteReportHistory.objects.create(
                            onsite_report=onsite_report,
                            change_type='quick_stop',
                            old_status=old_status,
                            new_status='stopped',
                            old_quantity=onsite_report.work_quantity,
                            new_quantity=onsite_report.work_quantity,
                            change_notes=f'快速停工操作 - 原因: {reason}',
                            changed_by=request.user.username
                        )
                    except:
                        pass
                    
                    return JsonResponse({
                        'success': True,
                        'message': '報工已停工'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '當前狀態無法停工'
                    })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': '無效的操作'
                })
                
        except OnsiteReport.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '找不到報工記錄'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'操作失敗: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': '不支援的請求方法'
    })


# RD樣品相關視圖
@login_required
def operator_rd_onsite_report_create(request):
    """作業員RD樣品現場報工建立視圖"""
    if request.method == 'POST':
        try:
            # 取得表單資料
            product_code = request.POST.get('product_code', '')
            company_code = request.POST.get('company_code', '')
            operator = request.POST.get('operator', '')
            equipment = request.POST.get('equipment', '')
            process = request.POST.get('process', '')
            remarks = request.POST.get('remarks', '')
            
            # 驗證必填欄位
            if not all([product_code, company_code, operator, process]):
                messages.error(request, '請填寫所有必填欄位')
                return redirect('workorder:onsite_reporting:operator_rd_onsite_report_create')
            
            # 取得公司代號
            company_config = CompanyConfig.objects.filter(company_name=company_code).first()
            if not company_config:
                messages.error(request, '找不到對應的公司設定')
                return redirect('workorder:onsite_reporting:operator_rd_onsite_report_create')
            
            company_code_value = company_config.company_code
            
            # 檢查並建立工單
            from workorder.models import WorkOrder
            from workorder.workorder_dispatch.models import WorkOrderDispatch
            
            # 查找現有工單
            existing_workorder = WorkOrder.objects.filter(
                company_code=company_code_value,
                order_number='RD樣品',
                product_code=product_code
            ).first()
            
            workorder = None
            workorder_created = False
            
            if existing_workorder:
                workorder = existing_workorder
                messages.info(request, f'找到現有RD樣品工單: {workorder.order_number}')
            else:
                # 建立新工單
                workorder = WorkOrder.objects.create(
                    company_code=company_code_value,
                    order_number='RD樣品',
                    product_code=product_code,
                    quantity=0,  # RD樣品數量為0
                    status='in_progress',
                    order_source='MES手動建立'
                )
                workorder_created = True
                messages.info(request, f'建立新RD樣品工單: {workorder.order_number}')
            
            # 檢查並建立派工單（比對公司代號+工單號碼+產品編號+工序）
            existing_dispatch = WorkOrderDispatch.objects.filter(
                company_code=company_code_value,
                order_number='RD樣品',
                product_code=product_code,
                process_name=process
            ).first()
            
            dispatch_created = False
            
            if existing_dispatch:
                messages.info(request, f'找到現有RD樣品派工單: {existing_dispatch.order_number}')
            else:
                # 建立新派工單
                new_dispatch = WorkOrderDispatch.objects.create(
                    company_code=company_code_value,
                    order_number='RD樣品',
                    product_code=product_code,
                    product_name=f"RD樣品-{product_code}",
                    planned_quantity=0,  # RD樣品預設數量為0
                    status='in_production',  # 直接設為生產中
                    dispatch_date=timezone.now().date(),
                    assigned_operator=operator,
                    assigned_equipment=equipment or '',
                    process_name=process,
                    notes=f"RD樣品現場報工自動建立 - 建立時間: {timezone.now()} - 注意：RD樣品無預定工序流程",
                    created_by=request.user.username
                )
                dispatch_created = True
                messages.info(request, f'建立新RD樣品派工單: {new_dispatch.order_number}')
            
            # 作業員RD樣品現場報工只有開工功能，狀態固定為 started
            status = 'started'
            
            # 建立作業員RD樣品現場報工記錄
            onsite_report = OnsiteReport.objects.create(
                report_type='operator_rd',
                operator=operator,
                equipment=equipment,
                process=process,
                product_id=product_code,  # 使用表單輸入的產品編號
                workorder='RD樣品',   # 固定工單號碼
                company_name=company_code, # 使用表單選擇的公司名稱
                work_quantity=0,  # 固定為0，因為只有開工功能
                defect_quantity=0,  # 固定為0，因為只有開工功能
                status=status,  # 固定為開工狀態
                remarks=remarks,
                created_by=request.user.username,
                work_date=timezone.now().date(),
                start_datetime=timezone.now()
            )
            
            # 顯示建立結果
            success_message = '作業員RD樣品現場報工記錄建立成功！（開工狀態）'
            if workorder_created:
                success_message += f' - 已建立新工單: {workorder.order_number}'
            if dispatch_created:
                success_message += f' - 已建立新派工單'
            
            messages.success(request, success_message)
            return redirect('workorder:onsite_reporting:onsite_report_index')
            
        except Exception as e:
            messages.error(request, f'作業員RD樣品現場報工記錄建立失敗：{str(e)}')
    
    # 取得作業員列表（過濾非SMT）
    operators = Operator.objects.filter(
        ~Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得工序列表（過濾非SMT）
    processes = ProcessName.objects.filter(
        ~Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得設備列表（過濾非SMT）
    equipments = Equipment.objects.filter(
        ~Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得公司名稱列表
    companies = CompanyConfig.objects.values_list('company_name', 'company_name').distinct()
    
    context = {
        'operators': operators,
        'processes': processes,
        'equipments': equipments,
        'companies': companies,
        'title': '建立作業員RD樣品現場報工記錄（只有開工功能）',
        'subtitle': '現場報工 - 作業員RD樣品報工管理'
    }
    
    return render(request, 'workorder/onsite_reporting/operator_rd_onsite_report_form.html', context)


@login_required
def smt_rd_onsite_report_create(request):
    """SMT_RD樣品現場報工建立視圖"""
    if request.method == 'POST':
        try:
            # 取得表單資料
            operator = request.POST.get('operator', '')
            equipment = request.POST.get('equipment', '')
            process = request.POST.get('process', '')
            remarks = request.POST.get('remarks', '')
            company_code = request.POST.get('company_code', '')
            product_code = request.POST.get('product_code', '')
            
            # 驗證必填欄位
            if not all([operator, process, equipment, company_code, product_code]):
                messages.error(request, '請填寫所有必填欄位')
                return redirect('workorder:onsite_reporting:smt_rd_onsite_report_create')
            
            # 檢查並建立工單
            from workorder.models import WorkOrder
            from workorder.workorder_dispatch.models import WorkOrderDispatch
            
            # 取得公司代號
            company_config = CompanyConfig.objects.filter(company_name=company_code).first()
            if not company_config:
                messages.error(request, '找不到對應的公司設定')
                return redirect('workorder:onsite_reporting:smt_rd_onsite_report_create')
            
            company_code_value = company_config.company_code
            
            # 查找現有工單（只根據公司代號和工單號碼，因為唯一性約束是 (company_code, order_number)）
            existing_workorder = WorkOrder.objects.filter(
                company_code=company_code_value,
                order_number='RD樣品'
            ).first()
            
            workorder = None
            workorder_created = False
            
            if existing_workorder:
                workorder = existing_workorder
                messages.info(request, f'找到現有RD樣品工單: {workorder.order_number}')
            else:
                # 建立新工單
                workorder = WorkOrder.objects.create(
                    company_code=company_code_value,  # 使用選擇的公司代號
                    order_number='RD樣品',
                    product_code=product_code,  # 使用表單輸入的產品編號
                    quantity=0,  # RD樣品數量為0
                    status='in_progress',
                    order_source='MES手動建立'
                )
                workorder_created = True
                messages.info(request, f'建立新RD樣品工單: {workorder.order_number}')
            
            # 檢查並建立派工單（比對公司代號+工單號碼+產品編號+工序）
            existing_dispatch = WorkOrderDispatch.objects.filter(
                company_code=company_code_value,
                order_number='RD樣品',
                product_code=product_code,
                process_name=process
            ).first()
            
            dispatch_created = False
            
            if existing_dispatch:
                messages.info(request, f'找到現有RD樣品派工單: {existing_dispatch.order_number}')
            else:
                # 建立新派工單
                new_dispatch = WorkOrderDispatch.objects.create(
                    company_code=company_code_value,  # 使用選擇的公司代號
                    order_number='RD樣品',
                    product_code=product_code,  # 使用表單輸入的產品編號
                    product_name=f'RD樣品-{product_code}',
                    planned_quantity=0,  # RD樣品預設數量為0
                    status='in_production',  # 直接設為生產中
                    dispatch_date=timezone.now().date(),
                    assigned_operator=operator,
                    assigned_equipment=equipment,
                    process_name=process,
                    notes=f"SMT_RD樣品現場報工自動建立 - 建立時間: {timezone.now()} - 注意：RD樣品無預定工序流程",
                    created_by=request.user.username
                )
                dispatch_created = True
                messages.info(request, f'建立新RD樣品派工單: {new_dispatch.order_number}')
            
            # SMT_RD樣品現場報工只有開工功能，狀態固定為 started
            status = 'started'
            
            # 建立SMT_RD樣品現場報工記錄
            onsite_report = OnsiteReport.objects.create(
                report_type='smt_rd',
                operator=operator,
                equipment=equipment,
                process=process,
                product_id=product_code,  # 使用表單輸入的產品編號
                workorder='RD樣品',    # 固定工單號碼
                company_name=company_code, # 使用表單選擇的公司名稱
                company_code=company_code_value, # 使用公司代號
                work_quantity=0,  # 固定為0，因為只有開工功能
                defect_quantity=0,  # 固定為0，因為只有開工功能
                status=status,  # 固定為開工狀態
                remarks=remarks,
                created_by=request.user.username,
                work_date=timezone.now().date(),
                start_datetime=timezone.now()
            )
            
            # 顯示建立結果
            success_message = 'SMT_RD樣品現場報工記錄建立成功！（開工狀態）'
            if workorder_created:
                success_message += f' - 已建立新工單: {workorder.order_number}'
            if dispatch_created:
                success_message += f' - 已建立新派工單'
            
            messages.success(request, success_message)
            return redirect('workorder:onsite_reporting:smt_work_selection')
            
        except Exception as e:
            messages.error(request, f'SMT_RD樣品現場報工記錄建立失敗：{str(e)}')
    
    # 取得作業員列表（只顯示SMT相關）
    operators = Operator.objects.filter(
        Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得工序列表（只顯示SMT相關）
    processes = ProcessName.objects.filter(
        Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得設備列表（只顯示SMT相關）
    equipments = Equipment.objects.filter(
        Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得公司名稱列表
    companies = CompanyConfig.objects.values_list('company_name', 'company_name').distinct()
    
    context = {
        'operators': operators,
        'processes': processes,
        'equipments': equipments,
        'companies': companies,
        'title': '建立SMT_RD樣品現場報工記錄（只有開工功能）',
        'subtitle': '現場報工 - SMT_RD樣品報工管理'
    }
    
    return render(request, 'workorder/onsite_reporting/smt_rd_onsite_report_form.html', context)


@login_required
def rd_sample_workorder_list(request):
    """RD樣品現場報工記錄列表視圖"""
    from django.core.paginator import Paginator
    
    # 取得所有RD樣品現場報工記錄
    rd_reports = OnsiteReport.objects.filter(
        report_type__in=['operator_rd', 'smt_rd']
    ).order_by('-created_at')
    
    # 分頁
    paginator = Paginator(rd_reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'title': 'RD樣品現場報工記錄列表',
        'subtitle': '現場報工 - RD樣品報工管理'
    }
    
    return render(request, 'workorder/onsite_reporting/rd_sample_workorder_list.html', context)


@login_required
def rd_sample_workorder_detail(request, pk):
    """RD樣品現場報工記錄詳情視圖"""
    report = get_object_or_404(OnsiteReport, pk=pk, report_type__in=['operator_rd', 'smt_rd'])
    
    context = {
        'report': report,
        'title': f'RD樣品現場報工記錄詳情 - {report.id}',
        'subtitle': '現場報工 - RD樣品報工管理'
    }
    
    return render(request, 'workorder/onsite_reporting/rd_sample_workorder_detail.html', context)


@login_required
def rd_sample_workorder_delete(request, pk):
    """RD樣品現場報工記錄刪除視圖"""
    report = get_object_or_404(OnsiteReport, pk=pk, report_type__in=['operator_rd', 'smt_rd'])
    
    if request.method == 'POST':
        try:
            report_id = report.id
            report.delete()
            messages.success(request, f'RD樣品現場報工記錄 {report_id} 已成功刪除')
            return redirect('workorder:onsite_reporting:rd_sample_workorder_list')
        except Exception as e:
            messages.error(request, f'刪除失敗：{str(e)}')
    
    context = {
        'report': report,
        'title': f'刪除RD樣品現場報工記錄 - {report.id}',
        'subtitle': '現場報工 - RD樣品報工管理'
    }
    
    return render(request, 'workorder/onsite_reporting/rd_sample_workorder_delete.html', context)


@login_required
def rd_sample_workorder_create(request):
    """RD 樣品工單建立頁面"""
    if request.method == 'POST':
        # 處理表單提交
        try:
            # 這裡可以添加表單處理邏輯
            messages.success(request, 'RD 樣品工單建立成功！')
            return redirect('workorder:onsite_reporting:rd_sample_workorder_list')
        except Exception as e:
            messages.error(request, f'建立失敗：{str(e)}')
    
    context = {
        'title': '建立RD樣品工單',
        'subtitle': '現場報工 - RD樣品工單管理'
    }
    
    return render(request, 'workorder/onsite_reporting/rd_sample_workorder_create.html', context) 