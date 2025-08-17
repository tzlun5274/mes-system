"""
生產中監控子模組 - 應用配置
"""

from django.apps import AppConfig


class ProductionMonitoringConfig(AppConfig):
    """
    生產中監控子模組配置
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder.production_monitoring'
    verbose_name = '生產中監控'
    
    def ready(self):
        """應用啟動時的初始化"""
        import logging
        logger = logging.getLogger('workorder')
        logger.info('生產中監控子模組已載入') 