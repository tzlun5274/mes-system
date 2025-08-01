from django.apps import AppConfig


class SupervisorConfig(AppConfig):
    """主管功能子模組配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.supervisor'
    verbose_name = '主管功能' 