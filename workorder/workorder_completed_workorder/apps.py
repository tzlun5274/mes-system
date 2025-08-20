"""
已完工工單管理子模組 - 應用程式配置
"""

from django.apps import AppConfig


class WorkorderCompletedWorkorderConfig(AppConfig):
    """已完工工單管理子模組配置"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.workorder_completed_workorder'
    verbose_name = '已完工工單管理'
    
    def ready(self):
        """應用程式準備就緒時的處理"""
        import workorder.workorder_completed_workorder.signals 