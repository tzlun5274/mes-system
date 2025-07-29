"""
工作報表服務 - 支援混合模式：直接計算和快取儲存
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.core.cache import cache

from workorder.models import (
    SMTProductionReport, 
    OperatorSupplementReport, 
    SupervisorProductionReport,
    WorkOrder
)
from reporting.models import (
    WorkTimeReportCache,
    WorkerPerformanceCache,
    WorkOrderSummaryCache,
)
from system.models import ReportDataSyncLog
from .base_service import BaseReportService


class WorkTimeReportService(BaseReportService):
    """工作報表服務 - 混合模式"""
    
    def __init__(self):
        super().__init__()
        self.cache_prefix = "work_time_report"
        self.cache_timeout = 3600  # 1小時快取
        self.use_cache = True  # 是否使用快取模式
    
    def get_work_time_data(self, start_date: date, end_date: date, report_type: str = "daily", use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        取得工作資料 - 支援混合模式
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            report_type: 報表類型 (daily/weekly/monthly)
            use_cache: 是否使用快取模式
            
        Returns:
            List[Dict[str, Any]]: 工作資料列表
        """
        # 如果啟用快取，先嘗試從快取取得
        if use_cache and self.use_cache:
            cached_data = self._get_cached_data(start_date, end_date, report_type)
            if cached_data:
                self.logger.info(f"使用快取數據: {report_type} {start_date} ~ {end_date}")
                return cached_data
        
        # 從報工記錄直接計算
        self.logger.info(f"直接計算數據: {report_type} {start_date} ~ {end_date}")
        data = self._calculate_from_source(start_date, end_date, report_type)
        
        # 如果啟用快取，儲存到快取
        if use_cache and self.use_cache:
            self._save_to_cache(data, start_date, end_date, report_type)
        
        return data
    
    def _get_cached_data(self, start_date: date, end_date: date, report_type: str) -> Optional[List[Dict[str, Any]]]:
        """從快取取得數據"""
        try:
            cache_key = WorkTimeReportCache.generate_cache_key(report_type, start_date, end_date)
            
            # 先檢查記憶體快取
            memory_cache_key = f"{self.cache_prefix}:{cache_key}"
            cached_data = cache.get(memory_cache_key)
            if cached_data:
                return cached_data
            
            # 檢查資料庫快取
            cache_record = WorkTimeReportCache.objects.filter(
                cache_key=cache_key,
                last_updated__gte=timezone.now() - timedelta(hours=24)  # 24小時內的有效快取
            ).first()
            
            if cache_record:
                # 儲存到記憶體快取
                cache.set(memory_cache_key, cache_record.detail_data, self.cache_timeout)
                return cache_record.detail_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"取得快取數據失敗: {str(e)}")
            return None
    
    def _save_to_cache(self, data: List[Dict[str, Any]], start_date: date, end_date: date, report_type: str):
        """儲存數據到快取"""
        try:
            cache_key = WorkTimeReportCache.generate_cache_key(report_type, start_date, end_date)
            
            # 儲存到記憶體快取
            memory_cache_key = f"{self.cache_prefix}:{cache_key}"
            cache.set(memory_cache_key, data, self.cache_timeout)
            
            # 儲存到資料庫快取
            cache_record, created = WorkTimeReportCache.objects.update_or_create(
                cache_key=cache_key,
                defaults={
                    'report_type': report_type,
                    'report_date': start_date,
                    'period_start': start_date,
                    'period_end': end_date,
                    'detail_data': self._serialize_data(data),
                    'data_source': 'workorder',
                    # 計算統計數據
                    'total_work_hours': sum(item.get('total_work_hours', 0) for item in data),
                    'total_completed_quantity': sum(item.get('total_completed_quantity', 0) for item in data),
                    'total_defect_quantity': sum(item.get('total_defect_quantity', 0) for item in data),
                    'worker_count': sum(item.get('worker_count', 0) for item in data),
                    'workorder_count': sum(item.get('workorder_count', 0) for item in data),
                    'avg_efficiency_rate': sum(item.get('avg_efficiency_rate', 0) for item in data) / len(data) if data else 0,
                    'avg_yield_rate': sum(item.get('avg_yield_rate', 0) for item in data) / len(data) if data else 0,
                }
            )
            
            self.logger.info(f"快取數據已儲存: {cache_key}")
            
        except Exception as e:
            self.logger.error(f"儲存快取數據失敗: {str(e)}")
    
    def _calculate_from_source(self, start_date: date, end_date: date, report_type: str) -> List[Dict[str, Any]]:
        """從報工記錄直接計算數據"""
        # 合併所有報工記錄
        smt_reports = self._get_smt_reports(start_date, end_date)
        operator_reports = self._get_operator_reports(start_date, end_date)
        supervisor_reports = self._get_supervisor_reports(start_date, end_date)
        
        # 統一資料格式
        all_reports = []
        all_reports.extend(smt_reports)
        all_reports.extend(operator_reports)
        all_reports.extend(supervisor_reports)
        
        # 按日期分組統計
        return self._group_by_date(all_reports, report_type)
    
    def sync_report_data(self, start_date: date, end_date: date, sync_type: str = "work_time") -> Dict[str, Any]:
        """
        同步報表數據到快取
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            sync_type: 同步類型
            
        Returns:
            Dict[str, Any]: 同步結果
        """
        sync_log = ReportDataSyncLog.objects.create(
            sync_type=sync_type,
            period_start=start_date,
            period_end=end_date,
            started_at=timezone.now(),
            status='success'
        )
        
        try:
            records_processed = 0
            records_created = 0
            records_updated = 0
            
            # 同步工作報表數據
            if sync_type == "work_time":
                for report_type in ['daily', 'weekly', 'monthly']:
                    data = self._calculate_from_source(start_date, end_date, report_type)
                    records_processed += len(data)
                    
                    for item in data:
                        cache_key = WorkTimeReportCache.generate_cache_key(report_type, start_date, end_date)
                        cache_record, created = WorkTimeReportCache.objects.update_or_create(
                            cache_key=cache_key,
                            defaults={
                                'report_type': report_type,
                                'report_date': item.get('date', start_date),
                                'period_start': start_date,
                                'period_end': end_date,
                                'detail_data': self._serialize_data(item),
                                'data_source': 'workorder',
                                'total_work_hours': item.get('total_work_hours', 0),
                                'total_completed_quantity': item.get('total_completed_quantity', 0),
                                'total_defect_quantity': item.get('total_defect_quantity', 0),
                                'worker_count': item.get('worker_count', 0),
                                'workorder_count': item.get('workorder_count', 0),
                                'avg_efficiency_rate': item.get('avg_efficiency_rate', 0),
                                'avg_yield_rate': item.get('avg_yield_rate', 0),
                            }
                        )
                        
                        if created:
                            records_created += 1
                        else:
                            records_updated += 1
            
            # 同步作業員績效數據
            elif sync_type == "worker_performance":
                worker_data = self.get_worker_performance(start_date, end_date)
                records_processed = len(worker_data)
                
                for item in worker_data:
                    cache_key = f"worker_{item['worker_name']}_{start_date}_{end_date}"
                    cache_record, created = WorkerPerformanceCache.objects.update_or_create(
                        cache_key=cache_key,
                        defaults={
                            'worker_name': item['worker_name'],
                            'worker_type': item['worker_type'],
                            'period_start': start_date,
                            'period_end': end_date,
                            'total_work_hours': item['total_work_hours'],
                            'total_completed_quantity': item['total_completed_quantity'],
                            'total_defect_quantity': item['total_defect_quantity'],
                            'workorder_count': item['workorder_count'],
                            'report_count': item['report_count'],
                            'efficiency_rate': item['efficiency_rate'],
                            'yield_rate': item['yield_rate'],
                            'avg_hourly_output': item['avg_hourly_output'],
                        }
                    )
                    
                    if created:
                        records_created += 1
                    else:
                        records_updated += 1
            
            # 同步工單摘要數據
            elif sync_type == "workorder_summary":
                workorder_data = self.get_workorder_summary(start_date, end_date)
                records_processed = len(workorder_data)
                
                for item in workorder_data:
                    cache_key = f"workorder_{item['workorder_number']}_{start_date}_{end_date}"
                    cache_record, created = WorkOrderSummaryCache.objects.update_or_create(
                        cache_key=cache_key,
                        defaults={
                            'workorder_number': item['workorder_number'],
                            'product_code': item['product_code'],
                            'period_start': start_date,
                            'period_end': end_date,
                            'total_work_hours': item['total_work_hours'],
                            'total_completed_quantity': item['total_completed_quantity'],
                            'total_defect_quantity': item['total_defect_quantity'],
                            'worker_count': item['worker_count'],
                            'process_count': item['process_count'],
                            'report_count': item['report_count'],
                            'efficiency_rate': item['efficiency_rate'],
                            'yield_rate': item['yield_rate'],
                            'avg_hourly_output': item['avg_hourly_output'],
                        }
                    )
                    
                    if created:
                        records_created += 1
                    else:
                        records_updated += 1
            
            # 更新同步日誌
            duration = (timezone.now() - sync_log.started_at).total_seconds()
            sync_log.completed_at = timezone.now()
            sync_log.duration_seconds = int(duration)
            sync_log.records_processed = records_processed
            sync_log.records_created = records_created
            sync_log.records_updated = records_updated
            sync_log.save()
            
            return {
                'success': True,
                'sync_type': sync_type,
                'period': f"{start_date} ~ {end_date}",
                'records_processed': records_processed,
                'records_created': records_created,
                'records_updated': records_updated,
                'duration_seconds': duration
            }
            
        except Exception as e:
            # 更新同步日誌為失敗狀態
            duration = (timezone.now() - sync_log.started_at).total_seconds()
            sync_log.completed_at = timezone.now()
            sync_log.duration_seconds = int(duration)
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            sync_log.save()
            
            self.logger.error(f"同步報表數據失敗: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'sync_type': sync_type,
                'period': f"{start_date} ~ {end_date}"
            }
    
    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """序列化數據，處理日期等不可JSON序列化的對象"""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, date):
                serialized[key] = value.isoformat()
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, (int, float, str, bool, list, dict)) or value is None:
                serialized[key] = value
            else:
                serialized[key] = str(value)
        return serialized
    
    def clear_cache(self, cache_type: str = "all", before_date: Optional[date] = None):
        """
        清理快取數據
        
        Args:
            cache_type: 快取類型 (all/work_time/worker_performance/workorder_summary)
            before_date: 清理指定日期之前的快取
        """
        try:
            if cache_type == "all" or cache_type == "work_time":
                queryset = WorkTimeReportCache.objects.all()
                if before_date:
                    queryset = queryset.filter(created_at__lt=before_date)
                count = queryset.count()
                queryset.delete()
                self.logger.info(f"清理工作報表快取: {count} 筆記錄")
            
            if cache_type == "all" or cache_type == "worker_performance":
                queryset = WorkerPerformanceCache.objects.all()
                if before_date:
                    queryset = queryset.filter(created_at__lt=before_date)
                count = queryset.count()
                queryset.delete()
                self.logger.info(f"清理作業員績效快取: {count} 筆記錄")
            
            if cache_type == "all" or cache_type == "workorder_summary":
                queryset = WorkOrderSummaryCache.objects.all()
                if before_date:
                    queryset = queryset.filter(created_at__lt=before_date)
                count = queryset.count()
                queryset.delete()
                self.logger.info(f"清理工單摘要快取: {count} 筆記錄")
            
            # 清理記憶體快取
            cache.clear()
            self.logger.info("記憶體快取已清理")
            
            return {
                'success': True,
                'message': f"快取清理完成: {cache_type}"
            }
            
        except Exception as e:
            self.logger.error(f"清理快取失敗: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_smt_reports(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """取得SMT報工記錄"""
        reports = SMTProductionReport.objects.filter(
            work_date__gte=start_date,
            work_date__lte=end_date,
            approval_status='approved'  # 只統計已核准的記錄
        ).select_related('workorder', 'equipment')
        
        data = []
        for report in reports:
            # 使用新的工作時數計算器
            work_time_data = work_time_calc.calculate_work_time_for_report(report)
            work_hours = work_time_data['actual_work_hours']  # 使用實際工作時數
            
            data.append({
                'date': report.work_date,
                'worker_name': report.equipment.name if report.equipment else '未分配設備',
                'worker_type': 'smt',
                'workorder_number': report.workorder_number,
                'product_code': report.product_id,
                'process_name': report.operation,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'work_hours': work_hours,
                'completed_quantity': report.work_quantity,
                'defect_quantity': report.defect_quantity,
                'efficiency_rate': self._calculate_efficiency(work_hours, report.work_quantity),
                'yield_rate': self._calculate_yield_rate(report.work_quantity, report.defect_quantity),
                'report_type': 'smt',
                'report_id': report.id
            })
        
        return data
    
    def _get_operator_reports(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """取得作業員報工記錄"""
        reports = OperatorSupplementReport.objects.filter(
            work_date__gte=start_date,
            work_date__lte=end_date,
            approval_status='approved'  # 只統計已核准的記錄
        ).select_related('operator', 'workorder', 'process', 'equipment')
        
        data = []
        for report in reports:
            # 使用新的工作時數計算器
            from .work_time_calculator import WorkTimeCalculator
            work_time_calc = WorkTimeCalculator()
            work_time_data = work_time_calc.calculate_work_time_for_report(report)
            work_hours = work_time_data['actual_work_hours']  # 使用實際工作時數
            
            # 使用分配數量或原始數量
            final_quantity = report.allocated_quantity if report.allocated_quantity > 0 else report.work_quantity
            
            data.append({
                'date': report.work_date,
                'worker_name': report.operator.name if report.operator else '未分配作業員',
                'worker_type': 'operator',
                'workorder_number': report.workorder_number,
                'product_code': report.product_id,
                'process_name': report.process_name,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'work_hours': work_hours,
                'completed_quantity': final_quantity,
                'defect_quantity': report.defect_quantity,
                'efficiency_rate': self._calculate_efficiency(work_hours, final_quantity),
                'yield_rate': self._calculate_yield_rate(final_quantity, report.defect_quantity),
                'report_type': 'operator',
                'report_id': report.id,
                'quantity_source': report.quantity_source,
                'allocation_notes': report.allocation_notes
            })
        
        return data
    
    def _get_supervisor_reports(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """取得主管報工記錄"""
        reports = SupervisorProductionReport.objects.filter(
            work_date__gte=start_date,
            work_date__lte=end_date,
            approval_status='approved'  # 只統計已核准的記錄
        ).select_related('workorder', 'process', 'equipment', 'operator')
        
        data = []
        for report in reports:
            # 使用新的工作時數計算器
            work_time_data = work_time_calc.calculate_work_time_for_report(report)
            work_hours = work_time_data['actual_work_hours']  # 使用實際工作時數
            
            data.append({
                'date': report.work_date,
                'worker_name': report.supervisor,
                'worker_type': 'supervisor',
                'workorder_number': report.workorder_number,
                'product_code': report.workorder.product_code if report.workorder else '',
                'process_name': report.process_name,
                'start_time': report.start_time,
                'end_time': report.end_time,
                'work_hours': work_hours,
                'completed_quantity': report.work_quantity,
                'defect_quantity': report.defect_quantity,
                'efficiency_rate': self._calculate_efficiency(work_hours, report.work_quantity),
                'yield_rate': self._calculate_yield_rate(report.work_quantity, report.defect_quantity),
                'report_type': 'supervisor',
                'report_id': report.id
            })
        
        return data
    
    def _group_by_date(self, reports: List[Dict[str, Any]], report_type: str) -> List[Dict[str, Any]]:
        """按日期分組統計"""
        if report_type == "daily":
            return self._group_by_daily(reports)
        elif report_type == "weekly":
            return self._group_by_weekly(reports)
        elif report_type == "monthly":
            return self._group_by_monthly(reports)
        else:
            return reports
    
    def _group_by_daily(self, reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按日分組"""
        daily_stats = {}
        
        for report in reports:
            date_key = report['date']
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    'date': date_key,
                    'total_work_hours': 0,
                    'total_completed_quantity': 0,
                    'total_defect_quantity': 0,
                    'worker_count': set(),
                    'workorder_count': set(),
                    'reports': []
                }
            
            daily_stats[date_key]['total_work_hours'] += report['work_hours']
            daily_stats[date_key]['total_completed_quantity'] += report['completed_quantity']
            daily_stats[date_key]['total_defect_quantity'] += report['defect_quantity']
            daily_stats[date_key]['worker_count'].add(report['worker_name'])
            daily_stats[date_key]['workorder_count'].add(report['workorder_number'])
            daily_stats[date_key]['reports'].append(report)
        
        # 轉換為列表並計算統計值
        result = []
        for date_key, stats in sorted(daily_stats.items()):
            avg_efficiency = sum(r['efficiency_rate'] for r in stats['reports']) / len(stats['reports']) if stats['reports'] else 0
            avg_yield = sum(r['yield_rate'] for r in stats['reports']) / len(stats['reports']) if stats['reports'] else 0
            
            result.append({
                'date': stats['date'].isoformat() if isinstance(stats['date'], date) else stats['date'],
                'total_work_hours': round(stats['total_work_hours'], 2),
                'total_completed_quantity': stats['total_completed_quantity'],
                'total_defect_quantity': stats['total_defect_quantity'],
                'worker_count': len(stats['worker_count']),
                'workorder_count': len(stats['workorder_count']),
                'avg_efficiency_rate': round(avg_efficiency, 2),
                'avg_yield_rate': round(avg_yield, 2),
                'reports': [self._serialize_data(r) for r in stats['reports']]
            })
        
        return result
    
    def _group_by_weekly(self, reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按週分組"""
        weekly_stats = {}
        
        for report in reports:
            # 計算週開始日期
            week_start = report['date'] - timedelta(days=report['date'].weekday())
            week_key = week_start
            
            if week_key not in weekly_stats:
                weekly_stats[week_key] = {
                    'week_start': week_start,
                    'week_end': week_start + timedelta(days=6),
                    'total_work_hours': 0,
                    'total_completed_quantity': 0,
                    'total_defect_quantity': 0,
                    'worker_count': set(),
                    'workorder_count': set(),
                    'reports': []
                }
            
            weekly_stats[week_key]['total_work_hours'] += report['work_hours']
            weekly_stats[week_key]['total_completed_quantity'] += report['completed_quantity']
            weekly_stats[week_key]['total_defect_quantity'] += report['defect_quantity']
            weekly_stats[week_key]['worker_count'].add(report['worker_name'])
            weekly_stats[week_key]['workorder_count'].add(report['workorder_number'])
            weekly_stats[week_key]['reports'].append(report)
        
        # 轉換為列表
        result = []
        for week_key, stats in sorted(weekly_stats.items()):
            avg_efficiency = sum(r['efficiency_rate'] for r in stats['reports']) / len(stats['reports']) if stats['reports'] else 0
            avg_yield = sum(r['yield_rate'] for r in stats['reports']) / len(stats['reports']) if stats['reports'] else 0
            
            result.append({
                'period': f"{stats['week_start']} ~ {stats['week_end']}",
                'total_work_hours': round(stats['total_work_hours'], 2),
                'total_completed_quantity': stats['total_completed_quantity'],
                'total_defect_quantity': stats['total_defect_quantity'],
                'worker_count': len(stats['worker_count']),
                'workorder_count': len(stats['workorder_count']),
                'avg_efficiency_rate': round(avg_efficiency, 2),
                'avg_yield_rate': round(avg_yield, 2),
                'reports': [self._serialize_data(r) for r in stats['reports']]
            })
        
        return result
    
    def _group_by_monthly(self, reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按月分組"""
        monthly_stats = {}
        
        for report in reports:
            # 計算月份開始日期
            month_start = report['date'].replace(day=1)
            month_key = month_start
            
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'month_start': month_start,
                    'total_work_hours': 0,
                    'total_completed_quantity': 0,
                    'total_defect_quantity': 0,
                    'worker_count': set(),
                    'workorder_count': set(),
                    'reports': []
                }
            
            monthly_stats[month_key]['total_work_hours'] += report['work_hours']
            monthly_stats[month_key]['total_completed_quantity'] += report['completed_quantity']
            monthly_stats[month_key]['total_defect_quantity'] += report['defect_quantity']
            monthly_stats[month_key]['worker_count'].add(report['worker_name'])
            monthly_stats[month_key]['workorder_count'].add(report['workorder_number'])
            monthly_stats[month_key]['reports'].append(report)
        
        # 轉換為列表
        result = []
        for month_key, stats in sorted(monthly_stats.items()):
            avg_efficiency = sum(r['efficiency_rate'] for r in stats['reports']) / len(stats['reports']) if stats['reports'] else 0
            avg_yield = sum(r['yield_rate'] for r in stats['reports']) / len(stats['reports']) if stats['reports'] else 0
            
            result.append({
                'period': stats['month_start'].strftime('%Y年%m月'),
                'total_work_hours': round(stats['total_work_hours'], 2),
                'total_completed_quantity': stats['total_completed_quantity'],
                'total_defect_quantity': stats['total_defect_quantity'],
                'worker_count': len(stats['worker_count']),
                'workorder_count': len(stats['workorder_count']),
                'avg_efficiency_rate': round(avg_efficiency, 2),
                'avg_yield_rate': round(avg_yield, 2),
                'reports': [self._serialize_data(r) for r in stats['reports']]
            })
        
        return result
    
    def _calculate_efficiency(self, work_hours: float, quantity: int) -> float:
        """計算效率 (件/小時)"""
        if work_hours > 0:
            return round(quantity / work_hours, 2)
        return 0.0
    
    def _calculate_yield_rate(self, completed_quantity: int, defect_quantity: int) -> float:
        """計算良率 (%)"""
        total_quantity = completed_quantity + defect_quantity
        if total_quantity > 0:
            return round((completed_quantity / total_quantity) * 100, 2)
        return 0.0
    
    def get_worker_performance(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """取得作業員績效統計"""
        # 取得所有報工記錄
        smt_reports = self._get_smt_reports(start_date, end_date)
        operator_reports = self._get_operator_reports(start_date, end_date)
        supervisor_reports = self._get_supervisor_reports(start_date, end_date)
        
        all_reports = smt_reports + operator_reports + supervisor_reports
        
        # 按作業員分組統計
        worker_stats = {}
        for report in all_reports:
            worker_name = report['worker_name']
            if worker_name not in worker_stats:
                worker_stats[worker_name] = {
                    'worker_name': worker_name,
                    'worker_type': report['worker_type'],
                    'total_work_hours': 0,
                    'total_completed_quantity': 0,
                    'total_defect_quantity': 0,
                    'workorder_count': set(),
                    'report_count': 0
                }
            
            worker_stats[worker_name]['total_work_hours'] += report['work_hours']
            worker_stats[worker_name]['total_completed_quantity'] += report['completed_quantity']
            worker_stats[worker_name]['total_defect_quantity'] += report['defect_quantity']
            worker_stats[worker_name]['workorder_count'].add(report['workorder_number'])
            worker_stats[worker_name]['report_count'] += 1
        
        # 轉換為列表並計算績效指標
        result = []
        for worker_name, stats in worker_stats.items():
            efficiency_rate = self._calculate_efficiency(stats['total_work_hours'], stats['total_completed_quantity'])
            yield_rate = self._calculate_yield_rate(stats['total_completed_quantity'], stats['total_defect_quantity'])
            
            result.append({
                'worker_name': stats['worker_name'],
                'worker_type': stats['worker_type'],
                'total_work_hours': round(stats['total_work_hours'], 2),
                'total_completed_quantity': stats['total_completed_quantity'],
                'total_defect_quantity': stats['total_defect_quantity'],
                'workorder_count': len(stats['workorder_count']),
                'report_count': stats['report_count'],
                'efficiency_rate': efficiency_rate,
                'yield_rate': yield_rate,
                'avg_hourly_output': round(stats['total_completed_quantity'] / stats['total_work_hours'], 2) if stats['total_work_hours'] > 0 else 0
            })
        
        # 按效率排序
        result.sort(key=lambda x: x['efficiency_rate'], reverse=True)
        return result
    
    def get_workorder_summary(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """取得工單摘要統計"""
        # 取得所有報工記錄
        smt_reports = self._get_smt_reports(start_date, end_date)
        operator_reports = self._get_operator_reports(start_date, end_date)
        supervisor_reports = self._get_supervisor_reports(start_date, end_date)
        
        all_reports = smt_reports + operator_reports + supervisor_reports
        
        # 按工單分組統計
        workorder_stats = {}
        for report in all_reports:
            workorder_number = report['workorder_number']
            if workorder_number not in workorder_stats:
                workorder_stats[workorder_number] = {
                    'workorder_number': workorder_number,
                    'product_code': report['product_code'],
                    'total_work_hours': 0,
                    'total_completed_quantity': 0,
                    'total_defect_quantity': 0,
                    'worker_count': set(),
                    'process_count': set(),
                    'report_count': 0
                }
            
            workorder_stats[workorder_number]['total_work_hours'] += report['work_hours']
            workorder_stats[workorder_number]['total_completed_quantity'] += report['completed_quantity']
            workorder_stats[workorder_number]['total_defect_quantity'] += report['defect_quantity']
            workorder_stats[workorder_number]['worker_count'].add(report['worker_name'])
            workorder_stats[workorder_number]['process_count'].add(report['process_name'])
            workorder_stats[workorder_number]['report_count'] += 1
        
        # 轉換為列表並計算統計指標
        result = []
        for workorder_number, stats in workorder_stats.items():
            efficiency_rate = self._calculate_efficiency(stats['total_work_hours'], stats['total_completed_quantity'])
            yield_rate = self._calculate_yield_rate(stats['total_completed_quantity'], stats['total_defect_quantity'])
            
            result.append({
                'workorder_number': stats['workorder_number'],
                'product_code': stats['product_code'],
                'total_work_hours': round(stats['total_work_hours'], 2),
                'total_completed_quantity': stats['total_completed_quantity'],
                'total_defect_quantity': stats['total_defect_quantity'],
                'worker_count': len(stats['worker_count']),
                'process_count': len(stats['process_count']),
                'report_count': stats['report_count'],
                'efficiency_rate': efficiency_rate,
                'yield_rate': yield_rate,
                'avg_hourly_output': round(stats['total_completed_quantity'] / stats['total_work_hours'], 2) if stats['total_work_hours'] > 0 else 0
            })
        
        # 按完成數量排序
        result.sort(key=lambda x: x['total_completed_quantity'], reverse=True)
        return result 