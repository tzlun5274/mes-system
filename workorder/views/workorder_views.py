"""
工單基本管理視圖
包含工單的列表、新增、編輯、刪除、詳情等功能
使用 Django 類別視圖，符合設計規範
"""

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
    View,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, render
from django.db.models import Q, Sum
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.management import call_command
import logging

from ..models import WorkOrder, WorkOrderProductionDetail
# 移除 ProductionMonitoringData 引用，改用派工單監控資料
from ..workorder_erp.models import CompanyOrder, SystemConfig, PrdMKOrdMain
from ..forms import WorkOrderForm
from erp_integration.models import CompanyConfig
from ..workorder_dispatch.models import WorkOrderDispatch
from ..workorder_dispatch.services import WorkOrderDispatchService
from ..workorder_fill_work.models import FillWork
from ..workorder_onsite_report.models import OnsiteReport
from ..services.completion_service import FillWorkCompletionService

# 設定 logger
workorder_logger = logging.getLogger('workorder')

class WorkOrderListView(LoginRequiredMixin, ListView):
    """
    工單列表視圖
    顯示所有工單，支援搜尋和分頁功能
    """

    model = WorkOrder
    template_name = "workorder/workorder/workorder_list.html"
    context_object_name = "workorders"
    paginate_by = 20
    ordering = ["created_at"]

    def get_queryset(self):
        """取得查詢集，支援搜尋功能"""
        queryset = super().get_queryset()
        search = self.request.GET.get("search", "")
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search)
                | Q(product_code__icontains=search)
                | Q(company_code__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        """添加上下文資料"""
        context = super().get_context_data(**kwargs)
        context["is_debug"] = (
            self.request.settings.DEBUG if hasattr(self.request, "settings") else False
        )
        return context

class WorkOrderDetailView(LoginRequiredMixin, DetailView):
    """
    工單詳情視圖
    顯示單一工單的詳細資訊
    """

    model = WorkOrder
    template_name = "workorder/workorder/workorder_detail.html"
    context_object_name = "workorder"

    def get(self, request, *args, **kwargs):
        """檢查工單狀態，如果是已完工工單則重定向到已完工工單詳情頁面"""
        workorder = self.get_object()
        
        # 如果工單狀態是 completed，重定向到已完工工單詳情頁面
        if workorder.status == 'completed':
            # 檢查是否已經有對應的已完工工單記錄
            completed_workorder = CompletedWorkOrder.objects.filter(
                order_number=workorder.order_number,
                company_code=workorder.company_code,
                product_code=workorder.product_code
            ).first()
            
            if completed_workorder:
                # 重定向到已完工工單詳情頁面
                return redirect('workorder:completed_workorder_detail', pk=completed_workorder.id)
            else:
                # 如果沒有已完工工單記錄，可能是資料不一致，顯示錯誤訊息
                messages.error(request, f'工單 {workorder.order_number} 狀態為已完工，但找不到對應的已完工工單記錄。請聯繫系統管理員。')
                return redirect('workorder:index')
        
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """添加上下文資料，使用派工單監控資料作為資料來源"""
        context = super().get_context_data(**kwargs)
        workorder = self.get_object()
        
        # 使用原始工單資料，不進行強制修正
        # 保持工單的原始公司代號和產品編號

        # 首先取得公司名稱（在監控資料處理之前）
        company_name = None
        if workorder.company_code:
            try:
                company_config = CompanyConfig.objects.filter(company_code=workorder.company_code).first()
                if company_config:
                    company_name = company_config.company_name
                    workorder_logger.info(f"成功取得公司名稱: {company_name} (代號: {workorder.company_code})")
                else:
                    workorder_logger.warning(f"找不到公司代號 {workorder.company_code} 的配置")
            except Exception as e:
                workorder_logger.error(f"查詢公司配置時發生錯誤: {str(e)}")
        
        # 如果無法從 CompanyConfig 取得，使用公司代號作為後備
        if not company_name:
            company_name = workorder.company_code or '未知公司'
            workorder_logger.warning(f"使用後備公司名稱: {company_name}")
        
        context['company_name'] = company_name

        # 取得派工單監控資料
        
        # 查找對應的派工單
        dispatch = WorkOrderDispatch.objects.filter(
            order_number=workorder.order_number,
            product_code=workorder.product_code,
            company_code=workorder.company_code
        ).first()
        
        if dispatch:
            # 更新派工單的監控資料
            WorkOrderDispatchService.update_monitoring_data(dispatch)
            
            # 從派工單取得工序統計
            context["completed_processes_count"] = dispatch.completed_processes
            context["in_progress_processes_count"] = dispatch.in_progress_processes
            context["pending_processes_count"] = dispatch.pending_processes
            context["total_processes_count"] = dispatch.total_processes

            # 從派工單取得統計資訊
            context["monitoring_data"] = dispatch
            
            # 總計資料（從派工單取得）
            total_stats = {
                "total_good_quantity": dispatch.total_good_quantity,
                "total_defect_quantity": dispatch.total_defect_quantity,
                "total_quantity": dispatch.total_quantity,
                "total_report_count": dispatch.fillwork_report_count + dispatch.onsite_report_count,
                "total_work_hours": float(dispatch.total_work_hours),
                "total_overtime_hours": float(dispatch.total_overtime_hours),
                "total_all_hours": float(dispatch.total_all_hours),
                "unique_operators": dispatch.unique_operators,
                "unique_equipment": dispatch.unique_equipment,
            }
            
            # 出貨包裝專項統計
            packaging_stats = {
                "packaging_good_quantity": dispatch.packaging_good_quantity,
                "packaging_defect_quantity": dispatch.packaging_defect_quantity,
                "packaging_total_quantity": dispatch.packaging_total_quantity,
                "packaging_completion_rate": float(dispatch.packaging_completion_rate),
            }
            
            context["production_total_stats"] = total_stats
            context["packaging_stats"] = packaging_stats
            context["can_complete"] = dispatch.can_complete
            context["completion_rate"] = float(dispatch.completion_rate)
        else:
            # 如果沒有派工單，使用預設值
            context["completed_processes_count"] = 0
            context["in_progress_processes_count"] = 0
            context["pending_processes_count"] = 0
            context["total_processes_count"] = 0
            context["monitoring_data"] = None
            context["packaging_stats"] = {
                "packaging_good_quantity": 0,
                "packaging_defect_quantity": 0,
                "packaging_total_quantity": 0,
                "packaging_completion_rate": 0.0,
            }
            context["can_complete"] = False
            context["completion_rate"] = 0.0

        # 添加完工判斷資訊
        try:
            completion_summary = FillWorkCompletionService.get_completion_summary(workorder.id)
            context["completion_summary"] = completion_summary
        except Exception as e:
            workorder_logger.error(f"獲取工單 {workorder.order_number} 完工摘要失敗: {str(e)}")
            context["completion_summary"] = {'error': '獲取完工摘要失敗'}

        # 取得所有報工記錄（填報記錄 + 現場報工）
        
        # 取得已核准的填報記錄
        approved_fillwork = FillWork.objects.filter(
            workorder=workorder.order_number,
            product_id=workorder.product_code,
            company_name=company_name,
            approval_status='approved'
        ).order_by('work_date', 'start_time')
        
        # 取得現場報工記錄
        onsite_reports = OnsiteReport.objects.filter(
            workorder=workorder.order_number,
            product_id=workorder.product_code,
            company_name=company_name
        ).order_by('work_date', 'start_datetime')
        
        # 合併報工記錄
        all_production_reports = []
        
        # 處理填報記錄
        for fillwork in approved_fillwork:
            all_production_reports.append({
                'report_date': fillwork.work_date,
                'process_name': fillwork.operation or fillwork.process.name if fillwork.process else '未知工序',
                'operator': fillwork.operator,
                'equipment': fillwork.equipment or '-',
                'work_quantity': fillwork.work_quantity,
                'defect_quantity': fillwork.defect_quantity,
                'work_hours': float(fillwork.work_hours_calculated or 0),
                'overtime_hours': float(fillwork.overtime_hours_calculated or 0),
                'report_source': '填報記錄',
                'report_type': 'fillwork'
            })
        
        # 處理現場報工記錄
        for onsite in onsite_reports:
            all_production_reports.append({
                'report_date': onsite.work_date,
                'process_name': onsite.operation or onsite.process,
                'operator': onsite.operator,
                'equipment': onsite.equipment or '-',
                'work_quantity': onsite.work_quantity,
                'defect_quantity': onsite.defect_quantity,
                'work_hours': float(onsite.work_minutes / 60 if onsite.work_minutes else 0),
                'overtime_hours': 0,  # 現場報工暫時不計算加班時數
                'report_source': '現場報工',
                'report_type': 'onsite'
            })
        
        # 按日期和時間排序
        all_production_reports.sort(key=lambda x: (x['report_date'], x.get('start_time', '00:00')))
        
        context['all_production_reports'] = all_production_reports
        
        # 計算報工記錄統計
        total_work_hours = sum(r['work_hours'] for r in all_production_reports)
        total_overtime_hours = sum(r['overtime_hours'] for r in all_production_reports)
        
        production_total_stats = {
            'total_good_quantity': sum(r['work_quantity'] for r in all_production_reports),
            'total_defect_quantity': sum(r['defect_quantity'] for r in all_production_reports),
            'total_report_count': len(all_production_reports),
            'total_work_hours': total_work_hours,
            'total_overtime_hours': total_overtime_hours,
            'total_all_hours': total_work_hours + total_overtime_hours,
            'unique_operators': list(set(r['operator'] for r in all_production_reports if r['operator'] and r['operator'] != '-')),
            'unique_equipment': list(set(r['equipment'] for r in all_production_reports if r['equipment'] and r['equipment'] != '-')),
        }
        context['production_total_stats'] = production_total_stats
        
        # 按工序統計
        production_stats_by_process = {}
        for report in all_production_reports:
            process_name = report['process_name']
            if process_name not in production_stats_by_process:
                production_stats_by_process[process_name] = {
                    'process_name': process_name,
                    'total_good_quantity': 0,
                    'total_defect_quantity': 0,
                    'report_count': 0,
                    'total_work_hours': 0.0,
                    'operators': set(),
                    'equipment': set()
                }
            
            stats = production_stats_by_process[process_name]
            stats['total_good_quantity'] += report['work_quantity']
            stats['total_defect_quantity'] += report['defect_quantity']
            stats['report_count'] += 1
            stats['total_work_hours'] += report['work_hours']
            
            if report['operator'] and report['operator'] != '-':
                stats['operators'].add(report['operator'])
            if report['equipment'] and report['equipment'] != '-':
                stats['equipment'].add(report['equipment'])
        
        # 將 set 轉換為 list 以便在模板中使用
        for process_name, stats in production_stats_by_process.items():
            stats['operators'] = list(stats['operators'])
            stats['equipment'] = list(stats['equipment'])
        
        context['production_stats_by_process'] = production_stats_by_process

        return context

class WorkOrderCreateView(LoginRequiredMixin, CreateView):
    """
    工單新增視圖
    用於建立新的工單
    """

    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "workorder/workorder/workorder_form.html"
    success_url = reverse_lazy("workorder:list")

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, "工單建立成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "工單建立失敗，請檢查輸入資料！")
        return super().form_invalid(form)

class WorkOrderUpdateView(LoginRequiredMixin, UpdateView):
    """
    工單編輯視圖
    用於編輯現有工單
    """

    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "workorder/workorder/workorder_form.html"
    success_url = reverse_lazy("workorder:list")

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, "工單更新成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "工單更新失敗，請檢查輸入資料！")
        return super().form_invalid(form)

class WorkOrderDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    工單刪除視圖
    用於刪除工單，僅限管理員使用
    """

    model = WorkOrder
    template_name = "workorder/workorder/workorder_confirm_delete.html"
    success_url = reverse_lazy("workorder:list")

    def test_func(self):
        """檢查用戶是否有刪除權限"""
        return self.request.user.is_staff or self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        messages.success(request, "工單刪除成功！")
        return super().delete(request, *args, **kwargs)

@method_decorator(ensure_csrf_cookie, name="dispatch")
class CompanyOrderListView(LoginRequiredMixin, ListView):
    """
    公司製令單列表視圖
    顯示從 ERP 同步的未結案公司製令單（CompleteStatus=2 或空白，且 BillStatus 不是 1），
    方便現場追蹤與管理，支援管理員設定功能
    """

    model = CompanyOrder
    template_name = "workorder/dispatch/company_orders.html"
    context_object_name = "workorders"
    paginate_by = 20
    ordering = ["sync_time"]

    def get_queryset(self):
        """取得查詢集，支援搜尋和排序功能"""
        # 只顯示未結案的公司製令單
        # CompleteStatus=2，且 BillStatus 不是 1（排除已結案的）
        queryset = (
            super()
            .get_queryset()
            .filter(
                # CompleteStatus 為 2
                Q(complete_status=2)
                &
                # BillStatus 不是 1（排除已結案的）
                ~Q(bill_status=1)
            )
        )

        search = self.request.GET.get("search", "").strip()
        sort = self.request.GET.get("sort", "")

        # 搜尋條件
        if search:
            queryset = queryset.filter(
                Q(company_code__icontains=search)
                | Q(mkordno__icontains=search)
                | Q(product_id__icontains=search)
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
        context["companies"] = CompanyConfig.objects.all()

        # 取得所有公司代號供篩選使用
        context["company_codes"] = (
            CompanyOrder.objects.values_list("company_code", flat=True)
            .distinct()
            .order_by("company_code")
        )

        # 計算統計數據
        queryset = self.get_queryset()
        context["total_orders"] = queryset.count()
        context["converted_orders"] = queryset.filter(is_converted=True).count()
        context["unconverted_orders"] = queryset.filter(is_converted=False).count()

        # 讀取系統設定
        # 自動轉換工單間隔設定（預設 30 分鐘）
        auto_convert_interval = 30
        try:
            config = SystemConfig.objects.get(key="auto_convert_interval")
            auto_convert_interval = int(config.value)
        except SystemConfig.DoesNotExist:
            pass
        context["auto_convert_interval"] = auto_convert_interval

        # 自動同步製令間隔（預設 30 分鐘）
        auto_sync_companyorder_interval = 30
        try:
            config = SystemConfig.objects.get(key="auto_sync_companyorder_interval")
            auto_sync_companyorder_interval = int(config.value)
        except SystemConfig.DoesNotExist:
            pass
        context["auto_sync_companyorder_interval"] = auto_sync_companyorder_interval

        # 轉換成字典格式，保持與原本模板的相容性
        workorders_list = []
        for order in self.get_queryset():
            # 格式化公司代號，確保是兩位數格式（例如：2 -> 02）
            formatted_company_code = order.company_code
            if formatted_company_code and formatted_company_code.isdigit():
                formatted_company_code = formatted_company_code.zfill(2)

            workorder_dict = {
                "company_code": formatted_company_code,
                "mkordno": order.mkordno,
                "MKOrdNO": f"{formatted_company_code}_{order.mkordno}",
                "ProductID": order.product_id,
                "ProdtQty": order.prodt_qty,
                "EstTakeMatDate": order.est_take_mat_date,
                "EstStockOutDate": order.est_stock_out_date,
                "is_converted": order.is_converted,
                "conversion_status": "已轉換" if order.is_converted else "未轉換",
            }
            workorders_list.append(workorder_dict)

        context["workorders"] = workorders_list

        return context

    def post(self, request, *args, **kwargs):
        """處理 POST 請求，用於管理員設定功能"""
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "您沒有權限執行此操作")
            return self.get(request, *args, **kwargs)

        workorder_logger = logging.getLogger("workorder")

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
            old_value = request.POST.get(
                "current_auto_sync_companyorder_interval", "30"
            )
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
                messages.warning(
                    request, f"間隔設定已更新，但重新設定定時任務失敗：{str(e)}"
                )

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
        return JsonResponse({"error": "未登入"}, status=401)

    try:
        company_code = request.GET.get("company_code")
        if not company_code:
            return JsonResponse({"error": "缺少公司代號參數"}, status=400)

        # 取得該公司的製令單數量統計
        total_orders = CompanyOrder.objects.filter(company_code=company_code).count()
        converted_orders = CompanyOrder.objects.filter(
            company_code=company_code, is_converted=True
        ).count()
        pending_orders = total_orders - converted_orders

        return JsonResponse(
            {
                "total_orders": total_orders,
                "converted_orders": converted_orders,
                "pending_orders": pending_orders,
                "company_code": company_code,
            }
        )

    except Exception as e:
        return JsonResponse({"error": f"查詢失敗：{str(e)}"}, status=500)

class MesOrderListView(LoginRequiredMixin, ListView):
    """
    MES 工單管理清單：集中查看已轉成 MES 的工單，並提供批量派工入口
    """

    model = WorkOrder
    template_name = "workorder/mes_orders.html"
    context_object_name = "orders"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # 排除已完工的工單（已完工的工單不應該在 MES 工單管理中顯示）
        qs = qs.exclude(status='completed')
        
        # 依關鍵字過濾（工單號/產品/公司代號）
        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search)
                | Q(product_code__icontains=search)
                | Q(company_code__icontains=search)
            )
        # 派工狀態過濾：undispatched/dispatched/all
        status = self.request.GET.get("dispatch_status", "all")
        if status == "undispatched":
            qs = qs.exclude(order_number__in=WorkOrderDispatch.objects.values_list("order_number", flat=True))
        elif status == "dispatched":
            qs = qs.filter(order_number__in=WorkOrderDispatch.objects.values_list("order_number", flat=True))
        
        # 添加公司名稱
        qs = qs.extra(
            select={'company_name': '''
                SELECT company_name 
                FROM erp_integration_companyconfig 
                WHERE erp_integration_companyconfig.company_code = workorder_workorder.company_code
            '''}
        )
        
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dispatched_numbers = set(
            WorkOrderDispatch.objects.values_list("order_number", flat=True)
        )
        ctx["dispatched_map"] = dispatched_numbers
        ctx["search"] = self.request.GET.get("search", "")
        ctx["dispatch_status"] = self.request.GET.get("dispatch_status", "all")
        
        # 統計資料（排除已完工的工單）
        total_orders = WorkOrder.objects.exclude(status='completed').count()
        dispatched_orders = WorkOrderDispatch.objects.count()
        undispatched_orders = total_orders - dispatched_orders
        
        ctx["total_orders"] = total_orders
        ctx["dispatched_orders"] = dispatched_orders
        ctx["undispatched_orders"] = undispatched_orders
        
        # 讀取自動批次派工間隔設定
        auto_dispatch_interval = 60
        try:
            config = SystemConfig.objects.get(key="auto_batch_dispatch_interval")
            auto_dispatch_interval = int(config.value)
        except SystemConfig.DoesNotExist:
            pass
        ctx["auto_dispatch_interval"] = auto_dispatch_interval
        
        return ctx

@login_required
@require_POST
def mes_orders_bulk_dispatch(request):
    """
    批量派工：從 MES 工單管理頁選取多筆工單，建立派工單
    """
    import json

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "資料格式錯誤"}, status=400)

    order_numbers = payload.get("order_numbers") or []
    if not order_numbers:
        return JsonResponse({"error": "沒有選取工單"}, status=400)

    created = 0
    skipped = 0
    for no in order_numbers:
        # 查詢所有匹配的工單
        # 使用公司代號和工單號碼組合查詢，確保唯一性
        work_orders = WorkOrder.objects.filter(order_number=no)
        # 注意：這裡需要從請求中獲取公司代號，暫時保持原有邏輯
        if not work_orders.exists():
            skipped += 1
            continue
        
        # 如果有多個工單，只處理第一個（保持原有行為）
        wo = work_orders.first()
        
        # 若已有派工單，略過
        if WorkOrderDispatch.objects.filter(order_number=no).exists():
            skipped += 1
            continue
        
        # 建立派工單，直接設定為生產中狀態
        dispatch = WorkOrderDispatch.objects.create(
            company_code=getattr(wo, "company_code", None),
            order_number=wo.order_number,
            product_code=wo.product_code,
            planned_quantity=wo.quantity,
            status="in_production",  # 直接設定為生產中
            dispatch_date=timezone.now().date(),  # 設定派工日期為今天
            created_by=str(request.user) if request.user.is_authenticated else "system",
        )
        created += 1
        
        # 記錄派工單建立日誌
        workorder_logger.info(
            f"批量派工：工單 {wo.order_number} 轉派為生產中狀態。操作者: {request.user}, IP: {request.META.get('REMOTE_ADDR')}"
        )

    return JsonResponse({"success": True, "created": created, "skipped": skipped})

@login_required
@require_POST
def mes_order_dispatch(request):
    """
    單筆派工：為指定工單建立派工單
    """
    order_number = request.POST.get("order_number")
    if not order_number:
        return JsonResponse({"error": "工單號碼不能為空"}, status=400)
    
    # 使用 first() 避免 MultipleObjectsReturned 錯誤
    # 注意：這裡需要從請求中獲取公司代號，暫時保持原有邏輯
    wo = WorkOrder.objects.filter(order_number=order_number).first()
    if not wo:
        return JsonResponse({"error": "工單不存在"}, status=400)
    
    # 檢查是否已有派工單
    if WorkOrderDispatch.objects.filter(order_number=order_number).exists():
        return JsonResponse({"error": "此工單已有派工單"}, status=400)
    
    # 建立派工單，直接設定為生產中狀態
    dispatch = WorkOrderDispatch.objects.create(
        company_code=getattr(wo, "company_code", None),
        order_number=wo.order_number,
        product_code=wo.product_code,
        planned_quantity=wo.quantity,
        status="in_production",  # 直接設定為生產中
        dispatch_date=timezone.now().date(),  # 設定派工日期為今天
        created_by=str(request.user) if request.user.is_authenticated else "system",
    )
    
    # 記錄派工單建立日誌
    workorder_logger.info(
        f"單筆派工：工單 {wo.order_number} 轉派為生產中狀態。操作者: {request.user}, IP: {request.META.get('REMOTE_ADDR')}"
    )
    
    return JsonResponse({"success": True, "message": "派工單建立成功，已設定為生產中狀態"})

@login_required
@require_POST
def mes_order_delete(request):
    """
    刪除工單：刪除指定的 MES 工單
    """
    order_number = request.POST.get("order_number")
    if not order_number:
        return JsonResponse({"error": "工單號碼不能為空"}, status=400)
    
    # 使用 first() 避免 MultipleObjectsReturned 錯誤
    # 注意：這裡需要從請求中獲取公司代號，暫時保持原有邏輯
    wo = WorkOrder.objects.filter(order_number=order_number).first()
    if not wo:
        return JsonResponse({"error": "工單不存在"}, status=400)
    
    # 檢查是否有派工單
    if WorkOrderDispatch.objects.filter(order_number=order_number).exists():
        return JsonResponse({"error": "此工單已有派工單，無法刪除"}, status=400)
    
    # 刪除工單
    wo.delete()
    
    return JsonResponse({"success": True, "message": "工單刪除成功"})

@login_required
@require_POST
def mes_orders_auto_dispatch(request):
    """
    自動批次派工：自動為所有未派工的工單建立派工單
    """
    try:
        # 取得所有未派工的工單（修復多公司系統的派工邏輯）
        undispatched_orders = WorkOrder.objects.all()
        
        # 檢查每個工單是否已有對應的派工單（使用 order_number + product_code 組合）
        truly_undispatched = []
        for wo in undispatched_orders:
            dispatch_exists = WorkOrderDispatch.objects.filter(
                order_number=wo.order_number,
                product_code=wo.product_code
            ).exists()
            if not dispatch_exists:
                truly_undispatched.append(wo)
        
        created = 0
        for wo in truly_undispatched:
            # 建立派工單，直接設定為生產中狀態
            dispatch = WorkOrderDispatch.objects.create(
                company_code=getattr(wo, "company_code", None),
                order_number=wo.order_number,
                product_code=wo.product_code,
                planned_quantity=wo.quantity,
                status="in_production",  # 直接設定為生產中
                dispatch_date=timezone.now().date(),  # 設定派工日期為今天
                created_by=str(request.user) if request.user.is_authenticated else "system",
            )
            created += 1
            
            # 記錄派工單建立日誌
            workorder_logger.info(
                f"自動批次派工：工單 {wo.order_number} 轉派為生產中狀態。操作者: {request.user}, IP: {request.META.get('REMOTE_ADDR')}"
            )
        
        return JsonResponse({
            "success": True, 
            "message": f"自動批次派工完成，共建立 {created} 筆派工單"
        })
        
    except Exception as e:
        return JsonResponse({"error": f"自動批次派工失敗：{str(e)}"}, status=500)

@login_required
@require_POST
def mes_orders_set_auto_dispatch_interval(request):
    """
    設定自動批次派工間隔
    """
    try:
        interval = request.POST.get("interval")
        if not interval or not interval.isdigit():
            return JsonResponse({"error": "間隔時間必須是正整數"}, status=400)
        
        interval_minutes = int(interval)
        if interval_minutes < 1 or interval_minutes > 1440:  # 1分鐘到24小時
            return JsonResponse({"error": "間隔時間必須在1-1440分鐘之間"}, status=400)
        
        # 更新系統設定
        SystemConfig.objects.update_or_create(
            key="auto_batch_dispatch_interval",
            defaults={"value": str(interval_minutes)}
        )
        
        # 更新 Celery 定時任務
        from django_celery_beat.models import PeriodicTask, IntervalSchedule
        
        # 建立或更新間隔排程
        interval_schedule, created = IntervalSchedule.objects.get_or_create(
            every=interval_minutes,
            period=IntervalSchedule.MINUTES,
        )
        
        # 更新定時任務
        periodic_task, created = PeriodicTask.objects.get_or_create(
            name="自動批次派工",
            defaults={
                "task": "workorder.tasks.auto_batch_dispatch_orders",
                "interval": interval_schedule,
                "enabled": True,
            },
        )
        
        if not created:
            periodic_task.interval = interval_schedule
            periodic_task.enabled = True
            periodic_task.save()
        
        workorder_logger.info(
            f"管理員 {request.user} 設定自動批次派工間隔為 {interval_minutes} 分鐘。IP: {request.META.get('REMOTE_ADDR')}"
        )
        
        return JsonResponse({
            "success": True, 
            "message": f"自動批次派工間隔已設定為 {interval_minutes} 分鐘"
        })
        
    except Exception as e:
        workorder_logger.error(f"設定自動批次派工間隔失敗：{str(e)}")
        return JsonResponse({"error": f"設定失敗：{str(e)}"}, status=500)

@method_decorator(login_required, name='dispatch')
class CreateMissingWorkOrdersView(LoginRequiredMixin, View):
    """
    從填報資料創建缺失工單的視圖
    提供網頁介面讓使用者執行工單創建功能
    """
    
    def get(self, request):
        """顯示工單創建頁面"""
        
        # 統計資訊
        total_fill_works = FillWork.objects.count()
        total_workorders = WorkOrder.objects.count()
        
        # 分析可能缺失的工單
        missing_workorders = []
        try:
            # 取得所有填報資料中的唯一組合
            fill_work_combinations = FillWork.objects.values(
                'company_name', 'workorder', 'product_id'
            ).distinct()
            
            for combo in fill_work_combinations:
                # 檢查是否已存在對應的工單
                existing_workorder = WorkOrder.objects.filter(
                    order_number=combo['workorder'],
                    product_code=combo['product_id']
                ).first()
                
                if not existing_workorder:
                    missing_workorders.append({
                        'company_name': combo['company_name'],
                        'workorder': combo['workorder'],
                        'product_id': combo['product_id']
                    })
        except Exception as e:
            workorder_logger.error(f"分析缺失工單時發生錯誤: {e}")
        
        context = {
            'total_fill_works': total_fill_works,
            'total_workorders': total_workorders,
            'missing_workorders': missing_workorders,
            'missing_count': len(missing_workorders)
        }
        
        return render(request, 'workorder/workorder/create_missing_workorders.html', context)
    
    def post(self, request):
        """執行工單創建功能"""
        # 直接定義函數，避免循環導入問題
        def create_missing_workorders_from_fillwork():
            logger = logging.getLogger(__name__)
            
            # 統計資訊
            created_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            try:
                # 取得所有填報資料
                fill_works = FillWork.objects.all()
                
                for fill_work in fill_works:
                    try:
                        # 檢查必要欄位
                        if not fill_work.company_name or not fill_work.workorder or not fill_work.product_id:
                            workorder_logger.warning(f"填報資料缺少必要欄位: ID={fill_work.id}")
                            error_count += 1
                            continue
                        
                        # 從公司名稱查找公司代號
                        company_code = None
                        try:
                            company_config = CompanyConfig.objects.filter(
                                company_name__icontains=fill_work.company_name
                            ).first()
                            
                            if company_config:
                                company_code = company_config.company_code
                            else:
                                # 如果找不到公司配置，嘗試從製令資料中查找
                                mkord_main = PrdMKOrdMain.objects.filter(
                                    MKOrdNO=fill_work.workorder,
                                    ProductID=fill_work.product_id
                                ).first()
                                
                                if mkord_main:
                                    # 從製令資料中查找公司代號
                                    company_order = CompanyOrder.objects.filter(
                                        mkordno=fill_work.workorder,
                                        product_id=fill_work.product_id
                                    ).first()
                                    
                                    if company_order:
                                        company_code = company_order.company_code
                        
                        except Exception as e:
                            workorder_logger.error(f"查找公司代號時發生錯誤: {e}")
                            error_count += 1
                            continue
                        
                        if not company_code:
                            workorder_logger.warning(f"無法找到公司代號: 公司名稱={fill_work.company_name}, 工單號={fill_work.workorder}")
                            error_count += 1
                            continue
                        
                        # 檢查工單是否已存在
                        existing_workorder = WorkOrder.objects.filter(
                            company_code=company_code,
                            order_number=fill_work.workorder,
                            product_code=fill_work.product_id
                        ).first()
                        
                        if existing_workorder:
                            workorder_logger.info(f"工單已存在，跳過: {company_code}-{fill_work.workorder}-{fill_work.product_id}")
                            skipped_count += 1
                            continue
                        
                        # 創建新工單
                        with transaction.atomic():
                            new_workorder = WorkOrder.objects.create(
                                company_code=company_code,
                                order_number=fill_work.workorder,
                                product_code=fill_work.product_id,
                                quantity=fill_work.planned_quantity or 0,
                                status='pending',
                                order_source='mes'  # 從填報資料創建的工單標記為MES來源
                            )
                            
                            created_count += 1
                            workorder_logger.info(f"成功創建工單: {new_workorder}")
                        
                    except Exception as e:
                        workorder_logger.error(f"處理填報資料時發生錯誤 (ID={fill_work.id}): {e}")
                        error_count += 1
                        errors.append({
                            'fill_work_id': fill_work.id,
                            'error': str(e)
                        })
                
                # 記錄統計結果
                workorder_logger.info(f"工單創建完成 - 成功: {created_count}, 跳過: {skipped_count}, 錯誤: {error_count}")
                
                return {
                    'success': True,
                    'created_count': created_count,
                    'skipped_count': skipped_count,
                    'error_count': error_count,
                    'errors': errors
                }
                
            except Exception as e:
                workorder_logger.error(f"創建缺失工單時發生嚴重錯誤: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'created_count': created_count,
                    'skipped_count': skipped_count,
                    'error_count': error_count,
                    'errors': errors
                }
        
        try:
            # 執行工單創建功能
            result = create_missing_workorders_from_fillwork()
            
            if result['success']:
                messages.success(
                    request,
                    f'工單創建完成！成功創建 {result["created_count"]} 個工單，'
                    f'跳過 {result["skipped_count"]} 個已存在的工單，'
                    f'處理 {result["error_count"]} 個錯誤記錄。'
                )
            else:
                messages.error(
                    request,
                    f'工單創建失敗: {result["error"]}'
                )
            
            # 重定向到工單列表頁面
            return redirect('workorder:list')
            
        except Exception as e:
            workorder_logger.error(f"執行工單創建時發生錯誤: {e}")
            messages.error(request, f'執行過程中發生錯誤: {e}')
            return redirect('workorder:list')


