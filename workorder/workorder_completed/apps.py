"""
已完工工單管理子模組 - 應用程式設定
"""

from django.apps import AppConfig


class WorkOrderCompletedConfig(AppConfig):
    """
    已完工工單管理子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.workorder_completed'
    verbose_name = '已完工工單管理' 