"""
公司製造命令管理子模組 - 應用程式設定
"""

from django.apps import AppConfig


class ManufacturingOrderConfig(AppConfig):
    """
    公司製造命令管理子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.manufacturing_order'
    verbose_name = '公司製造命令管理' 