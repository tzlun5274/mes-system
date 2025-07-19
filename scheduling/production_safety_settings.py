from django.db import models
from django.utils.translation import gettext_lazy as _

class ProductionSafetySettings(models.Model):
    delivery_to_completion_safety_days = models.IntegerField(default=3, verbose_name=_("預定出貨日到完工日安全天數（天）"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("創建時間"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("更新時間"))

    class Meta:
        verbose_name = _("生產安全設置")
        verbose_name_plural = _("生產安全設置")

    def __str__(self):
        return f"預定出貨日到完工日安全天數 {self.delivery_to_completion_safety_days} 天"
