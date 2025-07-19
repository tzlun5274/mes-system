from celery import shared_task
from django.utils import timezone
from django.db import connections
from django.db.utils import DatabaseError
from scheduling.models import OrderUpdateSchedule, OrderMain  # 從排程模組匯入訂單主檔
from .models import CompanyView
from django.conf import settings
import logging

logger = logging.getLogger('scheduling.tasks')

@shared_task
def update_orders_task():
    try:
        logger.debug("開始執行訂單更新任務")
        
        # 清空現有訂單資料
        OrderMain.objects.all().delete()
        logger.debug("已清空 OrderMain 表")

        orders = []
        companies = CompanyView.objects.all()
        logger.debug(f"從 CompanyView 獲取 {len(companies)} 家公司資料: {[c.mes_database for c in companies]}")
        
        if not companies:
            logger.warning("CompanyView 表為空，無法查詢訂單")
            return

        default_db_config = settings.DATABASES['default'].copy()
        
        for company in companies:
            db_name = company.mes_database
            company_name = company.company_name
            
            if not db_name:
                logger.warning(f"公司 {company_name} 的 mes_database 為空，跳過")
                continue

            db_config = default_db_config.copy()
            db_config['NAME'] = db_name
            connections.databases[db_name] = db_config
            
            try:
                with connections[db_name].cursor() as cursor:
                    # 檢查表是否存在
                    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ordBillMain')")
                    ordBillMain_exists = cursor.fetchone()[0]
                    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'TraBillMain')")
                    TraBillMain_exists = cursor.fetchone()[0]
                    logger.debug(f"資料庫 {db_name} 表檢查: ordBillMain={ordBillMain_exists}, TraBillMain={TraBillMain_exists}")

                    # 查詢國內訂單
                    if ordBillMain_exists:
                        try:
                            cursor.execute("""
                                SELECT 
                                    COALESCE(c."ShortName", 'N/A') AS CustomerShortName,
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
                            """)
                            domestic_orders = cursor.fetchall()
                            logger.info(f"國內訂單查詢（{db_name}）返回 {len(domestic_orders)} 筆數據")
                            
                            for order in domestic_orders:
                                pre_in_date = 'N/A'
                                bill_date = 'N/A'
                                if order[5] is not None:
                                    try:
                                        date_str = str(order[5])
                                        if len(date_str) == 8:
                                            pre_in_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                        else:
                                            logger.warning(f"無效的 PreInDate 格式 {order[5]}，訂單 {order[1]}")
                                    except Exception as e:
                                        logger.warning(f"無法轉換 PreInDate {order[5]}，訂單 {order[1]}，錯誤: {str(e)}")
                                if order[7] is not None:
                                    try:
                                        date_str = str(order[7])
                                        if len(date_str) == 8:
                                            bill_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                        else:
                                            logger.warning(f"無效的 BillDate 格式 {order[7]}，訂單 {order[1]}")
                                    except Exception as e:
                                        logger.warning(f"無法轉換 BillDate {order[7]}，訂單 {order[1]}，錯誤: {str(e)}")
                                
                                quantity = int(order[4]) if order[4] is not None else 0
                                qty_remain = int(order[6]) if order[6] is not None else 0
                                
                                orders.append({
                                    'company_name': company_name,
                                    'customer_short_name': order[0],
                                    'bill_no': order[1] if order[1] else 'N/A',
                                    'product_id': order[2] if order[2] else 'N/A',
                                    'product_name': order[3] if order[3] else 'N/A',
                                    'quantity': quantity,
                                    'pre_in_date': pre_in_date,
                                    'qty_remain': qty_remain,
                                    'order_type': '國內',
                                    'bill_date': bill_date
                                })
                        except DatabaseError as e:
                            logger.error(f"查詢國內訂單失敗，資料庫: {db_name}，公司: {company_name}，錯誤: {str(e)}")
                    
                    # 查詢國外訂單
                    if TraBillMain_exists:
                        try:
                            cursor.execute("""
                                SELECT 
                                    COALESCE(c."ShortName", 'N/A') AS CustomerShortName,
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
                            """)
                            foreign_orders = cursor.fetchall()
                            logger.info(f"國外訂單查詢（{db_name}）返回 {len(foreign_orders)} 筆數據")
                            
                            for order in foreign_orders:
                                pre_in_date = 'N/A'
                                bill_date = 'N/A'
                                if order[5] is not None:
                                    try:
                                        date_str = str(order[5])
                                        if len(date_str) == 8:
                                            pre_in_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                        else:
                                            logger.warning(f"無效的 OnBoardDay 格式 {order[5]}，訂單 {order[1]}")
                                    except Exception as e:
                                        logger.warning(f"無法轉換 OnBoardDay {order[5]}，訂單 {order[1]}，錯誤: {str(e)}")
                                if order[7] is not None:
                                    try:
                                        date_str = str(order[7])
                                        if len(date_str) == 8:
                                            bill_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                        else:
                                            logger.warning(f"無效的 BillDate 格式 {order[7]}，訂單 {order[1]}")
                                    except Exception as e:
                                        logger.warning(f"無法轉換 BillDate {order[7]}，訂單 {order[1]}，錯誤: {str(e)}")
                                
                                quantity = int(order[4]) if order[4] is not None else 0
                                qty_remain = int(order[6]) if order[6] is not None else 0
                                
                                orders.append({
                                    'company_name': company_name,
                                    'customer_short_name': order[0],
                                    'bill_no': order[1] if order[1] else 'N/A',
                                    'product_id': order[2] if order[2] else 'N/A',
                                    'product_name': order[3] if order[3] else 'N/A',
                                    'quantity': quantity,
                                    'pre_in_date': pre_in_date,
                                    'qty_remain': qty_remain,
                                    'order_type': '國外',
                                    'bill_date': bill_date
                                })
                        except DatabaseError as e:
                            logger.error(f"查詢國外訂單失敗，資料庫: {db_name}，公司: {company_name}，錯誤: {str(e)}")
            
            except DatabaseError as e:
                logger.error(f"連接到資料庫 {db_name} 失敗，公司: {company_name}，錯誤: {str(e)}")
            finally:
                if db_name in connections.databases:
                    del connections.databases[db_name]

        # 儲存訂單資料到 OrderMain 模型
        for order in orders:
            OrderMain.objects.create(
                company_name=order['company_name'],
                customer_short_name=order['customer_short_name'],
                bill_no=order['bill_no'],
                product_id=order['product_id'],
                product_name=order['product_name'],
                quantity=order['quantity'],
                pre_in_date=order['pre_in_date'],
                qty_remain=order['qty_remain'],
                order_type=order['order_type'],
                bill_date=order['bill_date']
            )

        # 更新 OrderUpdateSchedule 的 last_updated
        schedule = OrderUpdateSchedule.objects.first()
        if schedule:
            schedule.last_updated = timezone.now()
            schedule.save()

        logger.info(f"訂單更新任務完成，儲存 {len(orders)} 筆訂單資料")
    except Exception as e:
        logger.error(f"訂單更新任務失敗: {str(e)}")
