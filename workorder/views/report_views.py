"""
報工管理視圖
包含作業員報工、SMT報工、主管報工等相關功能
使用 Django 類別視圖，符合設計規範
"""

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib.auth.decorators import login_required

from ..workorder_reporting.models import BackupOperatorSupplementReport, BackupSMTSupplementReport
from ..forms import (
    SMTSupplementReportForm,
    BackupOperatorSupplementReportForm,
    BackupRDSampleSupplementReportForm,
    # 移除主管報工相關的 form，避免混淆
    # 主管職責：監督、審核、管理，不代為報工
)
from ..forms_smt_rd_sample import SMTRDSampleSupplementReportForm
from ..forms_operator_rd_sample import OperatorRDSampleSupplementReportForm
from process.models import Operator, ProcessName
from workorder.models import WorkOrder
from production.models import ProductionLine


class ReportIndexView(LoginRequiredMixin, ListView):
    """
    生產環境報工管理首頁視圖
    顯示生產環境的報工功能總覽
    """

    template_name = "workorder/backup_report/backup_index.html"
    context_object_name = "reports"

    def get_queryset(self):
        """取得最近的報工記錄"""
        return BackupOperatorSupplementReport.objects.all()[:10]

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)

        from ..services.statistics_service import StatisticsService

        # 使用統一的統計服務 - 顯示全部統計（作業員+SMT）
        stats_data = StatisticsService.get_report_index_statistics()

        context.update(stats_data)

        return context


class OperatorSupplementReportListView(LoginRequiredMixin, ListView):
    """
    作業員補登報工列表視圖
    顯示所有待核准的作業員補登報工記錄
    """

    model = BackupOperatorSupplementReport
    template_name = "workorder/backup_report/backup_operator/backup_supplement/backup_index.html"
    context_object_name = "supplement_reports"
    paginate_by = 20  # 每頁顯示20筆記錄

    def get_queryset(self):
        """取得查詢集 - 只顯示待核准的記錄，並支援篩選功能"""
        queryset = super().get_queryset().filter(approval_status="pending")

        # 取得篩選參數
        company_name = self.request.GET.get("company_name", "").strip()
        operator_name = self.request.GET.get("operator_name", "").strip()
        workorder_no = self.request.GET.get("workorder_no", "").strip()
        product_id = self.request.GET.get("product_id", "").strip()
        process_name = self.request.GET.get("process_name", "").strip()
        start_date = self.request.GET.get("start_date", "").strip()
        end_date = self.request.GET.get("end_date", "").strip()

        # 應用篩選條件
        if company_name:
            queryset = queryset.filter(company_code=company_name)

        if operator_name:
            queryset = queryset.filter(operator__name=operator_name)

        if workorder_no:
            queryset = queryset.filter(
                Q(workorder__order_number__icontains=workorder_no)
                | Q(original_workorder_number__icontains=workorder_no)
            )

        if product_id:
            queryset = queryset.filter(
                Q(product_id__icontains=product_id)
                | Q(workorder__product_code__icontains=product_id)
            )

        if process_name:
            queryset = queryset.filter(process__name=process_name)

        if start_date:
            queryset = queryset.filter(work_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(work_date__lte=end_date)

        return queryset.select_related(
            "operator", "operator__production_line", "workorder", "process", "equipment"
        ).order_by("-work_date", "-start_time")

    def get_context_data(self, **kwargs):
        """添加額外的上下文數據"""
        context = super().get_context_data(**kwargs)

        # 添加篩選參數到上下文，用於保持表單狀態
        context["filters"] = {
            "company_name": self.request.GET.get("company_name", ""),
            "operator_name": self.request.GET.get("operator_name", ""),
            "workorder_no": self.request.GET.get("workorder_no", ""),
            "product_id": self.request.GET.get("product_id", ""),
            "process_name": self.request.GET.get("process_name", ""),
            "start_date": self.request.GET.get("start_date", ""),
            "end_date": self.request.GET.get("end_date", ""),
        }

        # 計算統計數據
        context["pending_count"] = BackupOperatorSupplementReport.objects.filter(
            approval_status="pending"
        ).count()

        context["approved_count"] = BackupOperatorSupplementReport.objects.filter(
            approval_status="approved"
        ).count()

        context["rejected_count"] = BackupOperatorSupplementReport.objects.filter(
            approval_status="rejected"
        ).count()

        # 添加選項數據供篩選下拉選單使用
        context["operators"] = (
            Operator.objects.filter(backupoperatorsupplementreport__approval_status="pending")
            .distinct()
            .order_by("name")
        )

        context["processes"] = (
            ProcessName.objects.filter(
                backupoperatorsupplementreport__approval_status="pending"
            )
            .distinct()
            .order_by("name")
        )

        context["workorders"] = (
            WorkOrder.objects.filter(
                backupoperatorsupplementreport__approval_status="pending"
            )
            .distinct()
            .order_by("-created_at")[:50]
        )  # 限制顯示最近50筆工單

        # 修正：使用公司設定而不是產線名稱
        from erp_integration.models import CompanyConfig

        context["companies"] = CompanyConfig.objects.all().order_by("company_name")

        return context


class OperatorSupplementReportCreateView(LoginRequiredMixin, CreateView):
    """
    備用的作業員補登報工新增視圖
    用於建立新的作業員補登報工記錄
    """

    model = BackupOperatorSupplementReport
    form_class = BackupOperatorSupplementReportForm
    template_name = "workorder/backup_report/backup_operator/backup_supplement/backup_form.html"
    success_url = reverse_lazy("workorder:operator_supplement_report_index")

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        messages.success(self.request, "作業員補登報工記錄建立成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "作業員補登報工記錄建立失敗，請檢查輸入資料！")
        return super().form_invalid(form)


class OperatorSupplementReportUpdateView(LoginRequiredMixin, UpdateView):
    """
    備用的作業員補登報工編輯視圖
    用於編輯現有作業員補登報工記錄
    """

    model = BackupOperatorSupplementReport
    form_class = BackupOperatorSupplementReportForm
    template_name = "workorder/backup_report/backup_operator/backup_supplement/backup_form.html"
    success_url = reverse_lazy("workorder:operator_supplement_report_index")

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, "作業員補登報工記錄更新成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "作業員補登報工記錄更新失敗，請檢查輸入資料！")
        return super().form_invalid(form)


class OperatorSupplementReportDetailView(LoginRequiredMixin, DetailView):
    """
    備用的作業員補登報工詳情視圖
    顯示單一作業員補登報工記錄的詳細資訊
    """

    model = BackupOperatorSupplementReport
    template_name = "workorder/backup_report/backup_operator/backup_supplement/backup_detail.html"
    context_object_name = "report"

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)

        # 獲取公司資訊
        from erp_integration.models import CompanyConfig

        # 直接從記錄的 company_code 欄位獲取公司代號
        company_code = self.object.company_code

        # 獲取公司名稱
        company_name = ""
        if company_code:
            company = CompanyConfig.objects.filter(company_code=company_code).first()
            if company:
                company_name = company.company_name

        context["company_name"] = company_name
        context["company_code"] = company_code

        return context


class SMTSupplementReportListView(LoginRequiredMixin, ListView):
    """
    備用的SMT補登報工列表視圖
    顯示所有SMT補登報工記錄
    """

    model = BackupSMTSupplementReport
    template_name = "workorder/backup_report/backup_smt/backup_supplement/backup_index.html"
    context_object_name = "reports"
    paginate_by = 20
    ordering = ["-work_date", "-start_time"]

    def get_queryset(self):
        """取得查詢集，支援搜尋功能"""
        queryset = super().get_queryset().filter(approval_status="pending")

        # 取得篩選參數
        company_name = self.request.GET.get("company_name", "").strip()
        smt_line = self.request.GET.get("smt_line", "").strip()
        workorder_no = self.request.GET.get("workorder_no", "").strip()
        product_id = self.request.GET.get("product_id", "").strip()
        start_date = self.request.GET.get("start_date", "").strip()
        end_date = self.request.GET.get("end_date", "").strip()

        # 應用篩選條件
        if company_name:
            queryset = queryset.filter(company_code=company_name)

        if smt_line:
            queryset = queryset.filter(equipment__production_line__line_name=smt_line)

        if workorder_no:
            queryset = queryset.filter(
                Q(workorder__order_number__icontains=workorder_no)
                | Q(original_workorder_number__icontains=workorder_no)
            )

        if product_id:
            queryset = queryset.filter(product_id__icontains=product_id)

        if start_date:
            queryset = queryset.filter(work_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(work_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)

        # 計算統計數據
        context["pending_count"] = BackupSMTSupplementReport.objects.filter(
            approval_status="pending"
        ).count()

        context["approved_count"] = BackupSMTSupplementReport.objects.filter(
            approval_status="approved"
        ).count()

        context["rejected_count"] = BackupSMTSupplementReport.objects.filter(
            approval_status="rejected"
        ).count()

        context["total_count"] = BackupSMTSupplementReport.objects.count()

        # 添加篩選參數到上下文，用於保持表單狀態
        context["filters"] = {
            "company_name": self.request.GET.get("company_name", ""),
            "smt_line": self.request.GET.get("smt_line", ""),
            "workorder_no": self.request.GET.get("workorder_no", ""),
            "product_id": self.request.GET.get("product_id", ""),
            "start_date": self.request.GET.get("start_date", ""),
            "end_date": self.request.GET.get("end_date", ""),
        }

        # 添加選項數據供篩選下拉選單使用
        # 公司設定選項
        from erp_integration.models import CompanyConfig

        context["companies"] = CompanyConfig.objects.all().order_by("company_name")

        # SMT 產線選項（從設備的產線取得）
        from equip.models import Equipment
        from production.models import ProductionLine

        smt_equipment = Equipment.objects.filter(
            name__icontains="SMT", production_line__isnull=False
        ).select_related("production_line")

        smt_lines = (
            ProductionLine.objects.filter(equipment__in=smt_equipment)
            .distinct()
            .order_by("line_name")
        )
        context["smt_lines"] = smt_lines

        return context


class SMTSupplementReportCreateView(LoginRequiredMixin, CreateView):
    """
    備用的SMT補登報工新增視圖
    用於建立新的SMT補登報工記錄
    """

    model = BackupSMTSupplementReport
    form_class = SMTSupplementReportForm
    template_name = "workorder/backup_report/backup_smt/backup_supplement/backup_form.html"
    success_url = reverse_lazy("workorder:smt_supplement_report_index")

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        messages.success(self.request, "SMT生產報工記錄建立成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "SMT生產報工記錄建立失敗，請檢查輸入資料！")
        return super().form_invalid(form)


class SMTSupplementReportUpdateView(LoginRequiredMixin, UpdateView):
    """
    備用的SMT補登報工編輯視圖
    用於編輯現有SMT補登報工記錄
    """

    model = BackupSMTSupplementReport
    form_class = SMTSupplementReportForm
    template_name = "workorder/backup_report/backup_smt/backup_supplement/backup_form.html"
    success_url = reverse_lazy("workorder:smt_supplement_report_index")

    def get_context_data(self, **kwargs):
        """添加備用系統標記"""
        context = super().get_context_data(**kwargs)
        context["is_backup"] = True
        return context

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, "SMT生產報工記錄更新成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "SMT生產報工記錄更新失敗，請檢查輸入資料！")
        return super().form_invalid(form)


class SMTSupplementReportDetailView(LoginRequiredMixin, DetailView):
    """
    備用的SMT補登報工詳情視圖
    顯示單一SMT補登報工記錄的詳細資訊
    """

    model = BackupSMTSupplementReport
    template_name = "workorder/backup_report/backup_smt/backup_supplement/backup_detail.html"
    context_object_name = "supplement_report"

    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)

        # 獲取公司資訊
        from erp_integration.models import CompanyConfig

        # 直接從記錄的 company_code 欄位獲取公司代號
        company_code = self.object.company_code

        # 獲取公司名稱
        company_name = ""
        if company_code:
            company = CompanyConfig.objects.filter(company_code=company_code).first()
            if company:
                company_name = company.company_name

        context["company_name"] = company_name
        context["company_code"] = company_code

        # 計算總工作時數
        total_work_hours = float(self.object.work_hours_calculated) + float(self.object.overtime_hours_calculated)
        context["total_work_hours"] = round(total_work_hours, 2)

        return context


class SMTSupplementReportDeleteView(
    LoginRequiredMixin, UserPassesTestMixin, DeleteView
):
    """
    備用的SMT補登報工刪除視圖
    用於刪除SMT補登報工記錄，僅限管理員使用
    """

    model = BackupSMTSupplementReport
    template_name = "workorder/backup_report/backup_smt/backup_supplement/backup_delete_confirm.html"
    context_object_name = "supplement_report"
    success_url = reverse_lazy("workorder:smt_supplement_report_index")

    def test_func(self):
        """檢查用戶是否有刪除權限"""
        try:
            # 獲取要刪除的對象
            obj = self.get_object()
            # 檢查用戶權限
            return self.request.user.is_staff or self.request.user.is_superuser
        except SMTSupplementReport.DoesNotExist:
            # 記錄不存在，返回 False 讓 handle_no_permission 處理
            return False

    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        try:
            obj = self.get_object()
            # 執行刪除
            obj.delete()

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": True, "message": "SMT生產報工記錄刪除成功！"}
                )

            messages.success(request, "SMT生產報工記錄刪除成功！")
            return redirect("workorder:smt_supplement_report_index")
        except SMTSupplementReport.DoesNotExist:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "message": "找不到指定的SMT報工記錄！該記錄可能已被刪除或不存在。",
                    }
                )
            messages.error(
                request, "找不到指定的SMT報工記錄！該記錄可能已被刪除或不存在。"
            )
            return redirect("workorder:smt_supplement_report_index")
        except Exception as e:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": f"刪除失敗：{str(e)}"}
                )
            messages.error(request, f"刪除失敗：{str(e)}")
            return redirect("workorder:smt_supplement_report_index")

    def handle_no_permission(self):
        """處理權限不足的情況"""
        # 檢查是否是因為記錄不存在
        try:
            self.get_object()
            # 如果記錄存在，則是權限問題
            messages.error(self.request, "您沒有權限執行此操作！")
        except SMTSupplementReport.DoesNotExist:
            # 記錄不存在
            messages.error(
                self.request, "找不到指定的SMT報工記錄！該記錄可能已被刪除或不存在。"
            )

        return redirect("workorder:smt_supplement_report_index")


class OperatorSupplementReportDeleteView(
    LoginRequiredMixin, UserPassesTestMixin, DeleteView
):
    """
    備用的作業員補登報工刪除視圖
    僅允許建立者本人或超級用戶刪除
    """

    model = BackupOperatorSupplementReport
    template_name = "workorder/backup_report/backup_operator/backup_supplement/backup_delete_confirm.html"
    context_object_name = "supplement_report"
    success_url = reverse_lazy("workorder:operator_supplement_report_index")

    def test_func(self):
        obj = self.get_object()
        return (
            self.request.user.is_superuser
            or obj.created_by == self.request.user.username
        )

    def handle_no_permission(self):
        messages.error(self.request, "您沒有權限刪除此補登報工記錄！")
        return redirect("workorder:operator_supplement_report_index")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "作業員補登報工記錄刪除成功！")
        return super().delete(request, *args, **kwargs)


class SMTRDSampleSupplementReportCreateView(LoginRequiredMixin, CreateView):
    """
    備用的SMT RD樣品補登報工新增視圖
    用於建立新的SMT RD樣品補登報工記錄
    """

    model = BackupSMTSupplementReport
    form_class = SMTRDSampleSupplementReportForm
    template_name = "workorder/backup_report/backup_smt/backup_rd_sample/backup_form.html"
    success_url = reverse_lazy("workorder:smt_supplement_report_index")

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        messages.success(self.request, "SMT RD樣品生產報工記錄建立成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "SMT RD樣品生產報工記錄建立失敗，請檢查輸入資料！")
        return super().form_invalid(form)


class SMTRDSampleSupplementReportUpdateView(LoginRequiredMixin, UpdateView):
    """
    備用的SMT RD樣品補登報工編輯視圖
    用於編輯現有SMT RD樣品補登報工記錄
    """

    model = BackupSMTSupplementReport
    form_class = SMTRDSampleSupplementReportForm
    template_name = "workorder/backup_report/backup_smt/backup_rd_sample/backup_form.html"
    success_url = reverse_lazy("workorder:smt_supplement_report_index")

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, "SMT RD樣品生產報工記錄更新成功！")
        return super().form_valid(form)

    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "SMT RD樣品生產報工記錄更新失敗，請檢查輸入資料！")
        return super().form_invalid(form)


# 已移除作業員RD樣品補登報工列表視圖 - 只保留新增功能


class OperatorRDSampleSupplementReportCreateView(LoginRequiredMixin, CreateView):
    """
    備用的作業員RD樣品補登報工新增視圖
    使用專用的RD樣品表單
    """

    model = BackupOperatorSupplementReport
    form_class = BackupRDSampleSupplementReportForm
    template_name = "workorder/backup_report/backup_operator/backup_rd_sample_supplement/backup_form.html"

    def get_success_url(self):
        return reverse_lazy("workorder:operator_supplement_report_index")

    def get_initial(self):
        """設定表單初始值"""
        initial = super().get_initial()
        initial["product_id"] = "PFP-CCT"
        initial["original_workorder_number"] = "RD樣品"
        return initial

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        messages.success(self.request, "作業員RD樣品補登報工記錄已成功建立！")
        return super().form_valid(form)


class OperatorRDSampleSupplementReportUpdateView(LoginRequiredMixin, UpdateView):
    """
    備用的作業員RD樣品補登報工編輯視圖
    使用專用的RD樣品表單
    """

    model = BackupOperatorSupplementReport
    form_class = BackupRDSampleSupplementReportForm
    template_name = "workorder/backup_report/backup_operator/backup_rd_sample_supplement/backup_form.html"

    def get_success_url(self):
        return reverse_lazy("workorder:operator_rd_sample_supplement_report_index")

    def form_valid(self, form):
        """表單驗證成功時的處理"""
        messages.success(self.request, "作業員RD樣品補登報工記錄已成功更新！")
        return super().form_valid(form)


# 已移除作業員RD樣品補登報工詳情視圖 - 只保留新增功能


# 已移除作業員RD樣品補登報工刪除視圖 - 只保留新增功能


@require_POST
@login_required
def approve_report(request, report_id):
    """
    核准報工記錄
    用於核准作業員補登報工或SMT生產報工記錄
    """
    try:
        report_type = request.POST.get("report_type")
        if report_type == "operator":
            report = get_object_or_404(OperatorSupplementReport, id=report_id)
        elif report_type == "smt":
            report = get_object_or_404(SMTSupplementReport, id=report_id)
        else:
            messages.error(request, "無效的報工記錄類型！")
            return redirect("workorder:backup_report_index")

        if report.can_approve(request.user):
            report.approve(request.user, request.POST.get("remarks", ""))

            # 核准成功後，同步到生產中工單詳情資料表
            try:
                from workorder.services import ProductionReportSyncService

                if hasattr(report, "workorder") and report.workorder:
                    ProductionReportSyncService.sync_specific_workorder(
                        report.workorder.id
                    )
            except Exception as sync_error:
                # 同步失敗不影響核准流程，只記錄錯誤
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"同步報工記錄到生產詳情失敗: {str(sync_error)}")

            messages.success(request, "報工記錄核准成功！")
        else:
            messages.error(request, "您沒有權限核准此報工記錄！")

    except Exception as e:
        messages.error(request, f"核准失敗：{str(e)}")

    return redirect("workorder:backup_report_index")


@require_POST
@login_required
def reject_report(request, report_id):
    """
    駁回報工記錄
    用於駁回作業員補登報工或SMT生產報工記錄
    """
    try:
        report_type = request.POST.get("report_type")
        if report_type == "operator":
            report = get_object_or_404(OperatorSupplementReport, id=report_id)
        elif report_type == "smt":
            report = get_object_or_404(SMTSupplementReport, id=report_id)
        else:
            messages.error(request, "無效的報工記錄類型！")
            return redirect("workorder:backup_report_index")

        if report.can_approve(request.user):
            report.reject(request.user, request.POST.get("reason", ""))
            messages.success(request, "報工記錄駁回成功！")
        else:
            messages.error(request, "您沒有權限駁回此報工記錄！")

    except Exception as e:
        messages.error(request, f"駁回失敗：{str(e)}")

    return redirect("workorder:backup_report_index")


class BackupReportIndexView(ReportIndexView):
    """
    測試環境報工管理首頁視圖
    使用與 ReportIndexView 相同的邏輯，但顯示測試環境標題
    """
    template_name = 'workorder/backup_report/backup_index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 添加備用標識
        context['is_backup'] = True
        return context
