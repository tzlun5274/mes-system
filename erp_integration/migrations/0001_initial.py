# Generated by Django 5.1.8 on 2025-06-22 00:59

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CompanyConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "company_name",
                    models.CharField(max_length=100, verbose_name="公司名稱"),
                ),
                (
                    "company_code",
                    models.CharField(max_length=50, verbose_name="公司編號"),
                ),
                (
                    "database",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="資料庫名稱",
                    ),
                ),
                (
                    "mssql_database",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="MSSQL 資料庫名稱",
                    ),
                ),
                (
                    "mes_database",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="MES 資料庫名稱",
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, default="", verbose_name="備註"),
                ),
                (
                    "sync_tables",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=500,
                        verbose_name="需要同步的 MSSQL 資料表（逗號分隔，可選）",
                    ),
                ),
                (
                    "last_sync_version",
                    models.BigIntegerField(
                        blank=True, null=True, verbose_name="公司最後同步版本"
                    ),
                ),
                (
                    "last_sync_time",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="最後同步時間"
                    ),
                ),
                (
                    "sync_interval_minutes",
                    models.IntegerField(
                        default=0, verbose_name="自動同步間隔（分鐘，0表示禁用）"
                    ),
                ),
            ],
            options={
                "verbose_name": "公司設定",
                "verbose_name_plural": "公司設定",
            },
        ),
        migrations.CreateModel(
            name="ERPConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "server",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="MSSQL 伺服器地址",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=100,
                        verbose_name="使用者名稱",
                    ),
                ),
                (
                    "password",
                    models.CharField(
                        blank=True, default="", max_length=100, verbose_name="密碼"
                    ),
                ),
                (
                    "last_updated",
                    models.DateTimeField(auto_now=True, verbose_name="最後更新時間"),
                ),
            ],
            options={
                "verbose_name": "ERP 連線設定",
                "verbose_name_plural": "ERP 連線設定",
            },
        ),
        migrations.CreateModel(
            name="ERPIntegrationOperationLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("user", models.CharField(max_length=150, verbose_name="操作者")),
                ("action", models.CharField(max_length=1000, verbose_name="操作描述")),
                (
                    "timestamp",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="操作時間"
                    ),
                ),
            ],
            options={
                "verbose_name": "操作日誌",
                "verbose_name_plural": "操作日誌",
                "default_permissions": (),
            },
        ),
    ]
