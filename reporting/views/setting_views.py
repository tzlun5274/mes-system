# -*- coding: utf-8 -*-
"""
同步設定管理視圖
提供同步設定的新增、編輯、刪除、啟用/停用等功能
"""

from django.views.generic import CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from system.models import ReportSyncSettings
import logging

logger = logging.getLogger(__name__)


class AddSyncSettingView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """新增同步設定視圖"""
    model = ReportSyncSettings
    template_name = 'reporting/sync_setting_form.html'
    fields = ['name', 'description', 'sync_type', 'interval_minutes', 'is_active']
    success_url = reverse_lazy('reporting:sync_settings')
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def form_valid(self, form):
        """表單驗證成功"""
        form.instance.created_by = self.request.user.username
        messages.success(self.request, "同步設定新增成功！")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """表單驗證失敗"""
        messages.error(self.request, "同步設定新增失敗，請檢查輸入資料。")
        return super().form_invalid(form)


class EditSyncSettingView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """編輯同步設定視圖"""
    model = ReportSyncSettings
    template_name = 'reporting/sync_setting_form.html'
    fields = ['name', 'description', 'sync_type', 'interval_minutes', 'is_active']
    success_url = reverse_lazy('reporting:sync_settings')
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def get_object(self, queryset=None):
        """取得要編輯的物件"""
        setting_id = self.request.POST.get('setting_id')
        return get_object_or_404(ReportSyncSettings, id=setting_id)
    
    def form_valid(self, form):
        """表單驗證成功"""
        form.instance.updated_by = self.request.user.username
        messages.success(self.request, "同步設定更新成功！")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """表單驗證失敗"""
        messages.error(self.request, "同步設定更新失敗，請檢查輸入資料。")
        return super().form_invalid(form)


class DeleteSyncSettingView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """刪除同步設定視圖"""
    model = ReportSyncSettings
    success_url = reverse_lazy('reporting:sync_settings')
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def delete(self, request, *args, **kwargs):
        """刪除同步設定"""
        setting = self.get_object()
        setting_name = setting.name
        
        try:
            result = super().delete(request, *args, **kwargs)
            messages.success(request, f"同步設定「{setting_name}」刪除成功！")
            return result
        except Exception as e:
            logger.error(f"刪除同步設定失敗：{str(e)}")
            messages.error(request, f"刪除同步設定失敗：{str(e)}")
            return redirect('reporting:sync_settings')


class ToggleSyncSettingView(LoginRequiredMixin, UserPassesTestMixin, View):
    """切換同步設定啟用狀態視圖"""
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        """切換同步設定狀態"""
        try:
            setting_id = kwargs.get('pk')
            setting = get_object_or_404(ReportSyncSettings, id=setting_id)
            
            # 切換狀態
            setting.is_active = not setting.is_active
            setting.updated_by = request.user.username
            setting.save()
            
            status_text = "啟用" if setting.is_active else "停用"
            messages.success(request, f"同步設定「{setting.name}」已{status_text}！")
            
            return JsonResponse({
                'status': 'success',
                'message': f'同步設定已{status_text}',
                'is_active': setting.is_active
            })
            
        except Exception as e:
            logger.error(f"切換同步設定狀態失敗：{str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'切換狀態失敗：{str(e)}'
            }, status=500) 