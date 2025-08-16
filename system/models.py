from django.db import models
from django.utils import timezone


class EmailConfig(models.Model):
    email_host = models.CharField(max_length=100, blank=True, default="")
    email_port = models.IntegerField(default=25)
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.CharField(max_length=100, blank=True, default="")
    email_host_password = models.CharField(max_length=100, blank=True, default="")
    default_from_email = models.EmailField(max_length=254, blank=True, default="")

    class Meta:
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return "Email Configuration"


class BackupSchedule(models.Model):
    """資料庫備份排程設定"""
    SCHEDULE_CHOICES = [
        ("daily", "每天"),
        ("weekly", "每週"),
        ("monthly", "每月"),
    ]
    
    schedule_type = models.CharField(
        max_length=10, 
        choices=SCHEDULE_CHOICES, 
        default="daily", 
        verbose_name="備份頻率"
    )
    backup_time = models.TimeField(
        verbose_name="備份時間", 
        help_text="每天執行備份的時間"
    )
    retention_days = models.IntegerField(
        default=30, 
        verbose_name="保留天數", 
        help_text="備份檔案保留的天數"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="啟用備份"
    )
    last_backup = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="最後備份時間"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "備份排程設定"
        verbose_name_plural = "備份排程設定"

    def __str__(self):
        return f"{self.get_schedule_type_display()} - {self.backup_time}"


class OperationLogConfig(models.Model):
    """操作日誌設定"""
    log_level = models.CharField(
        max_length=20,
        choices=[
            ("DEBUG", "DEBUG"),
            ("INFO", "INFO"),
            ("WARNING", "WARNING"),
            ("ERROR", "ERROR"),
        ],
        default="INFO",
        verbose_name="日誌等級"
    )
    retention_days = models.IntegerField(
        default=90,
        verbose_name="保留天數",
        help_text="操作日誌保留的天數"
    )
    max_file_size = models.IntegerField(
        default=10,
        verbose_name="最大檔案大小(MB)",
        help_text="單個日誌檔案的最大大小"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="啟用日誌記錄"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "操作日誌設定"
        verbose_name_plural = "操作日誌設定"

    def __str__(self):
        return f"日誌等級: {self.log_level} - 保留{self.retention_days}天"


class ReportDataSyncLog(models.Model):
    """報表資料同步日誌"""
    sync_type = models.CharField(max_length=50, verbose_name="同步類型")
    period_start = models.DateField(verbose_name="期間開始")
    period_end = models.DateField(verbose_name="期間結束")
    status = models.CharField(
        max_length=20,
        choices=[
            ("success", "成功"),
            ("failed", "失敗"),
            ("partial", "部分成功"),
        ],
        verbose_name="同步狀態"
    )
    records_processed = models.IntegerField(default=0, verbose_name="處理記錄數")
    records_updated = models.IntegerField(default=0, verbose_name="更新記錄數")
    records_created = models.IntegerField(default=0, verbose_name="新增記錄數")
    error_message = models.TextField(blank=True, verbose_name="錯誤訊息")
    started_at = models.DateTimeField(verbose_name="開始時間")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="完成時間")
    duration_seconds = models.IntegerField(default=0, verbose_name="執行時間(秒)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")

    class Meta:
        verbose_name = "報表資料同步日誌"
        verbose_name_plural = "報表資料同步日誌"
        db_table = 'system_report_data_sync_log'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.sync_type} - {self.period_start} ~ {self.period_end} - {self.get_status_display()}"


class ReportSyncSettings(models.Model):
    """報表同步設定"""
    sync_type = models.CharField(
        max_length=20,
        choices=[
            ("work_time", "工作報表"),
            ("work_order", "工單機種報表"),
            ("personnel", "人員績效報表"),
            ("equipment", "設備效率報表"),
            ("quality", "品質分析報表"),
            ("comprehensive", "綜合分析報表"),
            ("all", "所有報表"),
        ],
        verbose_name="同步類型"
    )
    sync_frequency = models.CharField(
        max_length=10,
        choices=[
            ("hourly", "每小時"),
            ("daily", "每天"),
            ("weekly", "每週"),
            ("monthly", "每月"),
        ],
        default="daily",
        verbose_name="同步頻率"
    )
    sync_time = models.TimeField(
        help_text="每天執行同步的時間",
        verbose_name="同步時間"
    )
    data_source_modules = models.JSONField(
        default=list,
        help_text="要同步的資料來源模組清單",
        verbose_name="資料來源模組"
    )
    include_pending_reports = models.BooleanField(
        default=False,
        help_text="是否包含待核准的報工記錄",
        verbose_name="包含待核准報工"
    )
    include_approved_reports = models.BooleanField(
        default=True,
        help_text="是否包含已核准的報工記錄",
        verbose_name="包含已核准報工"
    )
    auto_sync = models.BooleanField(
        default=True,
        help_text="是否啟用自動同步",
        verbose_name="自動同步"
    )
    sync_retention_days = models.IntegerField(
        default=365,
        help_text="同步資料的保留天數",
        verbose_name="資料保留天數"
    )
    retry_on_failure = models.BooleanField(
        default=True,
        help_text="同步失敗時是否重試",
        verbose_name="失敗重試"
    )
    max_retry_attempts = models.IntegerField(default=3, verbose_name="最大重試次數")
    last_sync_time = models.DateTimeField(
        blank=True, null=True, verbose_name="最後同步時間"
    )
    last_sync_status = models.CharField(
        blank=True,
        max_length=20,
        null=True,
        choices=[
            ("success", "成功"),
            ("failed", "失敗"),
            ("partial", "部分成功"),
        ],
        verbose_name="最後同步狀態"
    )
    is_active = models.BooleanField(default=True, verbose_name="啟用設定")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "報表同步設定"
        verbose_name_plural = "報表同步設定"
        unique_together = [("sync_type", "sync_frequency")]

    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_sync_frequency_display()}"


class CompletionCheckConfig(models.Model):
    """
    完工檢查定時任務配置
    用於管理完工檢查定時任務的運行時間和啟用狀態
    """
    
    # 基本配置
    enabled = models.BooleanField(default=True, verbose_name="啟用狀態")
    interval_minutes = models.IntegerField(
        default=5, 
        verbose_name="檢查間隔（分鐘）",
        help_text="每多少分鐘檢查一次完工狀態"
    )
    
    # 運行時間設定
    start_time = models.TimeField(
        default="08:00",
        verbose_name="開始時間",
        help_text="每日開始檢查的時間"
    )
    end_time = models.TimeField(
        default="18:00", 
        verbose_name="結束時間",
        help_text="每日結束檢查的時間"
    )
    
    # 進階設定
    max_workorders_per_check = models.IntegerField(
        default=100,
        verbose_name="每次檢查最大工單數",
        help_text="每次檢查最多處理多少個工單，避免系統負載過重"
    )
    
    # 通知設定
    enable_notifications = models.BooleanField(
        default=True,
        verbose_name="啟用通知",
        help_text="完工時是否發送通知"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    updated_by = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="最後更新者"
    )
    
    class Meta:
        verbose_name = "完工檢查配置"
        verbose_name_plural = "完工檢查配置"
        db_table = "system_completion_check_config"
    
    def __str__(self):
        return f"完工檢查配置 (間隔{self.interval_minutes}分鐘)"
    
    def save(self, *args, **kwargs):
        """儲存時自動更新定時任務"""
        # 記錄更新者
        if not self.updated_by:
            # 這裡可以從request中獲取當前用戶，暫時設為系統
            self.updated_by = "系統"
        
        super().save(*args, **kwargs)
        
        # 自動更新定時任務設定
        try:
            self._update_periodic_task()
        except Exception as e:
            # 記錄錯誤但不中斷儲存
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"更新定時任務失敗：{str(e)}")
    
    def _update_periodic_task(self):
        """更新定時任務設定"""
        try:
            from django_celery_beat.models import PeriodicTask, IntervalSchedule
            
            # 建立或取得間隔排程
            interval_schedule, created = IntervalSchedule.objects.get_or_create(
                every=self.interval_minutes,
                period=IntervalSchedule.MINUTES,
            )
            
            # 更新現有的完工觸發檢查任務
            task_name = 'workorder.tasks.completion_trigger_task'
            task = PeriodicTask.objects.filter(name='完工觸發檢查任務').first()
            
            if task:
                # 更新現有任務
                task.interval = interval_schedule
                task.enabled = self.enabled
                task.description = f'每 {self.interval_minutes} 分鐘檢查工單完工觸發條件，支援工序記錄和填報記錄雙重累加機制'
                task.save()
            else:
                # 如果任務不存在，建立新任務
                task = PeriodicTask.objects.create(
                    name='完工觸發檢查任務',
                    task=task_name,
                    interval=interval_schedule,
                    enabled=self.enabled,
                    description=f'每 {self.interval_minutes} 分鐘檢查工單完工觸發條件，支援工序記錄和填報記錄雙重累加機制'
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"更新定時任務設定失敗：{str(e)}")
    
    @classmethod
    def get_config(cls):
        """取得配置，如果不存在則建立預設配置"""
        config, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'enabled': True,
                'interval_minutes': 5,
                'start_time': '08:00',
                'end_time': '18:00',
                'max_workorders_per_check': 100,
                'enable_notifications': True,
                'updated_by': '系統'
            }
        )
        return config









