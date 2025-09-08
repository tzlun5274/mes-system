"""
公司生產製造命令管理子模組 - 應用程式設定
"""

from django.apps import AppConfig


class CompanyOrderConfig(AppConfig):
    """
    公司生產製造命令管理子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.company_order'
    verbose_name = '公司生產製造命令管理' 