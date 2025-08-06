"""
自動管理功能視圖
用於管理各種自動化功能的設定和執行
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.utils import timezone
from datetime import datetime
import logging

from ..models import AutoManagementConfig
from ..forms import AutoManagementConfigForm

logger = logging.getLogger(__name__)


class AutoManagementConfigListView(LoginRequiredMixin, ListView):
    """
    自動管理功能設定列表視圖
    顯示所有自動化功能的設定狀態
    """
    
    model = AutoManagementConfig
    template_name = "workorder/auto_management/config_list.html"
    context_object_name = "configs"
    paginate_by = 20
    
    # def test_func(self):
    #     """檢查用戶是否有管理權限"""
    #     return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        """提供模板所需的上下文數據"""
        context = super().get_context_data(**kwargs)
        
        # 添加統計資訊
        context['total_configs'] = AutoManagementConfig.objects.count()
        context['enabled_configs'] = AutoManagementConfig.objects.filter(is_enabled=True).count()
        context['disabled_configs'] = AutoManagementConfig.objects.filter(is_enabled=False).count()
        
        return context


class AutoManagementConfigCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    自動管理功能設定新增視圖
    用於建立新的自動化功能設定
    """
    
    model = AutoManagementConfig
    form_class = AutoManagementConfigForm
    template_name = "workorder/auto_management/config_form.html"
    success_url = reverse_lazy("workorder:auto_management_config_list")
    
    def test_func(self):
        """檢查用戶是否有管理權限"""
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def form_valid(self, form):
        """表單驗證成功時的處理"""
        form.instance.created_by = self.request.user.username
        response = super().form_valid(form)
        
        messages.success(self.request, f"自動管理功能設定「{form.instance.get_function_type_display()}」建立成功！")
        
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "message": f"自動管理功能設定「{form.instance.get_function_type_display()}」建立成功！",
                "redirect_url": self.success_url
            })
        
        return response
    
    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "自動管理功能設定建立失敗，請檢查輸入資料！")
        return super().form_invalid(form)


class AutoManagementConfigUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    自動管理功能設定編輯視圖
    用於編輯現有自動化功能設定
    """
    
    model = AutoManagementConfig
    form_class = AutoManagementConfigForm
    template_name = "workorder/auto_management/config_form.html"
    success_url = reverse_lazy("workorder:auto_management_config_list")
    
    def test_func(self):
        """檢查用戶是否有管理權限"""
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def form_valid(self, form):
        """表單驗證成功時的處理"""
        response = super().form_valid(form)
        
        messages.success(self.request, f"自動管理功能設定「{form.instance.get_function_type_display()}」更新成功！")
        
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "message": f"自動管理功能設定「{form.instance.get_function_type_display()}」更新成功！",
                "redirect_url": self.success_url
            })
        
        return response
    
    def form_invalid(self, form):
        """表單驗證失敗時的處理"""
        messages.error(self.request, "自動管理功能設定更新失敗，請檢查輸入資料！")
        return super().form_invalid(form)


class AutoManagementConfigDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    自動管理功能設定刪除視圖
    用於刪除自動化功能設定
    """
    
    model = AutoManagementConfig
    template_name = "workorder/auto_management/config_delete_confirm.html"
    context_object_name = "config"
    success_url = reverse_lazy("workorder:auto_management_config_list")
    
    def test_func(self):
        """檢查用戶是否有管理權限"""
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def delete(self, request, *args, **kwargs):
        """刪除成功時的處理"""
        try:
            obj = self.get_object()
            function_name = obj.get_function_type_display()
            obj.delete()
            
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "message": f"自動管理功能設定「{function_name}」刪除成功！"
                })
            
            messages.success(request, f"自動管理功能設定「{function_name}」刪除成功！")
            return redirect(self.success_url)
            
        except Exception as e:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": False,
                    "message": f"刪除失敗：{str(e)}"
                })
            
            messages.error(request, f"刪除失敗：{str(e)}")
            return redirect(self.success_url)


@require_POST
@login_required
def execute_auto_function(request, function_type):
    """
    手動執行自動化功能
    
    Args:
        request: HTTP請求
        function_type: 功能類型
        
    Returns:
        JsonResponse: 執行結果
    """
    try:
        # 檢查權限
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({
                "success": False,
                "message": "您沒有權限執行此操作"
            })
        
        # 獲取功能設定
        config = AutoManagementConfig.get_config(function_type)
        
        # 根據功能類型執行對應的命令
        if function_type == 'auto_completion_check':
            # 執行完工判斷轉寫已完工
            call_command('auto_completion_check')
            success_message = "完工判斷轉寫已完工功能執行成功"

        elif function_type == 'auto_approval':
            # 執行自動核准（如果有的話）
            success_message = "自動核准功能執行成功"
        elif function_type == 'auto_notification':
            # 執行自動通知（如果有的話）
            success_message = "自動通知功能執行成功"
        else:
            return JsonResponse({
                "success": False,
                "message": f"未知的功能類型：{function_type}"
            })
        
        # 更新執行統計
        config.update_execution_time(success=True)
        
        return JsonResponse({
            "success": True,
            "message": success_message,
            "execution_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    except Exception as e:
        logger.error(f"執行自動化功能 {function_type} 時發生錯誤: {str(e)}")
        
        # 更新執行統計
        if 'config' in locals():
            config.update_execution_time(success=False, error_message=str(e))
        
        return JsonResponse({
            "success": False,
            "message": f"執行失敗：{str(e)}"
        })


@require_POST
@login_required
def toggle_auto_function(request, function_type):
    """
    切換自動化功能的啟用狀態
    
    Args:
        request: HTTP請求
        function_type: 功能類型
        
    Returns:
        JsonResponse: 切換結果
    """
    try:
        # 檢查權限
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({
                "success": False,
                "message": "您沒有權限執行此操作"
            })
        
        # 獲取功能設定
        config = AutoManagementConfig.get_config(function_type)
        
        # 切換啟用狀態
        config.is_enabled = not config.is_enabled
        config.save()
        
        status_text = "啟用" if config.is_enabled else "停用"
        
        return JsonResponse({
            "success": True,
            "message": f"自動管理功能「{config.get_function_type_display()}」已{status_text}",
            "is_enabled": config.is_enabled
        })
        
    except Exception as e:
        logger.error(f"切換自動化功能 {function_type} 狀態時發生錯誤: {str(e)}")
        
        return JsonResponse({
            "success": False,
            "message": f"操作失敗：{str(e)}"
        }) 