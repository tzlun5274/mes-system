# 工單管理模組的 Celery 任務檔案
# 功能：自動同步各公司製令單、自動轉換工單
# 作者：MES 系統
# 建立時間：2024年

from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from django.db import transaction
from .models import WorkOrder, CompanyOrder, SystemConfig, WorkOrderProcess
from erp_integration.models import CompanyConfig
from process.models import ProductProcessRoute, ProductProcessStandardCapacity
import logging
import psycopg2

# 設定工單管理模組的日誌記錄器
workorder_logger = logging.getLogger("workorder")


@shared_task
def auto_sync_company_orders():
    """
    自動同步各公司製令單到 CompanyOrder 表
    從 SystemConfig 讀取自動同步間隔設定
    """
    try:
        workorder_logger.info("=== 開始自動同步公司製令單 ===")

        # 讀取自動同步間隔設定（預設 30 分鐘）
        auto_sync_interval = 30
        try:
            config = SystemConfig.objects.get(key="auto_sync_companyorder_interval")
            auto_sync_interval = int(config.value)
            workorder_logger.info(f"讀取到自動同步間隔設定：{auto_sync_interval} 分鐘")
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動同步間隔設定，使用預設值 30 分鐘")

        # 執行同步命令
        call_command("sync_pending_workorders")
        workorder_logger.info("自動同步公司製令單完成")

        return {
            "status": "success",
            "message": f"自動同步完成，間隔設定：{auto_sync_interval} 分鐘",
            "timestamp": timezone.now().isoformat(),
        }

    except Exception as e:
        workorder_logger.error(f"自動同步公司製令單失敗：{str(e)}")
        return {
            "status": "error",
            "message": f"自動同步失敗：{str(e)}",
            "timestamp": timezone.now().isoformat(),
        }


@shared_task
def auto_convert_orders():
    """
    自動轉換製令單為 MES 工單
    從 SystemConfig 讀取自動轉換間隔設定
    """
    try:
        workorder_logger.info("=== 開始自動轉換製令單 ===")

        # 讀取自動轉換間隔設定（預設 30 分鐘）
        auto_convert_interval = 30
        try:
            config = SystemConfig.objects.get(key="auto_convert_interval")
            auto_convert_interval = int(config.value)
            workorder_logger.info(f"讀取到自動轉換間隔設定：{auto_convert_interval} 分鐘")
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動轉換間隔設定，使用預設值 30 分鐘")

        # 取得未轉換的製令單
        pending_orders = CompanyOrder.objects.filter(is_converted=False)
        if not pending_orders.exists():
            workorder_logger.info("沒有需要轉換的製令單")
            return {
                "status": "success",
                "message": "沒有需要轉換的製令單",
                "timestamp": timezone.now().isoformat(),
            }

        count_converted = 0
        count_processes_created = 0

        for company_order in pending_orders:
            try:
                # 檢查工單是否已存在（使用公司代號和製令單號的組合）
                existing_workorder = WorkOrder.objects.filter(
                    company_code=company_order.company_code,
                    order_number=company_order.mkordno
                ).first()
                
                if existing_workorder:
                    # 如果工單已存在，跳過並標記為已轉換
                    company_order.is_converted = True
                    company_order.save()
                    workorder_logger.warning(f"工單已存在，跳過轉換：{company_order.mkordno}")
                    continue
                
                # 建立工單（使用製令單號作為工單號碼）
                workorder = WorkOrder.objects.create(
                    order_number=company_order.mkordno,  # 直接使用製令單號
                    product_code=company_order.product_id,  # 使用 product_id
                    quantity=company_order.prodt_qty,  # 使用 prodt_qty
                    status="pending",
                    company_code=company_order.company_code,
                )
                count_converted += 1

                # 建立工序明細
                try:
                    # 從產品工藝路線取得工序資料
                    routes = ProductProcessRoute.objects.filter(
                        product_id=workorder.product_code
                    ).order_by("step_order")

                    if routes.exists():
                        # 使用產品工藝路線建立工序明細
                        for route in routes:
                            # 查詢標準產能資料
                            capacity_data = ProductProcessStandardCapacity.objects.filter(
                                product_code=workorder.product_code,
                                process_name=route.process_name.name,
                                is_active=True
                            ).order_by('-version').first()
                            
                            # 使用標準產能或預設值
                            target_hourly_output = (
                                capacity_data.standard_capacity_per_hour 
                                if capacity_data else 1000
                            )
                            
                            WorkOrderProcess.objects.create(
                                workorder=workorder,
                                process_name=route.process_name.name,
                                step_order=route.step_order,
                                planned_quantity=workorder.quantity,
                                target_hourly_output=target_hourly_output,
                            )
                            count_processes_created += 1
                        workorder_logger.info(
                            f"工單 {workorder.order_number} 建立 {len(routes)} 個工序明細"
                        )
                    else:
                        workorder_logger.warning(
                            f"工單 {workorder.order_number} 沒有找到產品工藝路線"
                        )

                except Exception as e:
                    workorder_logger.error(
                        f"建立工序明細失敗 (工單: {workorder.order_number}): {e}"
                    )

            except Exception as e:
                workorder_logger.error(
                    f"轉換製令單失敗 (製令單: {company_order.mkordno}): {e}"
                )

        # 更新 CompanyOrder 的轉換狀態
        if count_converted > 0:
            CompanyOrder.objects.filter(is_converted=False).update(is_converted=True)

        workorder_logger.info(
            f"自動轉換完成，轉換 {count_converted} 筆製令單，建立 {count_processes_created} 個工序明細"
        )

        return {
            "status": "success",
            "message": f"自動轉換完成，轉換 {count_converted} 筆製令單，建立 {count_processes_created} 個工序明細",
            "timestamp": timezone.now().isoformat(),
        }

    except Exception as e:
        workorder_logger.error(f"自動轉換製令單失敗：{str(e)}")
        return {
            "status": "error",
            "message": f"自動轉換失敗：{str(e)}",
            "timestamp": timezone.now().isoformat(),
        }


def get_standard_processes(product_code):
    """
    取得標準工序清單（當產品沒有設定工藝路線時使用）
    """
    # 標準工序設定，可根據實際需求調整
    standard_processes = [
        {"name": "SMT 貼片", "target_hourly_output": 1000},
        {"name": "測試", "target_hourly_output": 500},
        {"name": "包裝", "target_hourly_output": 200},
    ]
    return standard_processes
