#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動分配排程服務
負責管理自動分配功能的輪迴執行
"""

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from workorder.models import AutoAllocationSettings, AutoAllocationLog
from workorder.services.auto_allocation_service import AutoAllocationService

logger = logging.getLogger(__name__)


class AutoAllocationScheduler:
    """
    自動分配排程器
    管理自動分配功能的執行排程
    """
    
    def __init__(self):
        self.allocation_service = AutoAllocationService()
        self.cache_key = "auto_allocation_scheduler_running"
    
    def get_settings(self):
        """取得自動分配設定"""
        from datetime import time
        
        settings, created = AutoAllocationSettings.objects.get_or_create(
            id=1,  # 使用單一設定
            defaults={
                'enabled': False,
                'interval_minutes': 30,
                'start_time': time(8, 0),  # 08:00
                'end_time': time(18, 0),   # 18:00
                'max_execution_time': 30,
                'notification_enabled': True
            }
        )
        return settings
    
    def should_execute(self):
        """判斷是否應該執行自動分配"""
        settings = self.get_settings()
        return settings.should_execute()
    
    def execute_auto_allocation(self):
        """執行自動分配"""
        settings = self.get_settings()
        
        # 檢查是否已在執行
        if settings.is_running:
            logger.warning("自動分配已在執行中，跳過本次執行")
            return False
        
        # 移除執行時間範圍檢查，允許全天候執行
        # if not settings.is_within_execution_window():
        #     logger.info("當前時間不在執行時間範圍內，跳過執行")
        #     return False
        
        # 標記為執行中
        settings.is_running = True
        settings.save()
        
        # 創建執行記錄
        log_entry = AutoAllocationLog.objects.create(
            started_at=timezone.now()
        )
        
        try:
            logger.info("開始執行自動分配")
            
            # 使用現有的自動分配命令
            from django.core.management import call_command
            from io import StringIO
            from django.test.utils import override_settings
            
            # 捕獲命令輸出
            output = StringIO()
            
            # 執行自動分配命令
            call_command(
                'auto_allocate_quantities',
                '--all',
                stdout=output,
                stderr=output
            )
            
            # 解析輸出結果
            output_text = output.getvalue()
            logger.info(f"自動分配命令輸出: {output_text}")
            
            # 簡單的成功判斷（可以根據實際輸出調整）
            success = "成功分配" in output_text or "分配完成" in output_text
            
            # 嘗試從輸出中提取統計資訊
            total_workorders = 0
            successful_allocations = 0
            failed_allocations = 0
            
            for line in output_text.split('\n'):
                if '總工單數:' in line:
                    try:
                        total_workorders = int(line.split(':')[1].strip())
                    except:
                        pass
                elif '成功分配:' in line:
                    try:
                        successful_allocations = int(line.split(':')[1].strip().split()[0])
                    except:
                        pass
                elif '分配失敗:' in line:
                    try:
                        failed_allocations = int(line.split(':')[1].strip().split()[0])
                    except:
                        pass
            
            result = {
                'successful_allocations': successful_allocations,
                'total_workorders': total_workorders,
                'failed_allocations': failed_allocations,
                'output': output_text
            }
            
            # 更新執行記錄
            log_entry.completed_at = timezone.now()
            log_entry.execution_time = log_entry.completed_at - log_entry.started_at
            log_entry.success = result.get('successful_allocations', 0) >= 0  # 基本成功判斷
            log_entry.total_workorders = result.get('total_workorders', 0)
            log_entry.successful_allocations = result.get('successful_allocations', 0)
            log_entry.failed_allocations = result.get('failed_allocations', 0)
            log_entry.result_details = result
            log_entry.save()
            
            # 更新設定統計
            settings.total_executions += 1
            if log_entry.success:
                settings.success_count += 1
            else:
                settings.failure_count += 1
            
            if settings.total_execution_time:
                settings.total_execution_time += log_entry.execution_time
            else:
                settings.total_execution_time = log_entry.execution_time
            
            settings.last_execution = log_entry.started_at
            settings.next_execution = self._calculate_next_execution(settings)
            settings.is_running = False
            settings.save()
            
            logger.info(f"自動分配執行完成: 處理 {log_entry.total_workorders} 個工單, "
                       f"成功 {log_entry.successful_allocations} 個, "
                       f"失敗 {log_entry.failed_allocations} 個")
            
            return True
            
        except Exception as e:
            logger.error(f"自動分配執行失敗: {str(e)}")
            
            # 更新執行記錄
            log_entry.completed_at = timezone.now()
            log_entry.execution_time = log_entry.completed_at - log_entry.started_at
            log_entry.success = False
            log_entry.error_message = str(e)
            log_entry.save()
            
            # 更新設定統計
            settings.total_executions += 1
            settings.failure_count += 1
            settings.last_execution = log_entry.started_at
            settings.next_execution = self._calculate_next_execution(settings)
            settings.is_running = False
            settings.save()
            
            return False
    
    def _calculate_next_execution(self, settings):
        """計算下次執行時間"""
        if not settings.enabled:
            return None
        
        now = timezone.now()
        next_time = now + timedelta(minutes=settings.interval_minutes)
        
        # 確保下次執行時間在允許的時間範圍內
        next_date = next_time.date()
        start_datetime = timezone.make_aware(
            datetime.combine(next_date, settings.start_time)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(next_date, settings.end_time)
        )
        
        if next_time < start_datetime:
            next_time = start_datetime
        elif next_time > end_datetime:
            # 如果超過今天的結束時間，設定為明天的開始時間
            next_date = next_date + timedelta(days=1)
            next_time = timezone.make_aware(
                datetime.combine(next_date, settings.start_time)
            )
        
        return next_time
    
    def get_status(self):
        """取得當前狀態"""
        try:
            settings = self.get_settings()
            
            # 計算今日執行次數
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            today_executions = AutoAllocationLog.objects.filter(
                started_at__gte=today_start,
                started_at__lt=today_end
            ).count()
            
            # 安全地處理時間欄位
            start_time_str = settings.start_time.strftime('%H:%M') if settings.start_time else '08:00'
            end_time_str = settings.end_time.strftime('%H:%M') if settings.end_time else '18:00'
            last_execution_str = settings.last_execution.strftime('%Y-%m-%d %H:%M:%S') if settings.last_execution else None
            next_execution_str = settings.next_execution.strftime('%Y-%m-%d %H:%M:%S') if settings.next_execution else None
            
            return {
                'enabled': settings.enabled,
                'is_running': settings.is_running,
                'interval_minutes': settings.interval_minutes,
                'start_time': start_time_str,
                'end_time': end_time_str,
                'max_execution_time': settings.max_execution_time,
                'notification_enabled': settings.notification_enabled,
                'last_execution': last_execution_str,
                'next_execution': next_execution_str,
                'today_executions': today_executions,
                'success_count': settings.success_count,
                'failure_count': settings.failure_count,
                'avg_execution_time': settings.get_avg_execution_time_display(),
            }
        except Exception as e:
            logger.error(f"取得自動分配狀態失敗: {str(e)}")
            # 返回預設狀態
            return {
                'enabled': False,
                'is_running': False,
                'interval_minutes': 30,
                'start_time': '08:00',
                'end_time': '18:00',
                'max_execution_time': 30,
                'notification_enabled': True,
                'last_execution': None,
                'next_execution': None,
                'today_executions': 0,
                'success_count': 0,
                'failure_count': 0,
                'avg_execution_time': '0秒',
            }
    
    def update_settings(self, **kwargs):
        """更新設定"""
        settings = self.get_settings()
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        # 重新計算下次執行時間
        if settings.enabled:
            settings.next_execution = self._calculate_next_execution(settings)
        
        settings.save()
        return settings
    
    def stop_execution(self):
        """停止執行"""
        settings = self.get_settings()
        settings.is_running = False
        settings.enabled = False
        settings.save()
        return True
    
    def get_recent_logs(self, limit=50):
        """取得最近的執行記錄"""
        return AutoAllocationLog.objects.all()[:limit]
    
    def cleanup_old_logs(self, days=30):
        """清理舊的執行記錄"""
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = AutoAllocationLog.objects.filter(
            started_at__lt=cutoff_date
        ).delete()
        logger.info(f"清理了 {deleted_count} 條舊的自動分配記錄")
        return deleted_count


# 全域排程器實例
scheduler = AutoAllocationScheduler()


def run_auto_allocation_task():
    """
    Celery 任務：執行自動分配
    這個函數將被 Celery 定期調用
    """
    try:
        if scheduler.should_execute():
            return scheduler.execute_auto_allocation()
        else:
            logger.debug("自動分配條件不滿足，跳過執行")
            return False
    except Exception as e:
        logger.error(f"自動分配任務執行失敗: {str(e)}")
        return False 