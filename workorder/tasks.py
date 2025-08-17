# 工單管理模組的 Celery 任務檔案
# 功能：自動同步各公司製令單、自動轉換工單、自動檢查工單完工
# 作者：MES 系統
# 建立時間：2024年

from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from django.db import transaction
from .models import WorkOrder, CompanyOrder, SystemConfig, WorkOrderProcess, AutoAllocationSettings
# 完工判斷服務已移除，避免資料汙染
# from .services.completion_service import WorkOrderCompletionService
from erp_integration.models import CompanyConfig
from process.models import ProductProcessRoute, ProductProcessStandardCapacity
import logging
import psycopg2

# 設定工單管理模組的日誌記錄器
workorder_logger = logging.getLogger("workorder")


@shared_task
def auto_check_workorder_completion():
    """
    自動檢查工單完工狀態（已棄用）
    此功能已被簡化完工判斷機制取代
    請使用 simple_auto_completion_check 任務
    """
    workorder_logger.warning("此任務已棄用，請使用簡化完工判斷機制")
    return {
        "status": "deprecated",
        "message": "此任務已棄用，請使用 simple_auto_completion_check 任務",
        "timestamp": timezone.now().isoformat(),
    }



@shared_task
def auto_allocation_task():
    """
    自動分配任務
    定期執行自動分配功能，為數量為0的填報記錄分配數量
    """
    try:
        workorder_logger.info("=== 開始自動分配任務 ===")
        
        # 檢查自動分配設定
        try:
            settings = AutoAllocationSettings.objects.get(id=1)
            if not settings.enabled:
                workorder_logger.info("自動分配功能未啟用，跳過執行")
                return {
                    "status": "skipped",
                    "message": "自動分配功能未啟用",
                    "timestamp": timezone.now().isoformat(),
                }
            
            if settings.is_running:
                workorder_logger.warning("自動分配已在執行中，跳過本次執行")
                return {
                    "status": "skipped",
                    "message": "自動分配已在執行中",
                    "timestamp": timezone.now().isoformat(),
                }
                
        except AutoAllocationSettings.DoesNotExist:
            workorder_logger.warning("未找到自動分配設定，跳過執行")
            return {
                "status": "skipped",
                "message": "未找到自動分配設定",
                "timestamp": timezone.now().isoformat(),
            }
        
        # 執行自動分配
        from .services.auto_allocation_scheduler import scheduler
        success = scheduler.execute_auto_allocation()
        
        if success:
            workorder_logger.info("自動分配任務執行成功")
            return {
                "status": "success",
                "message": "自動分配執行成功",
                "timestamp": timezone.now().isoformat(),
            }
        else:
            workorder_logger.error("自動分配任務執行失敗")
            return {
                "status": "error",
                "message": "自動分配執行失敗",
                "timestamp": timezone.now().isoformat(),
            }
            
    except Exception as e:
        workorder_logger.error(f"自動分配任務執行異常：{str(e)}")
        return {
            "status": "error",
            "message": f"自動分配任務執行異常：{str(e)}",
            "timestamp": timezone.now().isoformat(),
        }


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
            workorder_logger.info(
                f"讀取到自動轉換間隔設定：{auto_convert_interval} 分鐘"
            )
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
                    order_number=company_order.mkordno,
                ).first()

                if existing_workorder:
                    # 如果工單已存在，跳過並標記為已轉換
                    company_order.is_converted = True
                    company_order.save()
                    workorder_logger.warning(
                        f"工單已存在，跳過轉換：{company_order.mkordno}"
                    )
                    continue

                # 建立工單（使用製令單號作為工單號碼）
                workorder = WorkOrder.objects.create(
                    order_number=company_order.mkordno,  # 直接使用製令單號
                    product_code=company_order.product_id,  # 使用 product_id
                    quantity=company_order.prodt_qty,  # 使用 prodt_qty
                    status="pending",
                    company_code=company_order.company_code,
                    order_source="erp",  # 明確指定工單來源為 ERP
                )
                count_converted += 1
                
                # 標記製令單為已轉換
                company_order.is_converted = True
                company_order.save()

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
                            capacity_data = (
                                ProductProcessStandardCapacity.objects.filter(
                                    product_code=workorder.product_code,
                                    process_name=route.process_name.name,
                                    is_active=True,
                                )
                                .order_by("-version")
                                .first()
                            )

                            # 使用標準產能或預設值
                            target_hourly_output = (
                                capacity_data.standard_capacity_per_hour
                                if capacity_data
                                else 1000
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
        # 只更新實際轉換成功的製令單
        if count_converted > 0:
            # 這裡不需要額外更新，因為在轉換過程中已經更新了 is_converted=True
            pass

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


@shared_task
def auto_batch_dispatch_orders():
    """
    自動批次派工任務
    定期自動為所有未派工的工單建立派工單
    從 SystemConfig 讀取自動批次派工間隔設定
    """
    try:
        workorder_logger.info("=== 開始自動批次派工任務 ===")

        # 讀取自動批次派工間隔設定（預設 60 分鐘）
        auto_dispatch_interval = 60
        try:
            config = SystemConfig.objects.get(key="auto_batch_dispatch_interval")
            auto_dispatch_interval = int(config.value)
            workorder_logger.info(
                f"讀取到自動批次派工間隔設定：{auto_dispatch_interval} 分鐘"
            )
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動批次派工間隔設定，使用預設值 60 分鐘")

        # 取得所有未派工的工單（排除已完工的工單）
        from .workorder_dispatch.models import WorkOrderDispatch
        undispatched_orders = WorkOrder.objects.exclude(
            status='completed'  # 排除已完工的工單
        )
        
        # 修復：檢查每個工單是否已有對應的派工單（使用 order_number + product_code 組合）
        # 避免多公司系統中同一個製令單號只建立一個派工單的問題
        truly_undispatched = []
        for wo in undispatched_orders:
            dispatch_exists = WorkOrderDispatch.objects.filter(
                order_number=wo.order_number,
                product_code=wo.product_code
            ).exists()
            if not dispatch_exists:
                truly_undispatched.append(wo)
        
        if not truly_undispatched:
            workorder_logger.info("沒有需要派工的工單")
            return {
                "status": "success",
                "message": "沒有需要派工的工單",
                "timestamp": timezone.now().isoformat(),
            }

        created = 0
        for wo in truly_undispatched:
            try:
                # 建立派工單
                dispatch = WorkOrderDispatch.objects.create(
                    company_code=getattr(wo, "company_code", None),
                    order_number=wo.order_number,
                    product_code=wo.product_code,
                    planned_quantity=wo.quantity,
                    status="pending",
                    created_by="system",
                )
                created += 1
                workorder_logger.info(f"自動建立派工單：{wo.order_number}")
                
                # 立即檢查工序分配並更新派工單狀態
                try:
                    from .services.dispatch_status_service import DispatchStatusService
                    DispatchStatusService.update_dispatch_status_by_process_allocation(wo.id)
                    workorder_logger.info(f"派工單 {wo.order_number} 狀態已自動更新")
                except Exception as status_error:
                    workorder_logger.warning(f"更新派工單 {wo.order_number} 狀態失敗：{status_error}")
                    
            except Exception as e:
                workorder_logger.error(f"建立派工單失敗 (工單: {wo.order_number}): {e}")

        workorder_logger.info(
            f"自動批次派工完成，共建立 {created} 筆派工單"
        )

        return {
            "status": "success",
            "message": f"自動批次派工完成，共建立 {created} 筆派工單，間隔設定：{auto_dispatch_interval} 分鐘",
            "timestamp": timezone.now().isoformat(),
        }

    except Exception as e:
        workorder_logger.error(f"自動批次派工失敗：{str(e)}")
        return {
            "status": "error",
            "message": f"自動批次派工失敗：{str(e)}",
            "timestamp": timezone.now().isoformat(),
        }


@shared_task
def auto_update_dispatch_statuses():
    """
    自動更新派工單狀態任務
    定期檢查工序分配情況並更新派工單狀態
    從 SystemConfig 讀取自動更新間隔設定
    """
    try:
        workorder_logger.info("=== 開始自動更新派工單狀態任務 ===")

        # 讀取自動更新間隔設定（預設 30 分鐘）
        auto_update_interval = 30
        try:
            config = SystemConfig.objects.get(key="auto_update_dispatch_status_interval")
            auto_update_interval = int(config.value)
            workorder_logger.info(
                f"讀取到自動更新派工單狀態間隔設定：{auto_update_interval} 分鐘"
            )
        except SystemConfig.DoesNotExist:
            workorder_logger.warning("未找到自動更新派工單狀態間隔設定，使用預設值 30 分鐘")

        # 執行派工單狀態更新
        from .services.dispatch_status_service import DispatchStatusService
        updated_count = DispatchStatusService.update_all_dispatch_statuses()
        
        workorder_logger.info(f"自動更新派工單狀態完成，共更新 {updated_count} 筆派工單")

        return {
            "status": "success",
            "message": f"自動更新派工單狀態完成，共更新 {updated_count} 筆派工單，間隔設定：{auto_update_interval} 分鐘",
            "timestamp": timezone.now().isoformat(),
        }

    except Exception as e:
        workorder_logger.error(f"自動更新派工單狀態失敗：{str(e)}")
        return {
            "status": "error",
            "message": f"自動更新派工單狀態失敗：{str(e)}",
            "timestamp": timezone.now().isoformat(),
        }


# 清理任務已移除，避免資料汙染
# @shared_task
# def cleanup_completed_production_records():
#     """
#     定時清理已完工工單的生產中記錄
#     保持資料庫效能，避免生產中記錄無限增長
#     """
#     此任務已移除


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


@shared_task
def auto_check_process_completion():
    """
    工序完工檢查定時任務（已棄用）
    此功能已被簡化完工判斷機制取代
    請使用 simple_auto_completion_check 任務
    """
    workorder_logger.warning("此任務已棄用，請使用簡化完工判斷機制")
    return {
        "status": "deprecated",
        "message": "此任務已棄用，請使用 simple_auto_completion_check 任務",
        "timestamp": timezone.now().isoformat(),
    }


@shared_task
def auto_check_report_completion():
    """
    填報完工檢查定時任務（已棄用）
    此功能已被簡化完工判斷機制取代
    請使用 simple_auto_completion_check 任務
    """
    workorder_logger.warning("此任務已棄用，請使用簡化完工判斷機制")
    return {
        "status": "deprecated",
        "message": "此任務已棄用，請使用 simple_auto_completion_check 任務",
        "timestamp": timezone.now().isoformat(),
    }


@shared_task
def completion_trigger_task():
    """
    完工觸發檢查任務（已棄用）
    此功能已被簡化完工判斷機制取代
    請使用 simple_auto_completion_check 任務
    """
    workorder_logger.warning("此任務已棄用，請使用簡化完工判斷機制")
    return {
        "status": "deprecated",
        "message": "此任務已棄用，請使用 simple_auto_completion_check 任務",
        "timestamp": timezone.now().isoformat(),
    }
