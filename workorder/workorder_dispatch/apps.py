"""
派工單管理子模組 - 應用程式設定
"""

from django.apps import AppConfig


class WorkOrderDispatchConfig(AppConfig):
    """
    派工單管理子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.workorder_dispatch'
    verbose_name = '派工單管理' 