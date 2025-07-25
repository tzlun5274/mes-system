# Generated by Django 5.1.8 on 2025-07-08 07:52

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("material", "0002_materialtransaction_materialinventorymanagement_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialOperationLog",
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
                ("user", models.CharField(max_length=50, verbose_name="操作用戶")),
                ("action", models.CharField(max_length=200, verbose_name="操作內容")),
                (
                    "timestamp",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="操作時間"
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True, verbose_name="備註")),
            ],
            options={
                "verbose_name": "物料操作日誌",
                "verbose_name_plural": "物料操作日誌",
                "ordering": ["-timestamp"],
            },
        ),
    ]
