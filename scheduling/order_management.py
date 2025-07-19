"""
訂單管理模組
整合所有訂單相關的邏輯功能，包含：
- 訂單資料同步
- 訂單查詢與篩選
- 訂單匯出功能
- 訂單排程設定
- 訂單狀態管理
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from django.db import connections, DatabaseError
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
import csv
import json

from .models import OrderMain, OrderUpdateSchedule, CompanyView, SchedulingOperationLog

logger = logging.getLogger('scheduling.order_management')


class OrderManager:
    """
    訂單管理器：負責所有訂單相關的操作
    """
    
    def __init__(self):
        self.logger = logging.getLogger('scheduling.order_manager')
    
    def sync_orders_from_erp(self, user=None, ip_address=None) -> Dict[str, any]:
        """
        從 ERP 系統同步訂單資料
        
        Args:
            user: 執行同步的使用者
            ip_address: 使用者 IP 地址
            
        Returns:
            Dict 包含同步結果
        """
        try:
            self.logger.info("開始執行訂單同步")
            
            # 清空現有訂單資料
            OrderMain.objects.all().delete()
            self.logger.debug("已清空 OrderMain 表")
            
            orders = []
            companies = CompanyView.objects.all()
            self.logger.debug(f"從 CompanyView 獲取 {len(companies)} 家公司資料")
            
            if not companies:
                self.logger.warning("CompanyView 表為空，無法查詢訂單")
                return {
                    'status': 'error',
                    'message': '無公司資料，請先同步公司數據',
                    'total_orders': 0
                }
            
            # 處理每家公司
            for company in companies:
                company_orders = self._sync_company_orders(company)
                orders.extend(company_orders)
            
            # 儲存訂單資料
            self._save_orders(orders)
            
            # 更新同步時間
            self._update_sync_timestamp()
            
            # 記錄操作日誌
            if user:
                self._log_operation(user, ip_address, f"同步 {len(orders)} 筆訂單")
            
            self.logger.info(f"訂單同步完成，共處理 {len(orders)} 筆訂單")
            return {
                'status': 'success',
                'message': f'訂單數據同步成功，共 {len(orders)} 筆',
                'total_orders': len(orders)
            }
            
        except Exception as e:
            self.logger.error(f"訂單同步失敗: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f'同步失敗: {str(e)}',
                'total_orders': 0
            }
    
    def _sync_company_orders(self, company: CompanyView) -> List[Dict]:
        """
        同步單一公司的訂單資料
        
        Args:
            company: 公司資料
            
        Returns:
            該公司的訂單列表
        """
        orders = []
        db_name = company.mes_database
        company_name = company.company_name
        
        if not db_name:
            self.logger.warning(f"公司 {company_name} 的 mes_database 為空，跳過")
            return orders
        
        try:
            # 建立資料庫連線
            db_config = settings.DATABASES['default'].copy()
            db_config['NAME'] = db_name
            connections.databases[db_name] = db_config
            
            with connections[db_name].cursor() as cursor:
                # 檢查表是否存在
                table_exists = self._check_tables_exist(cursor)
                
                # 同步國內訂單
                if table_exists['ordBillMain']:
                    domestic_orders = self._sync_domestic_orders(cursor, company_name)
                    orders.extend(domestic_orders)
                
                # 同步國外訂單
                if table_exists['TraBillMain']:
                    foreign_orders = self._sync_foreign_orders(cursor, company_name)
                    orders.extend(foreign_orders)
                    
        except DatabaseError as e:
            self.logger.error(f"連接到資料庫 {db_name} 失敗，公司: {company_name}，錯誤: {str(e)}")
        finally:
            # 清理連線
            if db_name in connections.databases:
                del connections.databases[db_name]
        
        return orders
    
    def _check_tables_exist(self, cursor) -> Dict[str, bool]:
        """檢查必要的資料表是否存在"""
        tables = {}
        for table_name in ['ordBillMain', 'TraBillMain']:
            cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
            tables[table_name] = cursor.fetchone()[0]
        return tables
    
    def _sync_domestic_orders(self, cursor, company_name: str) -> List[Dict]:
        """同步國內訂單"""
        try:
            cursor.execute("""
                SELECT 
                    COALESCE(c."ShortName", 'N/A') AS customer_short_name,
                    m."BillNO",
                    s."ProdID",
                    s."ProdName",
                    s."Quantity",
                    s."PreInDate",
                    s."QtyRemain",
                    m."BillDate"
                FROM "ordBillMain" m
                LEFT JOIN "ordBillSub" s ON m."BillNO" = s."BillNO"
                LEFT JOIN "comCustomer" c ON m."CustomerID" = c."ID"
                WHERE m."BillNO" LIKE '113-%'
                AND m."BillDate" >= 20200101
                AND (m."BillStatus" = 0 OR m."BillStatus" IS NULL)
                AND s."QtyRemain" > 0
                AND s."ProdID" LIKE 'PFP-%'
            """)
            
            orders = cursor.fetchall()
            self.logger.info(f"國內訂單查詢返回 {len(orders)} 筆數據")
            
            return [self._format_domestic_order(order, company_name) for order in orders]
            
        except DatabaseError as e:
            self.logger.error(f"查詢國內訂單失敗: {str(e)}")
            return []
    
    def _sync_foreign_orders(self, cursor, company_name: str) -> List[Dict]:
        """同步國外訂單"""
        try:
            cursor.execute("""
                SELECT 
                    COALESCE(c."ShortName", 'N/A') AS customer_short_name,
                    m."BillNo",
                    s."ItemNo",
                    s."Description",
                    s."Quantity",
                    s."OnBoardDay",
                    s."QtyRemain",
                    m."BillDate"
                FROM "TraBillMain" m
                LEFT JOIN "TraBillSub" s ON m."BillNo" = s."BillNo"
                LEFT JOIN "comCustomer" c ON m."CustID" = c."ID"
                WHERE m."BillNo" LIKE '542-%'
                AND m."BillDate" >= 20200101
                AND (m."BillStatus" = 0 OR m."BillStatus" IS NULL)
                AND s."QtyRemain" > 0
                AND s."ItemNo" LIKE 'PFP-%'
            """)
            
            orders = cursor.fetchall()
            self.logger.info(f"國外訂單查詢返回 {len(orders)} 筆數據")
            
            return [self._format_foreign_order(order, company_name) for order in orders]
            
        except DatabaseError as e:
            self.logger.error(f"查詢國外訂單失敗: {str(e)}")
            return []
    
    def _format_domestic_order(self, order_data: tuple, company_name: str) -> Dict:
        """格式化國內訂單資料"""
        return {
            'company_name': company_name,
            'customer_short_name': order_data[0],
            'bill_no': order_data[1] if order_data[1] else 'N/A',
            'product_id': order_data[2] if order_data[2] else 'N/A',
            'product_name': order_data[3] if order_data[3] else 'N/A',
            'quantity': int(order_data[4]) if order_data[4] is not None else 0,
            'pre_in_date': self._convert_date_format(order_data[5]),
            'qty_remain': int(order_data[6]) if order_data[6] is not None else 0,
            'order_type': '國內',
            'bill_date': self._convert_date_format(order_data[7])
        }
    
    def _format_foreign_order(self, order_data: tuple, company_name: str) -> Dict:
        """格式化國外訂單資料"""
        return {
            'company_name': company_name,
            'customer_short_name': order_data[0],
            'bill_no': order_data[1] if order_data[1] else 'N/A',
            'product_id': order_data[2] if order_data[2] else 'N/A',
            'product_name': order_data[3] if order_data[3] else 'N/A',
            'quantity': int(order_data[4]) if order_data[4] is not None else 0,
            'pre_in_date': self._convert_date_format(order_data[5]),
            'qty_remain': int(order_data[6]) if order_data[6] is not None else 0,
            'order_type': '國外',
            'bill_date': self._convert_date_format(order_data[7])
        }
    
    def _convert_date_format(self, date_value) -> str:
        """轉換 ERP 日期格式 (YYYYMMDD) 為標準格式 (YYYY-MM-DD)"""
        if date_value is None:
            return 'N/A'
        
        try:
            date_str = str(date_value)
            if len(date_str) == 8 and date_str.isdigit():
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            else:
                return 'N/A'
        except Exception:
            return 'N/A'
    
    def _save_orders(self, orders: List[Dict]):
        """批次儲存訂單資料"""
        for order in orders:
            OrderMain.objects.create(**order)
    
    def _update_sync_timestamp(self):
        """更新同步時間戳記"""
        schedule = OrderUpdateSchedule.objects.first()
        if schedule:
            schedule.last_updated = timezone.now()
            schedule.save()
    
    def _log_operation(self, user, ip_address: str, action: str):
        """記錄操作日誌"""
        SchedulingOperationLog.objects.create(
            user=user.username if user else 'system',
            action=action,
            timestamp=timezone.now(),
            ip_address=ip_address
        )


class OrderQueryManager:
    """
    訂單查詢管理器：負責訂單的查詢、篩選與匯出功能
    """
    
    def __init__(self):
        self.logger = logging.getLogger('scheduling.order_query')
    
    def get_orders_with_filters(self, filters: Dict) -> Tuple[List[OrderMain], Dict]:
        """
        根據篩選條件查詢訂單，支援排序
        Args:
            filters: 篩選條件字典，可包含 'order_by'（排序欄位，預設-pre_in_date）
        Returns:
            (訂單列表, 統計資訊)
        """
        try:
            # 建立查詢條件
            query = Q()
            
            if filters.get('company'):
                query &= Q(company_name=filters['company'])
            if filters.get('customer'):
                query &= Q(customer_short_name=filters['customer'])
            if filters.get('order_type'):
                query &= Q(order_type=filters['order_type'])
            if filters.get('date_start'):
                query &= Q(pre_in_date__gte=filters['date_start'])
            if filters.get('date_end'):
                query &= Q(pre_in_date__lte=filters['date_end'])

            # 取得排序欄位，預設用預交貨日（pre_in_date）升冪排序
            order_by = filters.get('order_by', 'pre_in_date')
            if order_by not in ['pre_in_date', '-pre_in_date', 'bill_date', '-bill_date']:
                order_by = 'pre_in_date'

            # 執行查詢
            orders = OrderMain.objects.filter(query).order_by(order_by)
            # 計算統計資訊
            stats = self._calculate_order_stats(orders)
            return orders, stats
        except Exception as e:
            self.logger.error(f"查詢訂單失敗: {str(e)}")
            return [], {}
    
    def _calculate_order_stats(self, orders) -> Dict:
        """計算訂單統計資訊"""
        try:
            total_orders = orders.count()
            total_quantity = orders.aggregate(Sum('quantity'))['quantity__sum'] or 0
            total_remain = orders.aggregate(Sum('qty_remain'))['qty_remain__sum'] or 0
            
            # 按公司統計
            company_stats = orders.values('company_name').annotate(
                count=Count('id'),
                total_qty=Sum('quantity'),
                total_remain=Sum('qty_remain')
            )
            
            # 按訂單類型統計
            type_stats = orders.values('order_type').annotate(
                count=Count('id'),
                total_qty=Sum('quantity'),
                total_remain=Sum('qty_remain')
            )
            
            return {
                'total_orders': total_orders,
                'total_quantity': total_quantity,
                'total_remain': total_remain,
                'company_stats': list(company_stats),
                'type_stats': list(type_stats)
            }
            
        except Exception as e:
            self.logger.error(f"計算統計資訊失敗: {str(e)}")
            return {}
    
    def get_filter_options(self) -> Dict:
        """取得篩選選項"""
        try:
            return {
                'companies': OrderMain.objects.values_list('company_name', flat=True).distinct(),
                'customers': OrderMain.objects.values_list('customer_short_name', flat=True).distinct(),
                'order_types': ['國內', '國外']
            }
        except Exception as e:
            self.logger.error(f"取得篩選選項失敗: {str(e)}")
            return {'companies': [], 'customers': [], 'order_types': []}
    
    def export_orders_to_csv(self, orders, filename: str = "orders.csv") -> HttpResponse:
        """
        將訂單資料匯出為 CSV 檔案
        
        Args:
            orders: 訂單查詢結果
            filename: 檔案名稱
            
        Returns:
            CSV 檔案回應
        """
        try:
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # 寫入 BOM 以支援中文
            response.write('\ufeff')
            
            writer = csv.writer(response)
            
            # 寫入標題列
            writer.writerow([
                '公司', '客戶', '訂單編號', '訂單類型', '產品編號', 
                '產品名稱', '訂購數量', '訂單日期', '預交貨日', '未交貨數量'
            ])
            
            # 寫入資料列
            for order in orders:
                writer.writerow([
                    order.company_name,
                    order.customer_short_name,
                    order.bill_no,
                    order.order_type,
                    order.product_id,
                    order.product_name,
                    order.quantity,
                    order.bill_date,
                    order.pre_in_date,
                    order.qty_remain
                ])
            
            return response
            
        except Exception as e:
            self.logger.error(f"匯出 CSV 失敗: {str(e)}")
            return HttpResponse("匯出失敗", status=500)


class OrderScheduleManager:
    """
    訂單排程管理器：負責訂單排程相關的設定與管理
    """
    
    def __init__(self):
        self.logger = logging.getLogger('scheduling.order_schedule')
    
    def update_sync_schedule(self, sync_interval_minutes: int, user=None, ip_address=None) -> Dict:
        """
        更新訂單同步排程設定
        
        Args:
            sync_interval_minutes: 同步間隔（分鐘）
            user: 執行使用者
            ip_address: 使用者 IP
            
        Returns:
            更新結果
        """
        try:
            # 驗證參數
            if sync_interval_minutes < 0:
                return {
                    'status': 'error',
                    'message': '同步間隔時間不能為負數'
                }
            
            # 更新排程設定
            schedule, created = OrderUpdateSchedule.objects.get_or_create(id=1)
            schedule.sync_interval_minutes = sync_interval_minutes
            schedule.save()
            
            # 更新 Celery 排程任務
            self._update_celery_schedule(sync_interval_minutes)
            
            # 記錄操作日誌
            if user:
                self._log_schedule_update(user, ip_address, sync_interval_minutes)
            
            return {
                'status': 'success',
                'message': f'訂單更新排程設定成功，間隔 {sync_interval_minutes} 分鐘'
            }
            
        except Exception as e:
            self.logger.error(f"更新排程設定失敗: {str(e)}")
            return {
                'status': 'error',
                'message': f'更新排程設定失敗: {str(e)}'
            }
    
    def _update_celery_schedule(self, sync_interval_minutes: int):
        """更新 Celery 排程任務"""
        try:
            from django_celery_beat.models import PeriodicTask, IntervalSchedule
            
            # 刪除現有任務
            PeriodicTask.objects.filter(name='Update Orders Task').delete()
            
            # 建立新任務
            if sync_interval_minutes > 0:
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=sync_interval_minutes,
                    period=IntervalSchedule.MINUTES
                )
                
                PeriodicTask.objects.create(
                    name='Update Orders Task',
                    task='scheduling.tasks.update_orders_task',
                    interval=interval,
                    enabled=True,
                    description=f'Update orders every {sync_interval_minutes} minutes'
                )
                
        except ImportError:
            self.logger.warning("django_celery_beat 未安裝，跳過 Celery 排程設定")
        except Exception as e:
            self.logger.error(f"更新 Celery 排程失敗: {str(e)}")
    
    def _log_schedule_update(self, user, ip_address: str, sync_interval_minutes: int):
        """記錄排程更新日誌"""
        SchedulingOperationLog.objects.create(
            user=user.username,
            action=f"更新訂單同步間隔為 {sync_interval_minutes} 分鐘",
            ip_address=ip_address,
            timestamp=timezone.now()
        )
    
    def get_sync_schedule(self) -> Optional[OrderUpdateSchedule]:
        """取得目前的同步排程設定"""
        try:
            return OrderUpdateSchedule.objects.first()
        except Exception as e:
            self.logger.error(f"取得排程設定失敗: {str(e)}")
            return None
    
    def get_sync_status(self) -> Dict:
        """取得同步狀態資訊"""
        try:
            schedule = self.get_sync_schedule()
            if not schedule:
                return {
                    'enabled': False,
                    'interval': 0,
                    'last_updated': None,
                    'next_update': None
                }
            
            next_update = None
            if schedule.last_updated and schedule.sync_interval_minutes > 0:
                next_update = schedule.last_updated + timedelta(minutes=schedule.sync_interval_minutes)
            
            return {
                'enabled': schedule.sync_interval_minutes > 0,
                'interval': schedule.sync_interval_minutes,
                'last_updated': schedule.last_updated,
                'next_update': next_update
            }
            
        except Exception as e:
            self.logger.error(f"取得同步狀態失敗: {str(e)}")
            return {}


class OrderAnalytics:
    """
    訂單分析器：提供訂單相關的統計分析功能
    """
    
    def __init__(self):
        self.logger = logging.getLogger('scheduling.order_analytics')
    
    def get_order_summary(self) -> Dict:
        """取得訂單摘要統計"""
        try:
            total_orders = OrderMain.objects.count()
            total_quantity = OrderMain.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
            total_remain = OrderMain.objects.aggregate(Sum('qty_remain'))['qty_remain__sum'] or 0
            
            # 按公司統計
            company_summary = OrderMain.objects.values('company_name').annotate(
                order_count=Count('id'),
                total_qty=Sum('quantity'),
                total_remain=Sum('qty_remain')
            )
            
            # 按訂單類型統計
            type_summary = OrderMain.objects.values('order_type').annotate(
                order_count=Count('id'),
                total_qty=Sum('quantity'),
                total_remain=Sum('qty_remain')
            )
            
            # 最近 30 天趨勢
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            recent_orders = OrderMain.objects.filter(
                bill_date__gte=thirty_days_ago.strftime('%Y-%m-%d')
            ).count()
            
            return {
                'total_orders': total_orders,
                'total_quantity': total_quantity,
                'total_remain': total_remain,
                'completion_rate': (total_quantity - total_remain) / total_quantity * 100 if total_quantity > 0 else 0,
                'company_summary': list(company_summary),
                'type_summary': list(type_summary),
                'recent_orders': recent_orders
            }
            
        except Exception as e:
            self.logger.error(f"取得訂單摘要失敗: {str(e)}")
            return {}
    
    def get_delivery_analysis(self) -> Dict:
        """取得交期分析"""
        try:
            # 即將到期的訂單（7天內）
            seven_days_later = (timezone.now().date() + timedelta(days=7)).strftime('%Y-%m-%d')
            urgent_orders = OrderMain.objects.filter(
                pre_in_date__lte=seven_days_later,
                qty_remain__gt=0
            ).count()
            
            # 已逾期的訂單
            today = timezone.now().date().strftime('%Y-%m-%d')
            overdue_orders = OrderMain.objects.filter(
                pre_in_date__lt=today,
                qty_remain__gt=0
            ).count()
            
            # 按交期分組統計
            delivery_groups = {
                'overdue': overdue_orders,
                'urgent': urgent_orders,
                'normal': OrderMain.objects.filter(
                    pre_in_date__gt=seven_days_later,
                    qty_remain__gt=0
                ).count()
            }
            
            return {
                'urgent_orders': urgent_orders,
                'overdue_orders': overdue_orders,
                'delivery_groups': delivery_groups
            }
            
        except Exception as e:
            self.logger.error(f"取得交期分析失敗: {str(e)}")
            return {}


# 全域實例
order_manager = OrderManager()
order_query_manager = OrderQueryManager()
order_schedule_manager = OrderScheduleManager()
order_analytics = OrderAnalytics() 