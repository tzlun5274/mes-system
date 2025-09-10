"""
工序模組的模板標籤
提供作業員技能查詢等功能
"""

from django import template
from ..models import OperatorSkill

register = template.Library()


@register.filter
def get_operator_skills(operator):
    """
    取得作業員的技能列表
    參數：operator - Operator 物件
    回傳：OperatorSkill 查詢集
    """
    return OperatorSkill.objects.filter(operator_id=str(operator.id)).order_by('priority')
