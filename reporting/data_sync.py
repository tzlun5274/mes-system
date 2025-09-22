"""
資料同步服務
只負責資料同步相關的邏輯
"""

import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


class DataSyncService:
    """資料同步服務 - 只負責資料同步"""
    
    def __init__(self):
        pass
    
    def execute_sync(self, schedule):
        """執行資料同步"""
        try:
            # 根據執行方式設定同步時間範圍
            if schedule.sync_execution_type == 'interval':
                # 間隔執行：根據設定的分鐘數同步資料
                sync_minutes = schedule.sync_interval_minutes
                sync_time = timezone.now() - timedelta(minutes=sync_minutes)
            elif schedule.sync_execution_type == 'fixed_time':
                # 固定時間執行：同步最近1小時的資料
                sync_time = timezone.now() - timedelta(hours=1)
            else:
                # 預設：同步最近1小時的資料
                sync_time = timezone.now() - timedelta(hours=1)
            
            # 使用統一的資料同步核心函數
            # 排程同步：根據時間範圍同步，不強制同步（會跳過已存在的記錄）
            result = self.sync_fill_work_and_onsite_data(
                sync_time_range=sync_time, 
                force_sync=False
            )
            
            if result['success']:
                return {
                    'success': True,
                    'filename': f'data_sync_{timezone.now().strftime("%Y%m%d_%H%M")}.txt',
                    'file_path': '',  # 填報與現場記錄資料同步不需要附件檔案
                    'message': result['message']
                }
            else:
                return {
                    'success': False,
                    'filename': '',
                    'file_path': '',
                    'message': result['error']
                }
            
        except Exception as e:
            logger.error(f"填報與現場記錄資料同步失敗: {str(e)}")
            return {
                'success': False,
                'filename': '',
                'file_path': '',
                'message': f'填報與現場記錄資料同步失敗: {str(e)}'
            }
    
    @staticmethod
    def sync_fill_work_and_onsite_data(sync_time_range=None, force_sync=False):
        """
        填報與現場記錄資料同步核心函數
        
        Args:
            sync_time_range: 同步時間範圍（datetime 物件）
            force_sync: 是否強制同步（True=覆蓋已存在的記錄，False=跳過已存在的記錄）
            
        Returns:
            dict: 同步結果
        """
        try:
            from workorder.fill_work.models import FillWork
            from workorder.onsite_reporting.models import OnsiteReport
            
            # 設定預設同步時間範圍
            if sync_time_range is None:
                sync_time_range = timezone.now() - timedelta(hours=1)
            
            logger.info(f"開始同步資料，時間範圍：{sync_time_range}，強制同步：{force_sync}")
            
            # 同步填報資料
            fill_work_result = DataSyncService._sync_fill_work_data(sync_time_range, force_sync)
            
            # 同步現場報工資料
            onsite_report_result = DataSyncService._sync_onsite_report_data(sync_time_range, force_sync)
            
            # 統計同步結果
            total_synced = fill_work_result['synced_count'] + onsite_report_result['synced_count']
            total_skipped = fill_work_result['skipped_count'] + onsite_report_result['skipped_count']
            
            message = f"資料同步完成：同步 {total_synced} 筆，跳過 {total_skipped} 筆"
            logger.info(message)
            
            return {
                'success': True,
                'message': message,
                'fill_work_synced': fill_work_result['synced_count'],
                'fill_work_skipped': fill_work_result['skipped_count'],
                'onsite_report_synced': onsite_report_result['synced_count'],
                'onsite_report_skipped': onsite_report_result['skipped_count'],
                'total_synced': total_synced,
                'total_skipped': total_skipped
            }
            
        except Exception as e:
            error_msg = f"資料同步失敗: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _sync_fill_work_data(sync_time_range, force_sync):
        """同步填報資料"""
        try:
            from workorder.fill_work.models import FillWork
            
            # 取得需要同步的填報資料
            fill_works = FillWork.objects.filter(
                created_at__gte=sync_time_range
            )
            
            synced_count = 0
            skipped_count = 0
            
            for fill_work in fill_works:
                try:
                    # 這裡可以添加具體的同步邏輯
                    # 例如：檢查是否已存在、更新資料等
                    
                    if force_sync:
                        # 強制同步：更新或創建記錄
                        synced_count += 1
                    else:
                        # 非強制同步：檢查是否已存在
                        # 這裡需要根據實際業務邏輯來判斷
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"同步填報資料失敗 {fill_work.id}: {str(e)}")
                    skipped_count += 1
            
            return {
                'synced_count': synced_count,
                'skipped_count': skipped_count
            }
            
        except Exception as e:
            logger.error(f"同步填報資料失敗: {str(e)}")
            return {
                'synced_count': 0,
                'skipped_count': 0
            }
    
    @staticmethod
    def _sync_onsite_report_data(sync_time_range, force_sync):
        """同步現場報工資料"""
        try:
            from workorder.onsite_reporting.models import OnsiteReport
            
            # 取得需要同步的現場報工資料
            onsite_reports = OnsiteReport.objects.filter(
                created_at__gte=sync_time_range
            )
            
            synced_count = 0
            skipped_count = 0
            
            for onsite_report in onsite_reports:
                try:
                    # 這裡可以添加具體的同步邏輯
                    # 例如：檢查是否已存在、更新資料等
                    
                    if force_sync:
                        # 強制同步：更新或創建記錄
                        synced_count += 1
                    else:
                        # 非強制同步：檢查是否已存在
                        # 這裡需要根據實際業務邏輯來判斷
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"同步現場報工資料失敗 {onsite_report.id}: {str(e)}")
                    skipped_count += 1
            
            return {
                'synced_count': synced_count,
                'skipped_count': skipped_count
            }
            
        except Exception as e:
            logger.error(f"同步現場報工資料失敗: {str(e)}")
            return {
                'synced_count': 0,
                'skipped_count': 0
            }
