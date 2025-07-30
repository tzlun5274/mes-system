"""
報表模組應用程式設定
提供工作報表、工單報表、工時報表等核心報表功能
"""

from django.apps import AppConfig


class ReportingConfig(AppConfig):
    """報表模組配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reporting'
    verbose_name = '報表管理'
    
    def ready(self):
        """應用程式啟動時的初始化"""
        import reporting.signals  # 註冊信號處理器 