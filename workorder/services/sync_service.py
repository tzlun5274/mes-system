"""
公司製令單同步服務
提供統一的同步邏輯，供網頁介面和命令列使用
"""

import logging
import psycopg2
from django.utils import timezone
from workorder.company_order.models import CompanyOrder
from workorder.models import WorkOrder
from erp_integration.models import CompanyConfig

logger = logging.getLogger(__name__)


class CompanyOrderSyncService:
    """公司製令單同步服務"""
    
    def sync_all_companies(self, company_filter=None, limit=None, auto_mode=False):
        """
        同步所有公司的製令單
        
        Args:
            company_filter (str): 只同步指定公司代號
            limit (int): 限制每個公司同步的記錄數量
            auto_mode (bool): 自動模式，檢查是否已轉換成工單
            
        Returns:
            dict: 同步結果
        """
        try:
            companies = CompanyConfig.objects.all()
            if company_filter:
                companies = companies.filter(company_code=company_filter)
            
            total_synced = 0
            sync_details = []
            
            for company in companies:
                if not company.mes_database:
                    sync_details.append({
                        'company': company.company_name,
                        'status': 'skipped',
                        'message': '沒有設定 MES 資料庫'
                    })
                    continue
                
                try:
                    result = self._sync_company_orders(
                        company, limit=limit, auto_mode=auto_mode
                    )
                    total_synced += result['synced_count']
                    sync_details.append({
                        'company': company.company_name,
                        'status': 'success',
                        'synced_count': result['synced_count'],
                        'message': f"同步完成，新增 {result['synced_count']} 筆記錄"
                    })
                    
                except Exception as e:
                    sync_details.append({
                        'company': company.company_name,
                        'status': 'error',
                        'message': str(e)
                    })
                    logger.error(f"公司 {company.company_name} 同步失敗：{e}")
            
            return {
                'success': True,
                'total_synced': total_synced,
                'sync_details': sync_details
            }
            
        except Exception as e:
            logger.error(f"同步所有公司製令單失敗：{e}")
            return {
                'success': False,
                'error': str(e),
                'total_synced': 0
            }
    
    def _sync_company_orders(self, company, limit=None, auto_mode=False):
        """
        同步單一公司的製令單
        
        Args:
            company (CompanyConfig): 公司配置物件
            limit (int): 限制同步記錄數量
            auto_mode (bool): 自動模式
            
        Returns:
            dict: 同步結果
        """
        # 連線到公司專用資料庫
        conn = psycopg2.connect(
            dbname=company.mes_database,
            user="mes_user",
            password="mes_password",
            host="localhost",
            port="5432",
        )
        cursor = conn.cursor()
        
        try:
            # 查詢：Flag IN (1,3) 且未完工狀態；排除 340-/341-；未結案；日期自 2024-01-01 起
            sql = """
                SELECT "MKOrdNO", "ProductID", "ProdtQty", "EstTakeMatDate", 
                       "EstStockOutDate", "CompleteStatus", "BillStatus"
                FROM "prdMKOrdMain" 
                WHERE "Flag" IN (1,3)
                AND "CompleteStatus" = 2
                AND ("BillStatus" IS NULL OR "BillStatus"<>1)
                AND LEFT("MKOrdNO",4) NOT IN ('340-','341-')
                AND COALESCE("MKOrdDate", 0) >= 20240101
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor.execute(sql)
            
            synced_count = 0
            for row in cursor.fetchall():
                (
                    mkordno,
                    product_id,
                    prodt_qty,
                    est_take_mat_date,
                    est_stock_out_date,
                    complete_status,
                    bill_status,
                ) = row
                
                # 自動模式：檢查是否已轉換成 MES 工單
                is_converted = False
                if auto_mode:
                    is_converted = WorkOrder.objects.filter(
                        order_number=mkordno
                    ).exists()
                
                # 更新或建立 CompanyOrder 記錄
                company_order, created = CompanyOrder.objects.update_or_create(
                    company_code=company.company_code,
                    mkordno=mkordno,
                    defaults={
                        "product_id": product_id,
                        "prodt_qty": int(float(prodt_qty)) if prodt_qty else 0,
                        "est_take_mat_date": (
                            str(est_take_mat_date) if est_take_mat_date else ""
                        ),
                        "est_stock_out_date": (
                            str(est_stock_out_date) if est_stock_out_date else ""
                        ),
                        "complete_status": complete_status,
                        "bill_status": bill_status,
                        "is_converted": is_converted,
                    },
                )
                
                if created:
                    synced_count += 1
            
            return {
                'success': True,
                'synced_count': synced_count
            }
            
        finally:
            cursor.close()
            conn.close()
    
    def sync_single_company(self, company_code, limit=None, auto_mode=False):
        """
        同步單一公司的製令單（公開方法）
        
        Args:
            company_code (str): 公司代號
            limit (int): 限制同步記錄數量
            auto_mode (bool): 自動模式
            
        Returns:
            dict: 同步結果
        """
        try:
            company = CompanyConfig.objects.get(company_code=company_code)
            result = self._sync_company_orders(company, limit=limit, auto_mode=auto_mode)
            
            return {
                'success': True,
                'company_name': company.company_name,
                'synced_count': result['synced_count']
            }
            
        except CompanyConfig.DoesNotExist:
            return {
                'success': False,
                'error': f'找不到公司代號 {company_code}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
