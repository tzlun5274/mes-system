"""
報表模組視圖 - 佔位符版本
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class ReportingIndexView(LoginRequiredMixin, TemplateView):
    """
    報表管理首頁視圖 - 佔位符
    """
    template_name = 'reporting/index.html'


@login_required
def placeholder_view(request, function_name=None):
    """
    通用佔位符視圖
    """
    return render(request, 'reporting/placeholder.html', {
        'function_name': function_name or '未知功能'
    }) 