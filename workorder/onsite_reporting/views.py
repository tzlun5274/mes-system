"""
現場報工子模組 - 視圖定義
負責現場報工的網頁視圖和表單處理
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Max
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from datetime import datetime, date, timedelta
import json

from .models import OnsiteReport, OnsiteReportHistory, OnsiteReportConfig
# 移除表單依賴，直接在模板中設計欄位


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
                            Q(order_number__icontains=search) |
            Q(product_code__icontains=search) |
            Q(company_code__icontains=search)
            )
        
        # 報工類型篩選
        report_type = self.request.GET.get("report_type", "")
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        # 狀態篩選
        status = self.request.GET.get("status", "")
        if status:
            queryset = queryset.filter(status=status)
        
        # 公司篩選
        company_code = self.request.GET.get("company_code", "")
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
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
        
        # 搜尋表單（暫時移除，待後續實作）
        
        # 統計資料
        queryset = self.get_queryset()
        context['total_count'] = queryset.count()
        context['active_count'] = queryset.filter(status__in=['started', 'resumed']).count()
        context['completed_count'] = queryset.filter(status='completed').count()
        context['stopped_count'] = queryset.filter(status='stopped').count()
        
        return context


class OnsiteReportDetailView(LoginRequiredMixin, DetailView):
    """現場報工詳情視圖"""
    
    model = OnsiteReport
    template_name = "workorder/onsite_reporting/onsite_report_detail.html"
    context_object_name = "onsite_report"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得歷史記錄
        context['history'] = OnsiteReportHistory.objects.filter(
            onsite_report=self.object
        ).order_by('-changed_at')
        
        # 計算進度
        context['progress_percentage'] = self.object.get_progress_percentage()
        context['duration_minutes'] = self.object.get_duration_minutes()
        
        return context


@login_required
def operator_onsite_report_create(request):
    """作業員現場報工新增視圖"""
    if request.method == 'POST':
        try:
            # 從 POST 資料取得欄位值
            report_type = 'operator'
            operator = request.POST.get('operator')
            order_number = request.POST.get('order_number')
            product_code = request.POST.get('product_code')
            company_code = request.POST.get('company_code')
            process = request.POST.get('process')
            equipment = request.POST.get('equipment', '')
            status = request.POST.get('status', 'started')  # 新增狀態欄位
            planned_quantity = int(request.POST.get('planned_quantity', 0))
            remarks = request.POST.get('remarks', '')
            
            # 驗證必填欄位
            if not all([operator, order_number, product_code, company_code, process]):
                messages.error(request, '請填寫所有必填欄位')
                return redirect('workorder:onsite_reporting:operator_onsite_report_create')
            
            # 設定公司代號（如果沒有提供）
            if not company_code:
                try:
                    from erp_integration.models import CompanyConfig
                    company_config = CompanyConfig.objects.filter(
                        company_code=company_code
                    ).first()
                    if company_config:
                        company_code = company_config.company_code
                except Exception:
                    pass
            
            # 計算開始數量
            previous_reports = OnsiteReport.objects.filter(
                operator=operator,
                order_number=order_number,
                product_code=product_code,
                status='completed'
            ).order_by('-end_datetime')
            
            start_quantity = 0
            if previous_reports.exists():
                last_report = previous_reports.first()
                start_quantity = last_report.work_quantity
            
            # 自動檢查並加入工序到工單
            auto_process_result = OnsiteReportAutoProcessService.check_and_add_process(
                workorder_number=workorder,
                process_name=process,
                operator=operator,
                equipment=equipment
            )
            
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
                status=status,  # 新增狀態欄位
                planned_quantity=planned_quantity,
                work_quantity=0,  # 初始工作數量為0
                remarks=remarks,
                created_by=request.user.username,
                work_date=timezone.now().date(),
                start_datetime=timezone.now()
            )
            
            # 根據自動加入工序的結果顯示訊息
            if auto_process_result['success']:
                if auto_process_result.get('already_exists', False):
                    messages.success(request, '作業員現場報工記錄已建立')
                else:
                    messages.success(request, f'作業員現場報工記錄已建立，並已自動將工序 {process} 加入到工單 {order_number}')
            else:
                messages.warning(request, f'作業員現場報工記錄已建立，但自動加入工序失敗：{auto_process_result["message"]}')
            return redirect('workorder:onsite_reporting:onsite_report_list')
            
        except Exception as e:
            messages.error(request, f'建立失敗: {str(e)}')
            return redirect('workorder:onsite_reporting:operator_onsite_report_create')
    
    # GET 請求：顯示新增頁面
    context = {
        'report_type': 'operator',
        'report_type_display': '作業員報工'
    }
    return render(request, 'workorder/onsite_reporting/operator_onsite_report_form.html', context)


@login_required
def smt_onsite_report_create(request):
    """SMT設備現場報工新增視圖"""
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
            status = request.POST.get('status', 'started')  # 新增狀態欄位
            planned_quantity = int(request.POST.get('planned_quantity', 0))
            remarks = request.POST.get('remarks', '')
            
            # 驗證必填欄位
            if not all([operator, workorder, product_id, company_name, process, equipment]):
                messages.error(request, '請填寫所有必填欄位（SMT設備報工需要選擇設備）')
                return redirect('workorder:onsite_reporting:smt_onsite_report_create')
            
            # 設定公司代號
            company_code = None
            try:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_name=company_name
                ).first()
                if company_config:
                    company_code = company_config.company_code
            except Exception:
                pass
            
            # 計算開始數量
            previous_reports = OnsiteReport.objects.filter(
                operator=operator,
                workorder=workorder,
                product_id=product_id,
                status='completed'
            ).order_by('-end_datetime')
            
            start_quantity = 0
            if previous_reports.exists():
                last_report = previous_reports.first()
                start_quantity = last_report.work_quantity
            
            # 自動檢查並加入工序到工單
            auto_process_result = OnsiteReportAutoProcessService.check_and_add_process(
                workorder_number=workorder,
                process_name=process,
                operator=operator,
                equipment=equipment
            )
            
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
                status=status,  # 新增狀態欄位
                planned_quantity=planned_quantity,
                work_quantity=0,  # 初始工作數量為0
                remarks=remarks,
                created_by=request.user.username,
                work_date=timezone.now().date(),
                start_datetime=timezone.now()
            )
            
            # 根據自動加入工序的結果顯示訊息
            if auto_process_result['success']:
                if auto_process_result.get('already_exists', False):
                    messages.success(request, 'SMT設備現場報工記錄已建立')
                else:
                    messages.success(request, f'SMT設備現場報工記錄已建立，並已自動將工序 {process} 加入到工單 {workorder}')
            else:
                messages.warning(request, f'SMT設備現場報工記錄已建立，但自動加入工序失敗：{auto_process_result["message"]}')
            return redirect('workorder:onsite_reporting:onsite_report_list')
            
        except Exception as e:
            messages.error(request, f'建立失敗: {str(e)}')
            return redirect('workorder:onsite_reporting:smt_onsite_report_create')
    
    # GET 請求：顯示新增頁面
    context = {
        'report_type': 'smt',
        'report_type_display': 'SMT設備報工'
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
            
            # 如果有結束時間，計算工作分鐘數（但不儲存到 work_minutes 欄位）
            if onsite_report.end_datetime:
                duration = onsite_report.end_datetime - onsite_report.start_datetime
                # onsite_report.work_minutes = int(duration.total_seconds() / 60)  # 暫時註解掉
            
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


class OnsiteReportConfigDeleteView(LoginRequiredMixin, DeleteView):
    """現場報工配置刪除視圖"""
    
    model = OnsiteReportConfig
    template_name = "workorder/onsite_reporting/onsite_report_config_confirm_delete.html"
    success_url = reverse_lazy('workorder:onsite_reporting:onsite_report_config')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '現場報工配置已刪除')
        return super().delete(request, *args, **kwargs)


# API 視圖
@require_POST
@login_required
def update_onsite_report_status(request, pk):
    """更新現場報工狀態 API"""
    try:
        onsite_report = get_object_or_404(OnsiteReport, pk=pk)
        data = json.loads(request.body)

        old_status = onsite_report.status
        old_quantity = onsite_report.work_quantity

        # 更新狀態
        if 'status' in data:
            onsite_report.status = data['status']

        # 更新數量
        if 'work_quantity' in data:
            onsite_report.work_quantity = data['work_quantity']

        # 更新不良品數量
        if 'defect_quantity' in data:
            onsite_report.defect_quantity = data['defect_quantity']

        # 如果完成，設定結束時間
        if onsite_report.status == 'completed' and not onsite_report.end_datetime:
            onsite_report.end_datetime = timezone.now()

        onsite_report.save()

        # 記錄歷史
        if old_status != onsite_report.status or old_quantity != onsite_report.work_quantity:
            change_type = 'update'
            if onsite_report.status == 'completed':
                change_type = 'complete'
            elif onsite_report.status == 'abnormal':
                change_type = 'abnormal'

            OnsiteReportHistory.objects.create(
                onsite_report=onsite_report,
                change_type=change_type,
                old_status=old_status,
                new_status=onsite_report.status,
                old_quantity=old_quantity,
                new_quantity=onsite_report.work_quantity,
                change_notes=f"API更新 - {request.user.username}",
                changed_by=request.user.username
            )

        return JsonResponse({
            'success': True,
            'message': '狀態更新成功',
            'data': {
                'id': onsite_report.id,
                'status': onsite_report.status,
                'work_quantity': onsite_report.work_quantity,
                'defect_quantity': onsite_report.defect_quantity,
                'progress_percentage': onsite_report.get_progress_percentage(),
                'updated_at': onsite_report.updated_at.isoformat()
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'更新失敗: {str(e)}'
        }, status=400)


@require_POST
@login_required
def complete_onsite_report(request, pk):
    """完成現場報工 API"""
    try:
        onsite_report = get_object_or_404(OnsiteReport, pk=pk)
        
        # 從請求中取得工作數量和不良品數量
        work_quantity = int(request.POST.get('work_quantity', 0))
        defect_quantity = int(request.POST.get('defect_quantity', 0))

        old_status = onsite_report.status
        onsite_report.complete_work(work_quantity, defect_quantity)

        # 記錄歷史
        OnsiteReportHistory.objects.create(
            onsite_report=onsite_report,
            change_type='complete',
            old_status=old_status,
            new_status='completed',
            old_quantity=0,
            new_quantity=onsite_report.work_quantity,
            change_notes=f"完成報工 - {request.user.username}",
            changed_by=request.user.username
        )

        return JsonResponse({
            'success': True,
            'message': '報工已完成',
            'data': {
                'id': onsite_report.id,
                'status': onsite_report.status,
                'work_minutes': onsite_report.get_duration_minutes(),
                'work_quantity': onsite_report.work_quantity,
                'defect_quantity': onsite_report.defect_quantity
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'完成失敗: {str(e)}'
        }, status=400)


@require_POST
@login_required
def resume_onsite_report(request, pk):
    """恢復現場報工 API"""
    try:
        onsite_report = get_object_or_404(OnsiteReport, pk=pk)

        old_status = onsite_report.status
        onsite_report.resume_work()

        # 記錄歷史
        OnsiteReportHistory.objects.create(
            onsite_report=onsite_report,
            change_type='resume',
            old_status=old_status,
            new_status='resumed',
            old_quantity=onsite_report.work_quantity,
            new_quantity=onsite_report.work_quantity,
            change_notes=f"恢復報工 - {request.user.username}",
            changed_by=request.user.username
        )

        return JsonResponse({
            'success': True,
            'message': '報工已恢復',
            'data': {
                'id': onsite_report.id,
                'status': onsite_report.status,
                'total_work_minutes': onsite_report.get_duration_minutes(),
                'work_minutes': onsite_report.work_minutes,
                'updated_at': onsite_report.updated_at.isoformat()
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'恢復失敗: {str(e)}'
        }, status=400)


@require_POST
@login_required
def pause_onsite_report(request, pk):
    """暫停現場報工 API"""
    try:
        onsite_report = get_object_or_404(OnsiteReport, pk=pk)
        pause_reason = request.POST.get('pause_reason', '')

        old_status = onsite_report.status
        onsite_report.pause_work()

        # 記錄歷史
        OnsiteReportHistory.objects.create(
            onsite_report=onsite_report,
            change_type='pause',
            old_status=old_status,
            new_status='paused',
            old_quantity=onsite_report.work_quantity,
            new_quantity=onsite_report.work_quantity,
            change_notes=f"暫停報工 - {request.user.username}",
            changed_by=request.user.username
        )

        return JsonResponse({
            'success': True,
            'message': '報工已暫停'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'暫停失敗: {str(e)}'
        }, status=400)





# 動態載入API
@login_required
def product_list_api(request):
    """產品編號列表 API - 使用 WorkOrderDispatch 模型以保持與填報功能一致"""
    try:
        from workorder.workorder_dispatch.models import WorkOrderDispatch
        
        company_name = request.GET.get('company_name', '')
        
        if company_name:
            # 根據公司代號篩選產品編號
            products = WorkOrderDispatch.objects.filter(
                company_code=company_name
            ).values('product_code').distinct().order_by('product_code')
        else:
            # 取得所有產品編號
            products = WorkOrderDispatch.objects.values('product_code').distinct().order_by('product_code')
        
        # 格式化資料
        product_list = []
        for product in products:
            product_list.append({
                'product_code': product['product_code']
            })
        
        return JsonResponse({
            'success': True,
            'products': product_list
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'載入失敗: {str(e)}'
        }, status=400)


# 現場報工的獨立API函數已移除，統一使用 /workorder/api/ 路徑的統一API


# ==================== RD樣品工單建立功能 ====================

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
@login_required
def operator_rd_onsite_report_create(request):
    """
    作業員RD樣品現場報工建立視圖
    用於在現場報工模組中建立作業員RD樣品現場報工記錄
    第一筆記錄時自動建立工單
    """
    from .models import OnsiteReport
    from workorder.models import WorkOrder
    from django.contrib import messages
    from django.shortcuts import render, redirect
    from django.db.models import Q
    from django.db import transaction
    from django.utils import timezone
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 取得表單資料
                operator = request.POST.get('operator', '')
                equipment = request.POST.get('equipment', '')
                process = request.POST.get('process', '')
                work_quantity = request.POST.get('work_quantity', 0)
                defect_quantity = request.POST.get('defect_quantity', 0)
                status = request.POST.get('status', 'started')
                remarks = request.POST.get('remarks', '')
                abnormal_notes = request.POST.get('abnormal_notes', '')
                company_code = request.POST.get('company_code', '')
                product_code = request.POST.get('product_code', 'PFP-CCT')  # 從表單取得產品編號
                order_number = request.POST.get('order_number', 'RD樣品')   # 從表單取得工單號碼
                
                # 驗證必填欄位
                if not all([operator, process, status]):
                    messages.error(request, '請填寫所有必填欄位')
                    return redirect('workorder:onsite_reporting:operator_rd_onsite_report_create')
                
                # 檢查是否已有RD樣品工單，如果沒有則自動建立
                rd_workorder = WorkOrder.objects.filter(
                    product_id='PFP-CCT',
                    workorder='RD樣品',
                    company_name='RD樣品'
                ).first()
                
                if not rd_workorder:
                    # 自動建立RD樣品工單
                    rd_workorder = WorkOrder.objects.create(
                        product_id='PFP-CCT',
                        workorder='RD樣品',
                        company_name='RD樣品',
                        planned_quantity=0,  # RD樣品無預設數量
                        order_source='mes',
                        status='pending',
                        created_by=request.user
                    )
                    messages.info(request, '已自動建立RD樣品工單')
                
                # 建立作業員RD樣品現場報工記錄
                onsite_report = OnsiteReport.objects.create(
                    report_type='operator_rd',
                    operator=operator,
                    equipment=equipment,
                    process=process,
                    product_code='PFP-CCT',  # 固定產品編號
                    order_number='RD樣品',   # 固定工單號碼
                    company_code=company_code,
                    work_quantity=int(work_quantity) if work_quantity else 0,
                    defect_quantity=int(defect_quantity) if defect_quantity else 0,
                    status=status,
                    remarks=remarks,
                    abnormal_notes=abnormal_notes,
                    created_by=request.user.username,
                    work_date=timezone.now().date(),
                    start_datetime=timezone.now()
                )
                
                messages.success(request, '作業員RD樣品現場報工記錄建立成功！')
                return redirect('workorder:onsite_reporting:onsite_report_index')
                
        except Exception as e:
            messages.error(request, f'作業員RD樣品現場報工記錄建立失敗：{str(e)}')
    
    # 取得作業員列表（過濾非SMT）
    from process.models import Operator
    operators = Operator.objects.filter(
        ~Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得工序列表（過濾非SMT）
    from process.models import ProcessName
    processes = ProcessName.objects.filter(
        ~Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得設備列表（過濾非SMT）
    from equip.models import Equipment
    equipments = Equipment.objects.filter(
        ~Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得公司名稱列表
    from erp_integration.models import CompanyConfig
    companies = CompanyConfig.objects.values_list('company_name', 'company_name').distinct()
    
    context = {
        'operators': operators,
        'processes': processes,
        'equipments': equipments,
        'companies': companies,
        'title': '建立作業員RD樣品現場報工記錄',
        'subtitle': '現場報工 - 作業員RD樣品報工管理'
    }
    
    return render(request, 'workorder/onsite_reporting/operator_rd_onsite_report_form.html', context)


@login_required
def smt_rd_onsite_report_create(request):
    """
    SMT_RD樣品現場報工建立視圖
    用於在現場報工模組中建立SMT_RD樣品現場報工記錄
    第一筆記錄時自動建立工單
    """
    from .models import OnsiteReport
    from workorder.models import WorkOrder
    from django.contrib import messages
    from django.http import JsonResponse
    from django.db.models import Q
    from django.db import transaction
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 取得表單資料
                operator = request.POST.get('operator', '')
                equipment = request.POST.get('equipment', '')
                process = request.POST.get('process', '')
                work_quantity = request.POST.get('work_quantity', 0)
                defect_quantity = request.POST.get('defect_quantity', 0)
                status = request.POST.get('status', 'start')
                notes = request.POST.get('notes', '')
                abnormal_record = request.POST.get('abnormal_record', '')
                
                # 檢查是否已有RD樣品工單，如果沒有則自動建立
                rd_workorder = WorkOrder.objects.filter(
                    product_id='PFP-CCT',
                    workorder='RD樣品',
                    company_name='RD樣品'
                ).first()
                
                if not rd_workorder:
                    # 自動建立RD樣品工單
                    rd_workorder = WorkOrder.objects.create(
                        product_id='PFP-CCT',
                        workorder='RD樣品',
                        company_name='RD樣品',
                        planned_quantity=100,  # 預設數量
                        order_source='mes',
                        status='pending',
                        created_by=request.user
                    )
                    messages.info(request, '已自動建立RD樣品工單')
                
                # 建立SMT_RD樣品現場報工記錄
                onsite_report = OnsiteReport.objects.create(
                    report_type='smt_rd',
                    operator=operator,
                    equipment=equipment,
                    process=process,
                    product_id='PFP-CCT',  # 固定產品編號
                    workorder='RD樣品',    # 固定工單號碼
                    company_name='RD樣品', # 固定公司名稱
                    work_quantity=int(work_quantity) if work_quantity else 0,
                    defect_quantity=int(defect_quantity) if defect_quantity else 0,
                    status=status,
                    remarks=notes,
                    abnormal_notes=abnormal_record,
                    created_by=request.user.username,
                    work_date=timezone.now().date(),
                    start_datetime=timezone.now()
                )
                
                messages.success(request, f'SMT_RD樣品現場報工記錄建立成功！')
                return redirect('workorder:onsite_reporting:smt_work_selection')
                
        except Exception as e:
            messages.error(request, f'SMT_RD樣品現場報工記錄建立失敗：{str(e)}')
    
    # 取得作業員列表（只顯示SMT相關）
    from process.models import Operator
    operators = Operator.objects.filter(
        Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得工序列表（只顯示SMT相關）
    from process.models import ProcessName
    processes = ProcessName.objects.filter(
        Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得設備列表（只顯示SMT相關）
    from equip.models import Equipment
    equipments = Equipment.objects.filter(
        Q(name__icontains='SMT')
    ).values_list('name', flat=True).distinct()
    
    # 取得公司名稱列表
    from erp_integration.models import CompanyConfig
    companies = CompanyConfig.objects.values_list('company_name', 'company_name').distinct()
    
    context = {
        'operators': operators,
        'processes': processes,
        'equipments': equipments,
        'companies': companies,
        'title': '建立SMT_RD樣品現場報工記錄',
        'subtitle': '現場報工 - SMT_RD樣品報工管理'
    }
    
    return render(request, 'workorder/onsite_reporting/smt_rd_onsite_report_form.html', context)


@login_required
def rd_sample_workorder_list(request):
    """
    RD樣品現場報工記錄列表視圖
    顯示所有RD樣品現場報工記錄
    """
    from .models import OnsiteReport
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
    """
    RD樣品現場報工記錄詳情視圖
    顯示RD樣品現場報工記錄的詳細資訊
    """
    from .models import OnsiteReport
    from django.shortcuts import get_object_or_404
    
    report = get_object_or_404(OnsiteReport, pk=pk, report_type__in=['operator_rd', 'smt_rd'])
    
    context = {
        'report': report,
        'title': f'RD樣品現場報工記錄詳情 - {report.id}',
        'subtitle': '現場報工 - RD樣品報工管理'
    }
    
    return render(request, 'workorder/onsite_reporting/rd_sample_workorder_detail.html', context)


@login_required
def rd_sample_workorder_delete(request, pk):
    """
    RD樣品現場報工記錄刪除視圖
    刪除RD樣品現場報工記錄
    """
    from .models import OnsiteReport
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    
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
    """
    RD 樣品工單建立頁面
    提供 RD 樣品工單的建立介面
    """
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

# ==================== 自動加入工序功能 ====================

@login_required
def auto_add_process_to_workorder(request):
    """
    自動加入工序到工單的 API
    當現場報工時發現工單中沒有的工序，自動將該工序加入到工單中
    """
    from workorder.models import WorkOrder, WorkOrderProcess
    from django.http import JsonResponse
    import json
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            workorder_number = data.get('workorder_number')
            process_name = data.get('process_name')
            operator = data.get('operator')
            equipment = data.get('equipment', '')
            
            if not all([workorder_number, process_name]):
                return JsonResponse({
                    'success': False,
                    'message': '工單號碼和工序名稱不能為空'
                }, status=400)
            
            # 查找工單
            try:
                # 使用多公司架構唯一識別查詢工單
                workorder = WorkOrder.objects.filter(order_number=workorder_number).first()
                if not workorder:
                    return JsonResponse({
                        'success': False,
                        'message': f'找不到工單：{workorder_number}'
                    }, status=404)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'查詢工單失敗：{str(e)}'
                }, status=500)
            
            # 檢查工序是否已存在
            existing_process = WorkOrderProcess.objects.filter(
                workorder=workorder,
                process_name=process_name
            ).first()
            
            if existing_process:
                return JsonResponse({
                    'success': True,
                    'message': f'工序 {process_name} 已存在於工單中',
                    'process_id': existing_process.id,
                    'already_exists': True
                })
            
            # 取得最大步驟順序
            max_step = WorkOrderProcess.objects.filter(
                workorder=workorder
            ).aggregate(Max('step_order'))['step_order__max'] or 0
            
            # 建立新工序
            new_process = WorkOrderProcess.objects.create(
                workorder=workorder,
                process_name=process_name,
                step_order=max_step + 1,
                planned_quantity=workorder.quantity,
                assigned_operator=operator,
                assigned_equipment=equipment,
                status='pending'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'已成功將工序 {process_name} 加入到工單 {workorder_number}',
                'process_id': new_process.id,
                'step_order': new_process.step_order,
                'already_exists': False
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'JSON 格式錯誤'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'加入工序失敗：{str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': '只支援 POST 請求'
    }, status=405)


@login_required
def get_workorder_processes(request):
    """
    取得工單工序列表的 API
    用於檢查工單中已有的工序
    """
    from workorder.models import WorkOrder, WorkOrderProcess
    from django.http import JsonResponse
    
    workorder_number = request.GET.get('workorder_number')
    
    if not workorder_number:
        return JsonResponse({
            'success': False,
            'message': '工單號碼不能為空'
        }, status=400)
    
    try:
        # 使用多公司架構唯一識別查詢工單
        workorder = WorkOrder.objects.filter(order_number=workorder_number).first()
        if not workorder:
            return JsonResponse({
                'success': False,
                'message': f'找不到工單：{workorder_number}'
            }, status=404)
        
        processes = WorkOrderProcess.objects.filter(
            workorder=workorder
        ).order_by('step_order')
        
        process_list = []
        for process in processes:
            process_list.append({
                'id': process.id,
                'process_name': process.process_name,
                'step_order': process.step_order,
                'status': process.status,
                'assigned_operator': process.assigned_operator or '',
                'assigned_equipment': process.assigned_equipment or '',
                'planned_quantity': process.planned_quantity,
                'completed_quantity': process.completed_quantity
            })
        
        return JsonResponse({
            'success': True,
            'workorder_number': workorder_number,
            'processes': process_list
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f'找不到工單：{workorder_number}'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'取得工序列表失敗：{str(e)}'
        }, status=500)


class OnsiteReportAutoProcessService:
    """
    現場報工自動工序服務
    用於處理現場報工時的自動工序加入邏輯
    """
    
    @staticmethod
    def check_and_add_process(workorder_number, process_name, operator, equipment=''):
        """
        檢查並自動加入工序到工單
        
        Args:
            workorder_number: 工單號碼
            process_name: 工序名稱
            operator: 作業員
            equipment: 設備（可選）
            
        Returns:
            dict: 包含結果的字典
        """
        from workorder.models import WorkOrder, WorkOrderProcess
        
        try:
            # 查找工單
            workorder = WorkOrder.objects.get(order_number=workorder_number)
            
            # 檢查工序是否已存在
            existing_process = WorkOrderProcess.objects.filter(
                workorder=workorder,
                process_name=process_name
            ).first()
            
            if existing_process:
                return {
                    'success': True,
                    'message': f'工序 {process_name} 已存在於工單中',
                    'process_id': existing_process.id,
                    'already_exists': True,
                    'process': existing_process
                }
            
            # 取得最大步驟順序
            max_step = WorkOrderProcess.objects.filter(
                workorder=workorder
            ).aggregate(Max('step_order'))['step_order__max'] or 0
            
            # 建立新工序
            new_process = WorkOrderProcess.objects.create(
                workorder=workorder,
                process_name=process_name,
                step_order=max_step + 1,
                planned_quantity=workorder.quantity,
                assigned_operator=operator,
                assigned_equipment=equipment,
                status='pending'
            )
            
            return {
                'success': True,
                'message': f'已成功將工序 {process_name} 加入到工單 {workorder_number}',
                'process_id': new_process.id,
                'step_order': new_process.step_order,
                'already_exists': False,
                'process': new_process
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'success': False,
                'message': f'找不到工單：{workorder_number}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'加入工序失敗：{str(e)}'
            }
    
    @staticmethod
    def get_workorder_processes(workorder_number):
        """
        取得工單的所有工序
        
        Args:
            workorder_number: 工單號碼
            
        Returns:
            dict: 包含結果的字典
        """
        from workorder.models import WorkOrder, WorkOrderProcess
        
        try:
            workorder = WorkOrder.objects.get(order_number=workorder_number)
            processes = WorkOrderProcess.objects.filter(
                workorder=workorder
            ).order_by('step_order')
            
            process_list = []
            for process in processes:
                process_list.append({
                    'id': process.id,
                    'process_name': process.process_name,
                    'step_order': process.step_order,
                    'status': process.status,
                    'assigned_operator': process.assigned_operator or '',
                    'assigned_equipment': process.assigned_equipment or '',
                    'planned_quantity': process.planned_quantity,
                    'completed_quantity': process.completed_quantity
                })
            
            return {
                'success': True,
                'workorder_number': workorder_number,
                'processes': process_list
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'success': False,
                'message': f'找不到工單：{workorder_number}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'取得工序列表失敗：{str(e)}'
            } 

@login_required
def process_list_api(request):
    """工序列表 API"""
    try:
        from process.models import ProcessName
        
        # 取得所有工序
        processes = ProcessName.objects.values('name').distinct().order_by('name')
        
        return JsonResponse({
            'success': True,
            'processes': list(processes)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'載入失敗: {str(e)}'
        }, status=400)


@login_required
def workorder_debug_api(request):
    """工單調試 API - 檢查工單資料狀態（使用 WorkOrderDispatch 模型）"""
    try:
        from workorder.workorder_dispatch.models import WorkOrderDispatch
        
        # 取得基本統計
        total_workorders = WorkOrderDispatch.objects.count()
        
        # 取得前10筆工單作為範例
        sample_workorders = WorkOrderDispatch.objects.all()[:10].values(
            'id', 'order_number', 'product_code', 'company_code', 'planned_quantity', 'status'
        )
        
        # 取得公司代號統計
        company_stats = WorkOrderDispatch.objects.values('company_code').annotate(
            count=Count('id')
        ).order_by('company_code')
        
        # 取得產品編號統計
        product_stats = WorkOrderDispatch.objects.values('product_code').annotate(
            count=Count('id')
        ).order_by('product_code')[:10]
        
        return JsonResponse({
            'success': True,
            'debug_info': {
                'total_workorders': total_workorders,
                'sample_workorders': list(sample_workorders),
                'company_stats': list(company_stats),
                'product_stats': list(product_stats)
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'調試失敗: {str(e)}',
            'error_details': str(e)
        }, status=400) 

@login_required
def simple_test_api(request):
    """簡單測試 API - 檢查基本功能"""
    try:
        return JsonResponse({
            'success': True,
            'message': 'API 連線正常',
            'user': request.user.username,
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'測試失敗: {str(e)}'
        }, status=400) 