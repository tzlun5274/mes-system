from django.db import models
from django.utils import timezone


class ProductionDailyReport(models.Model):
    date = models.DateField(verbose_name="日期")
    operator_name = models.CharField(
        max_length=100, verbose_name="作業員姓名", default="未指定作業員"
    )
    equipment_name = models.CharField(
        max_length=100, verbose_name="設備名稱", default="未分配設備"
    )
    line = models.CharField(
        max_length=50,
        verbose_name="生產線",
        choices=[
            ("SMT1", "SMT 線 1"),
            ("SMT2", "SMT 線 2"),
            ("SMT3", "SMT 線 3"),
            ("TEST", "測試設備"),
        ],
    )
    production_quantity = models.IntegerField(verbose_name="生產數量")
    completed_quantity = models.IntegerField(verbose_name="完成數量")
    completion_rate = models.FloatField(verbose_name="完成率 (%)")
    work_hours = models.FloatField(default=0.0, verbose_name="工作時數")
    efficiency_rate = models.FloatField(default=0.0, verbose_name="效率 (%)")
    process_name = models.CharField(
        max_length=100, verbose_name="工序名稱", default="", blank=True
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "生產日報表數據"
        verbose_name_plural = "生產日報表數據"
        unique_together = [["date", "operator_name", "equipment_name"]]

    def __str__(self):
        return f"{self.date} - {self.operator_name} - {self.equipment_name}"

    @classmethod
    def calculate_from_supplement_logs(cls, date, operator_name=None):
        """
        從補登記錄計算指定日期和作業員的生產數量
        """
        # 取得該日期所有已核准的補登記錄
        supplement_logs = WorkOrderProcessSupplementLog.objects.filter(
            supplement_time__date=date, is_approved=True, action_type="complete"
        )

        # 如果指定作業員，則篩選該作業員的記錄
        if operator_name:
            supplement_logs = supplement_logs.filter(operator__name=operator_name)

        # 按作業員分組計算
        operator_stats = {}

        for log in supplement_logs:
            operator_name = log.operator.name if log.operator else "未指定作業員"
            equipment_name = log.workorder_process.assigned_equipment or "未分配設備"

            # 判斷生產線
            line = "SMT1"
            if "SMT1" in equipment_name:
                line = "SMT1"
            elif "SMT2" in equipment_name:
                line = "SMT2"
            elif "SMT3" in equipment_name:
                line = "SMT3"
            elif "TEST" in equipment_name:
                line = "TEST"

            if operator_name not in operator_stats:
                operator_stats[operator_name] = {
                    "equipment_name": equipment_name,
                    "line": line,
                    "completed_quantity": 0,
                    "work_hours": 0,
                    "logs": [],
                }

            operator_stats[operator_name][
                "completed_quantity"
            ] += log.completed_quantity
            operator_stats[operator_name]["logs"].append(log)

            # 計算工作時數
            if log.end_time and log.supplement_time:
                duration = log.end_time - log.supplement_time
                operator_stats[operator_name]["work_hours"] += (
                    duration.total_seconds() / 3600
                )

        # 更新或建立報表記錄
        for operator_name, stats in operator_stats.items():
            # 計算效率（每小時產出）
            efficiency = 0
            if stats["work_hours"] > 0:
                efficiency = (stats["completed_quantity"] / stats["work_hours"]) * 100

            report, created = cls.objects.update_or_create(
                date=date,
                operator_name=operator_name,
                equipment_name=stats["equipment_name"],
                defaults={
                    "line": stats["line"],
                    "production_quantity": 0,  # 計劃數量，可從工序取得
                    "completed_quantity": stats["completed_quantity"],
                    "completion_rate": (
                        100.0 if stats["completed_quantity"] > 0 else 0.0
                    ),
                    "work_hours": round(stats["work_hours"], 2),
                    "efficiency_rate": round(efficiency, 2),
                },
            )

        return operator_stats


class OperatorPerformance(models.Model):
    # 作業員名稱
    operator_name = models.CharField(max_length=100, verbose_name="作業員名稱")
    # 設備名稱
    equipment_name = models.CharField(max_length=100, verbose_name="設備名稱")
    # 生產數量
    production_quantity = models.IntegerField(verbose_name="生產數量")
    # 設備使用率
    equipment_usage_rate = models.FloatField(verbose_name="設備使用率 (%)")
    # 工單（新增）
    work_order = models.CharField(
        max_length=100, verbose_name="工單", default="", blank=True
    )
    # 產品名稱（新增）
    product_name = models.CharField(
        max_length=100, verbose_name="產品名稱", default="", blank=True
    )
    # 開始時間（新增）
    start_time = models.DateTimeField(verbose_name="開始時間", null=True, blank=True)
    # 結束時間（新增）
    end_time = models.DateTimeField(verbose_name="結束時間", null=True, blank=True)
    # 日期
    date = models.DateField(verbose_name="日期")
    # 工序名稱（新增）
    process_name = models.CharField(
        max_length=100, verbose_name="工序名稱", default="", blank=True
    )
    # 建立時間
    created_at = models.DateTimeField(default=timezone.now, verbose_name="建立時間")
    # 更新時間
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "作業員生產報表數據"
        verbose_name_plural = "作業員生產報表數據"

    def __str__(self):
        return f"{self.operator_name} - {self.equipment_name} - {self.date}"


class ReportingOperationLog(models.Model):
    user = models.CharField(max_length=100, verbose_name="用戶")
    action = models.TextField(verbose_name="操作")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="時間戳")

    class Meta:
        verbose_name = "報表操作日誌"
        verbose_name_plural = "報表操作日誌"
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"


class ReportSyncSettings(models.Model):
    """
    報表同步間隔設定模型
    用於設定SMT生產報表和作業員生產報表的自動同步間隔
    """

    REPORT_TYPE_CHOICES = [
        ("smt", "SMT生產報表"),
        ("operator", "作業員生產報表"),
    ]

    report_type = models.CharField(
        max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name="報表類型", unique=True
    )
    sync_interval_hours = models.IntegerField(
        default=24,
        verbose_name="同步間隔（小時）",
        help_text="設定自動同步的間隔時間，單位為小時",
    )
    is_active = models.BooleanField(default=True, verbose_name="啟用自動同步")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "報表同步設定"
        verbose_name_plural = "報表同步設定"

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.sync_interval_hours}小時"

    @classmethod
    def get_sync_interval(cls, report_type):
        """
        取得指定報表類型的同步間隔設定
        """
        try:
            setting = cls.objects.get(report_type=report_type, is_active=True)
            return setting.sync_interval_hours
        except cls.DoesNotExist:
            # 如果沒有設定，返回預設值24小時
            return 24


class ReportEmailSchedule(models.Model):
    """
    報表郵件發送排程設定模型
    用於設定每天自動發送報表給相關人員
    """

    REPORT_TYPE_CHOICES = [
        ("smt", "SMT生產報表"),
        ("operator", "作業員生產報表"),
        ("production_daily", "生產日報表"),
        ("all", "所有報表"),
    ]

    SCHEDULE_CHOICES = [
        ("daily", "每天"),
        ("weekly", "每週"),
        ("monthly", "每月"),
    ]

    report_type = models.CharField(
        max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name="報表類型"
    )
    schedule_type = models.CharField(
        max_length=10,
        choices=SCHEDULE_CHOICES,
        default="daily",
        verbose_name="發送頻率",
    )
    send_time = models.TimeField(
        verbose_name="發送時間", help_text="每天發送報表的時間"
    )
    recipients = models.TextField(
        verbose_name="收件人郵箱", help_text="多個郵箱請用逗號分隔"
    )
    cc_recipients = models.TextField(
        blank=True, verbose_name="副本收件人", help_text="多個郵箱請用逗號分隔"
    )
    subject_template = models.CharField(
        max_length=200,
        default="MES 系統 - {report_type} - {date}",
        verbose_name="郵件主旨模板",
    )
    is_active = models.BooleanField(default=True, verbose_name="啟用發送")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "報表郵件發送設定"
        verbose_name_plural = "報表郵件發送設定"
        unique_together = [["report_type", "schedule_type"]]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.get_schedule_type_display()} - {self.send_time}"

    def get_recipient_list(self):
        """取得收件人列表"""
        if not self.recipients:
            return []
        return [email.strip() for email in self.recipients.split(",") if email.strip()]

    def get_cc_list(self):
        """取得副本收件人列表"""
        if not self.cc_recipients:
            return []
        return [
            email.strip() for email in self.cc_recipients.split(",") if email.strip()
        ]


class ReportEmailLog(models.Model):
    """
    報表郵件發送記錄模型
    記錄每次報表郵件發送的詳細資訊
    """

    STATUS_CHOICES = [
        ("success", "發送成功"),
        ("failed", "發送失敗"),
        ("pending", "等待發送"),
    ]

    schedule = models.ForeignKey(
        ReportEmailSchedule, on_delete=models.CASCADE, verbose_name="發送設定"
    )
    report_type = models.CharField(max_length=20, verbose_name="報表類型")
    recipients = models.TextField(verbose_name="收件人")
    subject = models.CharField(max_length=200, verbose_name="郵件主旨")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="發送狀態",
    )
    error_message = models.TextField(blank=True, verbose_name="錯誤訊息")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="發送時間")

    class Meta:
        verbose_name = "報表郵件發送記錄"
        verbose_name_plural = "報表郵件發送記錄"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.report_type} - {self.status} - {self.sent_at}"


class ManufacturingWorkHour(models.Model):
    """
    製造工時單模型，對應 Excel 匯入欄位
    """

    operator = models.CharField(max_length=50, verbose_name="作業員")
    company = models.CharField(max_length=50, verbose_name="公司別")
    date = models.DateField(verbose_name="日期")
    start_time = models.CharField(max_length=10, verbose_name="開始時間")
    end_time = models.CharField(max_length=10, verbose_name="完成時間")
    order_number = models.CharField(max_length=50, verbose_name="製令號碼")
    equipment_name = models.CharField(max_length=100, verbose_name="機種名稱")
    work_content = models.CharField(max_length=100, verbose_name="工作內容")
    good_qty = models.IntegerField(verbose_name="良品數量（只填數字）")
    defect_qty = models.IntegerField(verbose_name="不良品數量（沒有請填0）")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="建立時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "製造工時單"
        verbose_name_plural = "製造工時單"

    def __str__(self):
        return f"{self.date} {self.operator} {self.order_number}"
