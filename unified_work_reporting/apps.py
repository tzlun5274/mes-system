"""
統一補登報工應用程式配置
"""

from django.apps import AppConfig


class UnifiedWorkReportingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'unified_work_reporting'
    verbose_name = '統一補登報工管理'
    
    def ready(self):
        """應用程式初始化"""
        import unified_work_reporting.signals
