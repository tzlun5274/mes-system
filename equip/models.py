from django.db import models
from django.utils import timezone


class Equipment(models.Model):
    """
    設備模型 - 定義工廠的機台資訊
    包含：設備名稱、型號、狀態、所屬產線
    """

    # 設備狀態選項
    STATUS_CHOICES = [
        ("idle", "閒置"),
        ("running", "運轉中"),
        ("maintenance", "維修"),
    ]

    # 基本資訊
    name = models.CharField(max_length=100, unique=True, verbose_name="設備名稱")
    model = models.CharField(max_length=100, blank=True, verbose_name="型號")

    # 狀態資訊
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="idle", verbose_name="設備狀態"
    )

    # 所屬產線
    production_line = models.ForeignKey(
        "production.ProductionLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="所屬產線",
        help_text="此設備所屬的生產線",
    )

    # 時間戳記
    created_at = models.DateTimeField(default=timezone.now, verbose_name="創建時間")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新時間")

    class Meta:
        verbose_name = "設備"
        verbose_name_plural = "設備"
        permissions = [
            ("can_view_equipment", "可以查看設備"),
            ("can_add_equipment", "可以添加設備"),
            ("can_edit_equipment", "可以編輯設備"),
            ("can_delete_equipment", "可以刪除設備"),
        ]
        ordering = ["name"]

    def __str__(self):
        line_name = (
            f" - {self.production_line.line_name}" if self.production_line else ""
        )
        return f"{self.name} ({self.get_status_display()}{line_name})"


class EquipOperationLog(models.Model):
    """
    設備操作日誌 - 記錄設備狀態變更
    """

    timestamp = models.DateTimeField(default=timezone.now, verbose_name="時間")
    user = models.CharField(max_length=150, verbose_name="用戶")
    action = models.CharField(max_length=255, verbose_name="操作")

    class Meta:
        verbose_name = "設備操作日誌"
        verbose_name_plural = "設備操作日誌"
        permissions = [
            ("can_view_equipoperationlog", "可以查看設備操作日誌"),
            ("can_add_equipoperationlog", "可以添加設備操作日誌"),
            ("can_edit_equipoperationlog", "可以編輯設備操作日誌"),
            ("can_delete_equipoperationlog", "可以刪除設備操作日誌"),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"
