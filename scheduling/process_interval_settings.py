from django.db import models
from django.utils.translation import gettext_lazy as _


class ProcessIntervalSettings(models.Model):
    process_interval_minutes = models.IntegerField(
        default=5, verbose_name=_("工序間隔時間（分鐘）")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("創建時間"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("更新時間"))

    class Meta:
        verbose_name = _("工序間隔設置")
        verbose_name_plural = _("工序間隔設置")

    def __str__(self):
        return f"工序間隔時間 {self.process_interval_minutes} 分鐘"
