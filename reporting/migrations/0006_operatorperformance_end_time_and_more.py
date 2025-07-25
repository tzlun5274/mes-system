# Generated by Django 5.1.8 on 2025-07-04 11:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0005_reportsyncsettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="operatorperformance",
            name="end_time",
            field=models.DateTimeField(blank=True, null=True, verbose_name="結束時間"),
        ),
        migrations.AddField(
            model_name="operatorperformance",
            name="product_name",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="產品名稱"
            ),
        ),
        migrations.AddField(
            model_name="operatorperformance",
            name="start_time",
            field=models.DateTimeField(blank=True, null=True, verbose_name="開始時間"),
        ),
        migrations.AddField(
            model_name="operatorperformance",
            name="work_order",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="工單"
            ),
        ),
        migrations.CreateModel(
            name="ReportEmailSchedule",
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
                    "report_type",
                    models.CharField(
                        choices=[
                            ("smt", "SMT生產報表"),
                            ("operator", "作業員生產報表"),
                            ("production_daily", "生產日報表"),
                            ("all", "所有報表"),
                        ],
                        max_length=20,
                        verbose_name="報表類型",
                    ),
                ),
                (
                    "schedule_type",
                    models.CharField(
                        choices=[
                            ("daily", "每天"),
                            ("weekly", "每週"),
                            ("monthly", "每月"),
                        ],
                        default="daily",
                        max_length=10,
                        verbose_name="發送頻率",
                    ),
                ),
                (
                    "send_time",
                    models.TimeField(
                        help_text="每天發送報表的時間", verbose_name="發送時間"
                    ),
                ),
                (
                    "recipients",
                    models.TextField(
                        help_text="多個郵箱請用逗號分隔", verbose_name="收件人郵箱"
                    ),
                ),
                (
                    "cc_recipients",
                    models.TextField(
                        blank=True,
                        help_text="多個郵箱請用逗號分隔",
                        verbose_name="副本收件人",
                    ),
                ),
                (
                    "subject_template",
                    models.CharField(
                        default="MES 系統 - {report_type} - {date}",
                        max_length=200,
                        verbose_name="郵件主旨模板",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="啟用發送"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="創建時間"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新時間"),
                ),
            ],
            options={
                "verbose_name": "報表郵件發送設定",
                "verbose_name_plural": "報表郵件發送設定",
                "unique_together": {("report_type", "schedule_type")},
            },
        ),
        migrations.CreateModel(
            name="ReportEmailLog",
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
                    "report_type",
                    models.CharField(max_length=20, verbose_name="報表類型"),
                ),
                ("recipients", models.TextField(verbose_name="收件人")),
                ("subject", models.CharField(max_length=200, verbose_name="郵件主旨")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("success", "發送成功"),
                            ("failed", "發送失敗"),
                            ("pending", "等待發送"),
                        ],
                        default="pending",
                        max_length=10,
                        verbose_name="發送狀態",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, verbose_name="錯誤訊息"),
                ),
                (
                    "sent_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="發送時間"),
                ),
                (
                    "schedule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.reportemailschedule",
                        verbose_name="發送設定",
                    ),
                ),
            ],
            options={
                "verbose_name": "報表郵件發送記錄",
                "verbose_name_plural": "報表郵件發送記錄",
                "ordering": ["-sent_at"],
            },
        ),
    ]
