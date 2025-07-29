# 報表模組的 Celery 任務檔案
# 功能：自動同步報表資料、工單數量分擔
# 作者：MES 系統
# 建立時間：2024年

from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
from reporting.services.sync_service import ReportDataSyncService
from system.models import ReportSyncSettings
import logging

# 設定報表模組的日誌記錄器
reporting_logger = logging.getLogger("reporting")


@shared_task
def auto_sync_report_data():
    """
    自動同步報表資料
    從 ReportSyncSettings 讀取自動同步設定
    """
    try:
        reporting_logger.info("=== 開始自動同步報表資料 ===")

        # 讀取同步設定
        sync_settings = ReportSyncSettings.objects.filter(is_active=True)
        
        if not sync_settings.exists():
            reporting_logger.warning("未找到啟用的報表同步設定")
            return {
                "status": "warning",
                "message": "未找到啟用的報表同步設定",
                "timestamp": timezone.now().isoformat(),
            }

        # 初始化同步服務
        sync_service = ReportDataSyncService()
        
        # 計算同步日期範圍（預設同步最近7天）
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        total_processed = 0
        total_created = 0
        total_updated = 0
        
        # 執行同步
        for setting in sync_settings:
            try:
                reporting_logger.info(f"同步 {setting.get_sync_type_display()}")
                
                result = sync_service.sync_data(
                    sync_type=setting.sync_type,
                    date_from=start_date.strftime('%Y-%m-%d'),
                    date_to=end_date.strftime('%Y-%m-%d'),
                    user='system_auto'
                )
                
                total_processed += result['processed']
                total_created += result['created']
                total_updated += result['updated']
                
                reporting_logger.info(
                    f"{setting.get_sync_type_display()} 同步完成: "
                    f"處理 {result['processed']} 筆記錄, "
                    f"新增 {result['created']} 筆, "
                    f"更新 {result['updated']} 筆"
                )
                
            except Exception as e:
                reporting_logger.error(f"{setting.get_sync_type_display()} 同步失敗: {str(e)}")

        reporting_logger.info("自動同步報表資料完成")

        return {
            "status": "success",
            "message": f"自動同步完成，處理 {total_processed} 筆記錄，新增 {total_created} 筆，更新 {total_updated} 筆",
            "timestamp": timezone.now().isoformat(),
            "processed": total_processed,
            "created": total_created,
            "updated": total_updated
        }

    except Exception as e:
        reporting_logger.error(f"自動同步報表資料失敗：{str(e)}")
        return {
            "status": "error",
            "message": f"自動同步失敗：{str(e)}",
            "timestamp": timezone.now().isoformat(),
        }


@shared_task
def auto_allocate_completed_workorders():
    """
    自動處理已完工工單的數量分擔
    """
    try:
        reporting_logger.info("=== 開始自動處理已完工工單數量分擔 ===")

        from workorder.models import WorkOrder
        
        # 取得已完工但尚未進行數量分擔的工單
        completed_workorders = WorkOrder.objects.filter(
            status='completed',
            # 可以加入其他條件來判斷是否需要分擔
        )
        
        if not completed_workorders.exists():
            reporting_logger.info("沒有需要進行數量分擔的已完工工單")
            return {
                "status": "info",
                "message": "沒有需要進行數量分擔的已完工工單",
                "timestamp": timezone.now().isoformat(),
            }

        # 初始化同步服務
        sync_service = ReportDataSyncService()
        
        processed_count = 0
        success_count = 0
        error_count = 0
        
        # 處理每個已完工的工單
        for workorder in completed_workorders:
            try:
                reporting_logger.info(f"處理工單數量分擔: {workorder.order_number}")
                
                result = sync_service.sync_workorder_allocation(workorder.id)
                
                if result['status'] == 'success':
                    success_count += 1
                    reporting_logger.info(
                        f"工單 {workorder.order_number} 數量分擔成功: "
                        f"總完成數量 {result['total_completed']}, "
                        f"分擔記錄數 {len(result['allocation_results'])}"
                    )
                else:
                    error_count += 1
                    reporting_logger.warning(
                        f"工單 {workorder.order_number} 數量分擔失敗: {result['message']}"
                    )
                
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                reporting_logger.error(f"工單 {workorder.order_number} 數量分擔異常: {str(e)}")

        reporting_logger.info("自動處理已完工工單數量分擔完成")

        return {
            "status": "success",
            "message": f"自動處理完成，處理 {processed_count} 個工單，成功 {success_count} 個，失敗 {error_count} 個",
            "timestamp": timezone.now().isoformat(),
            "processed": processed_count,
            "success": success_count,
            "error": error_count
        }

    except Exception as e:
        reporting_logger.error(f"自動處理已完工工單數量分擔失敗：{str(e)}")
        return {
            "status": "error",
            "message": f"自動處理失敗：{str(e)}",
            "timestamp": timezone.now().isoformat(),
        }


@shared_task
def sync_specific_workorder_allocation(workorder_id):
    """
    同步指定工單的數量分擔
    
    Args:
        workorder_id (int): 工單ID
    """
    try:
        reporting_logger.info(f"=== 開始同步工單數量分擔 - 工單ID: {workorder_id} ===")

        # 初始化同步服務
        sync_service = ReportDataSyncService()
        
        # 執行數量分擔
        result = sync_service.sync_workorder_allocation(workorder_id)
        
        if result['status'] == 'success':
            reporting_logger.info(
                f"工單數量分擔成功: "
                f"總完成數量 {result['total_completed']}, "
                f"分擔記錄數 {len(result['allocation_results'])}"
            )
            
            return {
                "status": "success",
                "message": f"工單數量分擔成功，總完成數量 {result['total_completed']}",
                "timestamp": timezone.now().isoformat(),
                "total_completed": result['total_completed'],
                "allocation_count": len(result['allocation_results'])
            }
        else:
            reporting_logger.error(f"工單數量分擔失敗: {result['message']}")
            
            return {
                "status": "error",
                "message": f"工單數量分擔失敗: {result['message']}",
                "timestamp": timezone.now().isoformat(),
            }

    except Exception as e:
        reporting_logger.error(f"同步工單數量分擔失敗：{str(e)}")
        return {
            "status": "error",
            "message": f"同步失敗：{str(e)}",
            "timestamp": timezone.now().isoformat(),
        }
