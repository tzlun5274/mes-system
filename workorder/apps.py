from django.apps import AppConfig


class WorkorderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workorder"
    
    def ready(self):
        """
        應用啟動時註冊信號處理器
        """
        # 移除信號處理器引用，完工判斷改為輪詢式
# import workorder.signals
