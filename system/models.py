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


class ReportSyncSettings(models.Model):
    """報表資料同步設定"""
    
    # 同步類型
    SYNC_TYPE_CHOICES = [
        ('work_time', '工作時間報表'),
        ('work_order', '工單機種報表'),
        ('personnel', '人員績效報表'),
        ('equipment', '設備效率報表'),
        ('quality', '品質分析報表'),
        ('comprehensive', '綜合分析報表'),
        ('all', '所有報表'),
    ]
    
    # 同步頻率
    SYNC_FREQUENCY_CHOICES = [
        ('hourly', '每小時'),
        ('daily', '每天'),
        ('weekly', '每週'),
        ('monthly', '每月'),
    ]
    
    sync_type = models.CharField(
        max_length=20, 
        choices=SYNC_TYPE_CHOICES, 
        verbose_name="同步類型"
    )
    sync_frequency = models.CharField(
        max_length=10, 
        choices=SYNC_FREQUENCY_CHOICES, 
        default='daily', 
        verbose_name="同步頻率"
    )
    sync_time = models.TimeField(
        verbose_name="同步時間", 
        help_text="每天執行同步的時間"
    )
    
    # 資料來源設定
    data_source_modules = models.JSONField(
        default=list, 
        verbose_name="資料來源模組",
        help_text="要同步的資料來源模組清單"
    )
    include_pending_reports = models.BooleanField(
        default=False, 
        verbose_name="包含待核准報工",
        help_text="是否包含待核准的報工記錄"
    )
    include_approved_reports = models.BooleanField(
        default=True, 
        verbose_name="包含已核准報工",
        help_text="是否包含已核准的報工記錄"
    )
    
    # 同步設定
    auto_sync = models.BooleanField(
        default=True, 
        verbose_name="自動同步",
        help_text="是否啟用自動同步"
    )
    sync_retention_days = models.IntegerField(
        default=365, 
        verbose_name="資料保留天數",
        help_text="同步資料的保留天數"
    )
    
    # 錯誤處理
    retry_on_failure = models.BooleanField(
        default=True, 
        verbose_name="失敗重試",
        help_text="同步失敗時是否重試"
    )
    max_retry_attempts = models.IntegerField(
        default=3, 
        verbose_name="最大重試次數"
    )
    
    # 系統欄位
    last_sync_time = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="最後同步時間"
    )
    last_sync_status = models.CharField(
        max_length=20, 
        choices=[
            ('success', '成功'),
            ('failed', '失敗'),
            ('partial', '部分成功'),
        ],
        null=True, 
        blank=True, 
        verbose_name="最後同步狀態"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="啟用設定"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "報表同步設定"
        verbose_name_plural = "報表同步設定"
        unique_together = ['sync_type', 'sync_frequency']

    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_sync_frequency_display()} - {self.sync_time}"


class ReportEmailSettings(models.Model):
    """報表郵件通知設定"""
    
    # 報表類型
    REPORT_TYPE_CHOICES = [
        ('work_time', '工作時間報表'),
        ('work_order', '工單機種報表'),
        ('personnel', '人員績效報表'),
        ('equipment', '設備效率報表'),
        ('quality', '品質分析報表'),
        ('comprehensive', '綜合分析報表'),
        ('all', '所有報表'),
    ]
    
    # 發送頻率
    SEND_FREQUENCY_CHOICES = [
        ('daily', '每天'),
        ('weekly', '每週'),
        ('monthly', '每月'),
        ('on_demand', '按需發送'),
    ]
    
    report_type = models.CharField(
        max_length=20, 
        choices=REPORT_TYPE_CHOICES, 
        verbose_name="報表類型"
    )
    send_frequency = models.CharField(
        max_length=10, 
        choices=SEND_FREQUENCY_CHOICES, 
        default='daily', 
        verbose_name="發送頻率"
    )
    send_time = models.TimeField(
        verbose_name="發送時間", 
        help_text="每天發送報表的時間"
    )
    
    # 收件人設定
    recipients = models.TextField(
        verbose_name="收件人郵箱", 
        help_text="多個郵箱請用逗號分隔"
    )
    cc_recipients = models.TextField(
        blank=True, 
        verbose_name="副本收件人", 
        help_text="多個郵箱請用逗號分隔"
    )
    bcc_recipients = models.TextField(
        blank=True, 
        verbose_name="密件副本收件人", 
        help_text="多個郵箱請用逗號分隔"
    )
    
    # 郵件內容設定
    subject_template = models.CharField(
        max_length=200,
        default="MES 系統 - {report_type} - {date}",
        verbose_name="郵件主旨模板",
        help_text="支援 {report_type}、{date}、{company} 等變數"
    )
    email_template = models.TextField(
        blank=True,
        verbose_name="郵件內容模板",
        help_text="支援 HTML 格式，可使用 {report_data}、{summary} 等變數"
    )
    
    # 附件設定
    include_excel = models.BooleanField(
        default=True, 
        verbose_name="包含 Excel 附件"
    )
    include_csv = models.BooleanField(
        default=False, 
        verbose_name="包含 CSV 附件"
    )
    include_pdf = models.BooleanField(
        default=False, 
        verbose_name="包含 PDF 附件"
    )
    
    # 發送設定
    is_active = models.BooleanField(
        default=True, 
        verbose_name="啟用發送"
    )
    auto_send = models.BooleanField(
        default=True, 
        verbose_name="自動發送",
        help_text="是否啟用自動發送"
    )
    
    # 系統欄位
    last_send_time = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="最後發送時間"
    )
    last_send_status = models.CharField(
        max_length=20, 
        choices=[
            ('success', '成功'),
            ('failed', '失敗'),
            ('partial', '部分成功'),
        ],
        null=True, 
        blank=True, 
        verbose_name="最後發送狀態"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "報表郵件設定"
        verbose_name_plural = "報表郵件設定"
        unique_together = ['report_type', 'send_frequency']

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.get_send_frequency_display()} - {self.send_time}"


class ReportDataSyncLog(models.Model):
    """報表資料同步日誌"""
    
    # 同步資訊
    sync_type = models.CharField(max_length=50, verbose_name="同步類型")
    period_start = models.DateField(verbose_name="期間開始")
    period_end = models.DateField(verbose_name="期間結束")
    
    # 同步結果
    status = models.CharField(
        max_length=20, 
        choices=[
            ('success', '成功'),
            ('failed', '失敗'),
            ('partial', '部分成功'),
        ], 
        verbose_name="同步狀態"
    )
    
    # 統計資訊
    records_processed = models.IntegerField(default=0, verbose_name="處理記錄數")
    records_updated = models.IntegerField(default=0, verbose_name="更新記錄數")
    records_created = models.IntegerField(default=0, verbose_name="新增記錄數")
    
    # 錯誤資訊
    error_message = models.TextField(blank=True, verbose_name="錯誤訊息")
    
    # 執行資訊
    started_at = models.DateTimeField(verbose_name="開始時間")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="完成時間")
    duration_seconds = models.IntegerField(default=0, verbose_name="執行時間(秒)")
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    
    class Meta:
        verbose_name = "報表資料同步日誌"
        verbose_name_plural = "報表資料同步日誌"
        db_table = 'system_report_data_sync_log'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.sync_type} - {self.period_start} ~ {self.period_end} - {self.status}"
