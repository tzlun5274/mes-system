from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class EmailConfig(models.Model):
    """郵件主機設定"""
    email_host = models.CharField(
        max_length=100, 
        blank=True, 
        default="",
        verbose_name=_("郵件主機")
    )
    email_port = models.IntegerField(
        default=25,
        verbose_name=_("郵件埠號")
    )
    email_use_tls = models.BooleanField(
        default=True,
        verbose_name=_("使用TLS加密")
    )
    email_host_user = models.CharField(
        max_length=100, 
        blank=True, 
        default="",
        verbose_name=_("郵件帳號")
    )
    email_host_password = models.CharField(
        max_length=100, 
        blank=True, 
        default="",
        verbose_name=_("郵件密碼")
    )
    default_from_email = models.EmailField(
        max_length=254, 
        blank=True, 
        default="",
        verbose_name=_("預設寄件者郵箱")
    )

    class Meta:
        default_permissions = ()  # 禁用默認權限
        verbose_name = "郵件主機設定"
        verbose_name_plural = "郵件主機設定"

    def __str__(self):
        return "郵件主機設定"


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
        help_text="每天執行備份的時間",
        default="02:00:00"
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


class AutoApprovalSettings(models.Model):
    """自動審核設定"""
    is_enabled = models.BooleanField(
        default=False,
        verbose_name="啟用自動審核",
        help_text="啟用後，符合條件的報工將自動審核通過"
    )
    approval_conditions = models.JSONField(
        default=dict,
        verbose_name="審核條件",
        help_text="自動審核的條件設定"
    )
    auto_approve_work_hours = models.BooleanField(
        default=True,
        verbose_name="自動審核工作時數",
        help_text="工作時數在正常範圍內時自動審核"
    )
    max_work_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=12.0,
        verbose_name="最大工作時數",
        help_text="超過此時數的報工需要人工審核"
    )
    auto_approve_defect_rate = models.BooleanField(
        default=True,
        verbose_name="自動審核不良率",
        help_text="不良率在正常範圍內時自動審核"
    )
    max_defect_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.0,
        verbose_name="最大不良率(%)",
        help_text="超過此不良率的報工需要人工審核"
    )
    auto_approve_overtime = models.BooleanField(
        default=False,
        verbose_name="自動審核加班",
        help_text="加班時數在正常範圍內時自動審核"
    )
    max_overtime_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=4.0,
        verbose_name="最大加班時數",
        help_text="超過此時數的加班需要人工審核"
    )
    exclude_operators = models.JSONField(
        default=list,
        verbose_name="排除作業員",
        help_text="這些作業員的報工不會自動審核"
    )
    exclude_processes = models.JSONField(
        default=list,
        verbose_name="排除工序",
        help_text="這些工序的報工不會自動審核"
    )
    notification_enabled = models.BooleanField(
        default=True,
        verbose_name="啟用通知",
        help_text="自動審核後發送通知給主管"
    )
    notification_recipients = models.JSONField(
        default=list,
        verbose_name="通知收件人",
        help_text="自動審核通知的收件人清單"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "自動審核設定"
        verbose_name_plural = "自動審核設定"

    def __str__(self):
        return f"自動審核設定 - {'啟用' if self.is_enabled else '停用'}"

    def get_approval_conditions_summary(self):
        """取得審核條件摘要"""
        conditions = []
        if self.auto_approve_work_hours:
            conditions.append(f"工作時數 ≤ {self.max_work_hours}小時")
        if self.auto_approve_defect_rate:
            conditions.append(f"不良率 ≤ {self.max_defect_rate}%")
        if self.auto_approve_overtime:
            conditions.append(f"加班時數 ≤ {self.max_overtime_hours}小時")
        return "、".join(conditions) if conditions else "無自動審核條件"


class ScheduledTask(models.Model):
    """定時任務設定"""
    TASK_TYPES = [
        ('auto_approve', '自動審核'),
        ('workorder_analysis', '工單分析'),
        ('data_backup', '資料備份'),
        ('report_generation', '報表生成'),
        ('data_cleanup', '資料清理'),
    ]
    
    # 執行類型選項
    EXECUTION_TYPE_CHOICES = [
        ('interval', '間隔執行'),
        ('fixed_time', '固定時間'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="任務名稱")
    task_type = models.CharField(max_length=50, choices=TASK_TYPES, verbose_name="任務類型")
    task_function = models.CharField(max_length=200, verbose_name="任務函數")
    
    execution_type = models.CharField(
        max_length=20,
        choices=EXECUTION_TYPE_CHOICES,
        default='interval',
        verbose_name="執行類型",
        help_text="選擇執行方式：間隔執行或固定時間執行"
    )
    
    # 間隔設定
    interval_minutes = models.IntegerField(
        default=30,
        verbose_name="間隔分鐘數",
        help_text="每多少分鐘執行一次（僅適用於間隔執行）"
    )
    
    # 固定時間設定
    fixed_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="固定執行時間",
        help_text="每天固定時間執行（僅適用於固定時間執行）"
    )
    
    is_enabled = models.BooleanField(default=True, verbose_name="啟用狀態")
    description = models.TextField(blank=True, verbose_name="任務描述")
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="最後執行時間")
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name="下次執行時間")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "定時任務"
        verbose_name_plural = "定時任務"
        db_table = 'system_scheduled_task'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_task_type_display()})"

    def get_schedule_description(self):
        """取得定時描述"""
        if self.execution_type == 'fixed_time':
            if self.fixed_time:
                return f"每天 {self.fixed_time.strftime('%H:%M')} 執行"
            else:
                return "未設定固定時間"
        else:
            if self.interval_minutes:
                if self.interval_minutes < 60:
                    return f"每 {self.interval_minutes} 分鐘執行一次"
                elif self.interval_minutes == 60:
                    return "每小時執行一次"
                else:
                    hours = self.interval_minutes // 60
                    minutes = self.interval_minutes % 60
                    if minutes == 0:
                        return f"每 {hours} 小時執行一次"
                    else:
                        return f"每 {hours} 小時 {minutes} 分鐘執行一次"
            else:
                return "未設定間隔"

    def clean(self):
        """驗證模型"""
        from django.core.exceptions import ValidationError
        
        if self.execution_type == 'interval':
            if not self.interval_minutes or self.interval_minutes <= 0:
                raise ValidationError("間隔分鐘數必須大於0")
        elif self.execution_type == 'fixed_time':
            if not self.fixed_time:
                raise ValidationError("固定時間執行必須設定執行時間")


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








# 完工判斷設定已整合到 workorder.company_order.models.SystemConfig
# 使用現有的 SystemConfig 模型來管理完工判斷相關設定


class CleanupLog(models.Model):
    """清理操作日誌"""
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失敗'),
        ('pending', '執行中'),
    ]
    
    action = models.CharField(max_length=100, verbose_name="操作類型")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name="執行狀態")
    execution_time = models.DateTimeField(auto_now_add=True, verbose_name="執行時間")
    details = models.TextField(blank=True, null=True, verbose_name="執行詳情")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="執行使用者")
    
    class Meta:
        verbose_name = "清理操作日誌"
        verbose_name_plural = "清理操作日誌"
        ordering = ['-execution_time']
    
    def __str__(self):
        return f"{self.action} - {self.get_status_display()} - {self.execution_time.strftime('%Y-%m-%d %H:%M:%S')}"


class AutoApprovalTask(models.Model):
    """自動審核定時任務模型 - 支援多個執行間隔和固定時間執行"""
    
    # 執行類型選項
    EXECUTION_TYPE_CHOICES = [
        ('interval', '間隔執行'),
        ('fixed_time', '固定時間'),
    ]
    
    name = models.CharField(
        max_length=100, 
        verbose_name="任務名稱",
        help_text="為此定時任務設定一個描述性名稱"
    )
    
    execution_type = models.CharField(
        max_length=20,
        choices=EXECUTION_TYPE_CHOICES,
        default='interval',
        verbose_name="執行類型",
        help_text="選擇執行方式：間隔執行或固定時間執行"
    )
    
    interval_minutes = models.IntegerField(
        verbose_name="執行間隔（分鐘）",
        help_text="每多少分鐘執行一次自動審核（僅適用於間隔執行）",
        validators=[MinValueValidator(1), MaxValueValidator(1440)],  # 1分鐘到24小時
        default=30
    )
    
    fixed_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="固定執行時間",
        help_text="每天固定時間執行（僅適用於固定時間執行）"
    )
    
    is_enabled = models.BooleanField(
        default=True,
        verbose_name="啟用狀態",
        help_text="是否啟用此定時任務"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="任務描述",
        help_text="可選的任務描述"
    )
    
    # 執行狀態追蹤
    last_run_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="最後執行時間"
    )
    
    next_run_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="下次執行時間"
    )
    
    execution_count = models.IntegerField(
        default=0,
        verbose_name="執行次數",
        help_text="此任務已執行的總次數"
    )
    
    success_count = models.IntegerField(
        default=0,
        verbose_name="成功次數",
        help_text="此任務成功執行的次數"
    )
    
    error_count = models.IntegerField(
        default=0,
        verbose_name="錯誤次數",
        help_text="此任務執行失敗的次數"
    )
    
    last_error_message = models.TextField(
        blank=True,
        verbose_name="最後錯誤訊息",
        help_text="記錄最後一次執行失敗的錯誤訊息"
    )
    
    # 系統欄位
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="建立時間"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="更新時間"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="建立者",
        related_name='created_auto_approval_tasks'
    )
    
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="更新者",
        related_name='updated_auto_approval_tasks'
    )

    class Meta:
        verbose_name = "自動審核定時任務"
        verbose_name_plural = "自動審核定時任務"
        db_table = 'system_auto_approval_task'
        ordering = ['-created_at']
        unique_together = ['name']  # 任務名稱必須唯一

    def __str__(self):
        status = "啟用" if self.is_enabled else "停用"
        if self.execution_type == 'fixed_time':
            return f"{self.name} (每天 {self.fixed_time.strftime('%H:%M')} - {status})"
        else:
            return f"{self.name} (每{self.interval_minutes}分鐘 - {status})"

    def get_interval_display(self):
        """取得間隔顯示文字"""
        if self.execution_type == 'fixed_time':
            return f"每天 {self.fixed_time.strftime('%H:%M')}"
        else:
            if self.interval_minutes < 60:
                return f"每 {self.interval_minutes} 分鐘"
            elif self.interval_minutes == 60:
                return "每小時"
            else:
                hours = self.interval_minutes // 60
                minutes = self.interval_minutes % 60
                if minutes == 0:
                    return f"每 {hours} 小時"
                else:
                    return f"每 {hours} 小時 {minutes} 分鐘"

    def get_status_display(self):
        """取得狀態顯示"""
        if not self.is_enabled:
            return "停用"
        elif self.last_run_at:
            return f"啟用 (最後執行: {self.last_run_at.strftime('%Y-%m-%d %H:%M')})"
        else:
            return "啟用 (尚未執行)"

    def get_success_rate(self):
        """取得成功率"""
        if self.execution_count == 0:
            return 0
        return round((self.success_count / self.execution_count) * 100, 1)

    def clean(self):
        """驗證模型"""
        from django.core.exceptions import ValidationError
        
        if not self.name:
            raise ValidationError("任務名稱不能為空")
        
        if self.execution_type == 'interval':
            if self.interval_minutes < 1:
                raise ValidationError("執行間隔必須大於0分鐘")
            
            if self.interval_minutes > 1440:
                raise ValidationError("執行間隔不能超過1440分鐘（24小時）")
        elif self.execution_type == 'fixed_time':
            if not self.fixed_time:
                raise ValidationError("固定時間執行必須設定執行時間")

    def save(self, *args, **kwargs):
        """儲存時自動設定描述"""
        if not self.description:
            self.description = f"自動審核定時任務 - {self.get_interval_display()}"
        super().save(*args, **kwargs)


class OrderSyncSettings(models.Model):
    """
    訂單同步設定：管理訂單資料的自動同步配置
    """
    
    # 同步設定
    sync_enabled = models.BooleanField(default=True, verbose_name="啟用自動同步")
    sync_interval_minutes = models.IntegerField(default=30, verbose_name="同步間隔（分鐘）")
    last_sync_time = models.DateTimeField(null=True, blank=True, verbose_name="上次同步時間")
    last_sync_status = models.CharField(max_length=20, default="未執行", verbose_name="上次同步狀態")
    last_sync_message = models.TextField(blank=True, verbose_name="上次同步訊息")
    
    # 清理設定
    cleanup_enabled = models.BooleanField(default=True, verbose_name="啟用自動清理")
    cleanup_interval_hours = models.IntegerField(default=24, verbose_name="清理間隔（小時）")
    cleanup_retention_days = models.IntegerField(default=90, verbose_name="資料保留天數")
    last_cleanup_time = models.DateTimeField(null=True, blank=True, verbose_name="上次清理時間")
    last_cleanup_count = models.IntegerField(default=0, verbose_name="上次清理數量")
    
    # 狀態更新設定
    status_update_enabled = models.BooleanField(default=True, verbose_name="啟用狀態更新")
    status_update_interval_minutes = models.IntegerField(default=60, verbose_name="狀態更新間隔（分鐘）")
    last_status_update_time = models.DateTimeField(null=True, blank=True, verbose_name="上次狀態更新時間")
    
    # 系統資訊
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "訂單同步設定"
        verbose_name_plural = "訂單同步設定"
        db_table = 'system_order_sync_settings'
    
    def __str__(self):
        return f"訂單同步設定 (ID: {self.id})"
    
    def get_sync_status_display(self):
        """取得同步狀態顯示文字"""
        status_map = {
            "未執行": "未執行",
            "執行中": "執行中",
            "成功": "成功",
            "失敗": "失敗"
        }
        return status_map.get(self.last_sync_status, self.last_sync_status)
    
    def get_sync_status_class(self):
        """取得同步狀態的 CSS 類別"""
        status_class_map = {
            "未執行": "text-muted",
            "執行中": "text-warning",
            "成功": "text-success",
            "失敗": "text-danger"
        }
        return status_class_map.get(self.last_sync_status, "text-muted")


class OrderSyncLog(models.Model):
    """
    訂單同步日誌：記錄每次同步的詳細資訊
    """
    
    SYNC_TYPES = [
        ('sync', '資料同步'),
        ('cleanup', '資料清理'),
        ('status_update', '狀態更新'),
    ]
    
    STATUS_CHOICES = [
        ('running', '執行中'),
        ('success', '成功'),
        ('failed', '失敗'),
    ]
    
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPES, verbose_name="同步類型")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="執行狀態")
    message = models.TextField(blank=True, verbose_name="執行訊息")
    details = models.JSONField(default=dict, verbose_name="詳細資訊")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="開始時間")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成時間")
    duration_seconds = models.FloatField(null=True, blank=True, verbose_name="執行時間（秒）")
    
    class Meta:
        verbose_name = "訂單同步日誌"
        verbose_name_plural = "訂單同步日誌"
        db_table = 'system_order_sync_log'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_status_display()} ({self.started_at})"
    
    def get_duration_display(self):
        """取得執行時間顯示"""
        if self.duration_seconds is None:
            return "未完成"
        
        if self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f} 秒"
        elif self.duration_seconds < 3600:
            minutes = self.duration_seconds / 60
            return f"{minutes:.1f} 分鐘"
        else:
            hours = self.duration_seconds / 3600
            return f"{hours:.1f} 小時"


class UserPermissionDetail(models.Model):
    """使用者權限細分設定"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者")
    
    # 作業員權限細分
    can_operate_all_operators = models.BooleanField(default=True, verbose_name="可操作全部作業員")
    allowed_operators = models.JSONField(default=list, blank=True, verbose_name="可操作作業員列表")
    
    # 工序權限細分
    can_operate_all_processes = models.BooleanField(default=True, verbose_name="可操作全部工序")
    allowed_processes = models.JSONField(default=list, blank=True, verbose_name="可操作工序列表")
    
    # 設備權限細分
    can_operate_all_equipments = models.BooleanField(default=True, verbose_name="可操作全部設備")
    allowed_equipments = models.JSONField(default=list, blank=True, verbose_name="可操作設備列表")
    
    # 報工類型權限
    can_fill_work = models.BooleanField(default=True, verbose_name="可填報報工")
    can_onsite_reporting = models.BooleanField(default=True, verbose_name="可現場報工")
    can_smt_reporting = models.BooleanField(default=False, verbose_name="可SMT報工")
    
    # 模組訪問權限
    can_access_equip = models.BooleanField(default=True, verbose_name="可訪問設備管理")
    can_access_workorder = models.BooleanField(default=True, verbose_name="可訪問工單管理")
    can_access_quality = models.BooleanField(default=True, verbose_name="可訪問品質管理")
    can_access_material = models.BooleanField(default=True, verbose_name="可訪問物料管理")
    can_access_scheduling = models.BooleanField(default=True, verbose_name="可訪問排程管理")
    can_access_process = models.BooleanField(default=True, verbose_name="可訪問製程管理")
    can_access_reporting = models.BooleanField(default=True, verbose_name="可訪問報表管理")
    can_access_kanban = models.BooleanField(default=True, verbose_name="可訪問看板管理")
    can_access_ai = models.BooleanField(default=True, verbose_name="可訪問AI管理")
    
    # 功能級權限
    can_view = models.BooleanField(default=True, verbose_name="可查看")
    can_add = models.BooleanField(default=True, verbose_name="可新增")
    can_edit = models.BooleanField(default=True, verbose_name="可編輯")
    can_delete = models.BooleanField(default=False, verbose_name="可刪除")
    can_export = models.BooleanField(default=True, verbose_name="可匯出")
    can_import = models.BooleanField(default=False, verbose_name="可匯入")
    can_approve = models.BooleanField(default=False, verbose_name="可審核")
    
    # 資料級權限
    DATA_SCOPE_CHOICES = [
        ('own', '自己的資料'),
        ('department', '部門資料'),
        ('company', '公司資料'),
        ('all', '所有資料'),
    ]
    data_scope = models.CharField(
        max_length=20, 
        choices=DATA_SCOPE_CHOICES, 
        default='own', 
        verbose_name="資料範圍"
    )
    
    # 特殊權限
    can_manage_users = models.BooleanField(default=False, verbose_name="可管理使用者")
    can_manage_permissions = models.BooleanField(default=False, verbose_name="可管理權限")
    can_view_logs = models.BooleanField(default=False, verbose_name="可查看日誌")
    can_system_config = models.BooleanField(default=False, verbose_name="可系統設定")
    
    # 時間限制權限
    can_access_24h = models.BooleanField(default=True, verbose_name="24小時存取權限")
    can_access_worktime = models.BooleanField(default=True, verbose_name="工作時間存取權限")
    work_start_time = models.TimeField(null=True, blank=True, verbose_name="工作開始時間")
    work_end_time = models.TimeField(null=True, blank=True, verbose_name="工作結束時間")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")
    
    class Meta:
        verbose_name = "使用者權限細分"
        verbose_name_plural = "使用者權限細分"
        unique_together = ['user']
        db_table = 'system_user_permission_detail'
    
    def __str__(self):
        return f"{self.user.username} 的權限細分設定"
    
    def get_operator_permissions(self):
        """獲取作業員權限描述"""
        if self.can_operate_all_operators:
            return "全部作業員"
        elif self.allowed_operators:
            return f"指定作業員 ({len(self.allowed_operators)} 個)"
        else:
            return "無權限"
    
    def get_process_permissions(self):
        """獲取工序權限描述"""
        if self.can_operate_all_processes:
            return "全部工序"
        elif self.allowed_processes:
            return f"指定工序 ({len(self.allowed_processes)} 個)"
        else:
            return "無權限"
    
    def get_equipment_permissions(self):
        """獲取設備權限描述"""
        if self.can_operate_all_equipments:
            return "全部設備"
        elif self.allowed_equipments:
            return f"指定設備 ({len(self.allowed_equipments)} 個)"
        else:
            return "無權限"
    
    def get_permission_summary(self):
        """獲取權限摘要"""
        summary = []
        if self.can_access_equip:
            summary.append("設備管理")
        if self.can_access_workorder:
            summary.append("工單管理")
        if self.can_access_quality:
            summary.append("品質管理")
        if self.can_access_material:
            summary.append("物料管理")
        if self.can_access_scheduling:
            summary.append("排程管理")
        if self.can_access_process:
            summary.append("製程管理")
        if self.can_access_reporting:
            summary.append("報表管理")
        if self.can_access_kanban:
            summary.append("看板管理")
        if self.can_access_ai:
            summary.append("AI管理")
        
        return ", ".join(summary) if summary else "無模組權限"
    
    def has_permission(self, permission_name):
        """檢查是否有特定權限"""
        permission_map = {
            'view': self.can_view,
            'add': self.can_add,
            'edit': self.can_edit,
            'delete': self.can_delete,
            'export': self.can_export,
            'import': self.can_import,
            'approve': self.can_approve,
        }
        return permission_map.get(permission_name, False)


class UserWorkPermission(models.Model):
    """用戶工作權限細分表 - 控制報工時的操作範圍"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="用戶")
    
    # 作業員權限控制
    can_operate_all_operators = models.BooleanField(default=True, verbose_name="可操作所有作業員")
    allowed_operators = models.JSONField(default=list, blank=True, verbose_name="允許的作業員ID列表")
    
    # 工序權限控制
    can_operate_all_processes = models.BooleanField(default=True, verbose_name="可操作所有工序")
    allowed_processes = models.JSONField(default=list, blank=True, verbose_name="允許的工序ID列表")
    
    # 設備權限控制
    can_operate_all_equipments = models.BooleanField(default=True, verbose_name="可操作所有設備")
    allowed_equipments = models.JSONField(default=list, blank=True, verbose_name="允許的設備ID列表")
    
    # 報工功能權限
    can_fill_work = models.BooleanField(default=True, verbose_name="可進行補登填報")
    can_onsite_reporting = models.BooleanField(default=True, verbose_name="可進行現場報工")
    can_smt_reporting = models.BooleanField(default=True, verbose_name="可進行SMT報工")
    
    # 資料範圍控制
    data_scope = models.CharField(
        max_length=20, 
        choices=[
            ('all', '全部資料'),
            ('own', '僅自己的資料'),
            ('department', '部門資料'),
            ('custom', '自定義範圍')
        ],
        default='all',
        verbose_name="資料範圍"
    )
    
    # 操作權限
    can_view = models.BooleanField(default=True, verbose_name="可查看")
    can_add = models.BooleanField(default=True, verbose_name="可新增")
    can_edit = models.BooleanField(default=True, verbose_name="可編輯")
    can_delete = models.BooleanField(default=False, verbose_name="可刪除")
    
    # 審核權限
    can_approve = models.BooleanField(default=False, verbose_name="可審核")
    can_reject = models.BooleanField(default=False, verbose_name="可駁回")
    
    # 特殊權限
    can_override_limits = models.BooleanField(default=False, verbose_name="可超越限制")
    can_export_data = models.BooleanField(default=True, verbose_name="可匯出資料")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "用戶工作權限"
        verbose_name_plural = "用戶工作權限"
        db_table = 'system_user_work_permission'

    def __str__(self):
        return f"{self.user.username} 的工作權限"

    def get_allowed_operators_display(self):
        """獲取允許的作業員顯示名稱"""
        if self.can_operate_all_operators:
            return "所有作業員"
        
        try:
            from process.models import Operator
            operators = Operator.objects.filter(id__in=self.allowed_operators)
            return ", ".join([op.name for op in operators])
        except:
            return "無權限"
    
    def get_allowed_processes_display(self):
        """獲取允許的工序顯示名稱"""
        if self.can_operate_all_processes:
            return "所有工序"
        
        try:
            from process.models import ProcessName
            processes = ProcessName.objects.filter(id__in=self.allowed_processes)
            return ", ".join([proc.name for proc in processes])
        except:
            return "無權限"
    
    def get_allowed_equipments_display(self):
        """獲取允許的設備顯示名稱"""
        if self.can_operate_all_equipments:
            return "所有設備"
        
        try:
            from equip.models import Equipment
            equipments = Equipment.objects.filter(id__in=self.allowed_equipments)
            return ", ".join([eq.name for eq in equipments])
        except:
            return "無權限"

    def check_operator_permission(self, operator_id):
        """檢查是否有操作指定作業員的權限"""
        if self.can_operate_all_operators:
            return True
        return operator_id in self.allowed_operators

    def check_process_permission(self, process_id):
        """檢查是否有操作指定工序的權限"""
        if self.can_operate_all_processes:
            return True
        return process_id in self.allowed_processes

    def check_equipment_permission(self, equipment_id):
        """檢查是否有操作指定設備的權限"""
        if self.can_operate_all_equipments:
            return True
        return equipment_id in self.allowed_equipments

    def get_permission_summary(self):
        """獲取權限摘要"""
        summary = []
        
        if self.can_fill_work:
            summary.append("補登填報")
        if self.can_onsite_reporting:
            summary.append("現場報工")
        if self.can_smt_reporting:
            summary.append("SMT報工")
        
        summary.append(f"作業員: {self.get_allowed_operators_display()}")
        summary.append(f"工序: {self.get_allowed_processes_display()}")
        summary.append(f"設備: {self.get_allowed_equipments_display()}")
        
        return " | ".join(summary)












