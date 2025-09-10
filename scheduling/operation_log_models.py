from django.db import models
from django.utils import timezone


class SchedulingOperationLog(models.Model):
    """
    排程操作日誌模型，記錄每次排程操作的基本資訊與細節
    """

    timestamp = models.DateTimeField(default=timezone.now, verbose_name="時間戳")
    user = models.CharField(
        max_length=150, 
        verbose_name="用戶",
        help_text="用戶名稱（非外鍵關係，純文字欄位）"
    )
    action = models.CharField(max_length=255, verbose_name="操作")
    event_related_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="關聯事件ID")
    event_related_title = models.CharField(max_length=200, null=True, blank=True, verbose_name="關聯事件標題")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="IP 地址"
    )
    details = models.TextField(blank=True, null=True, verbose_name="細節")

    class Meta:
        default_permissions = ()  # 禁用默認權限
        verbose_name = "排程操作日誌"
        verbose_name_plural = "排程操作日誌"

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"
