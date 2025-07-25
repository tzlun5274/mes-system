# Generated by Django 5.1.8 on 2025-06-22 00:59

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AIAnomaly",
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
                    "anomaly_type",
                    models.CharField(
                        choices=[("production", "生產異常"), ("defect", "缺陷檢測")],
                        max_length=50,
                        verbose_name="異常類型",
                    ),
                ),
                (
                    "production_line",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="生產線名稱"
                    ),
                ),
                (
                    "production_rate",
                    models.FloatField(blank=True, null=True, verbose_name="生產速率"),
                ),
                (
                    "product_name",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="產品名稱"
                    ),
                ),
                (
                    "defect_type",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="缺陷類型"
                    ),
                ),
                (
                    "anomaly_detected",
                    models.BooleanField(default=False, verbose_name="是否檢測到異常"),
                ),
                (
                    "anomaly_details",
                    models.CharField(
                        blank=True, max_length=200, verbose_name="異常詳情"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="創建時間"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新時間"),
                ),
            ],
            options={
                "verbose_name": "AI 異常檢測",
                "verbose_name_plural": "AI 異常檢測",
                "permissions": [
                    ("can_view_ai_anomaly", "可以查看 AI 異常檢測"),
                    ("can_run_ai_anomaly", "可以執行 AI 異常檢測"),
                ],
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="AIOperationLog",
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
                ("timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("user", models.CharField(max_length=150)),
                ("action", models.CharField(max_length=255)),
            ],
            options={
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="AIOptimization",
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
                    "optimization_type",
                    models.CharField(
                        choices=[
                            ("production", "生產優化"),
                            ("scheduling", "自動化調度"),
                        ],
                        max_length=50,
                        verbose_name="優化類型",
                    ),
                ),
                (
                    "production_line",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="生產線名稱"
                    ),
                ),
                (
                    "current_capacity",
                    models.FloatField(blank=True, null=True, verbose_name="當前產能"),
                ),
                (
                    "task_name",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="任務名稱"
                    ),
                ),
                (
                    "resource_available",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="可用資源"
                    ),
                ),
                (
                    "optimized_result",
                    models.CharField(
                        blank=True, max_length=200, verbose_name="優化結果"
                    ),
                ),
                (
                    "efficiency_gain",
                    models.FloatField(blank=True, null=True, verbose_name="效率提升"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="創建時間"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新時間"),
                ),
            ],
            options={
                "verbose_name": "AI 優化",
                "verbose_name_plural": "AI 優化",
                "permissions": [
                    ("can_view_ai_optimization", "可以查看 AI 優化"),
                    ("can_run_ai_optimization", "可以執行 AI 優化"),
                ],
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="AIPrediction",
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
                    "prediction_type",
                    models.CharField(
                        choices=[
                            ("production", "生產預測"),
                            ("demand", "需求預測"),
                            ("quality", "品質預測"),
                        ],
                        max_length=50,
                        verbose_name="預測類型",
                    ),
                ),
                (
                    "production_line",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="生產線名稱"
                    ),
                ),
                (
                    "current_output",
                    models.FloatField(blank=True, null=True, verbose_name="當前產量"),
                ),
                (
                    "product_name",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="產品名稱"
                    ),
                ),
                (
                    "historical_demand",
                    models.FloatField(blank=True, null=True, verbose_name="歷史需求量"),
                ),
                (
                    "production_temperature",
                    models.FloatField(blank=True, null=True, verbose_name="生產溫度"),
                ),
                (
                    "production_pressure",
                    models.FloatField(blank=True, null=True, verbose_name="生產壓力"),
                ),
                (
                    "predicted_output",
                    models.FloatField(blank=True, null=True, verbose_name="預測結果"),
                ),
                (
                    "confidence",
                    models.FloatField(blank=True, null=True, verbose_name="信心度"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="創建時間"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新時間"),
                ),
            ],
            options={
                "verbose_name": "AI 預測",
                "verbose_name_plural": "AI 預測",
                "permissions": [
                    ("can_view_ai_prediction", "可以查看 AI 預測"),
                    ("can_run_ai_prediction", "可以執行 AI 預測"),
                ],
                "default_permissions": (),
            },
        ),
    ]
