"""
MES 工單作業子模組 - 應用程式配置
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MesWorkorderOperationConfig(AppConfig):
    """
    MES 工單作業子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.mes_workorder_operation'
    verbose_name = _('MES 工單作業管理')

    def ready(self):
        """
        應用程式啟動時的初始化
        """
        try:
            import workorder.mes_workorder_operation.signals
        except ImportError:
            pass 