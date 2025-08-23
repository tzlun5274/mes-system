"""
公司製令單管理子模組 - 服務層
負責公司製令單的同步、轉換和業務邏輯
"""

import logging
from datetime import datetime
from django.db import connection
from django.utils import timezone
from erp_integration.models import CompanyConfig
from .models import CompanyOrder, CompanyOrderSystemConfig

logger = logging.getLogger(__name__)


class CompanyOrderSyncService:
    """公司製令單同步服務"""
    
    @classmethod
    def sync_company_orders(cls, company_code=None):
        """
        同步公司製令單
        根據設計規範的判斷機制同步製令單資料
        """
        try:
            # 取得公司設定
            if company_code:
                companies = CompanyConfig.objects.filter(company_code=company_code)
            else:
                companies = CompanyConfig.objects.all()
            
            total_synced = 0
            total_removed = 0
            
            for company in companies:
                synced, removed = cls._sync_single_company(company)
                total_synced += synced
                total_removed += removed
            
            logger.info(f"同步完成：新增 {total_synced} 筆，移除 {total_removed} 筆")
            return {
                'success': True,
                'synced': total_synced,
                'removed': total_removed
            }
            
        except Exception as e:
            logger.error(f"同步公司製令單失敗：{str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def _sync_single_company(cls, company):
        """同步單一公司的製令單"""
        try:
            # 連接到公司專用資料庫
            with connection.cursor() as cursor:
                # 查詢符合條件的製令單
                sql = """
                SELECT 
                    Flag, MKOrdNO, MKOrdDate, MakeType, ProductID, ProdtQty,
                    Producer, Functionary, EstTakeMatDate, EstWareInDate,
                    CompleteStatus, BillStatus, Remark
                FROM prdMKOrdMain 
                WHERE (Flag = 1 OR Flag = 3)
                AND CompleteStatus = 2
                AND BillStatus != 1
                AND MKOrdNO NOT LIKE '340-%'
                AND MKOrdNO NOT LIKE '341-%'
                AND MKOrdDate >= '2024-01-01'
                """
                
                cursor.execute(sql)
                results = cursor.fetchall()
                
                synced_count = 0
                removed_count = 0
                
                # 處理查詢結果
                for row in results:
                    flag, mkordno, mkord_date, make_type, product_id, prodt_qty, \
                    producer, functionary, est_take_mat_date, est_ware_in_date, \
                    complete_status, bill_status, remark = row
                    
                    # 檢查是否已存在
                    existing = CompanyOrder.objects.filter(
                        company_code=company.company_code,
                        mkordno=mkordno,
                        product_id=product_id
                    ).first()
                    
                    if existing:
                        # 更新現有記錄
                        existing.flag = flag
                        existing.mkord_date = mkord_date
                        existing.make_type = make_type
                        existing.prodt_qty = int(prodt_qty) if prodt_qty else 0
                        existing.producer = producer
                        existing.functionary = functionary
                        existing.est_take_mat_date = est_take_mat_date or ''
                        existing.est_stock_out_date = est_ware_in_date or ''
                        existing.complete_status = complete_status
                        existing.bill_status = bill_status
                        existing.remark = remark
                        existing.save()
                    else:
                        # 創建新記錄
                        CompanyOrder.objects.create(
                            company_code=company.company_code,
                            mkordno=mkordno,
                            product_id=product_id,
                            prodt_qty=int(prodt_qty) if prodt_qty else 0,
                            est_take_mat_date=est_take_mat_date or '',
                            est_stock_out_date=est_ware_in_date or '',
                            complete_status=complete_status,
                            bill_status=bill_status,
                            flag=flag,
                            mkord_date=mkord_date,
                            make_type=make_type,
                            producer=producer,
                            functionary=functionary,
                            remark=remark
                        )
                        synced_count += 1
                
                # 移除不符合條件的記錄
                removed_count = cls._remove_invalid_orders(company.company_code)
                
                return synced_count, removed_count
                
        except Exception as e:
            logger.error(f"同步公司 {company.company_code} 製令單失敗：{str(e)}")
            return 0, 0
    
    @classmethod
    def _remove_invalid_orders(cls, company_code):
        """移除不符合條件的製令單"""
        try:
            # 移除已完工或已結案的製令單
            removed_count = CompanyOrder.objects.filter(
                company_code=company_code
            ).exclude(
                complete_status=2
            ).exclude(
                bill_status__isnull=True
            ).filter(
                ~models.Q(bill_status=1)
            ).delete()[0]
            
            return removed_count
            
        except Exception as e:
            logger.error(f"移除無效製令單失敗：{str(e)}")
            return 0


class CompanyOrderConvertService:
    """公司製令單轉換服務"""
    
    @classmethod
    def convert_to_workorder(cls, company_order_ids=None):
        """
        將製令單轉換成 MES 工單
        """
        try:
            if company_order_ids:
                orders = CompanyOrder.objects.filter(
                    id__in=company_order_ids,
                    is_converted=False,
                    is_pending=True
                )
            else:
                orders = CompanyOrder.objects.filter(
                    is_converted=False,
                    is_pending=True
                )
            
            converted_count = 0
            
            for order in orders:
                if cls._create_workorder_from_order(order):
                    converted_count += 1
            
            logger.info(f"轉換完成：成功轉換 {converted_count} 筆製令單")
            return {
                'success': True,
                'converted': converted_count
            }
            
        except Exception as e:
            logger.error(f"轉換製令單失敗：{str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def _create_workorder_from_order(cls, company_order):
        """從製令單創建工單"""
        try:
            from workorder.models import WorkOrder, WorkOrderProcess
            
            # 創建工單
            workorder = WorkOrder.objects.create(
                workorder_no=company_order.mkordno,
                product_id=company_order.product_id,
                planned_quantity=company_order.prodt_qty,
                company_code=company_order.company_code,
                company_name=company_order.company_code,  # 可以從 CompanyConfig 取得完整名稱
                start_date=cls._parse_date(company_order.est_take_mat_date),
                due_date=cls._parse_date(company_order.est_stock_out_date),
                status='pending',
                order_source='erp_company_order'
            )
            
            # 創建預設工序
            WorkOrderProcess.objects.create(
                workorder=workorder,
                process_name='預設工序',
                sequence=1,
                estimated_hours=8,
                status='pending'
            )
            
            # 標記為已轉換
            company_order.is_converted = True
            company_order.save()
            
            return True
            
        except Exception as e:
            logger.error(f"創建工單失敗：{str(e)}")
            return False
    
    @classmethod
    def _parse_date(cls, date_str):
        """解析日期字串"""
        if not date_str:
            return timezone.now().date()
        
        try:
            # 嘗試解析不同格式的日期
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return timezone.now().date()
        except:
            return timezone.now().date()


class CompanyOrderQueryService:
    """公司製令單查詢服務"""
    
    @classmethod
    def get_company_statistics(cls):
        """取得各公司製令單統計"""
        from django.db.models import Count, Q
        
        stats = CompanyOrder.objects.values('company_code').annotate(
            total_orders=Count('id'),
            converted_orders=Count('id', filter=Q(is_converted=True)),
            pending_orders=Count('id', filter=Q(is_converted=False))
        ).order_by('company_code')
        
        return stats
    
    @classmethod
    def get_order_by_product(cls, product_id, company_code=None):
        """根據產品編號取得製令單資訊"""
        queryset = CompanyOrder.objects.filter(product_id=product_id)
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        return queryset.order_by('-est_stock_out_date')
    
    @classmethod
    def search_orders(cls, company_code=None, mkordno=None, product_id=None):
        """搜尋製令單"""
        queryset = CompanyOrder.objects.all()
        
        if company_code:
            queryset = queryset.filter(company_code=company_code)
        
        if mkordno:
            queryset = queryset.filter(mkordno__icontains=mkordno)
        
        if product_id:
            queryset = queryset.filter(product_id__icontains=product_id)
        
        return queryset.order_by('-est_stock_out_date')
