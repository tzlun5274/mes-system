"""
客戶訂單管理 API 視圖
提供訂單相關的 RESTful API 介面
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from ..customer_order_management import (
    order_manager,
    order_query_manager,
    order_schedule_manager,
    order_analytics,
)

logger = logging.getLogger("scheduling.customer_order_api")


@csrf_exempt
@require_http_methods(["GET"])
def get_orders_api(request):
    """
    取得客戶訂單列表 API
    GET /api/orders/
    """
    try:
        # 取得查詢參數
        filters = {
            "company": request.GET.get("company", "").strip(),
            "customer": request.GET.get("customer", "").strip(),
            "order_type": request.GET.get("order_type", "").strip(),
            "date_start": request.GET.get("date_start", "").strip(),
            "date_end": request.GET.get("date_end", "").strip(),
        }

        # 移除空值
        filters = {k: v for k, v in filters.items() if v}

        # 查詢訂單
        orders, stats = order_query_manager.get_orders_with_filters(filters)

        # 序列化訂單資料
        orders_data = []
        for order in orders:
            orders_data.append(
                {
                    "id": order.id,
                    "company_name": order.company_name,
                    "customer_short_name": order.customer_short_name,
                    "bill_no": order.bill_no,
                    "product_id": order.product_id,
                    "product_name": order.product_name,
                    "quantity": order.quantity,
                    "pre_in_date": order.pre_in_date,
                    "qty_remain": order.qty_remain,
                    "order_type": order.order_type,
                    "bill_date": order.bill_date,
                    "created_at": (
                        order.created_at.isoformat() if order.created_at else None
                    ),
                    "updated_at": (
                        order.updated_at.isoformat() if order.updated_at else None
                    ),
                }
            )

        return JsonResponse(
            {
                "status": "success",
                "data": {
                    "orders": orders_data,
                    "stats": stats,
                    "total_count": len(orders_data),
                },
            }
        )

    except Exception as e:
        logger.error(f"取得客戶訂單列表失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"取得客戶訂單列表失敗: {str(e)}"}, status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def sync_orders_api(request):
    """
    同步訂單資料 API
    POST /api/orders/sync/
    """
    try:
        # 執行同步
        result = order_manager.sync_orders_from_erp(
            user=request.user if hasattr(request, "user") else None,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        if result["status"] == "success":
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)

    except Exception as e:
        logger.error(f"同步訂單失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"同步訂單失敗: {str(e)}"}, status=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_order_summary_api(request):
    """
    取得訂單摘要統計 API
    GET /api/orders/summary/
    """
    try:
        summary = order_analytics.get_order_summary()
        delivery_analysis = order_analytics.get_delivery_analysis()

        return JsonResponse(
            {
                "status": "success",
                "data": {"summary": summary, "delivery_analysis": delivery_analysis},
            }
        )

    except Exception as e:
        logger.error(f"取得訂單摘要失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"取得訂單摘要失敗: {str(e)}"}, status=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_sync_status_api(request):
    """
    取得同步狀態 API
    GET /api/orders/sync-status/
    """
    try:
        sync_status = order_schedule_manager.get_sync_status()

        return JsonResponse({"status": "success", "data": sync_status})

    except Exception as e:
        logger.error(f"取得同步狀態失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"取得同步狀態失敗: {str(e)}"}, status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def update_sync_schedule_api(request):
    """
    更新同步排程 API
    POST /api/orders/sync-schedule/
    """
    try:
        # 解析請求資料
        data = json.loads(request.body)
        sync_interval_minutes = data.get("sync_interval_minutes")

        if sync_interval_minutes is None:
            return JsonResponse(
                {"status": "error", "message": "缺少 sync_interval_minutes 參數"},
                status=400,
            )

        try:
            sync_interval_minutes = int(sync_interval_minutes)
        except ValueError:
            return JsonResponse(
                {"status": "error", "message": "sync_interval_minutes 必須為整數"},
                status=400,
            )

        # 更新排程設定
        result = order_schedule_manager.update_sync_schedule(
            sync_interval_minutes=sync_interval_minutes,
            user=request.user if hasattr(request, "user") else None,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        if result["status"] == "success":
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)

    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "無效的 JSON 格式"}, status=400
        )
    except Exception as e:
        logger.error(f"更新同步排程失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"更新同步排程失敗: {str(e)}"}, status=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_filter_options_api(request):
    """
    取得篩選選項 API
    GET /api/orders/filter-options/
    """
    try:
        filter_options = order_query_manager.get_filter_options()

        return JsonResponse({"status": "success", "data": filter_options})

    except Exception as e:
        logger.error(f"取得篩選選項失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"取得篩選選項失敗: {str(e)}"}, status=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def export_orders_api(request):
    """
    匯出訂單資料 API
    GET /api/orders/export/
    """
    try:
        # 取得查詢參數
        filters = {
            "company": request.GET.get("company", "").strip(),
            "customer": request.GET.get("customer", "").strip(),
            "order_type": request.GET.get("order_type", "").strip(),
            "date_start": request.GET.get("date_start", "").strip(),
            "date_end": request.GET.get("date_end", "").strip(),
        }

        # 移除空值
        filters = {k: v for k, v in filters.items() if v}

        # 查詢訂單
        orders, _ = order_query_manager.get_orders_with_filters(filters)

        # 匯出 CSV
        filename = request.GET.get("filename", "orders.csv")
        return order_query_manager.export_orders_to_csv(orders, filename)

    except Exception as e:
        logger.error(f"匯出訂單失敗: {str(e)}", exc_info=True)
        return JsonResponse(
            {"status": "error", "message": f"匯出訂單失敗: {str(e)}"}, status=500
        )


class OrderAPIView(View):
    """
    訂單 API 視圖類別
    提供統一的客戶訂單管理 API 介面
    """

    def get(self, request, action=None):
        """處理 GET 請求"""
        if action == "sync-status":
            return get_sync_status_api(request)
        elif action == "summary":
            return get_order_summary_api(request)
        elif action == "filter-options":
            return get_filter_options_api(request)
        elif action == "export":
            return export_orders_api(request)
        else:
            return get_orders_api(request)

    def post(self, request, action=None):
        """處理 POST 請求"""
        if action == "sync":
            return sync_orders_api(request)
        elif action == "sync-schedule":
            return update_sync_schedule_api(request)
        else:
            return JsonResponse(
                {"status": "error", "message": "無效的操作"}, status=400
            )
