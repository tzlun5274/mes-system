# Generated by Django 5.1.8 on 2025-06-26 07:21

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="operatorperformance",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="建立時間"
            ),
        ),
    ]
