"""
分頁相關的 Django 模板標籤
提供全局共用的分頁功能
"""
from django import template
from django.utils.safestring import mark_safe
from urllib.parse import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def build_pagination_url(context, page_number, **kwargs):
    """
    建立分頁 URL，保留現有的查詢參數
    
    使用方式：
    {% build_pagination_url 2 equipment=1 status='pending' %}
    """
    # 獲取當前請求的所有參數
    request = context.get('request')
    if not request:
        return f"?page={page_number}"
    
    # 複製現有參數
    params = request.GET.copy()
    
    # 更新頁碼
    params['page'] = page_number
    
    # 更新額外參數
    for key, value in kwargs.items():
        if value is not None and value != '':
            params[key] = value
        elif key in params:
            del params[key]
    
    # 建立 URL
    return f"?{params.urlencode()}"


@register.simple_tag(takes_context=True)
def get_pagination_info(context, page_obj):
    """
    獲取分頁資訊
    
    使用方式：
    {% get_pagination_info page_obj as pagination_info %}
    """
    if not page_obj or not hasattr(page_obj, 'paginator'):
        return {
            'current_page': 1,
            'total_pages': 1,
            'total_count': 0,
            'has_previous': False,
            'has_next': False,
            'previous_page_number': None,
            'next_page_number': None,
        }
    
    return {
        'current_page': page_obj.number,
        'total_pages': page_obj.paginator.num_pages,
        'total_count': page_obj.paginator.count,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
    }


@register.filter
def pagination_range(page_obj, window=3):
    """
    獲取分頁範圍，用於顯示頁碼
    
    使用方式：
    {% for num in page_obj|pagination_range:3 %}
    """
    if not page_obj or not hasattr(page_obj, 'paginator'):
        return []
    
    current = page_obj.number
    total = page_obj.paginator.num_pages
    
    start = max(1, current - window)
    end = min(total, current + window)
    
    return range(start, end + 1)


@register.simple_tag(takes_context=True)
def render_pagination(context, page_obj, extra_params=None):
    """
    渲染完整的分頁組件
    
    使用方式：
    {% render_pagination page_obj %}
    或
    {% render_pagination page_obj 'equipment=1&status=pending' %}
    """
    if not page_obj or not hasattr(page_obj, 'paginator'):
        return mark_safe('<p class="text-muted text-center">無分頁資料</p>')
    
    # 建立分頁 HTML
    html_parts = []
    
    # 分頁資訊
    html_parts.append(f'''
    <div class="row mt-3">
        <div class="col-12 text-center">
            <p class="text-muted">
                顯示第 {page_obj.number} 頁，共 {page_obj.paginator.num_pages} 頁
                (總計 {page_obj.paginator.count} 筆記錄)
            </p>
        </div>
    </div>
    ''')
    
    # 分頁導航
    if page_obj.paginator.num_pages > 1:
        nav_html = ['<nav aria-label="分頁導航" class="mt-4">', '<ul class="pagination justify-content-center mb-0">']
        
        # 第一頁
        if page_obj.has_previous():
            first_url = f"?page=1{('&' + extra_params) if extra_params else ''}"
            nav_html.append(f'''
            <li class="page-item">
                <a class="page-link" href="{first_url}" title="第一頁">
                    <i class="fas fa-angle-double-left"></i>
                    <span class="d-none d-sm-inline">第一頁</span>
                </a>
            </li>
            ''')
        
        # 上一頁
        if page_obj.has_previous():
            prev_url = f"?page={page_obj.previous_page_number}{('&' + extra_params) if extra_params else ''}"
            nav_html.append(f'''
            <li class="page-item">
                <a class="page-link" href="{prev_url}" title="上一頁">
                    <i class="fas fa-angle-left"></i>
                    <span class="d-none d-sm-inline">上一頁</span>
                </a>
            </li>
            ''')
        else:
            nav_html.append('''
            <li class="page-item disabled">
                <span class="page-link text-muted">
                    <i class="fas fa-angle-left"></i>
                    <span class="d-none d-sm-inline">上一頁</span>
                </span>
            </li>
            ''')
        
        # 頁碼
        for num in page_obj.paginator.page_range:
            if page_obj.number == num:
                nav_html.append(f'<li class="page-item active"><span class="page-link">{num}</span></li>')
            elif num > page_obj.number - 3 and num < page_obj.number + 3:
                page_url = f"?page={num}{('&' + extra_params) if extra_params else ''}"
                nav_html.append(f'<li class="page-item"><a class="page-link" href="{page_url}">{num}</a></li>')
        
        # 下一頁
        if page_obj.has_next():
            next_url = f"?page={page_obj.next_page_number}{('&' + extra_params) if extra_params else ''}"
            nav_html.append(f'''
            <li class="page-item">
                <a class="page-link" href="{next_url}" title="下一頁">
                    <span class="d-none d-sm-inline">下一頁</span>
                    <i class="fas fa-angle-right"></i>
                </a>
            </li>
            ''')
        else:
            nav_html.append('''
            <li class="page-item disabled">
                <span class="page-link text-muted">
                    <span class="d-none d-sm-inline">下一頁</span>
                    <i class="fas fa-angle-right"></i>
                </span>
            </li>
            ''')
        
        # 最後一頁
        if page_obj.has_next():
            last_url = f"?page={page_obj.paginator.num_pages}{('&' + extra_params) if extra_params else ''}"
            nav_html.append(f'''
            <li class="page-item">
                <a class="page-link" href="{last_url}" title="最後一頁">
                    <span class="d-none d-sm-inline">最後一頁</span>
                    <i class="fas fa-angle-double-right"></i>
                </a>
            </li>
            ''')
        
        nav_html.append('</ul></nav>')
        html_parts.append(''.join(nav_html))
    
    return mark_safe(''.join(html_parts)) 