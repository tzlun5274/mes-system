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
from django.core.paginator import Paginator
from django.db import transaction
from datetime import datetime, timedelta
import json

from .models import WorkOrderDispatch, WorkOrderDispatchProcess, DispatchHistory
from .forms import WorkOrderDispatchForm, WorkOrderDispatchProcessForm, DispatchSearchForm, BulkDispatchForm
from workorder.models import WorkOrder


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
                Q(order_number__icontains=search) |
                Q(product_code__icontains=search) |
                Q(product_name__icontains=search) |
                Q(company_code__icontains=search) |
                Q(assigned_operator__icontains=search) |
                Q(process_name__icontains=search)
            )
        
        # 狀態篩選
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
        
        # 公司代號篩選
        company_code = self.request.GET.get('company_code', '')
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
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
        
        # 搜尋表單
        context['search_form'] = DispatchSearchForm(self.request.GET)
        
        # 統計資料（基於搜尋結果）
        queryset = self.get_queryset()
        context['total_count'] = queryset.count()
        context['pending_count'] = queryset.filter(status='pending').count()
        context['dispatched_count'] = queryset.filter(status='dispatched').count()
        context['in_production_count'] = queryset.filter(status='in_production').count()
        context['completed_count'] = queryset.filter(status='completed').count()
        
        # 搜尋參數
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        
        # 為每個派工單添加 ERP 製令單日期資訊和公司名稱
        dispatches = context['dispatches']
        for dispatch in dispatches:
            # 首先處理公司名稱
            if not dispatch.company_name and dispatch.company_code:
                try:
                    from erp_integration.models import CompanyConfig
                    company_config = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
                    if company_config:
                        dispatch.company_name = company_config.company_name
                        # 更新資料庫中的公司名稱
                        dispatch.save(update_fields=['company_name'])
                    else:
                        dispatch.company_name = dispatch.company_code
                except Exception as e:
                    import logging
                    logger = logging.getLogger('workorder')
                    logger.warning(f"取得公司名稱失敗: {dispatch.order_number} (公司代號: {dispatch.company_code}), 錯誤: {str(e)}")
                    dispatch.company_name = dispatch.company_code
            elif not dispatch.company_name:
                dispatch.company_name = dispatch.company_code or '-'
            
            # 然後處理 ERP 製令單資訊
            try:
                from workorder.company_order.models import CompanyOrder
                # 使用公司代號和工單號碼來精確匹配
                company_order = CompanyOrder.objects.filter(
                    mkordno=dispatch.order_number,
                    company_code=dispatch.company_code
                ).first()
                
                if company_order:
                    # 格式化日期：從 YYYYMMDD 轉換為 YYYY-MM-DD
                    def format_date(date_str):
                        if date_str and len(date_str) == 8:
                            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        return date_str
                    
                    dispatch.erp_start_date = format_date(company_order.est_take_mat_date)
                    dispatch.erp_end_date = format_date(company_order.est_stock_out_date)
                else:
                    dispatch.erp_start_date = None
                    dispatch.erp_end_date = None
            except Exception as e:
                # 記錄錯誤並設定預設值
                import logging
                logger = logging.getLogger('workorder')
                logger.warning(f"取得 ERP 製令單資訊失敗: {dispatch.order_number} (公司: {dispatch.company_code}), 錯誤: {str(e)}")
                dispatch.erp_start_date = None
                dispatch.erp_end_date = None
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['company_code'] = self.request.GET.get('company_code', '')
        
        return context


class DispatchCreateView(LoginRequiredMixin, CreateView):
    """
    派工單新增視圖
    建立新的派工單
    """
    model = WorkOrderDispatch
    form_class = WorkOrderDispatchForm
    template_name = 'workorder_dispatch/dispatch_form.html'
    success_url = reverse_lazy('workorder:workorder_dispatch:dispatch_list')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        with transaction.atomic():
            form.instance.created_by = self.request.user.username
            form.instance.status = 'in_production'  # 直接設定為生產中
            response = super().form_valid(form)
            
            # 記錄歷史
            DispatchHistory.objects.create(
                workorder_dispatch=form.instance,
                action='建立',
                new_status='in_production',
                operator=self.request.user.username,
                notes='建立派工單（生產中狀態）'
            )
            
            messages.success(self.request, '派工單建立成功，已設定為生產中狀態！')
            return response

    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        context['title'] = '新增派工單'
        context['submit_text'] = '建立派工單'
        context['is_create'] = True
        return context


class DispatchUpdateView(LoginRequiredMixin, UpdateView):
    """
    派工單編輯視圖
    編輯現有的派工單
    """
    model = WorkOrderDispatch
    form_class = WorkOrderDispatchForm
    template_name = 'workorder_dispatch/dispatch_form.html'
    success_url = reverse_lazy('workorder:workorder_dispatch:dispatch_list')

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        with transaction.atomic():
            old_status = self.get_object().status
            new_status = form.instance.status
            
            response = super().form_valid(form)
            
            # 記錄狀態變更歷史
            if old_status != new_status:
                DispatchHistory.objects.create(
                    workorder_dispatch=form.instance,
                    action='狀態變更',
                    old_status=old_status,
                    new_status=new_status,
                    operator=self.request.user.username,
                    notes=f'狀態從 {self.get_status_display(old_status)} 變更為 {self.get_status_display(new_status)}'
                )
            
            messages.success(self.request, '派工單更新成功！')
            return response

    def get_status_display(self, status):
        """取得狀態顯示名稱"""
        status_choices = dict(WorkOrderDispatch.STATUS_CHOICES)
        return status_choices.get(status, status)

    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        context['title'] = '編輯派工單'
        context['submit_text'] = '更新派工單'
        context['is_create'] = False
        return context


class DispatchDetailView(LoginRequiredMixin, DetailView):
    """
    派工單詳情視圖
    顯示派工單的詳細資訊
    """
    model = WorkOrderDispatch
    template_name = 'workorder_dispatch/dispatch_detail.html'
    context_object_name = 'dispatch'

    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        dispatch = self.get_object()
        
        # 取得相關的工單資訊
        try:
            # 使用多公司架構唯一識別：公司代號 + 工單號碼 + 產品編號
            context['work_order'] = WorkOrder.objects.filter(
                order_number=dispatch.order_number,
                company_code=dispatch.company_code,
                product_code=dispatch.product_code
            ).first()
        except Exception as e:
            # 記錄錯誤並設定預設值
            import logging
            logger = logging.getLogger('workorder')
            logger.warning(f"取得工單資訊失敗: {dispatch.order_number} (公司: {dispatch.company_code}), 錯誤: {str(e)}")
            context['work_order'] = None
        
        # 確保派工單有正確的公司名稱
        company_name = dispatch.company_name
        if not company_name and dispatch.company_code:
            try:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(company_code=dispatch.company_code).first()
                if company_config:
                    company_name = company_config.company_name
                    # 更新派工單的公司名稱欄位
                    dispatch.company_name = company_name
                    dispatch.save(update_fields=['company_name'])
                else:
                    company_name = dispatch.company_code
            except Exception as e:
                import logging
                logger = logging.getLogger('workorder')
                logger.warning(f"更新派工單公司名稱失敗: {dispatch.order_number}, 錯誤: {str(e)}")
                company_name = dispatch.company_code
        elif not company_name:
            company_name = dispatch.company_code or '-'
        
        # 將公司名稱添加到上下文中
        context['company_name'] = company_name
        
        # 取得 ERP 製令單資訊（預定開工日和預定出貨日）
        try:
            from workorder.company_order.models import CompanyOrder
            # 使用公司代號和工單號碼來精確匹配
            company_order = CompanyOrder.objects.filter(
                mkordno=dispatch.order_number,
                company_code=dispatch.company_code
            ).first()
            
            if company_order:
                # 格式化日期：從 YYYYMMDD 轉換為 YYYY-MM-DD
                def format_date(date_str):
                    if date_str and len(date_str) == 8:
                        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    return date_str
                
                context['erp_start_date'] = format_date(company_order.est_take_mat_date)
                context['erp_end_date'] = format_date(company_order.est_stock_out_date)
            else:
                context['erp_start_date'] = None
                context['erp_end_date'] = None
        except Exception as e:
            # 記錄錯誤並設定預設值
            import logging
            logger = logging.getLogger('workorder')
            logger.warning(f"取得 ERP 製令單資訊失敗: {dispatch.order_number} (公司: {dispatch.company_code}), 錯誤: {str(e)}")
            context['erp_start_date'] = None
            context['erp_end_date'] = None
        
        # 取得工序明細
        context['processes'] = dispatch.dispatch_processes.all()
        
        # 取得歷史記錄
        context['history'] = dispatch.dispatch_history.all()[:10]
        
        return context


class DispatchDeleteView(LoginRequiredMixin, DeleteView):
    """
    派工單刪除視圖
    刪除派工單
    """
    model = WorkOrderDispatch
    template_name = 'workorder_dispatch/dispatch_confirm_delete.html'
    success_url = reverse_lazy('workorder:workorder_dispatch:dispatch_list')

    def delete(self, request, *args, **kwargs):
        """刪除處理"""
        with transaction.atomic():
            dispatch = self.get_object()
            
            # 記錄刪除歷史
            DispatchHistory.objects.create(
                workorder_dispatch=dispatch,
                action='刪除',
                old_status=dispatch.status,
                operator=request.user.username,
                notes='刪除派工單'
            )
            
            response = super().delete(request, *args, **kwargs)
            messages.success(request, '派工單刪除成功！')
            return response


@login_required
def dispatch_dashboard(request):
    """
    派工單儀表板
    顯示派工單的統計資訊和概覽
    """
    # 統計資料
    total_dispatches = WorkOrderDispatch.objects.count()
    pending_dispatches = WorkOrderDispatch.objects.filter(status='pending').count()
    dispatched_dispatches = WorkOrderDispatch.objects.filter(status='dispatched').count()
    in_production_dispatches = WorkOrderDispatch.objects.filter(status='in_production').count()
    completed_dispatches = WorkOrderDispatch.objects.filter(status='completed').count()
    
    # 最近派工單
    recent_dispatches = WorkOrderDispatch.objects.order_by('-created_at')[:10]
    
    # 今日派工單
    today = timezone.now().date()
    today_dispatches = WorkOrderDispatch.objects.filter(dispatch_date=today).count()
    
    # 本週派工單
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_dispatches = WorkOrderDispatch.objects.filter(
        dispatch_date__range=[week_start, week_end]
    ).count()
    
    context = {
        'total_dispatches': total_dispatches,
        'pending_dispatches': pending_dispatches,
        'dispatched_dispatches': dispatched_dispatches,
        'in_production_dispatches': in_production_dispatches,
        'completed_dispatches': completed_dispatches,
        'recent_dispatches': recent_dispatches,
        'today_dispatches': today_dispatches,
        'week_dispatches': week_dispatches,
    }
    
    return render(request, 'workorder_dispatch/dispatch_dashboard.html', context)


@login_required
def bulk_dispatch_view(request):
    """
    批量派工視圖
    批量建立派工單
    """
    if request.method == 'POST':
        form = BulkDispatchForm(request.POST)
        if form.is_valid():
            work_order_numbers = form.cleaned_data['work_order_numbers']
            assigned_operator = form.cleaned_data['assigned_operator']
            assigned_equipment = form.cleaned_data['assigned_equipment']
            process_name = form.cleaned_data['process_name']
            dispatch_date = form.cleaned_data['dispatch_date']
            notes = form.cleaned_data['notes']
            
            created_count = 0
            skipped_count = 0
            
            with transaction.atomic():
                for order_number in work_order_numbers:
                    # 檢查是否已存在派工單
                    if WorkOrderDispatch.objects.filter(order_number=order_number).exists():
                        skipped_count += 1
                        continue
                    
                    try:
                        # 使用 company_code 和 order_number 組合查詢，避免 MultipleObjectsReturned 錯誤
                        # 注意：這裡需要從某個地方獲取 company_code，暫時使用第一個匹配的記錄
                        work_order = WorkOrder.objects.filter(order_number=order_number).first()
                        if not work_order:
                            skipped_count += 1
                            continue
                        
                        # 建立派工單，直接設定為生產中狀態
                        dispatch = WorkOrderDispatch.objects.create(
                            company_code=work_order.company_code,
                            order_number=work_order.order_number,
                            product_code=work_order.product_code,
                            product_name=getattr(work_order, 'product_name', ''),
                            planned_quantity=work_order.quantity,
                            status='in_production',  # 直接設定為生產中
                            dispatch_date=dispatch_date or timezone.now().date(),
                            assigned_operator=assigned_operator,
                            assigned_equipment=assigned_equipment,
                            process_name=process_name,
                            notes=notes,
                            created_by=request.user.username
                        )
                        
                        # 記錄歷史
                        DispatchHistory.objects.create(
                            workorder_dispatch=dispatch,
                            action='批量建立',
                            new_status='in_production',
                            operator=request.user.username,
                            notes=f'批量建立派工單（生產中狀態），作業員: {assigned_operator or "未指定"}'
                        )
                        
                        created_count += 1
                        
                    except Exception as e:
                        # 記錄錯誤並跳過
                        import logging
                        logger = logging.getLogger('workorder')
                        logger.warning(f"批量派工時取得工單失敗: {order_number}, 錯誤: {str(e)}")
                        skipped_count += 1
                        continue
            
            messages.success(
                request, 
                f'批量派工完成！成功建立 {created_count} 個派工單，跳過 {skipped_count} 個'
            )
            return redirect('workorder:workorder_dispatch:dispatch_list')
    else:
        form = BulkDispatchForm()
    
    context = {
        'form': form,
        'title': '批量派工',
        'submit_text': '建立批量派工單'
    }
    
    return render(request, 'workorder_dispatch/bulk_dispatch_form.html', context)


@login_required
def get_work_order_info(request):
    """
    AJAX 端點：取得工單資訊
    """
    if request.method != 'GET':
        return JsonResponse({'error': '只支援 GET 請求'}, status=405)
    
    order_number = request.GET.get('order_number', '').strip()
    if not order_number:
        return JsonResponse({'error': '請提供工單號碼'}, status=400)
    
    try:
        # 查詢所有匹配的工單（可能有多個公司）
        work_orders = WorkOrder.objects.filter(order_number=order_number)
        
        if work_orders.exists():
            # 如果只有一個工單，直接返回
            if work_orders.count() == 1:
                work_order = work_orders.first()
                return JsonResponse({
                    'success': True,
                    'data': {
                        'order_number': work_order.order_number,
                        'product_code': work_order.product_code,
                        'product_name': getattr(work_order, 'product_name', ''),
                        'quantity': work_order.quantity,
                        'status': work_order.status,
                        'company_code': work_order.company_code,
                    }
                })
            else:
                # 如果有多個工單，返回所有工單的資訊（需要前端選擇）
                work_orders_data = []
                for work_order in work_orders:
                    work_orders_data.append({
                        'order_number': work_order.order_number,
                        'product_code': work_order.product_code,
                        'product_name': getattr(work_order, 'product_name', ''),
                        'quantity': work_order.quantity,
                        'status': work_order.status,
                        'company_code': work_order.company_code,
                    })
                
                return JsonResponse({
                    'success': True,
                    'multiple_found': True,
                    'message': f'找到 {work_orders.count()} 個相同工單號碼的記錄，請選擇正確的公司',
                    'data': work_orders_data
                })
        else:
            return JsonResponse({'error': '找不到指定的工單'}, status=404)
    except Exception as e:
        # 記錄錯誤並返回錯誤訊息
        import logging
        logger = logging.getLogger('workorder')
        logger.error(f"取得工單資訊失敗: {order_number}, 錯誤: {str(e)}")
        return JsonResponse({'error': '取得工單資訊時發生錯誤'}, status=500)


@login_required
def update_dispatch_status(request, pk):
    """
    AJAX 端點：更新派工單狀態
    """
    if request.method != 'POST':
        return JsonResponse({'error': '只支援 POST 請求'}, status=405)
    
    try:
        dispatch = WorkOrderDispatch.objects.get(pk=pk)
        new_status = request.POST.get('status')
        
        if new_status not in dict(WorkOrderDispatch.STATUS_CHOICES):
            return JsonResponse({'error': '無效的狀態'}, status=400)
        
        old_status = dispatch.status
        dispatch.status = new_status
        dispatch.save()
        
        # 記錄歷史
        DispatchHistory.objects.create(
            workorder_dispatch=dispatch,
            action='狀態變更',
            old_status=old_status,
            new_status=new_status,
            operator=request.user.username,
            notes=f'狀態從 {dict(WorkOrderDispatch.STATUS_CHOICES)[old_status]} 變更為 {dict(WorkOrderDispatch.STATUS_CHOICES)[new_status]}'
        )
        
        return JsonResponse({
            'success': True,
            'message': '狀態更新成功',
            'new_status': new_status,
            'new_status_display': dict(WorkOrderDispatch.STATUS_CHOICES)[new_status]
        })
        
    except WorkOrderDispatch.DoesNotExist:
        return JsonResponse({'error': '找不到指定的派工單'}, status=404)


@login_required
def export_dispatches(request):
    """
    匯出派工單資料
    """
    import csv
    from django.http import HttpResponse
    
    # 取得篩選條件
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    company_code = request.GET.get('company_code', '')
    
    # 建立查詢集
    queryset = WorkOrderDispatch.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(order_number__icontains=search) |
            Q(product_code__icontains=search) |
            Q(product_name__icontains=search) |
            Q(company_code__icontains=search) |
            Q(assigned_operator__icontains=search) |
            Q(process_name__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    if company_code:
        queryset = queryset.filter(company_code=company_code)
    
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
    
    # 建立 CSV 回應
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="派工單_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # 寫入標題列
    writer.writerow([
        '派工單ID', '公司代號', '工單號碼', '產品編號', '產品名稱', '計劃數量',
        '狀態', '派工日期', '計劃開始日期', '計劃完成日期', '分配作業員',
        '分配設備', '工序名稱', '備註', '建立時間', '建立人員'
    ])
    
    # 寫入資料
    for dispatch in queryset:
        writer.writerow([
            dispatch.id,
            dispatch.company_code or '',
            dispatch.order_number,
            dispatch.product_code,
            dispatch.product_name or '',
            dispatch.planned_quantity or '',
            dict(WorkOrderDispatch.STATUS_CHOICES).get(dispatch.status, dispatch.status),
            dispatch.dispatch_date.strftime('%Y-%m-%d') if dispatch.dispatch_date else '',
            dispatch.planned_start_date.strftime('%Y-%m-%d') if dispatch.planned_start_date else '',
            dispatch.planned_end_date.strftime('%Y-%m-%d') if dispatch.planned_end_date else '',
            dispatch.assigned_operator or '',
            dispatch.assigned_equipment or '',
            dispatch.process_name or '',
            dispatch.notes or '',
            dispatch.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            dispatch.created_by
        ])
    
    return response 