"""
已完工工單視圖模組
提供已完工工單的列表、詳情等功能
"""

from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from ..models import CompletedWorkOrder, CompletedWorkOrderProcess, CompletedProductionReport

import logging

logger = logging.getLogger(__name__)


class CompletedWorkOrderListView(LoginRequiredMixin, ListView):
    """
    已完工工單列表視圖
    顯示所有已完工的工單，支援搜尋和分頁功能
    """
    model = CompletedWorkOrder
    template_name = 'workorder/completed_workorder/completed_workorder_list.html'
    context_object_name = 'completed_workorders'
    paginate_by = 20
    ordering = ['-completed_at']

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
        
        # 統計資料 - 排除 RD樣品的已完工工單數量
        queryset = self.get_queryset()
        context['total_completed'] = queryset.exclude(order_number__icontains='RD樣品').count()
        
        # RD樣品工單統計
        context['total_rd_samples'] = queryset.filter(order_number__icontains='RD樣品').count()
        
        # 為每個工單添加公司名稱和重新計算工作時數
        try:
            from erp_integration.models import CompanyConfig
            company_configs = {config.company_code: config.company_name 
                             for config in CompanyConfig.objects.all()}
            
            for workorder in context['completed_workorders']:
                # 添加公司名稱顯示
                workorder.company_name_display = (
                    workorder.company_name or 
                    company_configs.get(workorder.company_code, workorder.company_code)
                )
                
                # 重新計算工作時數（從報工記錄動態計算）
                from workorder.models import CompletedProductionReport
                production_reports = CompletedProductionReport.objects.filter(
                    completed_workorder_id=workorder.id
                )
                
                # 動態計算統計資料
                workorder.total_work_hours = sum(report.work_hours for report in production_reports)
                workorder.total_overtime_hours = sum(report.overtime_hours for report in production_reports)
                workorder.total_all_hours = workorder.total_work_hours + workorder.total_overtime_hours
                workorder.total_good_quantity = sum(report.work_quantity for report in production_reports)
                workorder.total_defect_quantity = sum(report.defect_quantity for report in production_reports)
                workorder.total_report_count = production_reports.count()
                
        except Exception:
            # 如果查詢公司配置失敗，使用公司代號作為備用
            for workorder in context['completed_workorders']:
                workorder.company_name_display = workorder.company_code
        
        return context


class CompletedWorkOrderDetailView(LoginRequiredMixin, DetailView):
    """
    已完工工單詳情視圖
    顯示單一已完工工單的詳細資訊
    """
    model = CompletedWorkOrder
    template_name = 'workorder/completed_workorder/completed_workorder_detail.html'
    context_object_name = 'completed_workorder'

    def get_context_data(self, **kwargs):
        """添加上下文資料，包括工序統計和所有填報記錄"""
        context = super().get_context_data(**kwargs)
        completed_workorder = self.get_object()
        
        # 獲取公司名稱
        company_name = completed_workorder.company_name or '-'
        if not company_name or company_name == '-':
            try:
                from erp_integration.models import CompanyConfig
                company_config = CompanyConfig.objects.filter(
                    company_code=completed_workorder.company_code
                ).first()
                if company_config:
                    company_name = company_config.company_name
            except Exception:
                pass
        context['company_name'] = company_name
        
        # 計算已完成工序數量
        from workorder.models import CompletedWorkOrderProcess
        completed_processes_count = CompletedWorkOrderProcess.objects.filter(
            completed_workorder_id=completed_workorder.id,
            status='completed'
        ).count()
        context['completed_processes_count'] = completed_processes_count
        
        # 獲取所有填報記錄
        from workorder.models import CompletedProductionReport
        production_reports = CompletedProductionReport.objects.filter(
            completed_workorder_id=completed_workorder.id
        ).order_by('report_date', 'start_time')
        
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
            'total_report_count': len(production_reports),
            'total_work_hours': 0.0,
            'total_overtime_hours': 0.0,
            'total_all_hours': 0.0,
            'unique_operators': set(),
            'unique_equipment': set()
        }
        
        # 按工序分組統計
        for report in production_reports:
            process_name = report.process_name
            
            # 更新工序統計
            stats_by_process[process_name]['process_name'] = process_name
            stats_by_process[process_name]['total_good_quantity'] += report.work_quantity
            stats_by_process[process_name]['total_defect_quantity'] += report.defect_quantity
            stats_by_process[process_name]['report_count'] += 1
            stats_by_process[process_name]['total_work_hours'] += report.work_hours
            
            # 更新總計
            total_stats['total_good_quantity'] += report.work_quantity
            total_stats['total_defect_quantity'] += report.defect_quantity
            total_stats['total_work_hours'] += report.work_hours
            total_stats['total_overtime_hours'] += report.overtime_hours
            
            # 記錄作業員和設備
            if report.operator != '-':
                stats_by_process[process_name]['operators'].add(report.operator)
                total_stats['unique_operators'].add(report.operator)
            
            if report.equipment != '-':
                stats_by_process[process_name]['equipment'].add(report.equipment)
                total_stats['unique_equipment'].add(report.equipment)
        
        # 計算總時數
        total_stats['total_all_hours'] = total_stats['total_work_hours'] + total_stats['total_overtime_hours']
        
        # 轉換 set 為 list 以便在模板中使用
        for process_stats in stats_by_process.values():
            process_stats['operators'] = list(process_stats['operators'])
            process_stats['equipment'] = list(process_stats['equipment'])
        
        total_stats['unique_operators'] = list(total_stats['unique_operators'])
        total_stats['unique_equipment'] = list(total_stats['unique_equipment'])
        
        # 按照工序的實際執行順序排列統計資料
        # 根據填報記錄的時間順序，確定工序的執行順序，但出貨包裝必須排在最後
        process_order = {}
        for i, report in enumerate(production_reports):
            process_name = report.process_name
            if process_name not in process_order:
                process_order[process_name] = i
        
        # 定義工序優先順序，出貨包裝必須排在最後
        def get_process_priority(process_name):
            if process_name == "出貨包裝":
                return 9999  # 出貨包裝排在最後，不按時間順序
            return process_order.get(process_name, 999)  # 其他工序按第一次出現的時間順序
        
        # 按照工序執行順序排序統計資料
        sorted_stats_by_process = dict(sorted(
            stats_by_process.items(),
            key=lambda x: get_process_priority(x[0])
        ))
        
        # 獲取工序資料
        processes = CompletedWorkOrderProcess.objects.filter(
            completed_workorder_id=completed_workorder.id
        ).order_by('process_order')
        
        context['all_production_reports'] = production_reports
        context['total_reports_count'] = len(production_reports)
        context['production_stats_by_process'] = sorted_stats_by_process
        context['production_total_stats'] = total_stats
        context['processes'] = processes
        context['processes_count'] = processes.count()
        
        return context


@require_POST
@csrf_exempt
def transfer_workorder_to_completed(request, workorder_id):
    """
    將生產中的工單轉移到已完工模組
    """
    try:
        from ..models import WorkOrder
        
        # 檢查工單是否存在
        workorder = WorkOrder.objects.get(id=workorder_id)
        
        # 檢查工單是否已經完工
        if workorder.status != 'completed':
            return JsonResponse({
                'success': False,
                'error': f'工單 {workorder.order_number} 尚未完工，無法轉移'
            })
        
        # 執行轉移
        from ..services.unified_transfer_service import UnifiedTransferService
        transfer_result = UnifiedTransferService.transfer_workorder_to_completed(workorder_id, "手動轉移")
        
        if not transfer_result.get('success'):
            return JsonResponse({
                'success': False,
                'error': transfer_result.get('error', '轉移失敗')
            })
        
        completed_workorder_id = transfer_result.get('completed_workorder_id')
        
        return JsonResponse({
            'success': True,
            'message': f'工單 {workorder.order_number} 成功轉移到已完工模組',
            'completed_workorder_id': completed_workorder_id
        })
        
    except WorkOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '工單不存在'
        })
    except Exception as e:
        logger.error(f"轉移工單失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'轉移失敗: {str(e)}'
        })


@require_POST
@csrf_exempt
def batch_transfer_completed_workorders(request):
    """
    批次轉移所有已完工的工單
    """
    try:
        from ..models import WorkOrder
        
        # 獲取所有已完工但尚未轉移的工單
        completed_workorders = WorkOrder.objects.filter(
            status='completed'
        ).exclude(
            id__in=CompletedWorkOrder.objects.values_list('original_workorder_id', flat=True)
        )
        
        transferred_count = 0
        errors = []
        
        for workorder in completed_workorders:
            try:
                from ..services.unified_transfer_service import UnifiedTransferService
                transfer_result = UnifiedTransferService.transfer_workorder_to_completed(workorder.id, "批次轉移")
                
                if transfer_result.get('success'):
                    transferred_count += 1
                else:
                    errors.append(f'工單 {workorder.order_number}: {transfer_result.get("error", "轉移失敗")}')
            except Exception as e:
                errors.append(f'工單 {workorder.order_number}: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'成功轉移 {transferred_count} 個工單',
            'transferred_count': transferred_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"批次轉移失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'批次轉移失敗: {str(e)}'
        }) 