from django.db import models
from django.utils import timezone


class ERPConfig(models.Model):
    server = models.CharField(
        max_length=100, blank=True, default="", verbose_name="MSSQL 伺服器地址"
    )
    username = models.CharField(
        max_length=100, blank=True, default="", verbose_name="使用者名稱"
    )
    password = models.CharField(
        max_length=100, blank=True, default="", verbose_name="密碼"
    )
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最後更新時間")

    class Meta:
        verbose_name = "ERP 連線設定"
        verbose_name_plural = "ERP 連線設定"

    def __str__(self):
        return f"ERP 連線設定 - {self.server}"


class CompanyConfig(models.Model):
    company_name = models.CharField(max_length=100, verbose_name="公司名稱")
    company_code = models.CharField(max_length=50, verbose_name="公司編號")
    database = models.CharField(
        max_length=100, blank=True, default="", verbose_name="資料庫名稱"
    )
    mssql_database = models.CharField(
        max_length=100, blank=True, default="", verbose_name="MSSQL 資料庫名稱"
    )
    mes_database = models.CharField(
        max_length=100, blank=True, default="", verbose_name="MES 資料庫名稱"
    )
    notes = models.TextField(blank=True, default="", verbose_name="備註")
    sync_tables = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="需要同步的 MSSQL 資料表（逗號分隔，可選）",
    )
    last_sync_version = models.BigIntegerField(
        null=True, blank=True, verbose_name="公司最後同步版本"
    )
    last_sync_time = models.DateTimeField(
        null=True, blank=True, verbose_name="最後同步時間"
    )
    sync_interval_minutes = models.IntegerField(
        default=0, verbose_name="自動同步間隔（分鐘，0表示禁用）"
    )

    class Meta:
        verbose_name = "公司設定"
        verbose_name_plural = "公司設定"

    def __str__(self):
        return f"公司設定 - {self.company_name}"


class ERPIntegrationOperationLog(models.Model):
    user = models.CharField(max_length=150, verbose_name="操作者")
    action = models.CharField(max_length=1000, verbose_name="操作描述")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="操作時間")

    class Meta:
        verbose_name = "操作日誌"
        verbose_name_plural = "操作日誌"
        default_permissions = ()  # 禁用默認權限

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
