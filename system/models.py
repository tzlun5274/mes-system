from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

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
    
    name = models.CharField(max_length=100, verbose_name="任務名稱")
    task_type = models.CharField(max_length=50, choices=TASK_TYPES, verbose_name="任務類型")
    task_function = models.CharField(max_length=200, verbose_name="任務函數")
    
    # 間隔設定
    interval_minutes = models.IntegerField(
        default=30,
        verbose_name="間隔分鐘數",
        help_text="每多少分鐘執行一次"
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
        
        if not self.interval_minutes or self.interval_minutes <= 0:
            raise ValidationError("間隔分鐘數必須大於0")


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
    
    # 設備名稱（支援多個，用逗號分隔）
    equipment_names = models.TextField(
        blank=True,
        null=True,
        verbose_name="設備名稱",
        help_text="可操作的設備名稱，多個用逗號分隔，留空表示可操作所有設備"
    )
    
    # 是否禁用所有設備
    disable_all_equipment = models.BooleanField(
        default=False,
        verbose_name="禁用所有設備",
        help_text="勾選此項將禁用該使用者的所有設備操作權限"
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
    
    def get_equipment_names_list(self):
        """獲取設備名稱列表"""
        if not self.equipment_names:
            return []
        return [name.strip() for name in self.equipment_names.split(',') if name.strip()]
    
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
    
    def can_operate_equipment(self, equipment_name):
        """檢查是否可以操作指定設備"""
        if not self.is_active:
            return False
        
        # 如果禁用所有設備，則無法操作任何設備
        if self.disable_all_equipment:
            return False
        
        # 如果沒有設定設備限制，表示可以操作所有設備
        if not self.equipment_names:
            return True
        
        return equipment_name in self.get_equipment_names_list()
    
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
    def check_user_permission(cls, user, operator_code=None, process_name=None, equipment_name=None, permission_type='both'):
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
        
        # 檢查設備權限
        if equipment_name and not permission.can_operate_equipment(equipment_name):
            return False
        
        return True


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
    """自動審核定時任務模型 - 支援多個執行間隔"""
    
    name = models.CharField(
        max_length=100, 
        verbose_name="任務名稱",
        help_text="為此定時任務設定一個描述性名稱"
    )
    
    interval_minutes = models.IntegerField(
        verbose_name="執行間隔（分鐘）",
        help_text="每多少分鐘執行一次自動審核",
        validators=[MinValueValidator(1), MaxValueValidator(1440)],  # 1分鐘到24小時
        default=30
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
        return f"{self.name} (每{self.interval_minutes}分鐘 - {status})"

    def get_interval_display(self):
        """取得間隔顯示文字"""
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
        
        if self.interval_minutes < 1:
            raise ValidationError("執行間隔必須大於0分鐘")
        
        if self.interval_minutes > 1440:
            raise ValidationError("執行間隔不能超過1440分鐘（24小時）")

    def save(self, *args, **kwargs):
        """儲存時自動設定描述"""
        if not self.description:
            self.description = f"自動審核定時任務 - {self.get_interval_display()}"
        super().save(*args, **kwargs)












