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
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import logging

from ..models import WorkOrder
from ..workorder_erp.models import CompanyOrder, SystemConfig
from ..forms import WorkOrderForm
from erp_integration.models import CompanyConfig
from ..workorder_dispatch.models import WorkOrderDispatch

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

    def get_context_data(self, **kwargs):
        """添加上下文資料，包括工序統計和所有已核准的報工記錄"""
        context = super().get_context_data(**kwargs)
        workorder = self.get_object()

        # 取得公司名稱（若 company_code 為空，嘗試推導）
        company_name = workorder.company_code or '-'
        code = workorder.company_code
        if not code:
            # 1) 嘗試從 CompanyOrder 推導
            try:
                from ..workorder_erp.models import CompanyOrder
                co = CompanyOrder.objects.filter(mkordno=workorder.order_number).first()
                if co and co.company_code:
                    code = co.company_code
            except Exception:
                pass
            # 2) 若仍無，保留 None
        if code:
            config = CompanyConfig.objects.filter(company_code=code).first()
            if config:
                company_name = config.company_name
        # 3) 最後後備：從填報記錄直接取公司名稱（以實際填報為準）
        if company_name in (None, '-', ''):
            try:
                from workorder.fill_work.models import FillWork
                fw = (
                    FillWork.objects
                    .filter(workorder=workorder.order_number)
                    .exclude(company_name__isnull=True)
                    .exclude(company_name__exact='')
                    .order_by('-created_at')
                    .first()
                )
                if fw:
                    company_name = fw.company_name
            except Exception:
                pass
        context['company_name'] = company_name

        # 計算已完成工序數量
        completed_processes_count = workorder.processes.filter(
            status="completed"
        ).count()

        # 計算進行中工序數量
        in_progress_processes_count = workorder.processes.filter(
            status="in_progress"
        ).count()

        context["completed_processes_count"] = completed_processes_count
        context["in_progress_processes_count"] = in_progress_processes_count

        # 獲取所有已核准的報工記錄
        from workorder.fill_work.models import FillWork

        # 獲取所有已核准的填報記錄
        fill_work_reports = FillWork.objects.filter(
            workorder=workorder.order_number,
            approval_status="approved"
        ).order_by("work_date", "start_time")

        # 處理填報記錄
        all_reports = []

        for report in fill_work_reports:
            all_reports.append(
                {
                    "type": "fill_work",
                    "report_date": report.work_date,
                    "process_name": report.operation or "未指定",
                    "operator": report.operator or "-",
                    "equipment": report.equipment or "-",
                    "work_quantity": report.work_quantity or 0,
                    "defect_quantity": report.defect_quantity or 0,
                    "work_hours": report.work_hours_calculated or 0,
                    "overtime_hours": report.overtime_hours_calculated or 0,
                    "report_source": "填報作業",
                    "report_time": report.start_time,
                    "start_time": report.start_time,
                    "end_time": report.end_time,
                    "remarks": report.remarks or "",
                    "abnormal_notes": report.abnormal_notes or "",
                    "approved_by": report.approved_by or "",
                    "approved_at": report.approved_at,
                }
            )

        # 按報工日期和開始時間排序（最早的在前）
        all_reports.sort(
            key=lambda x: (x["report_date"], x["start_time"]), reverse=False
        )

        # 計算統計資料
        from collections import defaultdict

        stats_by_process = defaultdict(
            lambda: {
                "process_name": "",
                "total_good_quantity": 0,
                "total_defect_quantity": 0,
                "report_count": 0,
                "total_work_hours": 0.0,
                "operators": set(),
                "equipment": set(),
            }
        )

        # 總計資料
        total_stats = {
            "total_good_quantity": 0,
            "total_defect_quantity": 0,
            "total_report_count": len(all_reports),
            "total_work_hours": 0.0,
            "total_overtime_hours": 0.0,
            "total_all_hours": 0.0,
            "unique_operators": set(),
            "unique_equipment": set(),
        }

        # 按工序分組統計
        for report in all_reports:
            process_name = report["process_name"]

            # 更新工序統計
            stats_by_process[process_name]["process_name"] = process_name
            stats_by_process[process_name]["total_good_quantity"] += report[
                "work_quantity"
            ]
            stats_by_process[process_name]["total_defect_quantity"] += report[
                "defect_quantity"
            ]
            stats_by_process[process_name]["report_count"] += 1
            # 確保工作時數為 float 類型
            work_hours = (
                float(report["work_hours"]) if report["work_hours"] is not None else 0.0
            )
            stats_by_process[process_name]["total_work_hours"] += work_hours

            # 更新總計
            total_stats["total_good_quantity"] += report["work_quantity"]
            total_stats["total_defect_quantity"] += report["defect_quantity"]
            total_stats["total_work_hours"] += work_hours
            # 確保加班時數為 float 類型
            overtime_hours = (
                float(report["overtime_hours"])
                if report["overtime_hours"] is not None
                else 0.0
            )
            total_stats["total_overtime_hours"] += overtime_hours

            # 記錄作業員和設備
            if report["operator"] != "-":
                stats_by_process[process_name]["operators"].add(report["operator"])
                total_stats["unique_operators"].add(report["operator"])

            if report["equipment"] != "-":
                stats_by_process[process_name]["equipment"].add(report["equipment"])
                total_stats["unique_equipment"].add(report["equipment"])

        # 計算總時數
        total_stats["total_all_hours"] = (
            total_stats["total_work_hours"] + total_stats["total_overtime_hours"]
        )

        # 轉換 set 為 list 以便在模板中使用
        for process_stats in stats_by_process.values():
            process_stats["operators"] = list(process_stats["operators"])
            process_stats["equipment"] = list(process_stats["equipment"])

        total_stats["unique_operators"] = list(total_stats["unique_operators"])
        total_stats["unique_equipment"] = list(total_stats["unique_equipment"])

        # 按照工序的實際執行順序排列統計資料
        # 根據報工記錄的時間順序，確定工序的執行順序
        process_order = {}
        for i, report in enumerate(all_reports):
            process_name = report["process_name"]
            if process_name not in process_order:
                process_order[process_name] = i

        # 按照工序執行順序排序統計資料
        sorted_stats_by_process = dict(
            sorted(
                stats_by_process.items(),
                key=lambda x: process_order.get(x[0], 999),  # 如果找不到順序，排在最後
            )
        )

        context["all_production_reports"] = all_reports
        context["total_reports_count"] = len(all_reports)
        context["production_stats_by_process"] = sorted_stats_by_process
        context["production_total_stats"] = total_stats

        # 添加完工判斷資訊
        try:
            from ..services.completion_service import WorkOrderCompletionService
            completion_summary = WorkOrderCompletionService.get_completion_summary(workorder.id)
            context["completion_summary"] = completion_summary
        except Exception as e:
            workorder_logger.error(f"獲取工單 {workorder.order_number} 完工摘要失敗: {str(e)}")
            context["completion_summary"] = {'error': '獲取完工摘要失敗'}

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
        from erp_integration.models import CompanyConfig

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
        from workorder.workorder_erp.models import SystemConfig

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

        from workorder.workorder_erp.models import SystemConfig
        from django.core.management import call_command
        import logging

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
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        dispatched_numbers = set(
            WorkOrderDispatch.objects.values_list("order_number", flat=True)
        )
        ctx["dispatched_map"] = dispatched_numbers
        ctx["search"] = self.request.GET.get("search", "")
        ctx["dispatch_status"] = self.request.GET.get("dispatch_status", "all")
        
        # 統計資料
        total_orders = WorkOrder.objects.count()
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
        try:
            wo = WorkOrder.objects.get(order_number=no)
        except WorkOrder.DoesNotExist:
            skipped += 1
            continue
        # 若已有派工單，略過
        if WorkOrderDispatch.objects.filter(order_number=no).exists():
            skipped += 1
            continue
        WorkOrderDispatch.objects.create(
            company_code=getattr(wo, "company_code", None),
            order_number=wo.order_number,
            product_code=wo.product_code,
            planned_quantity=wo.quantity,
            status="pending",
            created_by=str(request.user) if request.user.is_authenticated else "system",
        )
        created += 1

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
    
    try:
        wo = WorkOrder.objects.get(order_number=order_number)
    except WorkOrder.DoesNotExist:
        return JsonResponse({"error": "工單不存在"}, status=400)
    
    # 檢查是否已有派工單
    if WorkOrderDispatch.objects.filter(order_number=order_number).exists():
        return JsonResponse({"error": "此工單已有派工單"}, status=400)
    
    # 建立派工單
    WorkOrderDispatch.objects.create(
        company_code=getattr(wo, "company_code", None),
        order_number=wo.order_number,
        product_code=wo.product_code,
        planned_quantity=wo.quantity,
        status="pending",
        created_by=str(request.user) if request.user.is_authenticated else "system",
    )
    
    return JsonResponse({"success": True, "message": "派工單建立成功"})

@login_required
@require_POST
def mes_order_delete(request):
    """
    刪除工單：刪除指定的 MES 工單
    """
    order_number = request.POST.get("order_number")
    if not order_number:
        return JsonResponse({"error": "工單號碼不能為空"}, status=400)
    
    try:
        wo = WorkOrder.objects.get(order_number=order_number)
    except WorkOrder.DoesNotExist:
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
        # 取得所有未派工的工單
        undispatched_orders = WorkOrder.objects.exclude(
            order_number__in=WorkOrderDispatch.objects.values_list("order_number", flat=True)
        )
        
        created = 0
        for wo in undispatched_orders:
            WorkOrderDispatch.objects.create(
                company_code=getattr(wo, "company_code", None),
                order_number=wo.order_number,
                product_code=wo.product_code,
                planned_quantity=wo.quantity,
                status="pending",
                created_by=str(request.user) if request.user.is_authenticated else "system",
            )
            created += 1
        
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
        from ..fill_work.models import FillWork
        from ..models import WorkOrder
        
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
            from ..fill_work.models import FillWork
            from ..models import WorkOrder
            from erp_integration.models import CompanyConfig
            from ..workorder_erp.models import PrdMKOrdMain, CompanyOrder
            from django.db import transaction
            import logging
            
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


