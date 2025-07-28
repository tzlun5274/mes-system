# 報表資料同步服務
# 本檔案負責將已核准的報工資料同步到報表模組的專用資料表中

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from system.models import ReportDataSyncLog, ReportSyncSettings
from reporting.models import WorkTimeReport, WorkOrderProductReport
from workorder.models import (
    OperatorSupplementReport, 
    SMTProductionReport, 
    SupervisorProductionReport
)

logger = logging.getLogger(__name__)


class ReportDataSyncService:
    """報表資料同步服務"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def sync_data(self, sync_type='all', date_from=None, date_to=None, user=None):
        """
        同步報表資料
        
        Args:
            sync_type (str): 同步類型 ('work_time', 'work_order', 'all')
            date_from (str): 開始日期 (YYYY-MM-DD)
            date_to (str): 結束日期 (YYYY-MM-DD)
            user: 執行同步的用戶
            
        Returns:
            dict: 同步結果
        """
        start_time = timezone.now()
        
        try:
            # 解析日期
            if date_from:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            else:
                date_from = timezone.now().date() - timedelta(days=7)
                
            if date_to:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            else:
                date_to = timezone.now().date()
            
            # 建立同步日誌
            sync_log = ReportDataSyncLog.objects.create(
                sync_type=sync_type,
                period_start=date_from,
                period_end=date_to,
                status='pending',
                started_at=start_time
            )
            
            records_processed = 0
            records_created = 0
            records_updated = 0
            
            # 根據同步類型執行不同的同步邏輯
            if sync_type in ['work_time', 'all']:
                result = self._sync_work_time_reports(date_from, date_to)
                records_processed += result['processed']
                records_created += result['created']
                records_updated += result['updated']
            
            if sync_type in ['work_order', 'all']:
                result = self._sync_work_order_reports(date_from, date_to)
                records_processed += result['processed']
                records_created += result['created']
                records_updated += result['updated']
            
            # 更新同步日誌
            completed_time = timezone.now()
            duration_seconds = int((completed_time - start_time).total_seconds())
            
            sync_log.status = 'success'
            sync_log.completed_at = completed_time
            sync_log.duration_seconds = duration_seconds
            sync_log.records_processed = records_processed
            sync_log.records_created = records_created
            sync_log.records_updated = records_updated
            sync_log.save()
            
            self.logger.info(f"報表資料同步成功: {sync_type}, 處理 {records_processed} 筆記錄")
            
            return {
                'success': True,
                'records_processed': records_processed,
                'records_created': records_created,
                'records_updated': records_updated,
                'duration_seconds': duration_seconds
            }
            
        except Exception as e:
            # 記錄錯誤
            completed_time = timezone.now()
            duration_seconds = int((completed_time - start_time).total_seconds())
            
            if 'sync_log' in locals():
                sync_log.status = 'failed'
                sync_log.completed_at = completed_time
                sync_log.duration_seconds = duration_seconds
                sync_log.error_message = str(e)
                sync_log.save()
            
            self.logger.error(f"報表資料同步失敗: {sync_type}, 錯誤: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'duration_seconds': duration_seconds
            }
    
    def _sync_work_time_reports(self, date_from, date_to):
        """
        同步工作時間報表資料
        
        Args:
            date_from (date): 開始日期
            date_to (date): 結束日期
            
        Returns:
            dict: 同步結果統計
        """
        records_processed = 0
        records_created = 0
        records_updated = 0
        
        try:
            # 取得已核准的作業員補登報工記錄
            operator_reports = OperatorSupplementReport.objects.filter(
                approval_status='approved',
                work_date__gte=date_from,
                work_date__lte=date_to
            ).select_related('operator', 'workorder', 'process', 'equipment')
            
            # 取得已核准的SMT生產報工記錄
            smt_reports = SMTProductionReport.objects.filter(
                approval_status='approved',
                work_date__gte=date_from,
                work_date__lte=date_to
            ).select_related('workorder', 'equipment')
            
            # 取得已核准的主管生產報工記錄
            supervisor_reports = SupervisorProductionReport.objects.filter(
                approval_status='approved',
                work_date__gte=date_from,
                work_date__lte=date_to
            ).select_related('workorder', 'process', 'equipment', 'operator')
            
            # 處理作業員報工記錄
            for report in operator_reports:
                records_processed += 1
                
                # 計算工作時數
                start_time = report.start_time
                end_time = report.end_time
                work_hours = self._calculate_work_hours(start_time, end_time)
                
                # 計算效率
                efficiency_rate = 0
                if work_hours > 0:
                    efficiency_rate = report.work_quantity / work_hours
                
                # 計算良率
                total_quantity = report.work_quantity + report.defect_quantity
                yield_rate = 0
                if total_quantity > 0:
                    yield_rate = (report.work_quantity / total_quantity) * 100
                
                # 建立或更新工作時間報表記錄
                work_time_report, created = WorkTimeReport.objects.update_or_create(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.operator.name if report.operator else '未知作業員',
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    defaults={
                        'worker_type': 'operator',
                        'product_code': report.product_id,
                        'process_name': report.operation,
                        'start_time': start_time,
                        'end_time': end_time,
                        'total_work_hours': work_hours,
                        'actual_work_hours': work_hours,
                        'completed_quantity': report.work_quantity,
                        'defect_quantity': report.defect_quantity,
                        'yield_rate': yield_rate,
                        'efficiency_rate': efficiency_rate,
                        'original_quantity': report.work_quantity,
                        'allocated_quantity': report.allocated_quantity,
                        'quantity_source': 'allocated' if report.allocated_quantity > 0 else 'original',
                        'allocation_notes': report.allocation_notes or '',
                        'abnormal_notes': report.abnormal_notes or '',
                        'data_source': 'workorder',
                        'calculation_method': 'approved_reports_sync',
                        'created_by': 'system_sync'
                    }
                )
                
                if created:
                    records_created += 1
                else:
                    records_updated += 1
            
            # 處理SMT報工記錄
            for report in smt_reports:
                records_processed += 1
                
                # 計算工作時數
                start_time = report.start_time
                end_time = report.end_time
                work_hours = self._calculate_work_hours(start_time, end_time)
                
                # 計算效率
                efficiency_rate = 0
                if work_hours > 0:
                    efficiency_rate = report.work_quantity / work_hours
                
                # 計算良率
                total_quantity = report.work_quantity + report.defect_quantity
                yield_rate = 0
                if total_quantity > 0:
                    yield_rate = (report.work_quantity / total_quantity) * 100
                
                # 建立或更新工作時間報表記錄
                work_time_report, created = WorkTimeReport.objects.update_or_create(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.equipment.name if report.equipment else '未知設備',
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    defaults={
                        'worker_type': 'smt',
                        'product_code': report.product_id,
                        'process_name': report.operation,
                        'start_time': start_time,
                        'end_time': end_time,
                        'total_work_hours': work_hours,
                        'actual_work_hours': work_hours,
                        'completed_quantity': report.work_quantity,
                        'defect_quantity': report.defect_quantity,
                        'yield_rate': yield_rate,
                        'efficiency_rate': efficiency_rate,
                        'original_quantity': report.work_quantity,
                        'allocated_quantity': 0,
                        'quantity_source': 'original',
                        'allocation_notes': '',
                        'abnormal_notes': report.abnormal_notes or '',
                        'data_source': 'workorder',
                        'calculation_method': 'approved_reports_sync',
                        'created_by': 'system_sync'
                    }
                )
                
                if created:
                    records_created += 1
                else:
                    records_updated += 1
            
            # 處理主管報工記錄
            for report in supervisor_reports:
                records_processed += 1
                
                # 計算工作時數
                start_time = report.start_time
                end_time = report.end_time
                work_hours = self._calculate_work_hours(start_time, end_time)
                
                # 計算效率
                efficiency_rate = 0
                if work_hours > 0:
                    efficiency_rate = report.work_quantity / work_hours
                
                # 計算良率
                total_quantity = report.work_quantity + report.defect_quantity
                yield_rate = 0
                if total_quantity > 0:
                    yield_rate = (report.work_quantity / total_quantity) * 100
                
                # 建立或更新工作時間報表記錄
                work_time_report, created = WorkTimeReport.objects.update_or_create(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.supervisor,
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    defaults={
                        'worker_type': 'operator',
                        'product_code': report.workorder.product_id if report.workorder else '',
                        'process_name': report.process.name if report.process else '',
                        'start_time': start_time,
                        'end_time': end_time,
                        'total_work_hours': work_hours,
                        'actual_work_hours': work_hours,
                        'completed_quantity': report.work_quantity,
                        'defect_quantity': report.defect_quantity,
                        'yield_rate': yield_rate,
                        'efficiency_rate': efficiency_rate,
                        'original_quantity': report.work_quantity,
                        'allocated_quantity': 0,
                        'quantity_source': 'original',
                        'allocation_notes': '',
                        'abnormal_notes': report.abnormal_notes or '',
                        'data_source': 'workorder',
                        'calculation_method': 'approved_reports_sync',
                        'created_by': 'system_sync'
                    }
                )
                
                if created:
                    records_created += 1
                else:
                    records_updated += 1
            
            return {
                'processed': records_processed,
                'created': records_created,
                'updated': records_updated
            }
            
        except Exception as e:
            self.logger.error(f"同步工作時間報表失敗: {str(e)}")
            raise
    
    def _sync_work_order_reports(self, date_from, date_to):
        """
        同步工單機種報表資料
        
        Args:
            date_from (date): 開始日期
            date_to (date): 結束日期
            
        Returns:
            dict: 同步結果統計
        """
        records_processed = 0
        records_created = 0
        records_updated = 0
        
        try:
            # 取得已核准的報工記錄，按工單分組統計
            from django.db.models import Sum, Count
            
            # 作業員報工統計
            operator_stats = OperatorSupplementReport.objects.filter(
                approval_status='approved',
                work_date__gte=date_from,
                work_date__lte=date_to
            ).values('workorder__order_number', 'workorder__product_id', 'workorder__product_name').annotate(
                total_completed=Sum('work_quantity'),
                total_defect=Sum('defect_quantity'),
                total_work_hours=Sum('allocated_quantity'),  # 使用分配數量作為工時近似值
                report_count=Count('id')
            )
            
            # SMT報工統計
            smt_stats = SMTProductionReport.objects.filter(
                approval_status='approved',
                work_date__gte=date_from,
                work_date__lte=date_to
            ).values('workorder__order_number', 'workorder__product_id', 'workorder__product_name').annotate(
                total_completed=Sum('work_quantity'),
                total_defect=Sum('defect_quantity'),
                total_work_hours=Sum('work_quantity'),  # 使用完成數量作為工時近似值
                report_count=Count('id')
            )
            
            # 主管報工統計
            supervisor_stats = SupervisorProductionReport.objects.filter(
                approval_status='approved',
                work_date__gte=date_from,
                work_date__lte=date_to
            ).values('workorder__order_number', 'workorder__product_id', 'workorder__product_name').annotate(
                total_completed=Sum('work_quantity'),
                total_defect=Sum('defect_quantity'),
                total_work_hours=Sum('work_quantity'),  # 使用完成數量作為工時近似值
                report_count=Count('id')
            )
            
            # 合併所有統計資料
            all_stats = {}
            
            for stat in operator_stats:
                workorder_number = stat['workorder__order_number']
                if workorder_number not in all_stats:
                    all_stats[workorder_number] = {
                        'product_id': stat['workorder__product_id'],
                        'product_name': stat['workorder__product_name'],
                        'total_completed': 0,
                        'total_defect': 0,
                        'total_work_hours': 0,
                        'report_count': 0
                    }
                all_stats[workorder_number]['total_completed'] += stat['total_completed'] or 0
                all_stats[workorder_number]['total_defect'] += stat['total_defect'] or 0
                all_stats[workorder_number]['total_work_hours'] += stat['total_work_hours'] or 0
                all_stats[workorder_number]['report_count'] += stat['report_count'] or 0
            
            for stat in smt_stats:
                workorder_number = stat['workorder__order_number']
                if workorder_number not in all_stats:
                    all_stats[workorder_number] = {
                        'product_id': stat['workorder__product_id'],
                        'product_name': stat['workorder__product_name'],
                        'total_completed': 0,
                        'total_defect': 0,
                        'total_work_hours': 0,
                        'report_count': 0
                    }
                all_stats[workorder_number]['total_completed'] += stat['total_completed'] or 0
                all_stats[workorder_number]['total_defect'] += stat['total_defect'] or 0
                all_stats[workorder_number]['total_work_hours'] += stat['total_work_hours'] or 0
                all_stats[workorder_number]['report_count'] += stat['report_count'] or 0
            
            for stat in supervisor_stats:
                workorder_number = stat['workorder__order_number']
                if workorder_number not in all_stats:
                    all_stats[workorder_number] = {
                        'product_id': stat['workorder__product_id'],
                        'product_name': stat['workorder__product_name'],
                        'total_completed': 0,
                        'total_defect': 0,
                        'total_work_hours': 0,
                        'report_count': 0
                    }
                all_stats[workorder_number]['total_completed'] += stat['total_completed'] or 0
                all_stats[workorder_number]['total_defect'] += stat['total_defect'] or 0
                all_stats[workorder_number]['total_work_hours'] += stat['total_work_hours'] or 0
                all_stats[workorder_number]['report_count'] += stat['report_count'] or 0
            
            # 建立工單機種報表記錄
            for workorder_number, stats in all_stats.items():
                records_processed += 1
                
                # 計算良率
                total_quantity = stats['total_completed'] + stats['total_defect']
                yield_rate = 0
                if total_quantity > 0:
                    yield_rate = (stats['total_completed'] / total_quantity) * 100
                
                # 建立或更新工單機種報表記錄
                work_order_report, created = WorkOrderProductReport.objects.update_or_create(
                    report_type='daily',
                    report_date=date_from,  # 使用開始日期作為報表日期
                    workorder_number=workorder_number,
                    defaults={
                        'product_code': stats['product_id'] or '',
                        'product_name': stats['product_name'] or '',
                        'planned_quantity': 0,  # 需要從工單取得計劃數量
                        'planned_start_date': date_from,
                        'planned_end_date': date_to,
                        'completed_quantity': stats['total_completed'],
                        'completion_rate': 0,  # 需要計算完成率
                        'actual_start_date': date_from,
                        'actual_end_date': date_to,
                        'assigned_operators': '',  # 需要統計作業員清單
                        'total_work_hours': stats['total_work_hours'],
                        'assigned_equipment': '',  # 需要統計設備清單
                        'equipment_usage_rate': 0,  # 需要計算設備使用率
                        'defect_quantity': stats['total_defect'],
                        'yield_rate': yield_rate,
                        'quality_score': yield_rate,  # 使用良率作為品質評分
                        'data_source': 'workorder',
                        'calculation_method': 'approved_reports_sync',
                        'created_by': 'system_sync'
                    }
                )
                
                if created:
                    records_created += 1
                else:
                    records_updated += 1
            
            return {
                'processed': records_processed,
                'created': records_created,
                'updated': records_updated
            }
            
        except Exception as e:
            self.logger.error(f"同步工單機種報表失敗: {str(e)}")
            raise
    
    def _calculate_work_hours(self, start_time, end_time):
        """
        計算工作時數
        
        Args:
            start_time (time): 開始時間
            end_time (time): 結束時間
            
        Returns:
            float: 工作時數
        """
        if not start_time or not end_time:
            return 0.0
        
        # 轉換為小時
        start_hours = start_time.hour + start_time.minute / 60.0
        end_hours = end_time.hour + end_time.minute / 60.0
        
        # 計算時數差
        if end_hours >= start_hours:
            work_hours = end_hours - start_hours
        else:
            # 跨日的情況
            work_hours = (24 - start_hours) + end_hours
        
        return round(work_hours, 2)
    
    def get_sync_settings(self):
        """
        取得同步設定
        
        Returns:
            QuerySet: 同步設定列表
        """
        return ReportSyncSettings.objects.filter(is_active=True)
    
    def execute_scheduled_sync(self):
        """
        執行排程同步
        """
        settings = self.get_sync_settings()
        
        for setting in settings:
            try:
                # 檢查是否需要執行同步
                if self._should_execute_sync(setting):
                    self.sync_data(
                        sync_type=setting.sync_type,
                        date_from=(timezone.now().date() - timedelta(days=1)).strftime('%Y-%m-%d'),
                        date_to=timezone.now().date().strftime('%Y-%m-%d')
                    )
                    
                    # 更新最後同步時間
                    setting.last_sync_time = timezone.now()
                    setting.last_sync_status = 'success'
                    setting.save()
                    
            except Exception as e:
                self.logger.error(f"執行排程同步失敗: {setting.sync_type}, 錯誤: {str(e)}")
                
                # 更新同步狀態
                setting.last_sync_time = timezone.now()
                setting.last_sync_status = 'failed'
                setting.save()
    
    def _should_execute_sync(self, setting):
        """
        檢查是否應該執行同步
        
        Args:
            setting (ReportSyncSettings): 同步設定
            
        Returns:
            bool: 是否應該執行同步
        """
        if not setting.auto_sync:
            return False
        
        if not setting.last_sync_time:
            return True
        
        now = timezone.now()
        last_sync = setting.last_sync_time
        
        if setting.sync_frequency == 'hourly':
            return (now - last_sync).total_seconds() >= 3600
        elif setting.sync_frequency == 'daily':
            return (now - last_sync).days >= 1
        elif setting.sync_frequency == 'weekly':
            return (now - last_sync).days >= 7
        elif setting.sync_frequency == 'monthly':
            return (now - last_sync).days >= 30
        
        return False 