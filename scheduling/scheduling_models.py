from django.db import models
from django.utils.translation import gettext_lazy as _


class Unit(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("單位名稱"))
    work_start = models.TimeField(
        verbose_name=_("上班開始時間"), null=True, blank=True
    )  # 移除 default
    work_end = models.TimeField(
        verbose_name=_("下班時間"), null=True, blank=True
    )  # 移除 default
    has_lunch_break = models.BooleanField(
        default=False, verbose_name=_("是否有中午休息")
    )  # 改為 False
    lunch_start = models.TimeField(
        verbose_name=_("午休開始時間"), null=True, blank=True
    )  # 移除 default
    lunch_end = models.TimeField(
        verbose_name=_("午休結束時間"), null=True, blank=True
    )  # 移除 default
    overtime_start = models.TimeField(
        verbose_name=_("加班開始時間"), null=True, blank=True
    )  # 移除 default
    overtime_end = models.TimeField(
        verbose_name=_("加班結束時間"), null=True, blank=True
    )  # 移除 default
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("創建時間"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("更新時間"))

    class Meta:
        verbose_name = _("單位")
        verbose_name_plural = _("單位")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Event(models.Model):
    unit = models.ForeignKey(
        Unit, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("單位")
    )
    title = models.CharField(max_length=200, verbose_name=_("標題"))
    start = models.DateTimeField(verbose_name=_("開始時間"))
    end = models.DateTimeField(verbose_name=_("結束時間"))
    EVENT_TYPE_CHOICES = [
        ("holiday", _("放假日")),
        ("production", _("生產任務")),
        ("meeting", _("會議")),
        ("maintenance", _("維護")),
        ("workday", _("上班日")),
        ("overtime", _("加班")),
    ]
    type = models.CharField(
        max_length=20, choices=EVENT_TYPE_CHOICES, verbose_name=_("類型")
    )
    description = models.TextField(blank=True, verbose_name=_("描述"))
    classNames = models.CharField(max_length=50, blank=True, verbose_name=_("樣式類別"))
    all_day = models.BooleanField(default=False, verbose_name=_("全天事件"))
    CATEGORY_CHOICES = [
        ("general", _("一般")),
        ("urgent", _("緊急")),
        ("routine", _("例行")),
    ]
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="general",
        verbose_name=_("分類"),
    )
    created_by = models.CharField(max_length=150, verbose_name=_("創建者"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("創建時間"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("更新時間"))
    employee_id = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("作業員ID")
    )
    equipment_id = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("設備ID")
    )
    order_id = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("訂單ID")
    )

    class Meta:
        verbose_name = _("事件")
        verbose_name_plural = _("事件")
        ordering = ["start"]

    def __str__(self):
        return self.title


class ScheduleWarning(models.Model):
    """
    儲存排程驗證警告的資料表
    """

    order_id = models.CharField(max_length=50, verbose_name="訂單編號")
    process_name = models.CharField(max_length=100, verbose_name="工序名稱")
    warning_message = models.TextField(verbose_name="警告內容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="產生時間")

    class Meta:
        verbose_name = "排程警告"
        verbose_name_plural = "排程警告"
        ordering = ["-created_at"]

    def __str__(self):
        return f"訂單{self.order_id} 工序{self.process_name}：{str(self.warning_message)[:20]}..."
