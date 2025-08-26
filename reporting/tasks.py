"""
報表模組定時任務
包含報表檔案清理等自動化任務
"""

import os
import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def cleanup_report_files():
    """
    清理過期的報表檔案
    預設保留7天的報表檔案，超過7天的檔案會被自動刪除
    """
    try:
        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        
        if not os.path.exists(reports_dir):
            logger.info("報表目錄不存在，跳過清理")
            return
        
        # 設定保留天數（可從設定檔讀取，預設7天）
        retention_days = getattr(settings, 'REPORT_FILE_RETENTION_DAYS', 7)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        deleted_count = 0
        total_size_freed = 0
        
        logger.info(f"開始清理報表檔案，保留天數：{retention_days}天")
        
        for filename in os.listdir(reports_dir):
            file_path = os.path.join(reports_dir, filename)
            
            # 檢查是否為檔案
            if not os.path.isfile(file_path):
                continue
            
            # 檢查檔案修改時間
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_mtime = timezone.make_aware(file_mtime)
            
            if file_mtime < cutoff_date:
                try:
                    # 記錄檔案大小
                    file_size = os.path.getsize(file_path)
                    
                    # 刪除檔案
                    os.remove(file_path)
                    deleted_count += 1
                    total_size_freed += file_size
                    
                    logger.info(f"已刪除過期報表檔案：{filename}")
                    
                except Exception as e:
                    logger.error(f"刪除檔案失敗 {filename}: {str(e)}")
        
        # 記錄清理結果
        if deleted_count > 0:
            size_mb = total_size_freed / (1024 * 1024)
            logger.info(f"報表檔案清理完成：刪除 {deleted_count} 個檔案，釋放 {size_mb:.2f} MB 空間")
        else:
            logger.info("沒有需要清理的報表檔案")
            
    except Exception as e:
        logger.error(f"清理報表檔案失敗: {str(e)}")


@shared_task
def cleanup_report_execution_logs():
    """
    清理過期的報表執行日誌
    預設保留30天的執行日誌，超過30天的記錄會被自動刪除
    """
    try:
        from .models import ReportExecutionLog
        
        # 設定保留天數（可從設定檔讀取，預設30天）
        retention_days = getattr(settings, 'REPORT_LOG_RETENTION_DAYS', 30)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        # 刪除過期的日誌記錄
        deleted_count, _ = ReportExecutionLog.objects.filter(
            execution_time__lt=cutoff_date
        ).delete()
        
        if deleted_count > 0:
            logger.info(f"已清理 {deleted_count} 條過期的報表執行日誌")
        else:
            logger.info("沒有需要清理的報表執行日誌")
            
    except Exception as e:
        logger.error(f"清理報表執行日誌失敗: {str(e)}")


@shared_task
def generate_system_cleanup_report():
    """
    生成系統清理報告
    統計清理結果並記錄到日誌
    """
    try:
        from .models import ReportExecutionLog
        
        # 統計報表檔案數量
        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        file_count = 0
        total_size = 0
        
        if os.path.exists(reports_dir):
            for filename in os.listdir(reports_dir):
                file_path = os.path.join(reports_dir, filename)
                if os.path.isfile(file_path):
                    file_count += 1
                    total_size += os.path.getsize(file_path)
        
        # 統計日誌記錄數量
        log_count = ReportExecutionLog.objects.count()
        
        # 記錄統計資訊
        size_mb = total_size / (1024 * 1024)
        logger.info(f"系統清理報告 - 報表檔案：{file_count} 個，總大小：{size_mb:.2f} MB，執行日誌：{log_count} 條")
        
    except Exception as e:
        logger.error(f"生成系統清理報告失敗: {str(e)}")
