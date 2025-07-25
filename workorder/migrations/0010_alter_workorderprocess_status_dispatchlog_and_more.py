# Generated by Django 5.1.8 on 2025-07-14 04:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("process", "0011_operator_production_line_and_more"),
        ("workorder", "0009_remove_workorderprocess_actual_duration_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workorderprocess",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "待生產"),
                    ("in_progress", "生產中"),
                    ("completed", "已完成"),
                    ("paused", "暫停"),
                    ("cancelled", "取消"),
                ],
                default="pending",
                max_length=20,
                verbose_name="狀態",
            ),
        ),
        migrations.CreateModel(
            name="DispatchLog",
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
                    "quantity",
                    models.PositiveIntegerField(default=0, verbose_name="派工數量"),
                ),
                (
                    "created_by",
                    models.CharField(max_length=100, verbose_name="建立人員"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="建立時間"),
                ),
                (
                    "operator",
                    models.ForeignKey(
                        blank=True,
                        help_text="派工時選擇的作業員，可空白",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="process.operator",
                        verbose_name="作業員",
                    ),
                ),
                (
                    "process",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dispatch_logs",
                        to="workorder.workorderprocess",
                        verbose_name="工序",
                    ),
                ),
                (
                    "workorder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dispatch_logs",
                        to="workorder.workorder",
                        verbose_name="工單",
                    ),
                ),
            ],
            options={
                "verbose_name": "派工單記錄",
                "verbose_name_plural": "派工單記錄",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="QuickSupplementLog",
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
                    "product_code",
                    models.CharField(max_length=100, verbose_name="產品編號"),
                ),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("start", "開始"),
                            ("pause", "暫停"),
                            ("resume", "恢復"),
                            ("complete", "完成"),
                        ],
                        max_length=20,
                        verbose_name="動作類型",
                    ),
                ),
                ("supplement_time", models.DateTimeField(verbose_name="補登時間")),
                (
                    "end_time",
                    models.DateTimeField(
                        blank=True,
                        help_text="補登時段的結束時間（可選）",
                        null=True,
                        verbose_name="結束時間",
                    ),
                ),
                (
                    "completed_quantity",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="本次操作完成的數量",
                        verbose_name="本次完成數量",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="補登原因或說明",
                        null=True,
                        verbose_name="備註",
                    ),
                ),
                (
                    "equipment",
                    models.CharField(
                        blank=True,
                        help_text="補登時選擇的設備，SMT工序必填",
                        max_length=100,
                        null=True,
                        verbose_name="設備",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(max_length=100, verbose_name="補登人員"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="補登記錄時間"
                    ),
                ),
                (
                    "is_approved",
                    models.BooleanField(
                        default=False,
                        help_text="管理員核准狀態",
                        verbose_name="是否已核准",
                    ),
                ),
                (
                    "approved_by",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="核准人員"
                    ),
                ),
                (
                    "approved_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="核准時間"
                    ),
                ),
                (
                    "operator",
                    models.ForeignKey(
                        blank=True,
                        help_text="補登時選擇的作業員，可用於自動統計產能",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="process.operator",
                        verbose_name="作業員",
                    ),
                ),
                (
                    "process",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quick_supplement_logs",
                        to="workorder.workorderprocess",
                        verbose_name="工序",
                    ),
                ),
                (
                    "workorder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quick_supplement_logs",
                        to="workorder.workorder",
                        verbose_name="工單",
                    ),
                ),
            ],
            options={
                "verbose_name": "快速補登記錄",
                "verbose_name_plural": "快速補登記錄",
                "ordering": ["-supplement_time", "-created_at"],
            },
        ),
    ]
