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


@shared_task
def auto_analyze_completed_workorders():
    """
    定時自動分析已完工工單
    每小時執行一次，分析最近完工的工單
    """
    from workorder.models import CompletedWorkOrder
    from .models import CompletedWorkOrderAnalysis
    from .services import WorkOrderAnalysisService
    from datetime import datetime, timedelta
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # 取得最近24小時內完工的工單
        yesterday = datetime.now().date() - timedelta(days=1)
        
        # 查詢最近完工但尚未分析的工單
        recent_completed = CompletedWorkOrder.objects.filter(
            completed_at__date__gte=yesterday
        ).values_list('workorder_id', 'company_code')
        
        # 取得已經分析過的工單ID
        analyzed_workorders = set(
            CompletedWorkOrderAnalysis.objects.values_list('workorder_id', 'company_code')
        )
        
        # 過濾出尚未分析的工單
        pending_analysis = [
            (workorder_id, company_code) 
            for workorder_id, company_code in recent_completed
            if (workorder_id, company_code) not in analyzed_workorders
        ]
        
        if not pending_analysis:
            logger.info("沒有需要分析的工單")
            return {
                'success': True,
                'message': '沒有需要分析的工單',
                'analyzed_count': 0
            }
        
        # 批量分析
        success_count = 0
        error_count = 0
        errors = []
        
        for workorder_id, company_code in pending_analysis:
            try:
                result = WorkOrderAnalysisService.analyze_completed_workorder(
                    workorder_id, company_code, force=False
                )
                if result['success']:
                    success_count += 1
                    logger.info(f"成功分析工單: {workorder_id}")
                else:
                    error_count += 1
                    errors.append(f"工單 {workorder_id}: {result.get('error', '未知錯誤')}")
                    logger.error(f"分析工單失敗 {workorder_id}: {result.get('error', '未知錯誤')}")
            except Exception as e:
                error_count += 1
                errors.append(f"工單 {workorder_id}: {str(e)}")
                logger.error(f"分析工單時發生異常 {workorder_id}: {str(e)}")
        
        logger.info(f"自動分析完成: 成功 {success_count} 筆，失敗 {error_count} 筆")
        
        return {
            'success': True,
            'message': f'自動分析完成，成功: {success_count}，失敗: {error_count}',
            'analyzed_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"自動分析任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'自動分析任務執行失敗: {str(e)}'
        }


@shared_task
def batch_analyze_completed_workorders(start_date=None, end_date=None, company_code=None):
    """
    批量分析已完工工單（手動觸發）
    """
    from .services import WorkOrderAnalysisService
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        result = WorkOrderAnalysisService.analyze_completed_workorders_batch(
            start_date=start_date,
            end_date=end_date,
            company_code=company_code
        )
        
        if result['success']:
            logger.info(f"批量分析完成: {result['message']}")
        else:
            logger.error(f"批量分析失敗: {result.get('error', '未知錯誤')}")
        
        return result
        
    except Exception as e:
        logger.error(f"批量分析任務執行失敗: {str(e)}")
        return {
            'success': False,
            'error': f'批量分析任務執行失敗: {str(e)}'
        }
