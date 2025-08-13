# -*- coding: utf-8 -*-
"""
模板輔助：權限相關過濾器
提供 has_group 過濾器，用於判斷使用者是否屬於指定群組。
"""
from django import template

register = template.Library()


@register.filter(name="has_group")
def has_group(user, group_name: str) -> bool:
    """回傳使用者是否屬於指定群組。
    使用方式：{% if request.user|has_group:'主管' %} ... {% endif %}
    """
    try:
        if not getattr(user, "is_authenticated", False):
            return False
        return user.groups.filter(name=str(group_name)).exists()
    except Exception:
        return False 