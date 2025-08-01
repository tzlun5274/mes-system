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
    ordering = ['created_at']

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

    def get_context_data(self, **kwargs):
        """添加上下文資料，包括工序統計和所有已核准的報工記錄"""
        context = super().get_context_data(**kwargs)
        workorder = self.get_object()
        
        # 計算已完成工序數量
        completed_processes_count = workorder.processes.filter(status='completed').count()
        
        # 計算進行中工序數量
        in_progress_processes_count = workorder.processes.filter(status='in_progress').count()
        
        context['completed_processes_count'] = completed_processes_count
        context['in_progress_processes_count'] = in_progress_processes_count
        
        # 獲取所有已核准的報工記錄
        from workorder.workorder_reporting.models import OperatorSupplementReport, SMTProductionReport, SupervisorProductionReport
        
        # 作業員補登報工記錄（已核准）
        operator_reports = OperatorSupplementReport.objects.filter(
            workorder=workorder,
            approval_status='approved'
        ).order_by('work_date', 'start_time')
        
        # SMT生產報工記錄（已核准）
        smt_reports = SMTProductionReport.objects.filter(
            workorder=workorder,
            approval_status='approved'
        ).order_by('work_date', 'start_time')
        
        # 主管報工記錄（已核准）
        supervisor_reports = SupervisorProductionReport.objects.filter(
            workorder=workorder,
            approval_status='approved'
        ).order_by('work_date', 'start_time')
        
        # 合併所有報工記錄並按時間排序
        all_reports = []
        
        # 添加作業員報工記錄
        for report in operator_reports:
            all_reports.append({
                'type': 'operator',
                'report_date': report.work_date,
                'process_name': report.process_name,
                'operator': report.operator.name if report.operator else '-',
                'equipment': report.equipment.name if report.equipment else '-',
                'work_quantity': report.work_quantity or 0,
                'defect_quantity': report.defect_quantity or 0,
                'work_hours': report.work_hours_calculated or 0,
                'overtime_hours': report.overtime_hours_calculated or 0,
                'report_source': '作業員補登報工',
                'report_time': report.start_time,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'remarks': report.remarks,
                'abnormal_notes': report.abnormal_notes,
                'approved_by': report.approved_by,
                'approved_at': report.approved_at,
            })
        
        # 添加SMT報工記錄
        for report in smt_reports:
            all_reports.append({
                'type': 'smt',
                'report_date': report.work_date,
                'process_name': report.operation,
                'operator': '-',
                'equipment': report.equipment.name if report.equipment else '-',
                'work_quantity': report.work_quantity or 0,
                'defect_quantity': report.defect_quantity or 0,
                'work_hours': report.work_hours_calculated or 0,
                'overtime_hours': report.overtime_hours_calculated or 0,
                'report_source': 'SMT報工',
                'report_time': report.start_time,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'remarks': report.remarks,
                'abnormal_notes': report.abnormal_notes,
                'approved_by': report.approved_by,
                'approved_at': report.approved_at,
            })
        
        # 添加主管報工記錄
        for report in supervisor_reports:
            all_reports.append({
                'type': 'supervisor',
                'report_date': report.work_date,
                'process_name': report.process_name,
                'operator': report.operator.name if report.operator else '-',
                'equipment': report.equipment.name if report.equipment else '-',
                'work_quantity': report.work_quantity or 0,
                'defect_quantity': report.defect_quantity or 0,
                'work_hours': report.work_hours_calculated or 0,
                'overtime_hours': report.overtime_hours_calculated or 0,
                'report_source': '主管報工',
                'report_time': report.start_time,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'remarks': report.remarks,
                'abnormal_notes': report.abnormal_notes,
                'approved_by': report.approved_by,
                'approved_at': report.approved_at,
            })
        
        # 按報工日期和開始時間排序（最早的在前）
        all_reports.sort(key=lambda x: (x['report_date'], x['start_time']), reverse=False)
        
        # 計算統計資料
        from collections import defaultdict
        stats_by_process = defaultdict(lambda: {
            'process_name': '',
            'total_good_quantity': 0,
            'total_defect_quantity': 0,
            'report_count': 0,
            'total_work_hours': 0.0,
            'operators': set(),
            'equipment': set()
        })
        
        # 總計資料
        total_stats = {
            'total_good_quantity': 0,
            'total_defect_quantity': 0,
            'total_report_count': len(all_reports),
            'total_work_hours': 0.0,
            'total_overtime_hours': 0.0,
            'total_all_hours': 0.0,
            'unique_operators': set(),
            'unique_equipment': set()
        }
        
        # 按工序分組統計
        for report in all_reports:
            process_name = report['process_name']
            
            # 更新工序統計
            stats_by_process[process_name]['process_name'] = process_name
            stats_by_process[process_name]['total_good_quantity'] += report['work_quantity']
            stats_by_process[process_name]['total_defect_quantity'] += report['defect_quantity']
            stats_by_process[process_name]['report_count'] += 1
            # 確保工作時數為 float 類型
            work_hours = float(report['work_hours']) if report['work_hours'] is not None else 0.0
            stats_by_process[process_name]['total_work_hours'] += work_hours
            
            # 更新總計
            total_stats['total_good_quantity'] += report['work_quantity']
            total_stats['total_defect_quantity'] += report['defect_quantity']
            total_stats['total_work_hours'] += work_hours
            # 確保加班時數為 float 類型
            overtime_hours = float(report['overtime_hours']) if report['overtime_hours'] is not None else 0.0
            total_stats['total_overtime_hours'] += overtime_hours
            
            # 記錄作業員和設備
            if report['operator'] != '-':
                stats_by_process[process_name]['operators'].add(report['operator'])
                total_stats['unique_operators'].add(report['operator'])
            
            if report['equipment'] != '-':
                stats_by_process[process_name]['equipment'].add(report['equipment'])
                total_stats['unique_equipment'].add(report['equipment'])
        
        # 計算總時數
        total_stats['total_all_hours'] = total_stats['total_work_hours'] + total_stats['total_overtime_hours']
        
        # 轉換 set 為 list 以便在模板中使用
        for process_stats in stats_by_process.values():
            process_stats['operators'] = list(process_stats['operators'])
            process_stats['equipment'] = list(process_stats['equipment'])
        
        total_stats['unique_operators'] = list(total_stats['unique_operators'])
        total_stats['unique_equipment'] = list(total_stats['unique_equipment'])
        
        context['all_production_reports'] = all_reports
        context['total_reports_count'] = len(all_reports)
        context['production_stats_by_process'] = dict(stats_by_process)
        context['production_total_stats'] = total_stats
        
        return context


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
    顯示從 ERP 同步的公司製令單，支援管理員設定功能
    """
    model = CompanyOrder
    template_name = 'workorder/dispatch/company_orders.html'
    context_object_name = 'workorders'
    paginate_by = 20
    ordering = ['sync_time']

    def get_queryset(self):
        """取得查詢集，支援搜尋和排序功能"""
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '').strip()
        sort = self.request.GET.get('sort', '')
        
        # 搜尋條件
        if search:
            queryset = queryset.filter(
                Q(company_code__icontains=search) |
                Q(mkordno__icontains=search) |
                Q(product_id__icontains=search)
            )
        
        # 排序條件
        if sort == "est_stock_out_date_asc":
            queryset = queryset.order_by("est_stock_out_date")
        elif sort == "est_stock_out_date_desc":
            queryset = queryset.order_by("-est_stock_out_date")
        else:
            queryset = queryset.order_by("sync_time")
            
        return queryset

    def get_context_data(self, **kwargs):
        """添加上下文資料，包含統計數據和設定資訊"""
        context = super().get_context_data(**kwargs)
        
        # 取得所有公司配置
        from erp_integration.models import CompanyConfig
        context['companies'] = CompanyConfig.objects.all()
        
        # 取得所有公司代號供篩選使用
        context['company_codes'] = CompanyOrder.objects.values_list(
            'company_code', flat=True
        ).distinct().order_by('company_code')
        
        # 計算統計數據
        queryset = self.get_queryset()
        context['total_orders'] = queryset.count()
        context['converted_orders'] = queryset.filter(is_converted=True).count()
        context['unconverted_orders'] = queryset.filter(is_converted=False).count()
        
        # 讀取系統設定
        from workorder.workorder_erp.models import SystemConfig
        
        # 自動轉換工單間隔設定（預設 30 分鐘）
        auto_convert_interval = 30
        try:
            config = SystemConfig.objects.get(key="auto_convert_interval")
            auto_convert_interval = int(config.value)
        except SystemConfig.DoesNotExist:
            pass
        context['auto_convert_interval'] = auto_convert_interval
        
        # 自動同步製令間隔（預設 30 分鐘）
        auto_sync_companyorder_interval = 30
        try:
            config = SystemConfig.objects.get(key="auto_sync_companyorder_interval")
            auto_sync_companyorder_interval = int(config.value)
        except SystemConfig.DoesNotExist:
            pass
        context['auto_sync_companyorder_interval'] = auto_sync_companyorder_interval
        
        # 不分攤關鍵字設定（預設：只計算最後一天,不分攤,不分配）
        no_distribute_keywords = "只計算最後一天,不分攤,不分配"
        try:
            config = SystemConfig.objects.get(key="no_distribute_keywords")
            no_distribute_keywords = config.value
        except SystemConfig.DoesNotExist:
            pass
        context['no_distribute_keywords'] = no_distribute_keywords
        
        # 轉換成字典格式，保持與原本模板的相容性
        workorders_list = []
        for order in self.get_queryset():
            # 格式化公司代號，確保是兩位數格式（例如：2 -> 02）
            formatted_company_code = order.company_code
            if formatted_company_code and formatted_company_code.isdigit():
                formatted_company_code = formatted_company_code.zfill(2)
            
            workorder_dict = {
                "MKOrdNO": f"{formatted_company_code}_{order.mkordno}",
                "ProductID": order.product_id,
                "ProdtQty": order.prodt_qty,
                "EstTakeMatDate": order.est_take_mat_date,
                "EstStockOutDate": order.est_stock_out_date,
                "is_converted": order.is_converted,
                "conversion_status": "已轉換" if order.is_converted else "未轉換",
            }
            workorders_list.append(workorder_dict)
        
        context['workorders'] = workorders_list
        
        return context

    def post(self, request, *args, **kwargs):
        """處理 POST 請求，用於管理員設定功能"""
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "您沒有權限執行此操作")
            return self.get(request, *args, **kwargs)
        
        from workorder.workorder_erp.models import SystemConfig
        from django.core.management import call_command
        import logging
        
        workorder_logger = logging.getLogger('workorder')
        
        if "no_distribute_keywords" in request.POST:
            new_no_distribute_keywords = request.POST.get("no_distribute_keywords")
            if new_no_distribute_keywords:
                old_value = request.POST.get("current_no_distribute_keywords", "")
                SystemConfig.objects.update_or_create(
                    key="no_distribute_keywords",
                    defaults={"value": new_no_distribute_keywords},
                )
                workorder_logger.info(
                    f"管理員 {request.user} 變更不分攤關鍵字設定，原值：{old_value}，新值：{new_no_distribute_keywords}。IP: {request.META.get('REMOTE_ADDR')}"
                )
                messages.success(request, "不分攤關鍵字設定已更新！")
        else:
            # 自動轉換/同步間隔設定
            new_convert_interval = request.POST.get("auto_convert_interval")
            new_sync_interval = request.POST.get("auto_sync_companyorder_interval")
            interval_changed = False
            
            if (
                new_convert_interval
                and new_convert_interval.isdigit()
                and int(new_convert_interval) > 0
            ):
                old_value = request.POST.get("current_auto_convert_interval", "30")
                SystemConfig.objects.update_or_create(
                    key="auto_convert_interval",
                    defaults={"value": new_convert_interval},
                )
                workorder_logger.info(
                    f"管理員 {request.user} 變更自動轉換工單間隔，原值：{old_value} 分鐘，新值：{new_convert_interval} 分鐘。IP: {request.META.get('REMOTE_ADDR')}"
                )
                interval_changed = True
                
            if (
                new_sync_interval
                and new_sync_interval.isdigit()
                and int(new_sync_interval) > 0
            ):
                old_value = request.POST.get("current_auto_sync_companyorder_interval", "30")
                SystemConfig.objects.update_or_create(
                    key="auto_sync_companyorder_interval",
                    defaults={"value": new_sync_interval},
                )
                workorder_logger.info(
                    f"管理員 {request.user} 變更自動同步製令間隔，原值：{old_value} 分鐘，新值：{new_sync_interval} 分鐘。IP: {request.META.get('REMOTE_ADDR')}"
                )
                interval_changed = True
            
            # 如果間隔設定有變更，重新設定定時任務
            if interval_changed:
                try:
                    call_command("setup_workorder_tasks")
                    workorder_logger.info(
                        f"管理員 {request.user} 重新設定定時任務成功。IP: {request.META.get('REMOTE_ADDR')}"
                    )
                    messages.success(request, "間隔設定已更新，定時任務已重新設定！")
                except Exception as e:
                    workorder_logger.error(
                        f"重新設定定時任務失敗：{str(e)}。IP: {request.META.get('REMOTE_ADDR')}"
                    )
                    messages.warning(request, f"間隔設定已更新，但重新設定定時任務失敗：{str(e)}")
        
        workorder_logger.info(
            f"使用者 {request.user} 檢視公司製令單列表。IP: {request.META.get('REMOTE_ADDR')}"
        )
        
        return self.get(request, *args, **kwargs)


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