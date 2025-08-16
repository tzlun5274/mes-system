"""
工單清除視圖
提供網頁介面來安全地清除所有工單資料
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from workorder.models import WorkOrder
from workorder.workorder_erp.models import PrdMKOrdMain, PrdMkOrdMats, CompanyOrder
from workorder.fill_work.models import FillWork
from workorder.workorder_dispatch.models import WorkOrderDispatch, WorkOrderDispatchProcess
import logging

logger = logging.getLogger(__name__)


class WorkOrderClearView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    工單清除視圖
    只有超級用戶可以訪問
    """
    template_name = 'workorder/workorder_clear.html'
    
    def test_func(self):
        """只有超級用戶可以訪問"""
        return self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 統計目前資料數量
        from workorder.models import CompletedWorkOrder, CompletedWorkOrderProcess, CompletedProductionReport
        
        context.update({
            'workorder_count': WorkOrder.objects.count(),
            'fillwork_count': FillWork.objects.count(),
            'company_order_count': CompanyOrder.objects.count(),
            'mkord_main_count': PrdMKOrdMain.objects.count(),
            'mkord_mats_count': PrdMkOrdMats.objects.count(),
            'completed_workorder_count': CompletedWorkOrder.objects.count(),
            'completed_process_count': CompletedWorkOrderProcess.objects.count(),
            'completed_report_count': CompletedProductionReport.objects.count(),
            'dispatch_count': WorkOrderDispatch.objects.count(),
            'dispatch_process_count': WorkOrderDispatchProcess.objects.count(),
            'total_count': (
                WorkOrder.objects.count() + 
                FillWork.objects.count() + 
                CompanyOrder.objects.count() +
                PrdMKOrdMain.objects.count() +
                PrdMkOrdMats.objects.count() +
                CompletedWorkOrder.objects.count() +
                CompletedWorkOrderProcess.objects.count() +
                CompletedProductionReport.objects.count() +
                WorkOrderDispatch.objects.count() +
                WorkOrderDispatchProcess.objects.count()
            )
        })
        
        return context


class WorkOrderClearAjaxView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    工單清除AJAX視圖
    處理清除操作的AJAX請求
    """
    
    def test_func(self):
        """只有超級用戶可以訪問"""
        return self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        """處理POST請求，執行清除操作"""
        try:
            # 檢查確認參數
            if request.POST.get('confirm') != 'true':
                return JsonResponse({
                    'success': False,
                    'error': '需要確認參數'
                })
            
            # 檢查備份選項
            create_backup = request.POST.get('backup') == 'true'
            
            # 執行清除操作
            result = self._clear_all_workorders(create_backup)
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"清除工單時發生錯誤: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def _clear_all_workorders(self, create_backup=False):
        """清除所有工單資料"""
        try:
            # 創建備份
            backup_path = None
            if create_backup:
                backup_path = self._create_backup()
            
            # 執行刪除
            with transaction.atomic():
                # 統計刪除數量
                fillwork_count = FillWork.objects.count()
                company_order_count = CompanyOrder.objects.count()
                workorder_count = WorkOrder.objects.count()
                mkord_main_count = PrdMKOrdMain.objects.count()
                mkord_mats_count = PrdMkOrdMats.objects.count()
                
                # 新增：統計已完工工單相關資料
                from workorder.models import CompletedWorkOrder, CompletedWorkOrderProcess, CompletedProductionReport
                completed_workorder_count = CompletedWorkOrder.objects.count()
                completed_process_count = CompletedWorkOrderProcess.objects.count()
                completed_report_count = CompletedProductionReport.objects.count()
                
                # 新增：統計派工單相關資料
                from workorder.workorder_dispatch.models import WorkOrderDispatch, WorkOrderDispatchProcess
                dispatch_count = WorkOrderDispatch.objects.count()
                dispatch_process_count = WorkOrderDispatchProcess.objects.count()
                
                # 刪除資料
                FillWork.objects.all().delete()
                CompanyOrder.objects.all().delete()
                WorkOrder.objects.all().delete()
                PrdMKOrdMain.objects.all().delete()
                PrdMkOrdMats.objects.all().delete()
                
                # 新增：刪除已完工工單相關資料
                CompletedProductionReport.objects.all().delete()
                CompletedWorkOrderProcess.objects.all().delete()
                CompletedWorkOrder.objects.all().delete()
                
                # 新增：刪除派工單相關資料
                WorkOrderDispatchProcess.objects.all().delete()
                WorkOrderDispatch.objects.all().delete()
            
            return {
                'success': True,
                'message': '所有工單資料已成功清除',
                'deleted_counts': {
                    'fillwork': fillwork_count,
                    'company_order': company_order_count,
                    'workorder': workorder_count,
                    'mkord_main': mkord_main_count,
                    'mkord_mats': mkord_mats_count,
                    'completed_workorder': completed_workorder_count,
                    'completed_process': completed_process_count,
                    'completed_report': completed_report_count,
                    'dispatch': dispatch_count,
                    'dispatch_process': dispatch_process_count,
                    'total': fillwork_count + company_order_count + workorder_count + mkord_main_count + mkord_mats_count + completed_workorder_count + completed_process_count + completed_report_count + dispatch_count + dispatch_process_count
                },
                'backup_path': backup_path,
                'clear_time': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"清除工單資料時發生錯誤: {e}")
            raise e
    
    def _create_backup(self):
        """創建資料備份"""
        try:
            from django.core import serializers
            import os
            from datetime import datetime
            
            # 創建備份目錄
            backup_dir = f'/var/www/mes/backups/workorder_clear_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            os.makedirs(backup_dir, exist_ok=True)
            
            # 備份工單資料
            workorders = WorkOrder.objects.all()
            with open(f'{backup_dir}/workorders.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', workorders, stream=f)
            
            # 備份填報紀錄
            fillworks = FillWork.objects.all()
            with open(f'{backup_dir}/fillworks.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', fillworks, stream=f)
            
            # 備份公司製令單
            company_orders = CompanyOrder.objects.all()
            with open(f'{backup_dir}/company_orders.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', company_orders, stream=f)
            
            # 備份製令主檔
            mkord_mains = PrdMKOrdMain.objects.all()
            with open(f'{backup_dir}/mkord_mains.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', mkord_mains, stream=f)
            
            # 新增：備份已完工工單相關資料
            from workorder.models import CompletedWorkOrder, CompletedWorkOrderProcess, CompletedProductionReport
            
            # 備份已完工工單
            completed_workorders = CompletedWorkOrder.objects.all()
            with open(f'{backup_dir}/completed_workorders.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', completed_workorders, stream=f)
            
            # 備份已完工工單工序
            completed_processes = CompletedWorkOrderProcess.objects.all()
            with open(f'{backup_dir}/completed_processes.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', completed_processes, stream=f)
            
            # 備份已完工生產報工記錄
            completed_reports = CompletedProductionReport.objects.all()
            with open(f'{backup_dir}/completed_reports.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', completed_reports, stream=f)
            
            # 備份製令用料
            mkord_mats = PrdMkOrdMats.objects.all()
            with open(f'{backup_dir}/mkord_mats.json', 'w', encoding='utf-8') as f:
                serializers.serialize('json', mkord_mats, stream=f)
            
            return backup_dir
            
        except Exception as e:
            logger.error(f"創建備份時發生錯誤: {e}")
            return None 