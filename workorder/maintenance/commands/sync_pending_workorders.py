from django.core.management.base import BaseCommand
from workorder.models import WorkOrder, CompanyOrder
from erp_integration.models import CompanyConfig
from django.db import models
import psycopg2
import logging

workorder_logger = logging.getLogger("workorder")


class Command(BaseCommand):
    help = "自動同步各公司製令單到 CompanyOrder 表"

    def handle(self, *args, **options):
        companies = CompanyConfig.objects.all()
        total_synced = 0

        for company in companies:
            if not company.mes_database:
                continue

            try:
                # 連線到公司專用資料庫
                conn = psycopg2.connect(
                    dbname=company.mes_database,
                    user="mes_user",
                    password="mes_password",
                    host="localhost",
                    port="5432",
                )
                cursor = conn.cursor()

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
                cursor.execute(sql)

                company_synced = 0
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

                    # 檢查是否已轉換成 MES 工單
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
                        company_synced += 1

                cursor.close()
                conn.close()

                total_synced += company_synced
                self.stdout.write(
                    f"公司 {company.company_name} 同步完成，新增 {company_synced} 筆記錄"
                )
                workorder_logger.info(
                    f"公司 {company.company_name} 手動同步製令單完成，新增 {company_synced} 筆記錄。"
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"公司 {company.company_name} 同步失敗：{e}")
                )
                workorder_logger.error(
                    f"公司 {company.company_name} 手動同步製令單失敗：{e}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"所有公司同步完成，共新增 {total_synced} 筆公司製令單記錄"
            )
        )
        workorder_logger.info(
            f"所有公司手動同步製令單完成，共新增 {total_synced} 筆公司製令單記錄。"
        )
