"""
現場報工子模組 - 應用程式配置
負責現場報工功能的應用程式設定
"""

from django.apps import AppConfig


class OnsiteReportingConfig(AppConfig):
    """現場報工應用程式配置"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.workorder_onsite_report'
    verbose_name = '現場報工管理'
    
    def ready(self):
        """應用程式準備就緒時的初始化"""
        try:
            import workorder.workorder_onsite_report.signals
        except ImportError:
            pass 