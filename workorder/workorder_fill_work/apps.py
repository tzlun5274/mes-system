"""
填報作業管理子模組 - 應用程式配置
負責填報作業的 Django 應用程式配置
"""

from django.apps import AppConfig


class FillWorkConfig(AppConfig):
    """
    填報作業管理子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.workorder_fill_work'
    verbose_name = '填報作業管理'
    
    def ready(self):
        """應用程式準備就緒時的初始化"""
        import workorder.workorder_fill_work.signals 