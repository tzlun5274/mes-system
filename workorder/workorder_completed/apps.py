"""
已完工工單管理子模組配置
負責管理已完成工單的資料儲存、查詢和報表功能
"""

from django.apps import AppConfig


class WorkOrderCompletedConfig(AppConfig):
    """已完工工單管理子模組配置類別"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.workorder_completed'
    verbose_name = '已完工工單管理'
    
    def ready(self):
        """應用程式準備就緒時的初始化操作"""
        try:
            import workorder.workorder_completed.signals
        except ImportError:
            pass
