"""
填報作業管理子模組 - 應用程式配置
"""

from django.apps import AppConfig


class FillWorkConfig(AppConfig):
    """
    填報作業管理應用程式配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.fill_work'
    verbose_name = '填報作業管理'

    def ready(self):
        """
        應用程式準備就緒時的處理
        """
        import workorder.fill_work.signals  # noqa 