"""
主管功能子模組應用配置
"""
from django.apps import AppConfig


class SupervisorConfig(AppConfig):
    """主管功能子模組配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.supervisor'
    verbose_name = '主管功能管理'
    
    def ready(self):
        """應用啟動時的初始化"""
        import workorder.supervisor.signals  # noqa 