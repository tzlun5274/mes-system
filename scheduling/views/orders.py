# 這個檔案負責訂單管理頁面的後端邏輯
from django.shortcuts import render
from django.http import HttpResponse
from ..order_management import order_query_manager, order_analytics


def order_list(request):
    """
    顯示訂單管理頁面，支援公司、客戶、訂單類型、交期查詢與Excel匯出，並可依預交貨日排序
    """
    # 取得查詢條件
    filters = {
        "company": request.GET.get("company", "").strip(),
        "customer": request.GET.get("customer", "").strip(),
        "order_type": request.GET.get("order_type", "").strip(),
        "date_start": request.GET.get("date_start", "").strip(),
        "date_end": request.GET.get("date_end", "").strip(),
    }
    # 排序參數
    order_by = request.GET.get("order_by", "pre_in_date")
    filters["order_by"] = order_by
    # 移除空值
    filters = {k: v for k, v in filters.items() if v}
    # 查詢訂單
    orders, stats = order_query_manager.get_orders_with_filters(filters)
    # 匯出Excel
    if request.GET.get("export") == "excel":
        return order_query_manager.export_orders_to_csv(orders, "orders.csv")
    # 取得篩選選項
    filter_options = order_query_manager.get_filter_options()
    # 取得訂單摘要
    order_summary = order_analytics.get_order_summary()
    # 取得交期分析
    delivery_analysis = order_analytics.get_delivery_analysis()
    # 建立匯出查詢字串
    export_querystring = ""
    for k, v in filters.items():
        if v and k != "order_by":
            export_querystring += f"&{k}={v}"
    return render(
        request,
        "scheduling/order_list.html",
        {
            "orders": orders,
            "stats": stats,
            "order_summary": order_summary,
            "delivery_analysis": delivery_analysis,
            "company_choices": filter_options["companies"],
            "customer_choices": filter_options["customers"],
            "export_querystring": export_querystring,
            "filters": filters,
            "order_by": order_by,
        },
    )
