"""
報工管理子模組 - 應用程式設定
"""

from django.apps import AppConfig


class WorkOrderReportingConfig(AppConfig):
    """
    報工管理子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.workorder_reporting'
    verbose_name = '報工管理' 