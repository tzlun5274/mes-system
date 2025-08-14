"""
填報紀錄相符性檢查視圖
提供網頁介面來檢查填報紀錄與工單的相符性，分成三種獨立檢查類型
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from workorder.services.fillwork_validation_service import FillWorkValidationService


class FillWorkConsistencyCheckView(LoginRequiredMixin, TemplateView):
    """
    填報紀錄相符性檢查視圖
    提供網頁介面來檢查填報紀錄與工單的相符性
    """
    template_name = 'workorder/fillwork_consistency_check.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 執行相符性檢查
        results = FillWorkValidationService.check_fillwork_workorder_consistency()
        
        # 取得RD樣品統計
        rd_stats = FillWorkValidationService.get_rd_sample_statistics()
        
        # 計算相符率
        match_rate = 0
        if results['total_fillwork'] > 0:
            match_rate = (results['matched_workorders'] / results['total_fillwork']) * 100
        
        context.update({
            'results': results,
            'rd_stats': rd_stats,
            'match_rate': match_rate,
            'check_time': timezone.now(),
        })
        
        return context


class FillWorkConsistencyAjaxView(LoginRequiredMixin, TemplateView):
    """
    填報紀錄相符性檢查AJAX視圖
    提供AJAX介面來執行檢查並返回JSON結果
    """
    
    def get(self, request, *args, **kwargs):
        """處理GET請求，執行檢查並返回JSON結果"""
        try:
            # 執行相符性檢查
            results = FillWorkValidationService.check_fillwork_workorder_consistency()
            
            # 取得RD樣品統計
            rd_stats = FillWorkValidationService.get_rd_sample_statistics()
            
            # 計算相符率
            match_rate = 0
            if results['total_fillwork'] > 0:
                match_rate = (results['matched_workorders'] / results['total_fillwork']) * 100
            
            # 準備回應資料
            response_data = {
                'success': True,
                'check_time': timezone.now().isoformat(),
                'results': results,
                'rd_stats': rd_stats,
                'match_rate': round(match_rate, 1),
                'summary': {
                    'total_issues': results['missing_workorders'] + results['product_mismatch'] + results['workorder_mismatch'] + results['company_mismatch'] + len(results['errors']),
                    'status': 'success' if results['missing_workorders'] + results['product_mismatch'] + results['workorder_mismatch'] + results['company_mismatch'] + len(results['errors']) == 0 else 'warning'
                }
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'check_time': timezone.now().isoformat()
            })


class MissingWorkOrdersView(LoginRequiredMixin, TemplateView):
    """
    缺失工單詳細視圖
    顯示缺失工單的詳細清單
    """
    template_name = 'workorder/missing_workorders.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得缺失工單報告
        missing_workorders = FillWorkValidationService.get_missing_workorders_report()
        
        context.update({
            'missing_workorders': missing_workorders,
            'total_missing': len(missing_workorders),
            'check_time': timezone.now(),
        })
        
        return context


class ProductMismatchView(LoginRequiredMixin, TemplateView):
    """
    產品編號不匹配詳細視圖
    顯示產品編號不匹配的詳細清單
    """
    template_name = 'workorder/product_mismatch.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得產品編號不匹配報告
        product_mismatches = FillWorkValidationService.get_product_mismatch_report()
        
        context.update({
            'product_mismatches': product_mismatches,
            'total_product_mismatch': len(product_mismatches),
            'check_time': timezone.now(),
        })
        
        return context


class WorkorderMismatchView(LoginRequiredMixin, TemplateView):
    """
    工單號碼不匹配詳細視圖
    顯示工單號碼不匹配的詳細清單
    """
    template_name = 'workorder/workorder_mismatch.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得工單號碼不匹配報告
        workorder_mismatches = FillWorkValidationService.get_workorder_mismatch_report()
        
        context.update({
            'workorder_mismatches': workorder_mismatches,
            'total_workorder_mismatch': len(workorder_mismatches),
            'check_time': timezone.now(),
        })
        
        return context


class CompanyMismatchView(LoginRequiredMixin, TemplateView):
    """
    公司代號不匹配詳細視圖
    顯示公司代號不匹配的詳細清單
    """
    template_name = 'workorder/company_mismatch.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得公司代號不匹配報告
        company_mismatches = FillWorkValidationService.get_company_mismatch_report()
        
        context.update({
            'company_mismatches': company_mismatches,
            'total_company_mismatch': len(company_mismatches),
            'check_time': timezone.now(),
        })
        
        return context


class RDSampleStatisticsView(LoginRequiredMixin, TemplateView):
    """
    RD樣品統計視圖
    顯示RD樣品的詳細統計資訊
    """
    template_name = 'workorder/rd_sample_statistics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得RD樣品統計
        rd_stats = FillWorkValidationService.get_rd_sample_statistics()
        
        context.update({
            'rd_stats': rd_stats,
            'check_time': timezone.now(),
        })
        
        return context 