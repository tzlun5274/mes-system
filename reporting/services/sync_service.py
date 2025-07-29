# 報表資料同步服務
# 本檔案負責將已核准的報工資料同步到報表模組的專用資料表中

import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Count
from system.models import ReportDataSyncLog, ReportSyncSettings
from reporting.models import WorkTimeReport, WorkOrderProductReport
from workorder.models import (
    OperatorSupplementReport, 
    SMTProductionReport, 
    SupervisorProductionReport,
    WorkOrder,
    WorkOrderProcess
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
                status='partial',
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
            
            self.logger.info(f"同步完成: 處理 {records_processed} 筆記錄，新增 {records_created} 筆，更新 {records_updated} 筆")
            
            return {
                'status': 'success',
                'processed': records_processed,
                'created': records_created,
                'updated': records_updated,
                'duration_seconds': duration_seconds
            }
            
        except Exception as e:
            self.logger.error(f"同步失敗: {str(e)}")
            
            # 更新同步日誌為失敗狀態
            if 'sync_log' in locals():
                sync_log.status = 'failed'
                sync_log.error_message = str(e)
                sync_log.completed_at = timezone.now()
                sync_log.duration_seconds = int((timezone.now() - start_time).total_seconds())
                sync_log.save()
            
            raise
    
    def _sync_work_time_reports(self, date_from, date_to):
        """
        同步工作時間報表資料
        以工作時間為主，記錄作業員和設備的工作時間統計
        
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
                work_hours = 0
                
                if start_time and end_time:
                    # 計算工作時數
                    start_dt = datetime.combine(report.work_date, start_time)
                    end_dt = datetime.combine(report.work_date, end_time)
                    
                    # 如果結束時間小於開始時間，表示跨日
                    if end_dt < start_dt:
                        end_dt += timedelta(days=1)
                    
                    work_hours = (end_dt - start_dt).total_seconds() / 3600
                
                # 計算良率和效率
                total_quantity = report.work_quantity + report.defect_quantity
                yield_rate = 0
                efficiency_rate = 0
                
                if total_quantity > 0:
                    yield_rate = (report.work_quantity / total_quantity) * 100
                
                if work_hours > 0:
                    efficiency_rate = report.work_quantity / work_hours
                
                # 檢查是否已存在相同記錄
                existing_record = WorkTimeReport.objects.filter(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.operator.name if report.operator else '未知作業員',
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    process_name=report.operation or (report.process.name if report.process else ''),
                    start_time=start_time,
                    end_time=end_time
                ).first()
                
                if existing_record:
                    # 如果記錄已存在，跳過同步（避免重複）
                    self.logger.info(f"跳過重複記錄: {existing_record}")
                    continue
                
                # 建立或更新工作時間報表記錄
                work_time_report, created = WorkTimeReport.objects.update_or_create(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.operator.name if report.operator else '未知作業員',
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    defaults={
                        'report_period_start': date_from,
                        'report_period_end': date_to,
                        'worker_type': 'operator',
                        'product_code': report.product_id or (report.workorder.product_code if report.workorder else ''),
                        'process_name': report.operation or (report.process.name if report.process else ''),
                        'start_time': start_time,
                        'end_time': end_time,
                        'total_work_hours': work_hours,
                        'actual_work_hours': work_hours,
                        'completed_quantity': report.work_quantity,
                        'defect_quantity': report.defect_quantity,
                        'yield_rate': yield_rate,
                        'efficiency_rate': efficiency_rate,
                        'original_quantity': report.work_quantity,
                        'allocated_quantity': report.allocated_quantity or 0,
                        'quantity_source': 'allocated' if report.allocated_quantity and report.allocated_quantity > 0 else 'original',
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
                work_hours = 0
                
                if start_time and end_time:
                    start_dt = datetime.combine(report.work_date, start_time)
                    end_dt = datetime.combine(report.work_date, end_time)
                    
                    if end_dt < start_dt:
                        end_dt += timedelta(days=1)
                    
                    work_hours = (end_dt - start_dt).total_seconds() / 3600
                
                # 計算良率和效率
                total_quantity = report.work_quantity + report.defect_quantity
                yield_rate = 0
                efficiency_rate = 0
                
                if total_quantity > 0:
                    yield_rate = (report.work_quantity / total_quantity) * 100
                
                if work_hours > 0:
                    efficiency_rate = report.work_quantity / work_hours
                
                # 檢查是否已存在相同記錄
                existing_record = WorkTimeReport.objects.filter(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.equipment.name if report.equipment else '未知設備',
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    process_name=report.operation or '',
                    start_time=start_time,
                    end_time=end_time
                ).first()
                
                if existing_record:
                    # 如果記錄已存在，跳過同步
                    self.logger.info(f"跳過重複記錄: {existing_record}")
                    continue
                
                # 建立或更新工作時間報表記錄
                work_time_report, created = WorkTimeReport.objects.update_or_create(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.equipment.name if report.equipment else '未知設備',
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    defaults={
                        'report_period_start': date_from,
                        'report_period_end': date_to,
                        'worker_type': 'smt',
                        'product_code': report.product_id or (report.workorder.product_code if report.workorder else ''),
                        'process_name': report.operation or '',
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
                work_hours = 0
                
                if start_time and end_time:
                    start_dt = datetime.combine(report.work_date, start_time)
                    end_dt = datetime.combine(report.work_date, end_time)
                    
                    if end_dt < start_dt:
                        end_dt += timedelta(days=1)
                    
                    work_hours = (end_dt - start_dt).total_seconds() / 3600
                
                # 計算良率和效率
                total_quantity = report.work_quantity + report.defect_quantity
                yield_rate = 0
                efficiency_rate = 0
                
                if total_quantity > 0:
                    yield_rate = (report.work_quantity / total_quantity) * 100
                
                if work_hours > 0:
                    efficiency_rate = report.work_quantity / work_hours
                
                # 檢查是否已存在相同記錄
                existing_record = WorkTimeReport.objects.filter(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.supervisor,
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    process_name=report.process.name if report.process else '',
                    start_time=start_time,
                    end_time=end_time
                ).first()
                
                if existing_record:
                    # 如果記錄已存在，跳過同步
                    self.logger.info(f"跳過重複記錄: {existing_record}")
                    continue
                
                # 建立或更新工作時間報表記錄
                work_time_report, created = WorkTimeReport.objects.update_or_create(
                    report_type='daily',
                    report_date=report.work_date,
                    worker_name=report.supervisor,
                    workorder_number=report.workorder.order_number if report.workorder else '',
                    defaults={
                        'report_period_start': date_from,
                        'report_period_end': date_to,
                        'worker_type': 'operator',
                        'product_code': report.workorder.product_code if report.workorder else '',
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
        以工單和工序為主，記錄工序明細，在工單完工後進行數量分擔
        
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
                
                # 取得工單詳細資訊
                try:
                    workorder = WorkOrder.objects.get(order_number=workorder_number)
                    planned_quantity = workorder.quantity
                    planned_start_date = workorder.planned_start_date or date_from
                    planned_end_date = workorder.planned_end_date or date_to
                    actual_start_date = workorder.actual_start_date or date_from
                    actual_end_date = workorder.actual_end_date or date_to
                    
                    # 計算完成率
                    completion_rate = 0
                    if planned_quantity > 0:
                        completion_rate = (stats['total_completed'] / planned_quantity) * 100
                    
                    # 取得作業員和設備清單
                    assigned_operators = self._get_workorder_operators(workorder_number, date_from, date_to)
                    assigned_equipment = self._get_workorder_equipment(workorder_number, date_from, date_to)
                    
                except WorkOrder.DoesNotExist:
                    # 如果工單不存在，使用預設值
                    planned_quantity = 0
                    planned_start_date = date_from
                    planned_end_date = date_to
                    actual_start_date = date_from
                    actual_end_date = date_to
                    completion_rate = 0
                    assigned_operators = ''
                    assigned_equipment = ''
                
                # 計算良率
                total_quantity = stats['total_completed'] + stats['total_defect']
                yield_rate = 0
                if total_quantity > 0:
                    yield_rate = (stats['total_completed'] / total_quantity) * 100
                
                # 檢查是否已存在相同記錄
                existing_record = WorkOrderProductReport.objects.filter(
                    report_type='daily',
                    report_date=date_from,
                    workorder_number=workorder_number
                ).first()
                
                if existing_record:
                    # 如果記錄已存在，跳過同步（避免重複）
                    self.logger.info(f"跳過重複工單記錄: {existing_record}")
                    continue
                
                # 建立或更新工單機種報表記錄
                work_order_report, created = WorkOrderProductReport.objects.update_or_create(
                    report_type='daily',
                    report_date=date_from,  # 使用開始日期作為報表日期
                    workorder_number=workorder_number,
                    defaults={
                        'report_period_start': date_from,
                        'report_period_end': date_to,
                        'product_code': stats['product_id'] or '',
                        'product_name': stats['product_name'] or '',
                        'planned_quantity': planned_quantity,
                        'planned_start_date': planned_start_date,
                        'planned_end_date': planned_end_date,
                        'completed_quantity': stats['total_completed'],
                        'completion_rate': completion_rate,
                        'actual_start_date': actual_start_date,
                        'actual_end_date': actual_end_date,
                        'assigned_operators': assigned_operators,
                        'total_work_hours': stats['total_work_hours'],
                        'assigned_equipment': assigned_equipment,
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
    
    def _get_workorder_operators(self, workorder_number, date_from, date_to):
        """取得工單的作業員清單"""
        operators = set()
        
        # 從作業員報工記錄取得
        operator_reports = OperatorSupplementReport.objects.filter(
            workorder__order_number=workorder_number,
            approval_status='approved',
            work_date__gte=date_from,
            work_date__lte=date_to
        ).select_related('operator')
        
        for report in operator_reports:
            if report.operator:
                operators.add(report.operator.name)
        
        # 從主管報工記錄取得
        supervisor_reports = SupervisorProductionReport.objects.filter(
            workorder__order_number=workorder_number,
            approval_status='approved',
            work_date__gte=date_from,
            work_date__lte=date_to
        ).select_related('operator')
        
        for report in supervisor_reports:
            if report.operator:
                operators.add(report.operator.name)
        
        return ', '.join(sorted(operators))
    
    def _get_workorder_equipment(self, workorder_number, date_from, date_to):
        """取得工單的設備清單"""
        equipment = set()
        
        # 從作業員報工記錄取得
        operator_reports = OperatorSupplementReport.objects.filter(
            workorder__order_number=workorder_number,
            approval_status='approved',
            work_date__gte=date_from,
            work_date__lte=date_to
        ).select_related('equipment')
        
        for report in operator_reports:
            if report.equipment:
                equipment.add(report.equipment.name)
        
        # 從SMT報工記錄取得
        smt_reports = SMTProductionReport.objects.filter(
            workorder__order_number=workorder_number,
            approval_status='approved',
            work_date__gte=date_from,
            work_date__lte=date_to
        ).select_related('equipment')
        
        for report in smt_reports:
            if report.equipment:
                equipment.add(report.equipment.name)
        
        # 從主管報工記錄取得
        supervisor_reports = SupervisorProductionReport.objects.filter(
            workorder__order_number=workorder_number,
            approval_status='approved',
            work_date__gte=date_from,
            work_date__lte=date_to
        ).select_related('equipment')
        
        for report in supervisor_reports:
            if report.equipment:
                equipment.add(report.equipment.name)
        
        return ', '.join(sorted(equipment))
    
    def sync_workorder_allocation(self, workorder_id):
        """
        工單完工後的數量分擔處理
        將工單的明細數量分擔，並將分擔後的資料回寫到作業員的資料表
        
        Args:
            workorder_id (int): 工單ID
            
        Returns:
            dict: 分擔結果
        """
        try:
            workorder = WorkOrder.objects.get(id=workorder_id)
            
            # 檢查工單是否已完工
            if workorder.status != 'completed':
                return {
                    'status': 'error',
                    'message': '工單尚未完工，無法進行數量分擔'
                }
            
            # 取得工單的所有工序明細
            processes = WorkOrderProcess.objects.filter(workorder=workorder)
            
            # 取得工單的所有報工記錄
            operator_reports = OperatorSupplementReport.objects.filter(
                workorder=workorder,
                approval_status='approved'
            )
            
            smt_reports = SMTProductionReport.objects.filter(
                workorder=workorder,
                approval_status='approved'
            )
            
            supervisor_reports = SupervisorProductionReport.objects.filter(
                workorder=workorder,
                approval_status='approved'
            )
            
            # 計算總完成數量
            total_completed = sum([p.completed_quantity for p in processes])
            
            if total_completed == 0:
                return {
                    'status': 'error',
                    'message': '工單完成數量為0，無法進行分擔'
                }
            
            # 按工序分組報工記錄
            process_reports = {}
            
            # 處理作業員報工記錄
            for report in operator_reports:
                process_name = report.operation
                if process_name not in process_reports:
                    process_reports[process_name] = []
                process_reports[process_name].append(report)
            
            # 處理SMT報工記錄
            for report in smt_reports:
                process_name = report.operation
                if process_name not in process_reports:
                    process_reports[process_name] = []
                process_reports[process_name].append(report)
            
            # 處理主管報工記錄
            for report in supervisor_reports:
                process_name = report.process.name if report.process else '未知工序'
                if process_name not in process_reports:
                    process_reports[process_name] = []
                process_reports[process_name].append(report)
            
            # 對每個工序進行數量分擔
            allocation_results = []
            
            for process_name, reports in process_reports.items():
                # 計算該工序的總工作時數
                total_work_hours = 0
                for report in reports:
                    if report.start_time and report.end_time:
                        start_dt = datetime.combine(report.work_date, report.start_time)
                        end_dt = datetime.combine(report.work_date, report.end_time)
                        if end_dt < start_dt:
                            end_dt += timedelta(days=1)
                        work_hours = (end_dt - start_dt).total_seconds() / 3600
                        total_work_hours += work_hours
                
                # 如果沒有工作時數，使用報工次數作為權重
                if total_work_hours == 0:
                    total_work_hours = len(reports)
                
                # 按比例分配數量
                for report in reports:
                    if total_work_hours > 0:
                        if report.start_time and report.end_time:
                            start_dt = datetime.combine(report.work_date, report.start_time)
                            end_dt = datetime.combine(report.work_date, report.end_time)
                            if end_dt < start_dt:
                                end_dt += timedelta(days=1)
                            work_hours = (end_dt - start_dt).total_seconds() / 3600
                        else:
                            work_hours = 1  # 預設1小時
                        
                        allocation_ratio = work_hours / total_work_hours
                        allocated_quantity = int(total_completed * allocation_ratio)
                        
                        # 更新報工記錄的分配數量
                        report.allocated_quantity = allocated_quantity
                        report.allocation_notes = f'工單完工後按工作時數比例分配 (佔比: {allocation_ratio:.2%})'
                        report.save()
                        
                        allocation_results.append({
                            'report_id': report.id,
                            'report_type': report.__class__.__name__,
                            'allocated_quantity': allocated_quantity,
                            'allocation_ratio': allocation_ratio
                        })
            
            return {
                'status': 'success',
                'message': f'工單 {workorder.order_number} 數量分擔完成',
                'total_completed': total_completed,
                'allocation_results': allocation_results
            }
            
        except WorkOrder.DoesNotExist:
            return {
                'status': 'error',
                'message': '找不到指定的工單'
            }
        except Exception as e:
            self.logger.error(f"工單數量分擔失敗: {str(e)}")
            return {
                'status': 'error',
                'message': f'數量分擔失敗: {str(e)}'
            }
    
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