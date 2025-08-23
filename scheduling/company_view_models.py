from django.db import models
from django.utils.translation import gettext_lazy as _


class CompanyView(models.Model):
    company_name = models.CharField(max_length=100, verbose_name=_("公司名稱"))
    mes_database = models.CharField(max_length=100, verbose_name=_("MES資料庫名稱"))
    sync_database = models.TextField(verbose_name=_("要同步的資料庫名稱"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("創建時間"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("更新時間"))

    class Meta:
        verbose_name = _("公司檢視")
        verbose_name_plural = _("公司檢視")
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name
