from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


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


class UserWorkPermission(models.Model):
    """
    使用者工作權限模型
    定義每個使用者可以針對哪些作業員和工序進行填報報工
    """
    
    # 關聯使用者
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name="使用者",
        related_name="work_permissions"
    )
    
    # 作業員編號（支援多個，用逗號分隔）
    operator_codes = models.TextField(
        verbose_name="作業員編號",
        help_text="可操作的作業員編號，多個用逗號分隔，留空表示可操作所有作業員"
    )
    
    # 工序名稱（支援多個，用逗號分隔）
    process_names = models.TextField(
        verbose_name="工序名稱",
        help_text="可操作的工序名稱，多個用逗號分隔，留空表示可操作所有工序"
    )
    
    # 權限類型
    PERMISSION_TYPES = [
        ('fill_work', '填報報工'),
        ('onsite_reporting', '現場報工'),
        ('both', '填報報工 + 現場報工'),
    ]
    
    permission_type = models.CharField(
        max_length=20,
        choices=PERMISSION_TYPES,
        default='both',
        verbose_name="權限類型"
    )
    
    # 是否啟用
    is_active = models.BooleanField(
        default=True,
        verbose_name="啟用狀態"
    )
    
    # 備註
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="備註"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="建立者",
        related_name="created_work_permissions"
    )
    
    class Meta:
        verbose_name = "使用者工作權限"
        verbose_name_plural = "使用者工作權限"
        db_table = "system_user_work_permission"
        unique_together = ['user', 'permission_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_permission_type_display()}"
    
    def get_operator_codes_list(self):
        """獲取作業員編號列表"""
        if not self.operator_codes:
            return []
        return [code.strip() for code in self.operator_codes.split(',') if code.strip()]
    
    def get_process_names_list(self):
        """獲取工序名稱列表"""
        if not self.process_names:
            return []
        return [name.strip() for name in self.process_names.split(',') if name.strip()]
    
    def can_operate_operator(self, operator_code):
        """檢查是否可以操作指定作業員"""
        if not self.is_active:
            return False
        
        # 如果沒有設定作業員限制，表示可以操作所有作業員
        if not self.operator_codes:
            return True
        
        return operator_code in self.get_operator_codes_list()
    
    def can_operate_process(self, process_name):
        """檢查是否可以操作指定工序"""
        if not self.is_active:
            return False
        
        # 如果沒有設定工序限制，表示可以操作所有工序
        if not self.process_names:
            return True
        
        return process_name in self.get_process_names_list()
    
    def can_fill_work(self):
        """檢查是否可以進行填報報工"""
        return self.is_active and self.permission_type in ['fill_work', 'both']
    
    def can_onsite_reporting(self):
        """檢查是否可以進行現場報工"""
        return self.is_active and self.permission_type in ['onsite_reporting', 'both']
    
    @classmethod
    def get_user_permission(cls, user, permission_type='both'):
        """獲取使用者的工作權限"""
        try:
            return cls.objects.get(user=user, permission_type=permission_type, is_active=True)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def check_user_permission(cls, user, operator_code=None, process_name=None, permission_type='both'):
        """檢查使用者是否有權限進行操作"""
        permission = cls.get_user_permission(user, permission_type)
        
        if not permission:
            return False
        
        # 檢查作業員權限
        if operator_code and not permission.can_operate_operator(operator_code):
            return False
        
        # 檢查工序權限
        if process_name and not permission.can_operate_process(process_name):
            return False
        
        return True


# 完工判斷設定已整合到 workorder.workorder_erp.models.SystemConfig
# 使用現有的 SystemConfig 模型來管理完工判斷相關設定












