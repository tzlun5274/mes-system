# -*- coding: utf-8 -*-
"""
報表資料同步狀態監控視圖
提供同步狀態查看、手動同步執行等功能
"""

from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from reporting.services.sync_service import ReportDataSyncService
from system.models import ReportDataSyncLog, ReportSyncSettings
from reporting.models import WorkTimeReport, WorkOrderProductReport
import json
import logging

logger = logging.getLogger(__name__)


class SyncStatusListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """同步狀態列表視圖"""
    model = ReportDataSyncLog
    template_name = 'reporting/sync_status_list.html'
    context_object_name = 'sync_logs'
    paginate_by = 20
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def get_queryset(self):
        """取得查詢集"""
        queryset = super().get_queryset()
        
        # 篩選條件
        sync_type = self.request.GET.get('sync_type')
        status = self.request.GET.get('status')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        if status:
            queryset = queryset.filter(status=status)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 統計資訊
        context['total_syncs'] = ReportDataSyncLog.objects.count()
        context['success_syncs'] = ReportDataSyncLog.objects.filter(status='success').count()
        context['error_syncs'] = ReportDataSyncLog.objects.filter(status='failed').count()
        context['pending_syncs'] = ReportDataSyncLog.objects.filter(status='partial').count()
        
        # 最近同步狀態
        context['recent_syncs'] = ReportDataSyncLog.objects.order_by('-created_at')[:5]
        
        # 同步設定
        context['sync_settings'] = ReportSyncSettings.objects.filter(is_active=True)
        
        return context


class SyncDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """同步詳情視圖"""
    model = ReportDataSyncLog
    template_name = 'reporting/sync_detail.html'
    context_object_name = 'sync_log'
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 同步詳細資訊
        context['sync_details'] = {
            'records_processed': self.object.records_processed,
            'records_created': self.object.records_created,
            'records_updated': self.object.records_updated,
            'duration_seconds': self.object.duration_seconds,
            'error_message': self.object.error_message,
        }
        
        return context


class ManualSyncView(LoginRequiredMixin, UserPassesTestMixin, View):
    """手動同步執行視圖"""
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        """執行手動同步"""
        try:
            # 取得同步參數
            sync_type = request.POST.get('sync_type', 'all')
            date_from = request.POST.get('date_from')
            date_to = request.POST.get('date_to')
            
            # 驗證日期格式
            if date_from:
                datetime.strptime(date_from, '%Y-%m-%d')
            if date_to:
                datetime.strptime(date_to, '%Y-%m-%d')
            
            # 執行同步
            sync_service = ReportDataSyncService()
            result = sync_service.sync_data(
                sync_type=sync_type,
                date_from=date_from,
                date_to=date_to,
                user=request.user.username
            )
            
            if result['status'] == 'success':
                messages.success(
                    request, 
                    f"同步執行成功！處理 {result['processed']} 筆記錄，新增 {result['created']} 筆資料。"
                )
            else:
                messages.error(request, f"同步執行失敗：{result['message']}")
                
        except ValueError as e:
            messages.error(request, f"日期格式錯誤：{str(e)}")
        except Exception as e:
            logger.error(f"手動同步執行失敗：{str(e)}")
            messages.error(request, f"同步執行失敗：{str(e)}")
        
        return redirect('reporting:sync_status_list')


class SyncDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    """同步儀表板視圖"""
    template_name = 'reporting/sync_dashboard.html'
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def get(self, request, *args, **kwargs):
        """顯示同步儀表板"""
        context = self.get_dashboard_data()
        return self.render_to_response(context)
    
    def get_dashboard_data(self):
        """取得儀表板資料"""
        # 今日同步統計
        today = timezone.now().date()
        today_syncs = ReportDataSyncLog.objects.filter(created_at__date=today)
        
        # 本週同步統計
        week_start = today - timedelta(days=today.weekday())
        week_syncs = ReportDataSyncLog.objects.filter(created_at__date__gte=week_start)
        
        # 本月同步統計
        month_start = today.replace(day=1)
        month_syncs = ReportDataSyncLog.objects.filter(created_at__date__gte=month_start)
        
        # 報表資料統計
        work_time_count = WorkTimeReport.objects.count()
        work_order_count = WorkOrderProductReport.objects.count()
        
        # 最近同步記錄
        recent_syncs = ReportDataSyncLog.objects.order_by('-created_at')[:10]
        
        # 同步成功率統計
        total_syncs = ReportDataSyncLog.objects.count()
        success_syncs = ReportDataSyncLog.objects.filter(status='success').count()
        success_rate = (success_syncs / total_syncs * 100) if total_syncs > 0 else 0
        
        return {
            'today_syncs': {
                'total': today_syncs.count(),
                'success': today_syncs.filter(status='success').count(),
                'error': today_syncs.filter(status='failed').count(),
            },
            'week_syncs': {
                'total': week_syncs.count(),
                'success': week_syncs.filter(status='success').count(),
                'error': week_syncs.filter(status='failed').count(),
            },
            'month_syncs': {
                'total': month_syncs.count(),
                'success': month_syncs.filter(status='success').count(),
                'error': month_syncs.filter(status='failed').count(),
            },
            'report_data': {
                'work_time_count': work_time_count,
                'work_order_count': work_order_count,
            },
            'recent_syncs': recent_syncs,
            'success_rate': round(success_rate, 2),
            'sync_settings': ReportSyncSettings.objects.filter(is_active=True),
        }


class SyncSettingsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """同步設定管理視圖"""
    model = ReportSyncSettings
    template_name = 'reporting/sync_settings.html'
    context_object_name = 'sync_settings'
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        """取得上下文資料"""
        context = super().get_context_data(**kwargs)
        
        # 統計資訊
        context['total_settings'] = ReportSyncSettings.objects.count()
        context['active_settings'] = ReportSyncSettings.objects.filter(is_active=True).count()
        
        return context


class SyncAPIView(LoginRequiredMixin, UserPassesTestMixin, View):
    """同步 API 視圖"""
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        """API 同步執行"""
        try:
            data = json.loads(request.body)
            sync_type = data.get('sync_type', 'all')
            date_from = data.get('date_from')
            date_to = data.get('date_to')
            
            # 執行同步
            sync_service = ReportDataSyncService()
            result = sync_service.sync_data(
                sync_type=sync_type,
                date_from=date_from,
                date_to=date_to,
                user=request.user.username
            )
            
            return JsonResponse(result)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'failed',
                'message': '請求格式錯誤'
            }, status=400)
        except Exception as e:
            logger.error(f"API 同步執行失敗：{str(e)}")
            return JsonResponse({
                'status': 'failed',
                'message': str(e)
            }, status=500)
    
    def get(self, request, *args, **kwargs):
        """取得同步狀態"""
        try:
            # 取得最近同步狀態
            recent_syncs = ReportDataSyncLog.objects.order_by('-created_at')[:5]
            
            sync_status = []
            for sync in recent_syncs:
                sync_status.append({
                    'id': sync.id,
                    'sync_type': sync.sync_type,
                    'status': sync.status,
                    'created_at': sync.created_at.isoformat(),
                    'duration_seconds': sync.duration_seconds,
                    'processed': sync.records_processed,
                    'created': sync.records_created,
                    'updated': sync.records_updated,
                })
            
            return JsonResponse({
                'status': 'success',
                'data': {
                    'recent_syncs': sync_status,
                    'total_syncs': ReportDataSyncLog.objects.count(),
                    'success_syncs': ReportDataSyncLog.objects.filter(status='success').count(),
                    'error_syncs': ReportDataSyncLog.objects.filter(status='failed').count(),
                }
            })
            
        except Exception as e:
            logger.error(f"取得同步狀態失敗：{str(e)}")
            return JsonResponse({
                'status': 'failed',
                'message': str(e)
            }, status=500)


class WorkOrderAllocationView(LoginRequiredMixin, UserPassesTestMixin, View):
    """工單數量分擔視圖"""
    
    def test_func(self):
        """檢查用戶權限"""
        return self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        """執行工單數量分擔"""
        try:
            workorder_id = request.POST.get('workorder_id')
            force = request.POST.get('force', 'false').lower() == 'true'
            
            if not workorder_id:
                messages.error(request, "請提供工單ID")
                return redirect('reporting:sync_status_list')
            
            # 執行數量分擔
            sync_service = ReportDataSyncService()
            result = sync_service.sync_workorder_allocation(
                int(workorder_id), 
                force=force
            )
            
            if result['status'] == 'success':
                messages.success(
                    request, 
                    f"工單數量分擔成功！總完成數量：{result['total_completed']}，處理 {len(result['allocation_results'])} 筆報工記錄。"
                )
            else:
                messages.error(request, f"工單數量分擔失敗：{result['message']}")
                
        except ValueError:
            messages.error(request, "工單ID格式錯誤")
        except Exception as e:
            logger.error(f"工單數量分擔執行失敗：{str(e)}")
            messages.error(request, f"工單數量分擔失敗：{str(e)}")
        
        return redirect('reporting:sync_status_list') 