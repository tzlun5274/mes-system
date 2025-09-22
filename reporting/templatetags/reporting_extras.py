"""
報表模組自定義模板標籤
"""

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    從字典中取得指定鍵的值
    用法: {{ dictionary|get_item:key }}
    """
    return dictionary.get(key)
