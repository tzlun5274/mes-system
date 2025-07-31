"""
公司製令單管理子模組 - 應用程式設定
"""

from django.apps import AppConfig


class WorkOrderERPConfig(AppConfig):
    """
    公司製令單管理子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.workorder_erp'
    verbose_name = '公司製令單管理' 