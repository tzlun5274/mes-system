# -*- coding: utf-8 -*-
"""
統一資料收集模組
負責從 WorkOrderReportData 收集報表資料
所有報表都使用統一的資料來源，避免重複讀取
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from django.db.models import Sum, Count, Avg, Q

logger = logging.getLogger(__name__)


class DataCollector:
    """統一資料收集器"""
    
    def __init__(self):
        pass
    
    def collect_report_data(self, start_date: datetime, end_date: datetime, 
                          company_code: str = None) -> Dict:
        """
        收集報表資料 - 按照原本設計從 WorkOrderReportData 讀取
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            company_code: 公司代號
            
        Returns:
            包含報表資料的字典
        """
        try:
            from .models import WorkOrderReportData
            from erp_integration.models import CompanyConfig
            
            # 建立查詢條件
            query_filters = Q(work_date__range=[start_date, end_date])
            
            # 如果有公司代號且不是 'ALL'，加入公司過濾條件
            if company_code and company_code != 'ALL':
                query_filters &= Q(company=company_code)
            
            # 取得資料
            queryset = WorkOrderReportData.objects.filter(query_filters)
            
            # 基本統計
            total_records = queryset.count()
            total_work_hours = queryset.aggregate(
                total=Sum('work_hours')
            )['total'] or 0
            total_overtime_hours = queryset.aggregate(
                total=Sum('overtime_hours')
            )['total'] or 0
            total_hours = queryset.aggregate(
                total=Sum('work_hours')
            )['total'] or 0
            
            # 計算作業員數和設備數
            operator_count = queryset.values('operator_name').distinct().count()
            equipment_count = queryset.values('workorder_id').distinct().count()
            
            # 計算不良品數量
            total_defect_quantity = queryset.aggregate(
                total=Sum('defect_quantity')
            )['total'] or 0
            
            # 按公司統計
            company_stats = self._get_company_statistics_from_workorder_report(queryset)
            
            # 按工序統計
            process_stats = self._get_process_statistics_from_workorder_report(queryset)
            
            # 按作業員統計
            operator_stats = self._get_operator_statistics_from_workorder_report(queryset)
            
            # 詳細資料
            detailed_data = self._get_detailed_data_from_workorder_report(queryset)
            
            return {
                'success': True,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'summary': {
                    'total_records': total_records,
                    'onsite_records': 0,  # WorkOrderReportData 不區分來源
                    'normal_hours': float(total_work_hours),
                    'overtime_hours': float(total_overtime_hours),
                    'total_work_hours': float(total_hours),
                    'operator_count': operator_count,
                    'equipment_count': equipment_count,
                    'defect_quantity': float(total_defect_quantity)
                },
                'company_stats': company_stats,
                'process_stats': process_stats,
                'operator_stats': operator_stats,
                'detailed_data': detailed_data
            }
            
        except Exception as e:
            logger.error(f"收集報表資料失敗: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {}
            }
    
    def _get_workorder_statistics(self, queryset) -> List[Dict]:
        """按工單分組統計"""
        try:
            from django.db.models import Sum, Count
            
            workorder_stats = queryset.values(
                'workorder_id', 'product_code'
            ).annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                record_count=Count('id')
            ).order_by('-total_work_hours')
            
            return list(workorder_stats)
            
        except Exception as e:
            logger.error(f"取得工單統計失敗: {str(e)}")
            return []
    
    def _get_product_statistics(self, queryset) -> List[Dict]:
        """按產品分組統計"""
        try:
            from django.db.models import Sum, Count
            
            product_stats = queryset.values('product_code').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                record_count=Count('id')
            ).order_by('-total_work_hours')
            
            return list(product_stats)
            
        except Exception as e:
            logger.error(f"取得產品統計失敗: {str(e)}")
            return []
    
    def _get_process_statistics(self, queryset) -> List[Dict]:
        """按工序分組統計"""
        try:
            from django.db.models import Sum, Count
            
            process_stats = queryset.values('process_name').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                record_count=Count('id')
            ).order_by('-total_work_hours')
            
            return list(process_stats)
            
        except Exception as e:
            logger.error(f"取得工序統計失敗: {str(e)}")
            return []
    
    def _get_operator_statistics(self, queryset) -> List[Dict]:
        """按作業員分組統計"""
        try:
            from django.db.models import Sum, Count
            
            operator_stats = queryset.values('operator_name').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                record_count=Count('id')
            ).order_by('-total_work_hours')
            
            return list(operator_stats)
            
        except Exception as e:
            logger.error(f"取得作業員統計失敗: {str(e)}")
            return []
    
    def _get_source_statistics(self, queryset) -> List[Dict]:
        """按資料來源分組統計"""
        try:
            from django.db.models import Sum, Count
            
            # WorkOrderReportData 沒有 data_source 欄位，改為按公司分組
            source_stats = queryset.values('company').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                record_count=Count('id')
            ).order_by('-total_work_hours')
            
            return list(source_stats)
            
        except Exception as e:
            logger.error(f"取得資料來源統計失敗: {str(e)}")
            return []
    
    def _get_detailed_records(self, queryset, limit: int = 1000) -> List[Dict]:
        """取得詳細記錄"""
        try:
            records = queryset.order_by('-work_date', '-created_at')[:limit]
            
            detailed_records = []
            for record in records:
                detailed_records.append({
                    'id': record.id,
                    'work_date': record.work_date.strftime('%Y-%m-%d') if record.work_date else '',
                    'workorder_id': record.workorder_id,
                    'company': record.company,
                    'product_code': record.product_code,
                    'process_name': record.process_name,
                    'operator_name': record.operator_name,
                    'work_hours': record.work_hours,
                    'overtime_hours': record.overtime_hours,
                    'total_hours': record.total_hours,
                    'start_time': record.start_time,
                    'end_time': record.end_time,
                    # 新增產量相關欄位
                    'work_quantity': record.work_quantity,
                    'defect_quantity': record.defect_quantity,
                    'equipment_name': '',  # WorkOrderReportData 沒有 equipment_name 欄位
                    'created_at': record.created_at,
                    'updated_at': record.updated_at
                })
            
            return detailed_records
            
        except Exception as e:
            logger.error(f"取得詳細記錄失敗: {str(e)}")
            return []
    
    def _get_company_statistics(self, queryset) -> List[Dict]:
        """按公司分組統計"""
        try:
            from django.db.models import Sum, Count
            
            company_stats = queryset.values('company').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                record_count=Count('id'),
                operator_count=Count('operator_name', distinct=True),
                equipment_count=Count('workorder_id', distinct=True)  # 使用 workorder_id 代替 equipment_name
            ).order_by('-total_work_hours')
            
            result = []
            for stat in company_stats:
                result.append({
                    'company_name': stat['company'] or '未指定',
                    'record_count': stat['record_count'],
                    'normal_hours': float(stat['total_work_hours'] or 0),
                    'overtime_hours': float(stat['total_overtime_hours'] or 0),
                    'total_hours': float(stat['total_hours'] or 0),
                    'operator_count': stat['operator_count'],
                    'equipment_count': stat['equipment_count']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"取得公司統計失敗: {str(e)}")
            return []
    
    def _get_process_statistics_with_efficiency(self, queryset) -> List[Dict]:
        """按工序分組統計（包含效率計算）"""
        try:
            from django.db.models import Sum, Count
            
            process_stats = queryset.values('process_name').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                total_work_quantity=Sum('work_quantity'),
                record_count=Count('id')
            ).order_by('-total_work_hours')
            
            result = []
            for stat in process_stats:
                total_hours = float(stat['total_hours'] or 0)
                work_quantity = float(stat['total_work_quantity'] or 0)
                efficiency = 0
                if total_hours > 0:
                    # 效率 = 完成數量 / 工作時數
                    efficiency = work_quantity / total_hours
                
                result.append({
                    'process_name': stat['process_name'] or '未指定',
                    'record_count': stat['record_count'],
                    'normal_hours': float(stat['total_work_hours'] or 0),
                    'overtime_hours': float(stat['total_overtime_hours'] or 0),
                    'total_hours': total_hours,
                    'quantity_produced': work_quantity,
                    'efficiency': efficiency
                })
            
            return result
            
        except Exception as e:
            logger.error(f"取得工序統計失敗: {str(e)}")
            return []
    
    def _get_operator_statistics_with_efficiency(self, queryset) -> List[Dict]:
        """按作業員分組統計（包含效率計算）"""
        try:
            from django.db.models import Sum, Count
            
            operator_stats = queryset.values('operator_name').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                total_work_quantity=Sum('work_quantity'),
                record_count=Count('id')
            ).order_by('-total_work_hours')
            
            result = []
            for stat in operator_stats:
                total_hours = float(stat['total_hours'] or 0)
                work_quantity = float(stat['total_work_quantity'] or 0)
                efficiency = 0
                if total_hours > 0:
                    # 效率 = 完成數量 / 工作時數
                    efficiency = work_quantity / total_hours
                
                result.append({
                    'operator_name': stat['operator_name'] or '未指定',
                    'record_count': stat['record_count'],
                    'normal_hours': float(stat['total_work_hours'] or 0),
                    'overtime_hours': float(stat['total_overtime_hours'] or 0),
                    'total_hours': total_hours,
                    'quantity_produced': work_quantity,
                    'efficiency': efficiency
                })
            
            return result
            
        except Exception as e:
            logger.error(f"取得作業員統計失敗: {str(e)}")
            return []
    
    def _format_detailed_data(self, detailed_records: List[Dict]) -> List[Dict]:
        """格式化詳細資料"""
        try:
            formatted_data = []
            for record in detailed_records:
                formatted_data.append({
                    'company_name': record.get('company', ''),
                    'operator_name': record.get('operator_name', ''),
                    'workorder_id': record.get('workorder_id', ''),
                    'product_code': record.get('product_code', ''),
                    'process_name': record.get('process_name', ''),
                    'equipment_name': '',  # WorkOrderReportData 沒有 equipment_name 欄位
                    'start_time': record.get('start_time', ''),
                    'end_time': record.get('end_time', ''),
                    'work_hours': float(record.get('work_hours', 0)),
                    'overtime_hours': float(record.get('overtime_hours', 0)),
                    'quantity_produced': 0,  # 暫時設為0
                    'remarks': ''
                })
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"格式化詳細資料失敗: {str(e)}")
            return []
    
    def get_data_summary(self, start_date: datetime, end_date: datetime, 
                        company_code: str = None) -> Dict:
        """
        取得資料摘要
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            company_code: 公司代號
            
        Returns:
            資料摘要字典
        """
        try:
            from .models import WorkOrderReportData
            
            # 建立查詢條件
            query_filters = Q(work_date__range=[start_date, end_date])
            
            if company_code:
                query_filters &= Q(company_code=company_code)
            
            queryset = WorkOrderReportData.objects.filter(query_filters)
            
            # 基本統計
            total_records = queryset.count()
            total_work_hours = queryset.aggregate(
                total=Sum('work_hours')
            )['total'] or 0
            total_overtime_hours = queryset.aggregate(
                total=Sum('overtime_hours')
            )['total'] or 0
            
            return {
                'success': True,
                'total_records': total_records,
                'total_work_hours': total_work_hours,
                'total_overtime_hours': total_overtime_hours
            }
            
        except Exception as e:
            logger.error(f"取得資料摘要失敗: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_company_statistics_from_workorder_report(self, queryset) -> List[Dict]:
        """從 WorkOrderReportData 按公司統計"""
        try:
            from django.db.models import Sum, Count
            
            company_stats = queryset.values('company').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('total_hours'),
                total_defect_quantity=Sum('defect_quantity'),
                record_count=Count('id'),
                operator_count=Count('operator_name', distinct=True),
                equipment_count=Count('workorder_id', distinct=True)
            ).order_by('-total_work_hours')
            
            result = []
            for stat in company_stats:
                result.append({
                    'company_name': stat['company'] or '未指定',
                    'record_count': stat['record_count'],
                    'normal_hours': float(stat['total_work_hours'] or 0),
                    'overtime_hours': float(stat['total_overtime_hours'] or 0),
                    'total_hours': float(stat['total_hours'] or 0),
                    'operator_count': stat['operator_count'],
                    'equipment_count': stat['equipment_count']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"取得公司統計失敗: {str(e)}")
            return []
    
    def _get_process_statistics_from_workorder_report(self, queryset) -> List[Dict]:
        """從 WorkOrderReportData 按工序統計"""
        try:
            from django.db.models import Sum, Count
            
            process_stats = queryset.values('process_name').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('work_hours'),
                total_work_quantity=Sum('work_quantity'),
                total_defect_quantity=Sum('defect_quantity'),
                record_count=Count('id'),
                operator_count=Count('operator_name', distinct=True)
            ).order_by('-total_work_hours')
            
            result = []
            for stat in process_stats:
                total_hours = float(stat['total_hours'] or 0)
                total_work = float(stat['total_work_quantity'] or 0)
                total_defect = float(stat['total_defect_quantity'] or 0)
                efficiency = 0
                if total_hours > 0:
                    # 計算效率：(工作數量 + 不良品數量) / 工作時數
                    efficiency = (total_work + total_defect) / total_hours
                
                result.append({
                    'process_name': stat['process_name'] or '未指定',
                    'record_count': stat['record_count'],
                    'normal_hours': float(stat['total_work_hours'] or 0),
                    'overtime_hours': float(stat['total_overtime_hours'] or 0),
                    'total_hours': total_hours,
                    'work_quantity': total_work,
                    'defect_quantity': float(stat['total_defect_quantity'] or 0),
                    'efficiency': efficiency,
                    'operator_count': stat['operator_count']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"取得工序統計失敗: {str(e)}")
            return []
    
    def _get_operator_statistics_from_workorder_report(self, queryset) -> List[Dict]:
        """從 WorkOrderReportData 按作業員統計"""
        try:
            from django.db.models import Sum, Count
            
            operator_stats = queryset.values('operator_name').annotate(
                total_work_hours=Sum('work_hours'),
                total_overtime_hours=Sum('overtime_hours'),
                total_hours=Sum('work_hours'),
                total_work_quantity=Sum('work_quantity'),
                total_defect_quantity=Sum('defect_quantity'),
                record_count=Count('id'),
                equipment_count=Count('workorder_id', distinct=True)  # 使用 workorder_id 代替 equipment_name
            ).order_by('-total_work_hours')
            
            result = []
            for stat in operator_stats:
                total_hours = float(stat['total_hours'] or 0)
                total_work = float(stat['total_work_quantity'] or 0)
                total_defect = float(stat['total_defect_quantity'] or 0)
                efficiency = 0
                if total_hours > 0:
                    # 計算效率：(工作數量 + 不良品數量) / 工作時數
                    efficiency = (total_work + total_defect) / total_hours
                
                result.append({
                    'operator_name': stat['operator_name'] or '未指定',
                    'record_count': stat['record_count'],
                    'normal_hours': float(stat['total_work_hours'] or 0),
                    'overtime_hours': float(stat['total_overtime_hours'] or 0),
                    'total_hours': total_hours,
                    'work_quantity': total_work,
                    'defect_quantity': float(stat['total_defect_quantity'] or 0),
                    'efficiency': efficiency,
                    'equipment_count': stat['equipment_count']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"取得作業員統計失敗: {str(e)}")
            return []
    
    def _get_detailed_data_from_workorder_report(self, queryset) -> List[Dict]:
        """從 WorkOrderReportData 取得詳細資料"""
        try:
            detailed_data = []
            for record in queryset:
                detailed_data.append({
                    'company_name': record.company or '',
                    'operator_name': record.operator_name or '',
                    'workorder_id': record.workorder_id or '',
                    'product_code': record.product_code or '',
                    'process_name': record.process_name or '',
                    'work_date': record.work_date.strftime('%Y-%m-%d') if record.work_date else '',
                    'equipment_name': '',  # WorkOrderReportData 沒有 equipment_name 欄位
                    'start_time': record.start_time.strftime('%H:%M') if record.start_time else '',
                    'end_time': record.end_time.strftime('%H:%M') if record.end_time else '',
                    'work_hours': float(record.work_hours or 0),
                    'overtime_hours': float(record.overtime_hours or 0),
                    'work_quantity': float(record.work_quantity or 0),
                    'remarks': ''
                })
            
            return detailed_data
            
        except Exception as e:
            logger.error(f"取得詳細資料失敗: {str(e)}")
            return []
    
