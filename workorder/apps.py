from django.apps import AppConfig


class WorkorderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workorder'
    verbose_name = '工單管理'

    def ready(self):
        """
        應用程式啟動時執行
        註冊信號處理器
        """
        try:
            # 註冊完工觸發信號
            from .signals.completion_trigger_signals import register_completion_trigger_signals
            register_completion_trigger_signals()
            
            # 註冊工單狀態信號
            from .signals.workorder_status_signals import register_workorder_status_signals
            register_workorder_status_signals()
            
            # 載入填報作業信號處理器（自動觸發完工判斷）
            import workorder.fill_work.signals
            
            # 載入現場報工信號處理器
            import workorder.onsite_reporting.signals
            
            # 註冊資料轉移信號
            from .signals.data_transfer_signals import register_data_transfer_signals
            register_data_transfer_signals()
            
        except Exception as e:
            # 避免在遷移時出現錯誤
            pass
