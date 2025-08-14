"""
填報紀錄修正視圖
提供網頁介面來修正填報紀錄中的不一致資料
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from workorder.services.fillwork_correction_service import FillWorkCorrectionService


class FillWorkCorrectionView(LoginRequiredMixin, TemplateView):
    """
    填報紀錄修正視圖
    提供三種修正類型的網頁介面
    """
    template_name = 'workorder/fillwork_correction.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得三種修正類型的分析報告
        analysis = FillWorkCorrectionService.get_correction_analysis()
        
        # 取得各類型的修正預覽
        previews = {
            'product_codes': FillWorkCorrectionService.get_correction_preview('product_codes'),
            'workorder_numbers': FillWorkCorrectionService.get_correction_preview('workorder_numbers'),
            'company_codes': FillWorkCorrectionService.get_correction_preview('company_codes')
        }
        
        context.update({
            'analysis': analysis,
            'previews': previews,
            'check_time': timezone.now(),
        })
        
        return context


class FillWorkCorrectionAjaxView(LoginRequiredMixin, TemplateView):
    """
    填報紀錄修正AJAX視圖
    提供AJAX介面來執行修正並返回JSON結果
    """
    
    def post(self, request, *args, **kwargs):
        """處理POST請求，執行指定類型的修正"""
        try:
            action = request.POST.get('action')
            correction_type = request.POST.get('correction_type')
            
            if not correction_type:
                return JsonResponse({
                    'success': False,
                    'error': '未指定修正類型',
                    'check_time': timezone.now().isoformat()
                })
            
            if action == 'preview':
                # 取得修正預覽
                results = FillWorkCorrectionService.get_correction_preview(correction_type)
                response_data = {
                    'success': True,
                    'action': 'preview',
                    'correction_type': correction_type,
                    'check_time': timezone.now().isoformat(),
                    'results': results,
                    'message': f'預覽完成，將會修正 {results["total_corrected"]} 筆記錄'
                }
                
            elif action == 'execute':
                # 執行實際修正
                results = FillWorkCorrectionService.execute_correction(correction_type)
                response_data = {
                    'success': True,
                    'action': 'execute',
                    'correction_type': correction_type,
                    'check_time': timezone.now().isoformat(),
                    'results': results,
                    'message': f'修正完成，已修正 {results["total_corrected"]} 筆記錄'
                }
                
            else:
                return JsonResponse({
                    'success': False,
                    'error': '無效的操作',
                    'check_time': timezone.now().isoformat()
                })
            
            return JsonResponse(response_data)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'check_time': timezone.now().isoformat()
            })


class FillWorkCorrectionAnalysisView(LoginRequiredMixin, TemplateView):
    """
    填報紀錄修正分析視圖
    顯示詳細的三種修正類型分析
    """
    template_name = 'workorder/fillwork_correction_analysis.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得三種修正類型的分析報告
        analysis = FillWorkCorrectionService.get_correction_analysis()
        
        context.update({
            'analysis': analysis,
            'check_time': timezone.now(),
        })
        
        return context


class FillWorkCorrectionPreviewView(LoginRequiredMixin, TemplateView):
    """
    填報紀錄修正預覽視圖
    顯示指定類型將會被修正的記錄詳細清單
    """
    template_name = 'workorder/fillwork_correction_preview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        correction_type = self.request.GET.get('type', 'product_codes')
        
        # 取得指定類型的修正預覽
        preview = FillWorkCorrectionService.get_correction_preview(correction_type)
        
        context.update({
            'preview': preview,
            'correction_type': correction_type,
            'check_time': timezone.now(),
        })
        
        return context


def execute_correction_view(request):
    """
    執行指定類型修正的函數視圖
    用於表單提交
    """
    if request.method == 'POST':
        correction_type = request.POST.get('correction_type')
        
        if not correction_type:
            messages.error(request, '未指定修正類型')
            return redirect('workorder:fillwork_correction')
        
        try:
            # 執行修正
            results = FillWorkCorrectionService.execute_correction(correction_type)
            
            if results['total_corrected'] > 0:
                messages.success(
                    request, 
                    f'修正完成！已修正 {results["total_corrected"]} 筆記錄。'
                )
            else:
                messages.info(
                    request, 
                    '沒有需要修正的記錄。'
                )
            
            if results['errors']:
                messages.warning(
                    request, 
                    f'修正過程中遇到 {len(results["errors"])} 個錯誤，請檢查日誌。'
                )
                
        except Exception as e:
            messages.error(
                request, 
                f'修正過程中發生錯誤：{str(e)}'
            )
    
    return redirect('workorder:fillwork_correction') 