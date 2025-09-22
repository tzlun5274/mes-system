"""
填報紀錄相符性檢查視圖
處理相符性檢查的頁面渲染和AJAX請求，排除RD樣品工單
"""

from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.views import View
from django.db.models import Count
from django.utils import timezone
from workorder.models import ConsistencyCheckResult
from workorder.services.consistency_check_service import ConsistencyCheckService

class ConsistencyCheckHomeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    相符性檢查首頁視圖
    顯示系統維護功能的相符性檢查卡片介面，排除RD樣品工單
    只有超級用戶可以訪問
    """
    template_name = 'workorder/consistency_check_home.html'
    
    def test_func(self):
        """只有超級用戶可以訪問"""
        return self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 取得各檢查類型的統計資料
        stats = ConsistencyCheckResult.objects.values('check_type', 'is_fixed').annotate(
            count=Count('id')
        )
        
        # 整理統計資料
        check_stats = {
            'missing_dispatch': {'total': 0, 'fixed': 0, 'unfixed': 0},
            'wrong_product_code': {'total': 0, 'fixed': 0, 'unfixed': 0},
            'wrong_company': {'total': 0, 'fixed': 0, 'unfixed': 0},
            'wrong_workorder': {'total': 0, 'fixed': 0, 'unfixed': 0},
        }
        
        for stat in stats:
            check_type = stat['check_type']
            count = stat['count']
            is_fixed = stat['is_fixed']
            
            if check_type in check_stats:
                check_stats[check_type]['total'] += count
                if is_fixed:
                    check_stats[check_type]['fixed'] += count
                else:
                    check_stats[check_type]['unfixed'] += count
        
        context.update({
            'page_title': '系統維護 - 相符性檢查',
            'check_stats': check_stats,
            'last_check_time': ConsistencyCheckResult.objects.order_by('-created_at').first().created_at if ConsistencyCheckResult.objects.exists() else None,
        })
        
        return context

class ConsistencyCheckAjaxView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    相符性檢查AJAX視圖
    處理各種相符性檢查的AJAX請求，排除RD樣品工單
    只有超級用戶可以訪問
    """
    
    def test_func(self):
        """只有超級用戶可以訪問"""
        return self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        """處理相符性檢查請求"""
        try:
            action = request.POST.get('action', 'check')
            
            if action == 'fix_issue':
                # 處理單筆修復請求
                result_id = request.POST.get('result_id')
                fix_method = request.POST.get('fix_method', 'update_fill_work')
                fix_data_json = request.POST.get('fix_data', '{}')
                fixed_by = request.user.username
                
                # 解析修復資料
                import json
                try:
                    fix_data = json.loads(fix_data_json)
                except (json.JSONDecodeError, TypeError):
                    fix_data = {}
                
                service = ConsistencyCheckService()
                service.fix_issue(result_id, fix_method, fixed_by, fix_data)
                
                return JsonResponse({
                    'success': True,
                    'message': '問題處理完成'
                })
            
            elif action == 'batch_fix_issues':
                # 處理批次修復請求
                result_ids = request.POST.get('result_ids', '').split(',')
                fix_method = request.POST.get('fix_method', 'update_fill_work')
                fix_data_json = request.POST.get('fix_data', '{}')
                fixed_by = request.user.username
                
                if not result_ids or result_ids[0] == '':
                    return JsonResponse({
                        'success': False,
                        'message': '請選擇要修復的問題'
                    })
                
                # 解析修復資料
                import json
                try:
                    fix_data = json.loads(fix_data_json)
                except (json.JSONDecodeError, TypeError):
                    fix_data = {}
                
                service = ConsistencyCheckService()
                fixed_count = 0
                errors = []
                
                for result_id in result_ids:
                    try:
                        service.fix_issue(result_id, fix_method, fixed_by, fix_data)
                        fixed_count += 1
                    except Exception as e:
                        errors.append(f'ID {result_id}: {str(e)}')
                
                if fixed_count > 0:
                    message = f'批次處理完成，成功處理 {fixed_count} 筆問題'
                    if errors:
                        message += f'，失敗 {len(errors)} 筆'
                    
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'fixed_count': fixed_count,
                        'error_count': len(errors),
                        'errors': errors
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '批次修復失敗：' + '; '.join(errors)
                    })
            
            # 處理檢查請求
            check_type = request.POST.get('check_type')
            service = ConsistencyCheckService()
            
            if check_type == 'missing_dispatch':
                count = service.check_missing_dispatch()
                message = f"填報異常檢查完成，發現 {count} 筆問題（已排除RD樣品）"
            elif check_type == 'wrong_product_code':
                count = service.check_wrong_product_code()
                message = f"產品編號錯誤檢查完成，發現 {count} 筆問題（已排除RD樣品）"
            elif check_type == 'wrong_company':
                count = service.check_wrong_company()
                message = f"公司代號/名稱錯誤檢查完成，發現 {count} 筆問題（已排除RD樣品）"
            elif check_type == 'wrong_workorder':
                count = service.check_wrong_workorder()
                message = f"工單號碼錯誤檢查完成，發現 {count} 筆問題（已排除RD樣品）"
            elif check_type == 'all':
                results = service.run_all_checks()
                total = sum(results.values())
                message = f"所有相符性檢查完成，總共發現 {total} 筆問題（已排除RD樣品）"
            else:
                return JsonResponse({
                    'success': False,
                    'message': '無效的檢查類型'
                })
            
            return JsonResponse({
                'success': True,
                'message': message,
                'check_type': check_type,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'操作失敗：{str(e)}'
            })

class ConsistencyCheckDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    相符性檢查詳細資料視圖
    顯示特定檢查類型的詳細結果，排除RD樣品工單
    只有超級用戶可以訪問
    """
    template_name = 'workorder/consistency_check_detail.html'
    
    def test_func(self):
        """只有超級用戶可以訪問"""
        return self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        check_type = self.request.GET.get('type', 'missing_fill_work')
        is_fixed = self.request.GET.get('fixed', 'false').lower() == 'true'
        
        # 取得檢查結果
        results = ConsistencyCheckResult.objects.filter(
            check_type=check_type,
            is_fixed=is_fixed
        ).order_by('-created_at')
        
        # 檢查類型顯示名稱
        type_display_names = {
            'missing_dispatch': '填報異常',
            'wrong_product_code': '產品編號錯誤',
            'wrong_company': '公司代號/名稱錯誤',
            'wrong_workorder': '工單號碼錯誤',
        }
        
        context.update({
            'check_type': check_type,
            'check_type_display': type_display_names.get(check_type, check_type),
            'is_fixed': is_fixed,
            'results': results,
            'total_count': results.count(),
        })
        
        return context

class ConsistencyCheckFixView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    相符性問題修復視圖
    處理相符性問題的修復請求
    只有超級用戶可以訪問
    """
    
    def test_func(self):
        """只有超級用戶可以訪問"""
        return self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        """處理修復請求"""
        try:
            result_id = request.POST.get('result_id')
            fix_method = request.POST.get('fix_method', 'update_fill_work')
            fix_data_json = request.POST.get('fix_data', '{}')
            fixed_by = request.user.username
            
            # 解析修復資料
            import json
            try:
                fix_data = json.loads(fix_data_json)
            except (json.JSONDecodeError, TypeError):
                fix_data = {}
            
            service = ConsistencyCheckService()
            service.fix_issue(result_id, fix_method, fixed_by, fix_data)
            
            return JsonResponse({
                'success': True,
                'message': '問題處理完成'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'修復失敗：{str(e)}'
            })

class ConsistencyCheckExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    相符性檢查結果匯出視圖
    匯出檢查結果為Excel或CSV格式
    只有超級用戶可以訪問
    """
    
    def test_func(self):
        """只有超級用戶可以訪問"""
        return self.request.user.is_superuser
    
    def get(self, request, *args, **kwargs):
        """匯出檢查結果"""
        try:
            import csv
            from django.http import HttpResponse
            
            check_type = request.GET.get('type', 'all')
            is_fixed = request.GET.get('fixed', 'false').lower() == 'true'
            format_type = request.GET.get('format', 'csv')
            
            # 取得檢查結果
            if check_type == 'all':
                results = ConsistencyCheckResult.objects.filter(is_fixed=is_fixed)
            else:
                results = ConsistencyCheckResult.objects.filter(
                    check_type=check_type,
                    is_fixed=is_fixed
                )
            
            # 建立回應
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="consistency_check_{check_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            # 寫入CSV
            writer = csv.writer(response)
            writer.writerow([
                '檢查類型', '公司代號', '公司名稱', '工單號碼', '產品編號',
                '錯誤公司代號', '錯誤公司名稱', '錯誤工單號碼', '錯誤產品編號',
                '作業員', '工作日期', '狀態', '數量', '是否已修復',
                '修復時間', '修復人員', '修復方式', '建立時間'
            ])
            
            for result in results:
                writer.writerow([
                    result.get_check_type_display(),
                    result.company_code,
                    result.company_name,
                    result.workorder,
                    result.product_code,
                    result.wrong_company_code,
                    result.wrong_company_name,
                    result.wrong_workorder,
                    result.wrong_product_code,
                    result.operator,
                    result.work_date,
                    result.status,
                    result.quantity,
                    '是' if result.is_fixed else '否',
                    result.fixed_at,
                    result.fixed_by,
                    result.fix_method,
                    result.created_at,
                ])
            
            return response
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'匯出失敗：{str(e)}'
            }) 