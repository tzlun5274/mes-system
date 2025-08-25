"""
報表服務模組
提供各種報表功能的業務邏輯
"""

from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
from decimal import Decimal
import logging

from .models import WorkOrderReportData, ReportSchedule, ReportExecutionLog

logger = logging.getLogger(__name__)


class WorkHourReportService:
    """工作時數報表服務"""
    
    def __init__(self, company_code=None):
        self.company_code = company_code
    
    def get_daily_report(self, company_code, date):
        """日報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_date=date
        )
    
    def get_daily_report_by_company_operator(self, company, operator, date):
        """按公司和作業員查詢日報表"""
        queryset = WorkOrderReportData.objects.filter(work_date=date)
        
        if company != 'all':
            queryset = queryset.filter(company=company)
        
        if operator != 'all':
            queryset = queryset.filter(operator_name=operator)
        
        return queryset
    
    def get_daily_summary_by_company_operator(self, company, operator, date):
        """按公司和作業員查詢日報表摘要"""
        data = self.get_daily_report_by_company_operator(company, operator, date)
        
        # 計算總工作時數
        total_work_hours = data.aggregate(total=Sum('daily_work_hours'))['total'] or Decimal('0')
        
        # 計算作業員數量（去重）
        if operator == 'all':
            total_operators = data.exclude(operator_name__isnull=True).values('operator_name').distinct().count()
        else:
            total_operators = 1  # 特定作業員
        
        # 計算總設備使用時數
        total_equipment_hours = data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0')
        
        # 計算工單數量
        workorder_count = data.count()
        
        # 計算平均日工作時數
        avg_daily_hours = data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0')
        
        summary = {
            'total_work_hours': total_work_hours,
            'total_operators': total_operators,
            'total_equipment_hours': total_equipment_hours,
            'workorder_count': workorder_count,
            'avg_daily_hours': avg_daily_hours,
        }
        
        return summary
    
    def get_operator_statistics(self, data):
        """生成作業員統計資料"""
        if not data:
            return []
        
        # 按作業員分組統計
        operator_stats = data.values('operator_name').annotate(
            total_work_hours=Sum('daily_work_hours'),
            total_overtime_hours=Sum('overtime_hours'),
            total_hours=Sum('daily_work_hours') + Sum('overtime_hours')
        ).order_by('-total_hours')
        
        # 格式化統計資料
        stats_list = []
        for i, stat in enumerate(operator_stats, 1):
            stats_list.append({
                'rank': i,
                'operator_name': stat['operator_name'] or '未指定',
                'work_hours': float(stat['total_work_hours'] or 0),
                'overtime_hours': float(stat['total_overtime_hours'] or 0),
                'total_hours': float(stat['total_hours'] or 0),
            })
        
        return stats_list
    
    def get_custom_report_by_company_operator(self, company, operator, start_date, end_date):
        """按公司和作業員查詢自訂報表"""
        queryset = WorkOrderReportData.objects.filter(
            work_date__range=[start_date, end_date]
        )
        
        if company != 'all':
            queryset = queryset.filter(company=company)
        
        if operator != 'all':
            queryset = queryset.filter(operator_name=operator)
        
        return queryset.order_by('work_date', 'operator_name')
    
    def get_custom_summary_by_company_operator(self, company, operator, start_date, end_date):
        """按公司和作業員查詢自訂報表摘要"""
        data = self.get_custom_report_by_company_operator(company, operator, start_date, end_date)
        
        # 計算總工作時數
        total_work_hours = data.aggregate(total=Sum('daily_work_hours'))['total'] or Decimal('0')
        
        # 計算作業員數量（去重）
        if operator == 'all':
            total_operators = data.exclude(operator_name__isnull=True).values('operator_name').distinct().count()
        else:
            total_operators = 1  # 特定作業員
        
        # 計算總設備使用時數
        total_equipment_hours = data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0')
        
        # 計算工單數量
        workorder_count = data.count()
        
        # 計算平均日工作時數
        avg_daily_hours = data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0')
        
        summary = {
            'total_work_hours': total_work_hours,
            'total_operators': total_operators,
            'total_equipment_hours': total_equipment_hours,
            'workorder_count': workorder_count,
            'avg_daily_hours': avg_daily_hours,
        }
        
        return summary
    
    def get_weekly_report(self, company_code, year, week):
        """週報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_year=year,
            work_week=week
        )
    
    def get_monthly_report(self, company_code, year, month):
        """月報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_year=year,
            work_month=month
        )
    
    def get_quarterly_report(self, company_code, year, quarter):
        """季報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_year=year,
            work_quarter=quarter
        )
    
    def get_yearly_report(self, company_code, year):
        """年報表"""
        return WorkOrderReportData.objects.filter(
            company=company_code,
            work_year=year
        )
    
    def get_daily_summary(self, company_code, date):
        """日報表摘要"""
        data = self.get_daily_report(company_code, date)
        
        summary = {
            'total_work_hours': data.aggregate(total=Sum('daily_work_hours'))['total'] or Decimal('0'),
            'total_operators': data.aggregate(total=Sum('operator_count'))['total'] or 0,
            'total_equipment_hours': data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0'),
            'workorder_count': data.count(),
            'avg_daily_hours': data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0'),
        }
        
        return summary
    
    def get_weekly_summary(self, company_code, year, week):
        """週報表摘要"""
        data = self.get_weekly_report(company_code, year, week)
        
        summary = {
            'total_work_hours': data.aggregate(total=Sum('daily_work_hours'))['total'] or Decimal('0'),
            'total_operators': data.aggregate(total=Sum('operator_count'))['total'] or 0,
            'total_equipment_hours': data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0'),
            'workorder_count': data.count(),
            'avg_daily_hours': data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0'),
        }
        
        return summary
    
    def get_monthly_summary(self, company_code, year, month):
        """月報表摘要"""
        data = self.get_monthly_report(company_code, year, month)
        
        summary = {
            'total_work_hours': data.aggregate(total=Sum('monthly_work_hours'))['total'] or Decimal('0'),
            'total_operators': data.aggregate(total=Sum('operator_count'))['total'] or 0,
            'total_equipment_hours': data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0'),
            'workorder_count': data.count(),
            'avg_daily_hours': data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0'),
        }
        
        return summary
    
    def get_quarterly_summary(self, company_code, year, quarter):
        """季報表摘要"""
        data = self.get_quarterly_report(company_code, year, quarter)
        
        summary = {
            'total_work_hours': data.aggregate(total=Sum('monthly_work_hours'))['total'] or Decimal('0'),
            'total_operators': data.aggregate(total=Sum('operator_count'))['total'] or 0,
            'total_equipment_hours': data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0'),
            'workorder_count': data.count(),
            'avg_daily_hours': data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0'),
        }
        
        return summary
    
    def get_yearly_summary(self, company_code, year):
        """年報表摘要"""
        data = self.get_yearly_report(company_code, year)
        
        summary = {
            'total_work_hours': data.aggregate(total=Sum('monthly_work_hours'))['total'] or Decimal('0'),
            'total_operators': data.aggregate(total=Sum('operator_count'))['total'] or 0,
            'total_equipment_hours': data.aggregate(total=Sum('equipment_hours'))['total'] or Decimal('0'),
            'workorder_count': data.count(),
            'avg_daily_hours': data.aggregate(avg=Avg('daily_work_hours'))['avg'] or Decimal('0'),
        }
        
        return summary


class ReportGeneratorService:
    """報表生成服務"""
    
    def __init__(self):
        self.work_hour_service = WorkHourReportService()
    
    def generate_daily_report_by_operator(self, operator, date, format='preview'):
        """按作業員生成日報表"""
        try:
            data = self.work_hour_service.get_daily_report_by_operator(operator, date)
            summary = self.work_hour_service.get_daily_summary_by_operator(operator, date)
            
            report_data = {
                'report_type': '日報表',
                'operator': operator,
                'date': date,
                'generated_at': timezone.now(),
                'summary': summary,
                'details': list(data.values()),
            }
            
            if format == 'excel':
                return self._export_to_excel(report_data, f'作業員日報表_{date}')
            elif format == 'csv':
                return self._export_to_csv(report_data, f'作業員日報表_{date}')
            else:
                return report_data
                
        except Exception as e:
            logger.error(f"生成日報表失敗: {str(e)}")
            raise
    
    def generate_daily_report(self, company_code, date, format='excel'):
        """生成日報表"""
        try:
            data = self.work_hour_service.get_daily_report(company_code, date)
            summary = self.work_hour_service.get_daily_summary(company_code, date)
            
            report_data = {
                'report_type': '日報表',
                'company_code': company_code,
                'date': date,
                'generated_at': timezone.now(),
                'summary': summary,
                'details': list(data.values()),
            }
            
            if format == 'excel':
                return self._export_to_excel(report_data, f'日報表_{company_code}_{date}')
            elif format == 'csv':
                return self._export_to_csv(report_data, f'日報表_{company_code}_{date}')
            else:
                return report_data
                
        except Exception as e:
            logger.error(f"生成日報表失敗: {str(e)}")
            raise
    
    def generate_weekly_report(self, company_code, year, week, format='excel'):
        """生成週報表"""
        try:
            data = self.work_hour_service.get_weekly_report(company_code, year, week)
            summary = self.work_hour_service.get_weekly_summary(company_code, year, week)
            
            report_data = {
                'report_type': '週報表',
                'company_code': company_code,
                'year': year,
                'week': week,
                'generated_at': timezone.now(),
                'summary': summary,
                'details': list(data.values()),
            }
            
            if format == 'excel':
                return self._export_to_excel(report_data, f'週報表_{company_code}_{year}_{week}')
            elif format == 'csv':
                return self._export_to_csv(report_data, f'週報表_{company_code}_{year}_{week}')
            else:
                return report_data
                
        except Exception as e:
            logger.error(f"生成週報表失敗: {str(e)}")
            raise
    
    def generate_monthly_report(self, company_code, year, month, format='excel'):
        """生成月報表"""
        try:
            data = self.work_hour_service.get_monthly_report(company_code, year, month)
            summary = self.work_hour_service.get_monthly_summary(company_code, year, month)
            
            report_data = {
                'report_type': '月報表',
                'company_code': company_code,
                'year': year,
                'month': month,
                'generated_at': timezone.now(),
                'summary': summary,
                'details': list(data.values()),
            }
            
            if format == 'excel':
                return self._export_to_excel(report_data, f'月報表_{company_code}_{year}_{month}')
            elif format == 'csv':
                return self._export_to_csv(report_data, f'月報表_{company_code}_{year}_{month}')
            else:
                return report_data
                
        except Exception as e:
            logger.error(f"生成月報表失敗: {str(e)}")
            raise
    
    def generate_quarterly_report(self, company_code, year, quarter, format='excel'):
        """生成季報表"""
        try:
            data = self.work_hour_service.get_quarterly_report(company_code, year, quarter)
            summary = self.work_hour_service.get_quarterly_summary(company_code, year, quarter)
            
            report_data = {
                'report_type': '季報表',
                'company_code': company_code,
                'year': year,
                'quarter': quarter,
                'generated_at': timezone.now(),
                'summary': summary,
                'details': list(data.values()),
            }
            
            if format == 'excel':
                return self._export_to_excel(report_data, f'季報表_{company_code}_{year}_{quarter}')
            elif format == 'csv':
                return self._export_to_csv(report_data, f'季報表_{company_code}_{year}_{quarter}')
            else:
                return report_data
                
        except Exception as e:
            logger.error(f"生成季報表失敗: {str(e)}")
            raise
    
    def generate_yearly_report(self, company_code, year, format='excel'):
        """生成年報表"""
        try:
            data = self.work_hour_service.get_yearly_report(company_code, year)
            summary = self.work_hour_service.get_yearly_summary(company_code, year)
            
            report_data = {
                'report_type': '年報表',
                'company_code': company_code,
                'year': year,
                'generated_at': timezone.now(),
                'summary': summary,
                'details': list(data.values()),
            }
            
            if format == 'excel':
                return self._export_to_excel(report_data, f'年報表_{company_code}_{year}')
            elif format == 'csv':
                return self._export_to_csv(report_data, f'年報表_{company_code}_{year}')
            else:
                return report_data
                
        except Exception as e:
            logger.error(f"生成年報表失敗: {str(e)}")
            raise
    
    def generate_custom_report_by_company_operator(self, company, operator, start_date, end_date, format='excel'):
        """按公司和作業員生成自訂報表"""
        try:
            data = self.work_hour_service.get_custom_report_by_company_operator(company, operator, start_date, end_date)
            summary = self.work_hour_service.get_custom_summary_by_company_operator(company, operator, start_date, end_date)
            operator_stats = self.work_hour_service.get_operator_statistics(data)
            
            report_data = {
                'report_type': '自訂報表',
                'company': company,
                'operator': operator,
                'start_date': start_date,
                'end_date': end_date,
                'generated_at': timezone.now(),
                'summary': summary,
                'details': list(data.values()),
                'operator_stats': operator_stats,
            }
            
            # 生成檔案名稱
            company_name = company if company != 'all' else '全部公司'
            operator_name = operator if operator != 'all' else '全部作業員'
            filename = f'{company_name}_{operator_name}_{start_date}_{end_date}'
            
            if format == 'excel':
                return self._export_to_excel(report_data, filename)
            elif format == 'csv':
                return self._export_to_csv(report_data, filename)
            else:
                return report_data
                
        except Exception as e:
            logger.error(f"生成自訂報表失敗: {str(e)}")
            raise
    
    def _export_to_excel(self, report_data, filename):
        """匯出為Excel格式（包含三個活頁簿：統計摘要、詳細、統計）"""
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from openpyxl.utils import get_column_letter
            
            wb = openpyxl.Workbook()
            
            # 移除預設的工作表
            wb.remove(wb.active)
            
            # 1. 統計摘要活頁簿
            ws_summary = wb.create_sheet("統計摘要")
            self._create_summary_sheet(ws_summary, report_data)
            
            # 2. 詳細活頁簿
            ws_detail = wb.create_sheet("詳細")
            self._create_detail_sheet(ws_detail, report_data)
            
            # 3. 統計活頁簿
            ws_stats = wb.create_sheet("統計")
            self._create_stats_sheet(ws_stats, report_data)
            
            # 儲存檔案
            file_path = f"/tmp/{filename}.xlsx"
            wb.save(file_path)
            
            return {
                'file_path': file_path,
                'filename': f"{filename}.xlsx",
                'format': 'excel'
            }
            
        except ImportError:
            logger.error("openpyxl未安裝，無法生成Excel檔案")
            raise
        except Exception as e:
            logger.error(f"生成Excel檔案失敗: {str(e)}")
            raise
    
    def _create_summary_sheet(self, ws, report_data):
        """建立統計摘要活頁簿"""
        # 設定樣式
        from openpyxl.styles import Font, PatternFill
        title_font = Font(bold=True, size=14)
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        
        # 報表標題
        ws['A1'] = f"{report_data['report_type']} - 統計摘要"
        ws['A1'].font = title_font
        ws.merge_cells('A1:D1')
        
        # 基本資訊
        if report_data['report_type'] == '自訂報表':
            ws['A3'] = "公司"
            ws['B3'] = report_data.get('company', '全部')
            ws['C3'] = "作業員"
            ws['D3'] = report_data.get('operator', '全部')
            
            ws['A4'] = "起始日期"
            ws['B4'] = report_data.get('start_date', '').strftime('%Y-%m-%d') if hasattr(report_data.get('start_date', ''), 'strftime') else str(report_data.get('start_date', ''))
            ws['C4'] = "結束日期"
            ws['D4'] = report_data.get('end_date', '').strftime('%Y-%m-%d') if hasattr(report_data.get('end_date', ''), 'strftime') else str(report_data.get('end_date', ''))
            
            ws['A5'] = "生成時間"
            ws['B5'] = report_data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            ws['A3'] = "作業員"
            ws['B3'] = report_data.get('operator', '全部')
            ws['C3'] = "報表日期"
            ws['D3'] = report_data.get('date', '').strftime('%Y-%m-%d') if hasattr(report_data.get('date', ''), 'strftime') else str(report_data.get('date', ''))
            
            ws['A4'] = "生成時間"
            ws['B4'] = report_data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        ws['A4'] = "生成時間"
        ws['B4'] = report_data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        # 摘要資料
        summary = report_data['summary']
        ws['A6'] = "總工作時數"
        ws['B6'] = float(summary['total_work_hours'])
        ws['C6'] = "總作業員數"
        ws['D6'] = summary['total_operators']
        
        ws['A7'] = "總設備使用時數"
        ws['B7'] = float(summary['total_equipment_hours'])
        ws['C7'] = "工單數量"
        ws['D7'] = summary['workorder_count']
        
        ws['A8'] = "平均日工作時數"
        ws['B8'] = float(summary['avg_daily_hours'])
        
        # 設定欄寬
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 15
    
    def _create_detail_sheet(self, ws, report_data):
        """建立詳細活頁簿"""
        # 設定樣式
        from openpyxl.styles import Font, PatternFill, Border, Side
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                       top=Side(style='thin'), bottom=Side(style='thin'))
        
        # 標題
        ws['A1'] = f"{report_data['report_type']} - 詳細資料"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:K1')
        
        # 表頭
        headers = ['作業員', '公司名稱', '工單編號', '產品編號', '工序', '工作日期', '開始時間', '結束時間', '工作時數', '加班時數', '合計時數']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
        
        # 資料行
        details = report_data['details']
        for row, detail in enumerate(details, 4):
            ws.cell(row=row, column=1, value=detail.get('operator_name', '-')).border = border
            ws.cell(row=row, column=2, value=detail.get('company', '-')).border = border
            ws.cell(row=row, column=3, value=detail.get('workorder_id', '-')).border = border
            ws.cell(row=row, column=4, value=detail.get('product_code', '-')).border = border
            ws.cell(row=row, column=5, value=detail.get('process_name', '-')).border = border
            ws.cell(row=row, column=6, value=detail.get('work_date', '-')).border = border
            ws.cell(row=row, column=7, value=detail.get('start_time', '-')).border = border
            ws.cell(row=row, column=8, value=detail.get('end_time', '-')).border = border
            ws.cell(row=row, column=9, value=float(detail.get('work_hours', 0))).border = border
            ws.cell(row=row, column=10, value=float(detail.get('overtime_hours', 0))).border = border
            ws.cell(row=row, column=11, value=float(detail.get('total_hours', 0))).border = border
        
        # 設定欄寬
        from openpyxl.utils import get_column_letter
        column_widths = [15, 15, 15, 20, 15, 12, 10, 10, 12, 12, 12]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width
    
    def _create_stats_sheet(self, ws, report_data):
        """建立統計活頁簿"""
        # 設定樣式
        from openpyxl.styles import Font, PatternFill, Border, Side
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                       top=Side(style='thin'), bottom=Side(style='thin'))
        
        # 標題
        ws['A1'] = f"{report_data['report_type']} - 作業員統計"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:E1')
        
        # 表頭
        headers = ['排名', '作業員', '工作時數', '加班時數', '合計時數']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
        
        # 計算作業員統計
        details = report_data['details']
        operator_stats = {}
        
        for detail in details:
            operator = detail.get('operator_name', '未指定')
            if operator not in operator_stats:
                operator_stats[operator] = {
                    'work_hours': 0,
                    'overtime_hours': 0,
                    'total_hours': 0
                }
            operator_stats[operator]['work_hours'] += float(detail.get('work_hours', 0))
            operator_stats[operator]['overtime_hours'] += float(detail.get('overtime_hours', 0))
            operator_stats[operator]['total_hours'] += float(detail.get('total_hours', 0))
        
        # 排序並寫入資料
        sorted_operators = sorted(operator_stats.items(), key=lambda x: x[1]['total_hours'], reverse=True)
        
        for row, (operator, stats) in enumerate(sorted_operators, 4):
            ws.cell(row=row, column=1, value=row-3).border = border  # 排名
            ws.cell(row=row, column=2, value=operator).border = border  # 作業員
            ws.cell(row=row, column=3, value=stats['work_hours']).border = border  # 工作時數
            ws.cell(row=row, column=4, value=stats['overtime_hours']).border = border  # 加班時數
            ws.cell(row=row, column=5, value=stats['total_hours']).border = border  # 合計時數
        
        # 設定欄寬
        from openpyxl.utils import get_column_letter
        column_widths = [8, 20, 12, 12, 12]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width
    
    def _export_to_csv(self, report_data, filename):
        """匯出為CSV格式"""
        try:
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 寫入標題
            writer.writerow([f"{report_data['report_type']}"])
            writer.writerow([])
            
            # 寫入基本資訊
            writer.writerow(["公司代號", report_data['company_code'], "生成時間", report_data['generated_at'].strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            # 寫入摘要
            summary = report_data['summary']
            writer.writerow(["總工作時數", float(summary['total_work_hours'])])
            writer.writerow(["總作業員數", summary['total_operators']])
            writer.writerow(["總設備時數", float(summary['total_equipment_hours'])])
            writer.writerow(["工單數量", summary['workorder_count']])
            writer.writerow(["平均日工作時數", float(summary['avg_daily_hours'])])
            writer.writerow([])
            
            # 寫入詳細資料
            if report_data['details']:
                writer.writerow(["工單編號", "工作日期", "日工作時數", "作業員人數", "設備時數"])
                for detail in report_data['details']:
                    writer.writerow([
                        detail.get('workorder_id', ''),
                        detail.get('work_date', ''),
                        float(detail.get('daily_work_hours', 0)),
                        detail.get('operator_count', 0),
                        float(detail.get('equipment_hours', 0))
                    ])
            
            # 儲存檔案
            file_path = f"/tmp/{filename}.csv"
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write(output.getvalue())
            
            return {
                'file_path': file_path,
                'filename': f"{filename}.csv",
                'format': 'csv'
            }
            
        except Exception as e:
            logger.error(f"生成CSV檔案失敗: {str(e)}")
            raise


class ReportSchedulerService:
    """報表排程服務"""
    
    def __init__(self):
        self.report_generator = ReportGeneratorService()
    
    def execute_scheduled_reports(self):
        """執行排程報表"""
        try:
            # 取得所有啟用的排程
            schedules = ReportSchedule.objects.filter(status='active')
            
            for schedule in schedules:
                try:
                    # 檢查是否該執行
                    if self._should_execute_schedule(schedule):
                        self._execute_schedule(schedule)
                        
                except Exception as e:
                    logger.error(f"執行排程 {schedule.name} 失敗: {str(e)}")
                    self._log_execution(schedule, 'failed', str(e))
                    
        except Exception as e:
            logger.error(f"執行排程報表失敗: {str(e)}")
    
    def _should_execute_schedule(self, schedule):
        """檢查是否該執行排程"""
        now = timezone.now()
        
        if schedule.report_type == 'weekly':
            # 週報表：檢查是否為指定的週幾和時間
            if schedule.schedule_day and now.weekday() + 1 == schedule.schedule_day:
                return now.time() >= schedule.schedule_time
                
        elif schedule.report_type == 'monthly':
            # 月報表：檢查是否為指定的日期和時間
            if schedule.schedule_day and now.day == schedule.schedule_day:
                return now.time() >= schedule.schedule_time
                
        elif schedule.report_type == 'quarterly':
            # 季報表：每季第一天
            if now.day == 1 and now.month in [1, 4, 7, 10]:
                return now.time() >= schedule.schedule_time
                
        elif schedule.report_type == 'yearly':
            # 年報表：每年第一天
            if now.day == 1 and now.month == 1:
                return now.time() >= schedule.schedule_time
        
        return False
    
    def _execute_schedule(self, schedule):
        """執行排程"""
        try:
            # 記錄開始執行
            self._log_execution(schedule, 'running', '開始執行')
            
            now = timezone.now()
            
            # 根據報表類型生成報表
            if schedule.report_type == 'weekly':
                # 上週的報表
                last_week = now - timedelta(days=7)
                year, week, _ = last_week.isocalendar()
                result = self.report_generator.generate_weekly_report(
                    schedule.company, year, week, 'excel'
                )
                
            elif schedule.report_type == 'monthly':
                # 上個月的報表
                if now.month == 1:
                    year = now.year - 1
                    month = 12
                else:
                    year = now.year
                    month = now.month - 1
                    
                result = self.report_generator.generate_monthly_report(
                    schedule.company, year, month, 'excel'
                )
                
            elif schedule.report_type == 'quarterly':
                # 上個季度的報表
                if now.month <= 3:
                    year = now.year - 1
                    quarter = 4
                else:
                    year = now.year
                    quarter = ((now.month - 1) // 3)
                    
                result = self.report_generator.generate_quarterly_report(
                    schedule.company, year, quarter, 'excel'
                )
                
            elif schedule.report_type == 'yearly':
                # 去年的報表
                year = now.year - 1
                result = self.report_generator.generate_yearly_report(
                    schedule.company, year, 'excel'
                )
            
            # 記錄成功執行
            self._log_execution(schedule, 'success', f'報表生成成功: {result["filename"]}', result['file_path'])
            
            # 發送郵件（如果有設定收件人）
            if schedule.email_recipients:
                self._send_report_email(schedule, result)
                
        except Exception as e:
            logger.error(f"執行排程 {schedule.name} 失敗: {str(e)}")
            self._log_execution(schedule, 'failed', str(e))
    
    def _log_execution(self, schedule, status, message, file_path=''):
        """記錄執行日誌"""
        ReportExecutionLog.objects.create(
            report_schedule=schedule,
            status=status,
            message=message,
            file_path=file_path
        )
    
    def _send_report_email(self, schedule, result):
        """發送報表郵件"""
        try:
            from django.core.mail import EmailMessage
            from django.conf import settings
            
            subject = f"自動報表 - {schedule.name}"
            message = f"""
            您好，
            
            這是自動生成的 {schedule.get_report_type_display()}。
            
            報表檔案：{result['filename']}
            生成時間：{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            此郵件由系統自動發送，請勿回覆。
            """
            
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=schedule.email_recipients.split(','),
            )
            
            # 附加檔案
            with open(result['file_path'], 'rb') as f:
                email.attach(result['filename'], f.read(), 'application/octet-stream')
            
            email.send()
            logger.info(f"報表郵件發送成功: {schedule.name}")
            
        except Exception as e:
            logger.error(f"發送報表郵件失敗: {str(e)}") 


class CompletedWorkOrderReportService:
    """
    已完工工單報表服務
    提供已完工工單報表的資料查詢和統計功能
    """
    
    @staticmethod
    def get_completed_workorder_summary(company_code=None, year=None, month=None, quarter=None):
        """
        取得已完工工單統計摘要
        
        Args:
            company_code: 公司代號
            year: 年份
            month: 月份
            quarter: 季度
            
        Returns:
            dict: 統計摘要
        """
        from .models import CompletedWorkOrderReportData
        
        queryset = CompletedWorkOrderReportData.objects.all()
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        if year:
            queryset = queryset.filter(completion_year=year)
        if month:
            queryset = queryset.filter(completion_month=month)
        if quarter:
            queryset = queryset.filter(completion_quarter=quarter)
        
        # 計算統計資料
        stats = queryset.aggregate(
            total_workorders=Count('id'),
            total_planned_quantity=Sum('planned_quantity'),
            total_completed_quantity=Sum('completed_quantity'),
            total_good_quantity=Sum('total_good_quantity'),
            total_defect_quantity=Sum('total_defect_quantity'),
            total_work_hours=Sum('total_work_hours'),
            total_overtime_hours=Sum('total_overtime_hours'),
            total_all_hours=Sum('total_all_hours'),
            avg_completion_rate=Avg('completion_rate'),
            avg_defect_rate=Avg('defect_rate'),
            avg_efficiency_rate=Avg('efficiency_rate'),
            avg_hourly_output=Avg('hourly_output'),
        )
        
        # 計算平均完工率
        avg_completion_rate = stats['avg_completion_rate'] or 0
        avg_defect_rate = stats['avg_defect_rate'] or 0
        avg_efficiency_rate = stats['avg_efficiency_rate'] or 0
        avg_hourly_output = stats['avg_hourly_output'] or 0
        
        return {
            'total_workorders': stats['total_workorders'] or 0,
            'total_planned_quantity': stats['total_planned_quantity'] or 0,
            'total_completed_quantity': stats['total_completed_quantity'] or 0,
            'total_good_quantity': stats['total_good_quantity'] or 0,
            'total_defect_quantity': stats['total_defect_quantity'] or 0,
            'total_work_hours': float(stats['total_work_hours'] or 0),
            'total_overtime_hours': float(stats['total_overtime_hours'] or 0),
            'total_all_hours': float(stats['total_all_hours'] or 0),
            'avg_completion_rate': float(avg_completion_rate),
            'avg_defect_rate': float(avg_defect_rate),
            'avg_efficiency_rate': float(avg_efficiency_rate),
            'avg_hourly_output': float(avg_hourly_output),
        }
    
    @staticmethod
    def get_completed_workorder_trend(company_code=None, days=30):
        """
        取得已完工工單趨勢資料
        
        Args:
            company_code: 公司代號
            days: 天數
            
        Returns:
            dict: 趨勢資料
        """
        from .models import CompletedWorkOrderReportData
        from datetime import datetime, timedelta
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        queryset = CompletedWorkOrderReportData.objects.filter(
            completion_date__range=[start_date, end_date]
        )
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        # 按日期分組統計
        daily_data = queryset.values('completion_date').annotate(
            workorder_count=Count('id'),
            total_completed_quantity=Sum('completed_quantity'),
            total_work_hours=Sum('total_work_hours'),
            avg_completion_rate=Avg('completion_rate'),
        ).order_by('completion_date')
        
        labels = []
        workorder_counts = []
        completed_quantities = []
        work_hours = []
        completion_rates = []
        
        for item in daily_data:
            labels.append(item['completion_date'].strftime('%m/%d'))
            workorder_counts.append(item['workorder_count'])
            completed_quantities.append(item['total_completed_quantity'] or 0)
            work_hours.append(float(item['total_work_hours'] or 0))
            completion_rates.append(float(item['avg_completion_rate'] or 0))
        
        return {
            'labels': labels,
            'workorder_counts': workorder_counts,
            'completed_quantities': completed_quantities,
            'work_hours': work_hours,
            'completion_rates': completion_rates,
        }
    
    @staticmethod
    def get_company_completion_distribution():
        """
        取得公司完工分布資料
        
        Returns:
            dict: 分布資料
        """
        from .models import CompletedWorkOrderReportData
        
        company_data = CompletedWorkOrderReportData.objects.values('company_name').annotate(
            workorder_count=Count('id'),
            total_completed_quantity=Sum('completed_quantity'),
            avg_completion_rate=Avg('completion_rate'),
        ).order_by('-workorder_count')
        
        labels = []
        workorder_counts = []
        completed_quantities = []
        completion_rates = []
        
        for item in company_data:
            company_name = item['company_name'] or '未指定'
            labels.append(company_name)
            workorder_counts.append(item['workorder_count'])
            completed_quantities.append(item['total_completed_quantity'] or 0)
            completion_rates.append(float(item['avg_completion_rate'] or 0))
        
        return {
            'labels': labels,
            'workorder_counts': workorder_counts,
            'completed_quantities': completed_quantities,
            'completion_rates': completion_rates,
        } 

# ==================== 評分報表服務 ====================

class ScoringService:
    """評分報表服務類別"""
    
    @staticmethod
    def calculate_production_score(company_code, start_date, end_date):
        """計算生產效率分數 - 以工序標準產能為基準"""
        from decimal import Decimal
        
        # 取得期間內的作業員工序產能評分資料
        capacity_scores = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            work_date__range=[start_date, end_date]
        )
        
        if not capacity_scores.exists():
            return Decimal('0.00')
        
        # 計算平均產能評分
        avg_capacity_score = capacity_scores.aggregate(
            avg=models.Avg('capacity_score')
        )['avg'] or Decimal('0.00')
        
        return avg_capacity_score
    
    @staticmethod
    def calculate_quality_score(company_code, start_date, end_date):
        """計算品質管理分數 - 基於作業員工序產能評分"""
        from decimal import Decimal
        
        # 取得期間內的作業員工序產能評分資料
        capacity_scores = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            work_date__range=[start_date, end_date]
        )
        
        if not capacity_scores.exists():
            return Decimal('0.00')
        
        # 計算品質指標
        total_quantity = capacity_scores.aggregate(
            total=models.Sum('completed_quantity')
        )['total'] or 0
        
        total_defect = capacity_scores.aggregate(
            total=models.Sum('defect_quantity')
        )['total'] or 0
        
        # 計算不良率
        defect_rate = (total_defect / total_quantity * 100) if total_quantity > 0 else 0
        
        # 計算平均品質評分
        avg_quality_score = capacity_scores.aggregate(
            avg=models.Avg('quality_score')
        )['avg'] or Decimal('0.00')
        
        # 品質分數 = 平均品質評分 (70%) + 不良率評分 (30%)
        defect_score = max(Decimal('100.00') - Decimal(str(defect_rate)), Decimal('0.00'))
        quality_score = (avg_quality_score * Decimal('0.7') + defect_score * Decimal('0.3'))
        
        return quality_score
    
    @staticmethod
    def calculate_delivery_score(company_code, start_date, end_date):
        """計算交期管理分數"""
        from decimal import Decimal
        
        # 取得期間內的工單資料
        workorder_data = CompletedWorkOrderReportData.objects.filter(
            company_code=company_code,
            completion_date__range=[start_date, end_date]
        )
        
        if not workorder_data.exists():
            return Decimal('0.00')
        
        # 計算準時完工率 (假設所有工單都準時完工)
        # 實際應用中需要比對計劃完工日期和實際完工日期
        on_time_count = workorder_data.count()  # 簡化計算
        total_count = workorder_data.count()
        
        on_time_rate = (on_time_count / total_count * 100) if total_count > 0 else 0
        
        return Decimal(str(on_time_rate))
    
    @staticmethod
    def calculate_equipment_score(company_code, start_date, end_date):
        """計算設備管理分數"""
        from decimal import Decimal
        
        # 取得期間內的工單資料
        workorder_data = CompletedWorkOrderReportData.objects.filter(
            company_code=company_code,
            completion_date__range=[start_date, end_date]
        )
        
        if not workorder_data.exists():
            return Decimal('0.00')
        
        # 計算設備利用率
        total_equipment_hours = workorder_data.aggregate(
            total=Sum('total_work_hours')
        )['total'] or Decimal('0.00')
        
        # 假設標準工作時數為8小時/天，工作天數為期間天數
        from datetime import timedelta
        work_days = (end_date - start_date).days + 1
        standard_hours = work_days * Decimal('8.00')
        
        # 設備利用率 (簡化計算)
        equipment_utilization = min((total_equipment_hours / standard_hours * 100), Decimal('100.00'))
        
        return equipment_utilization
    
    @staticmethod
    def calculate_cost_score(company_code, start_date, end_date):
        """計算成本控制分數"""
        from decimal import Decimal
        
        # 取得期間內的工單資料
        workorder_data = CompletedWorkOrderReportData.objects.filter(
            company_code=company_code,
            completion_date__range=[start_date, end_date]
        )
        
        if not workorder_data.exists():
            return Decimal('0.00')
        
        # 計算加班時數比例
        total_work_hours = workorder_data.aggregate(
            total=Sum('total_work_hours')
        )['total'] or Decimal('0.00')
        
        total_overtime_hours = workorder_data.aggregate(
            total=Sum('total_overtime_hours')
        )['total'] or Decimal('0.00')
        
        # 加班比例越低分數越高
        overtime_rate = (total_overtime_hours / total_work_hours * 100) if total_work_hours > 0 else 0
        cost_score = max(Decimal('100.00') - Decimal(str(overtime_rate)), Decimal('0.00'))
        
        return cost_score
    
    @staticmethod
    def calculate_safety_score(company_code, start_date, end_date):
        """計算安全管理分數"""
        from decimal import Decimal
        
        # 這裡可以整合安全事件資料
        # 目前簡化為固定分數
        safety_score = Decimal('95.00')  # 假設安全狀況良好
        
        return safety_score
    
    @staticmethod
    def calculate_personnel_score(company_code, start_date, end_date):
        """計算人員管理分數"""
        from decimal import Decimal
        
        # 取得期間內的工單資料
        workorder_data = CompletedWorkOrderReportData.objects.filter(
            company_code=company_code,
            completion_date__range=[start_date, end_date]
        )
        
        if not workorder_data.exists():
            return Decimal('0.00')
        
        # 計算人員效率
        total_operators = workorder_data.aggregate(
            total=Sum('unique_operators_count')
        )['total'] or 0
        
        total_work_hours = workorder_data.aggregate(
            total=Sum('total_work_hours')
        )['total'] or Decimal('0.00')
        
        # 人員效率 = 總工作時數 / 總人員數 (簡化計算)
        if total_operators > 0:
            personnel_efficiency = (total_work_hours / total_operators) / Decimal('8.00') * 100
            personnel_score = min(personnel_efficiency, Decimal('100.00'))
        else:
            personnel_score = Decimal('0.00')
        
        return personnel_score
    
    @staticmethod
    def generate_scoring_report(company_code, start_date, end_date, report_period='monthly'):
        """生成評分報表"""
        from decimal import Decimal
        from datetime import datetime
        
        # 計算生產效率分數
        production_score = ScoringService.calculate_production_score(company_code, start_date, end_date)
        
        # 生產效率佔100%權重
        total_score = production_score
        
        # 計算得分百分比
        score_percentage = total_score
        
        # 計算總體等級
        if score_percentage >= 90:
            overall_grade = '優秀'
        elif score_percentage >= 80:
            overall_grade = '良好'
        elif score_percentage >= 70:
            overall_grade = '及格'
        else:
            overall_grade = '不及格'
        
        # 統計各等級項目數
        scores = [production_score]
        
        excellent_count = sum(1 for score in scores if score >= 90)
        good_count = sum(1 for score in scores if 80 <= score < 90)
        pass_count = sum(1 for score in scores if 70 <= score < 80)
        fail_count = sum(1 for score in scores if score < 70)
        
        # 建立報表名稱
        report_name = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%Y年%m月%d日')} 評分報表"
        
        # 取得公司名稱
        from erp_integration.models import CompanyConfig
        try:
            company = CompanyConfig.objects.get(company_code=company_code)
            company_name = company.company_name
        except CompanyConfig.DoesNotExist:
            company_name = company_code
        
        # 暫時返回一個字典，因為ScoringReport模型已移除
        return {
            'id': None,
            'report_name': report_name,
            'company_name': company_name,
            'total_score': total_score,
            'score_percentage': score_percentage,
            'overall_grade': overall_grade,
            'production_score': production_score,
            'excellent_count': excellent_count,
            'good_count': good_count,
            'pass_count': pass_count,
            'fail_count': fail_count,
        }
    
    @staticmethod
    def generate_improvement_suggestions(scoring_report):
        """生成改善建議"""
        # 暫時返回空列表，因為ScoringImprovement模型已移除
        return []

# ==================== 作業員工序產能評分服務 ====================

class OperatorCapacityService:
    """作業員工序產能評分服務類別"""
    
    @staticmethod
    def calculate_operator_process_score(operator_name, operator_id, company_code, 
                                       product_code, process_name, workorder_id, 
                                       work_date, work_hours, completed_quantity, 
                                       defect_quantity=0, supervisor_name=None, 
                                       supervisor_score=None, supervisor_comment=None):
        """計算作業員工序評分"""
        from decimal import Decimal
        from datetime import datetime
        
        # 取得標準產能
        try:
            from process.models import ProductProcessStandardCapacity
            standard_capacity = ProductProcessStandardCapacity.objects.get(
                company_code=company_code,
                product_code=product_code,
                process_name=process_name
            )
            standard_capacity_per_hour = standard_capacity.standard_capacity_per_hour
        except ProductProcessStandardCapacity.DoesNotExist:
            # 如果沒有標準產能，使用預設值
            standard_capacity_per_hour = Decimal('1.00')
        
        # 計算實際產能
        if work_hours > 0:
            actual_capacity_per_hour = Decimal(str(completed_quantity)) / work_hours
        else:
            actual_capacity_per_hour = Decimal('0.00')
        
        # 計算產能比率
        if standard_capacity_per_hour > 0:
            capacity_ratio = actual_capacity_per_hour / standard_capacity_per_hour
        else:
            capacity_ratio = Decimal('0.00')
        
        # 計算效率因子和學習曲線因子
        efficiency_factor = min(Decimal('1.20'), capacity_ratio)
        learning_curve_factor = min(Decimal('1.10'), capacity_ratio)
        
        # 計算不良率
        if completed_quantity > 0:
            defect_rate = Decimal(str(defect_quantity)) / completed_quantity
        else:
            defect_rate = Decimal('0.00')
        
        # 建立或更新評分記錄
        score_record, created = OperatorProcessCapacityScore.objects.get_or_create(
            operator_id=operator_id,
            company_code=company_code,
            product_code=product_code,
            process_name=process_name,
            workorder_id=workorder_id,
            work_date=work_date,
            defaults={
                'operator_name': operator_name,
                'work_hours': work_hours,
                'standard_capacity_per_hour': standard_capacity_per_hour,
                'actual_capacity_per_hour': actual_capacity_per_hour,
                'completed_quantity': completed_quantity,
                'capacity_ratio': capacity_ratio,
                'efficiency_factor': efficiency_factor,
                'learning_curve_factor': learning_curve_factor,
                'defect_quantity': defect_quantity,
                'defect_rate': defect_rate,
                'supervisor_score': Decimal('80.00'),  # 預設80分
                'is_supervisor_scored': False,  # 預設未評分
            }
        )
        
        if not created:
            # 更新現有記錄
            score_record.operator_name = operator_name
            score_record.work_hours = work_hours
            score_record.standard_capacity_per_hour = standard_capacity_per_hour
            score_record.actual_capacity_per_hour = actual_capacity_per_hour
            score_record.completed_quantity = completed_quantity
            score_record.capacity_ratio = capacity_ratio
            score_record.efficiency_factor = efficiency_factor
            score_record.learning_curve_factor = learning_curve_factor
            score_record.defect_quantity = defect_quantity
            score_record.defect_rate = defect_rate
        
        # 如果提供了主管評分，更新主管評分資訊
        if supervisor_score is not None and supervisor_name:
            score_record.supervisor_score = supervisor_score
            score_record.supervisor_comment = supervisor_comment or ''
            score_record.supervisor_name = supervisor_name
            score_record.supervisor_date = datetime.now()
            score_record.is_supervisor_scored = True
        
        # 計算評分
        score_record.capacity_score = score_record.calculate_capacity_score()
        score_record.quality_score = score_record.calculate_quality_score()
        score_record.total_score = score_record.calculate_total_score()
        score_record.grade = score_record.get_grade(score_record.capacity_score)
        score_record.overall_grade = score_record.get_grade(score_record.total_score)
        
        score_record.save()
        return score_record
    
    @staticmethod
    def generate_operator_capacity_report(company_code, start_date, end_date, report_period='monthly'):
        """生成作業員產能評分報表"""
        from decimal import Decimal
        from datetime import datetime
        from django.db.models import Avg, Count, Sum
        
        # 取得期間內的評分資料
        scores = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            work_date__range=[start_date, end_date]
        )
        
        if not scores.exists():
            return None
        
        # 計算統計資料
        total_operators = scores.values('operator_id').distinct().count()
        total_processes = scores.values('process_name').distinct().count()
        total_work_hours = scores.aggregate(total=Sum('work_hours'))['total'] or Decimal('0.00')
        total_completed_quantity = scores.aggregate(total=Sum('completed_quantity'))['total'] or 0
        
        # 計算平均評分
        avg_capacity_score = scores.aggregate(avg=Avg('capacity_score'))['avg'] or Decimal('0.00')
        avg_quality_score = scores.aggregate(avg=Avg('quality_score'))['avg'] or Decimal('0.00')
        avg_total_score = scores.aggregate(avg=Avg('total_score'))['avg'] or Decimal('0.00')
        
        # 計算等級統計
        excellent_count = scores.filter(overall_grade='優秀').count()
        good_count = scores.filter(overall_grade='良好').count()
        pass_count = scores.filter(overall_grade='及格').count()
        fail_count = scores.filter(overall_grade='不及格').count()
        
        # 計算工序表現統計
        process_performance = {}
        process_stats = scores.values('process_name').annotate(
            avg_capacity=Avg('capacity_score'),
            avg_quality=Avg('quality_score'),
            avg_total=Avg('total_score'),
            operator_count=Count('operator_id', distinct=True),
            total_hours=Sum('work_hours'),
            total_quantity=Sum('completed_quantity')
        )
        
        for stat in process_stats:
            process_performance[stat['process_name']] = {
                'avg_capacity': float(stat['avg_capacity'] or 0),
                'avg_quality': float(stat['avg_quality'] or 0),
                'avg_total': float(stat['avg_total'] or 0),
                'operator_count': stat['operator_count'],
                'total_hours': float(stat['total_hours'] or 0),
                'total_quantity': stat['total_quantity'] or 0,
            }
        
        # 建立報表名稱
        report_name = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%Y年%m月%d日')} 作業員產能評分報表"
        
        # 建立或更新報表
        report, created = OperatorCapacityReport.objects.get_or_create(
            company_code=company_code,
            report_period=report_period,
            start_date=start_date,
            end_date=end_date,
            defaults={
                'report_name': report_name,
                'report_date': datetime.now().date(),
                'total_operators': total_operators,
                'total_processes': total_processes,
                'total_work_hours': total_work_hours,
                'total_completed_quantity': total_completed_quantity,
                'avg_capacity_score': avg_capacity_score,
                'avg_quality_score': avg_quality_score,
                'avg_total_score': avg_total_score,
                'excellent_count': excellent_count,
                'good_count': good_count,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'process_performance': process_performance,
            }
        )
        
        if not created:
            # 更新現有記錄
            report.report_name = report_name
            report.total_operators = total_operators
            report.total_processes = total_processes
            report.total_work_hours = total_work_hours
            report.total_completed_quantity = total_completed_quantity
            report.avg_capacity_score = avg_capacity_score
            report.avg_quality_score = avg_quality_score
            report.avg_total_score = avg_total_score
            report.excellent_count = excellent_count
            report.good_count = good_count
            report.pass_count = pass_count
            report.fail_count = fail_count
            report.process_performance = process_performance
            report.save()
        
        return report
    
    @staticmethod
    def get_operator_performance_summary(company_code, start_date, end_date, operator_id=None):
        """取得作業員表現摘要"""
        from django.db.models import Avg, Count, Sum
        
        # 建立查詢條件
        query = {
            'company_code': company_code,
            'work_date__range': [start_date, end_date]
        }
        
        if operator_id:
            query['operator_id'] = str(operator_id)
        
        scores = OperatorProcessCapacityScore.objects.filter(**query)
        
        if not scores.exists():
            return None
        
        # 計算摘要統計
        summary = scores.aggregate(
            total_records=Count('id'),
            avg_capacity_score=Avg('capacity_score'),
            avg_quality_score=Avg('quality_score'),
            avg_total_score=Avg('total_score'),
            total_work_hours=Sum('work_hours'),
            total_completed_quantity=Sum('completed_quantity'),
            total_defect_quantity=Sum('defect_quantity'),
        )
        
        # 計算等級分布
        grade_distribution = {
            'excellent': scores.filter(overall_grade='優秀').count(),
            'good': scores.filter(overall_grade='良好').count(),
            'pass': scores.filter(overall_grade='及格').count(),
            'fail': scores.filter(overall_grade='不及格').count(),
        }
        
        # 計算工序表現排名
        process_ranking = scores.values('process_name').annotate(
            avg_score=Avg('total_score'),
            record_count=Count('id')
        ).order_by('-avg_score')
        
        # 計算作業員表現排名
        operator_ranking = scores.values('operator_name', 'operator_id').annotate(
            avg_score=Avg('total_score'),
            total_hours=Sum('work_hours'),
            total_quantity=Sum('completed_quantity'),
            record_count=Count('id')
        ).order_by('-avg_score')
        
        return {
            'summary': summary,
            'grade_distribution': grade_distribution,
            'process_ranking': list(process_ranking),
            'operator_ranking': list(operator_ranking),
        }
    
    @staticmethod
    def get_operator_process_details(operator_id, start_date, end_date):
        """取得作業員工序詳細資料"""
        scores = OperatorProcessCapacityScore.objects.filter(
            operator_id=str(operator_id),
            work_date__range=[start_date, end_date]
        ).order_by('work_date', 'process_name')
        
        return list(scores.values(
            'work_date', 'process_name', 'product_code', 'workorder_id',
            'work_hours', 'completed_quantity', 'defect_quantity',
            'standard_capacity_per_hour', 'actual_capacity_per_hour',
            'capacity_ratio', 'capacity_score', 'quality_score', 'total_score',
            'overall_grade'
        ))
    
    @staticmethod
    def get_process_capacity_analysis(company_code, start_date, end_date, process_name=None):
        """取得工序產能分析"""
        from django.db.models import Avg, Count, Sum, StdDev
        
        query = {
            'company_code': company_code,
            'work_date__range': [start_date, end_date]
        }
        
        if process_name:
            query['process_name'] = process_name
        
        scores = OperatorProcessCapacityScore.objects.filter(**query)
        
        if not scores.exists():
            return None
        
        # 按工序分組統計
        process_stats = scores.values('process_name').annotate(
            operator_count=Count('operator_id', distinct=True),
            total_records=Count('id'),
            avg_capacity_score=Avg('capacity_score'),
            avg_quality_score=Avg('quality_score'),
            avg_total_score=Avg('total_score'),
            avg_capacity_ratio=Avg('capacity_ratio'),
            total_work_hours=Sum('work_hours'),
            total_completed_quantity=Sum('completed_quantity'),
            total_defect_quantity=Sum('defect_quantity'),
            capacity_score_std=StdDev('capacity_score'),
            quality_score_std=StdDev('quality_score'),
        )
        
        # 計算整體統計
        overall_stats = scores.aggregate(
            total_operators=Count('operator_id', distinct=True),
            total_processes=Count('process_name', distinct=True),
            avg_capacity_score=Avg('capacity_score'),
            avg_quality_score=Avg('quality_score'),
            avg_total_score=Avg('total_score'),
            avg_capacity_ratio=Avg('capacity_ratio'),
            total_work_hours=Sum('work_hours'),
            total_completed_quantity=Sum('completed_quantity'),
            total_defect_quantity=Sum('defect_quantity'),
        )
        
        return {
            'process_stats': list(process_stats),
            'overall_stats': overall_stats,
        } 

# ==================== 評分週期管理服務 ====================

class ScorePeriodService:
    """評分週期管理服務"""
    
    @staticmethod
    def get_current_period_dates(period_type='monthly'):
        """取得當前評分週期的日期範圍"""
        from datetime import datetime, timedelta
        from calendar import monthrange
        
        today = datetime.now().date()
        
        if period_type == 'monthly':
            # 當月第一天到最後一天
            start_date = today.replace(day=1)
            _, last_day = monthrange(today.year, today.month)
            end_date = today.replace(day=last_day)
            
        elif period_type == 'quarterly':
            # 當前季度
            quarter = (today.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            
            start_date = today.replace(month=start_month, day=1)
            _, last_day = monthrange(today.year, end_month)
            end_date = today.replace(month=end_month, day=last_day)
            
        elif period_type == 'yearly':
            # 當年
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            
        else:
            raise ValueError(f"不支援的評分週期類型: {period_type}")
        
        return start_date, end_date
    
    @staticmethod
    def get_period_name(period_type, start_date, end_date):
        """取得評分週期名稱"""
        if period_type == 'monthly':
            return f"{start_date.year}年{start_date.month}月評分"
        elif period_type == 'quarterly':
            quarter = (start_date.month - 1) // 3 + 1
            return f"{start_date.year}年第{quarter}季評分"
        elif period_type == 'yearly':
            return f"{start_date.year}年度評分"
        else:
            return f"{start_date}至{end_date}評分"
    
    @staticmethod
    def create_period_score_records(company_code, period_type='monthly', force=False):
        """建立評分週期記錄"""
        from datetime import datetime
        
        start_date, end_date = ScorePeriodService.get_current_period_dates(period_type)
        
        # 檢查是否已存在該週期的記錄
        existing_records = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            score_period=period_type,
            period_start_date=start_date,
            period_end_date=end_date
        )
        
        if existing_records.exists() and not force:
            return existing_records
        
        # 取得該週期內的所有作業員工作記錄
        from workorder.fill_work.models import FillWork
        from workorder.onsite_reporting.models import OnsiteReport
        
        # 從填報資料建立評分記錄
        fill_works = FillWork.objects.filter(
            company_name=company_code,
            work_date__range=[start_date, end_date]
        )
        
        created_records = []
        for fill_work in fill_works:
            # 計算作業員評分
            score_record = OperatorCapacityService.calculate_operator_process_score(
                operator_name=fill_work.operator_name,
                operator_id=fill_work.operator_id,
                company_code=company_code,
                product_code=fill_work.product_code,
                process_name=fill_work.process_name,
                workorder_id=fill_work.workorder,
                work_date=fill_work.work_date,
                work_hours=fill_work.work_hours_calculated or 0,
                completed_quantity=fill_work.completed_quantity or 0,
                defect_quantity=fill_work.defect_quantity or 0
            )
            
            if score_record:
                # 設定評分週期資訊
                score_record.score_period = period_type
                score_record.period_start_date = start_date
                score_record.period_end_date = end_date
                score_record.save()
                created_records.append(score_record)
        
        # 從現場報工資料建立評分記錄
        onsite_reports = OnsiteReport.objects.filter(
            company_code=company_code,
            work_date__range=[start_date, end_date]
        )
        
        for report in onsite_reports:
            score_record = OperatorCapacityService.calculate_operator_process_score(
                operator_name=report.operator_name,
                operator_id=report.operator_id,
                company_code=company_code,
                product_code=report.product_code,
                process_name=report.process_name,
                workorder_id=report.workorder_id,
                work_date=report.work_date,
                work_hours=report.work_hours or 0,
                completed_quantity=report.completed_quantity or 0,
                defect_quantity=report.defect_quantity or 0
            )
            
            if score_record:
                # 設定評分週期資訊
                score_record.score_period = period_type
                score_record.period_start_date = start_date
                score_record.period_end_date = end_date
                score_record.save()
                created_records.append(score_record)
        
        return created_records
    
    @staticmethod
    def close_period(company_code, period_type='monthly'):
        """關閉評分週期"""
        from datetime import datetime
        
        start_date, end_date = ScorePeriodService.get_current_period_dates(period_type)
        
        # 更新該週期的所有記錄為已關閉
        updated_count = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            score_period=period_type,
            period_start_date=start_date,
            period_end_date=end_date
        ).update(
            is_period_closed=True,
            period_closed_date=datetime.now()
        )
        
        return updated_count
    
    @staticmethod
    def get_period_summary(company_code, period_type='monthly'):
        """取得評分週期摘要"""
        start_date, end_date = ScorePeriodService.get_current_period_dates(period_type)
        
        records = OperatorProcessCapacityScore.objects.filter(
            company_code=company_code,
            score_period=period_type,
            period_start_date=start_date,
            period_end_date=end_date
        )
        
        if not records.exists():
            return None
        
        # 計算統計資料
        total_records = records.count()
        avg_capacity_score = records.aggregate(avg=Avg('capacity_score'))['avg'] or 0
        avg_quality_score = records.aggregate(avg=Avg('quality_score'))['avg'] or 0
        avg_total_score = records.aggregate(avg=Avg('total_score'))['avg'] or 0
        
        # 等級分布
        grade_distribution = records.values('overall_grade').annotate(
            count=Count('id')
        ).order_by('overall_grade')
        
        # 主管評分統計
        supervisor_scored_count = records.filter(is_supervisor_scored=True).count()
        supervisor_score_rate = (supervisor_scored_count / total_records * 100) if total_records > 0 else 0
        
        return {
            'period_name': ScorePeriodService.get_period_name(period_type, start_date, end_date),
            'start_date': start_date,
            'end_date': end_date,
            'total_records': total_records,
            'avg_capacity_score': avg_capacity_score,
            'avg_quality_score': avg_quality_score,
            'avg_total_score': avg_total_score,
            'grade_distribution': grade_distribution,
            'supervisor_scored_count': supervisor_scored_count,
            'supervisor_score_rate': supervisor_score_rate,
            'is_closed': records.filter(is_period_closed=True).exists(),
        } 