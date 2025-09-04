# 這個檔案負責訂單管理頁面的後端邏輯
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ..order_management import order_query_manager, order_analytics
from ..models import OrderMain


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
    
    # 分頁設定
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 20)  # 每頁顯示數量，預設20筆
    
    try:
        per_page = int(per_page)
        if per_page < 1:
            per_page = 20
        elif per_page > 100:  # 限制最大每頁數量
            per_page = 100
    except ValueError:
        per_page = 20
    
    # 建立分頁器
    paginator = Paginator(orders, per_page)
    
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        # 如果頁碼不是整數，顯示第一頁
        orders_page = paginator.page(1)
    except EmptyPage:
        # 如果頁碼超出範圍，顯示最後一頁
        orders_page = paginator.page(paginator.num_pages)
    
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
            "orders": orders_page,
            "stats": stats,
            "order_summary": order_summary,
            "delivery_analysis": delivery_analysis,
            "company_choices": filter_options["companies"],
            "customer_choices": filter_options["customers"],
            "export_querystring": export_querystring,
            "filters": filters,
            "order_by": order_by,
            "per_page": per_page,
            "total_pages": paginator.num_pages,
            "current_page": orders_page.number,
            "has_previous": orders_page.has_previous(),
            "has_next": orders_page.has_next(),
            "previous_page_number": orders_page.previous_page_number() if orders_page.has_previous() else None,
            "next_page_number": orders_page.next_page_number() if orders_page.has_next() else None,
            "page_range": orders_page.paginator.page_range,
            "total_count": paginator.count,
        },
    )


def order_detail(request, order_id):
    """
    顯示訂單詳情頁面
    """
    order = get_object_or_404(OrderMain, id=order_id)
    
    # 計算訂單相關統計
    context = {
        'order': order,
        'delivery_progress': (order.delivered_quantity / order.quantity * 100) if order.quantity > 0 else 0,
        'days_until_delivery': None,
        'delivery_status': 'normal'
    }
    
    # 計算距離交期的天數
    try:
        from datetime import datetime
        from django.utils import timezone
        
        delivery_date = datetime.strptime(order.pre_in_date, '%Y-%m-%d').date()
        today = timezone.now().date()
        days_diff = (delivery_date - today).days
        
        context['days_until_delivery'] = days_diff
        
        # 設定交期狀態
        if days_diff < 0:
            context['delivery_status'] = 'overdue'
        elif days_diff <= 3:
            context['delivery_status'] = 'urgent'
        elif days_diff <= 7:
            context['delivery_status'] = 'warning'
    except:
        pass
    
    return render(request, 'scheduling/order_detail.html', context)


def order_detail_api(request, order_id):
    """
    訂單詳情 API，用於 AJAX 請求
    """
    try:
        order = get_object_or_404(OrderMain, id=order_id)
        
        # 計算距離交期的天數
        days_until_delivery = None
        delivery_status = 'normal'
        
        try:
            from datetime import datetime
            from django.utils import timezone
            
            delivery_date = datetime.strptime(order.pre_in_date, '%Y-%m-%d').date()
            today = timezone.now().date()
            days_diff = (delivery_date - today).days
            
            days_until_delivery = days_diff
            
            if days_diff < 0:
                delivery_status = 'overdue'
            elif days_diff <= 3:
                delivery_status = 'urgent'
            elif days_diff <= 7:
                delivery_status = 'warning'
        except:
            pass
        
        data = {
            'id': order.id,
            'company_name': order.company_name,
            'customer_short_name': order.customer_short_name,
            'bill_no': order.bill_no,
            'product_id': order.product_id,
            'product_name': order.product_name,
            'quantity': order.quantity,
            'delivered_quantity': order.delivered_quantity,
            'qty_remain': order.qty_remain,
            'pre_in_date': order.pre_in_date,
            'order_type': order.order_type,
            'bill_date': order.bill_date,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': order.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'delivery_progress': round((order.delivered_quantity / order.quantity * 100), 2) if order.quantity > 0 else 0,
            'days_until_delivery': days_until_delivery,
            'delivery_status': delivery_status,
            'is_overdue': order.is_overdue,
            'is_urgent': order.is_urgent
        }
        
        return JsonResponse({'success': True, 'data': data})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
