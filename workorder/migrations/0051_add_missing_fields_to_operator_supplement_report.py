# Generated by Django 5.1.8 on 2025-07-24 12:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0050_add_completion_method_to_operator_supplement_report"),
    ]

    operations = [
        migrations.AddField(
            model_name="operatorsupplementreport",
            name="auto_completed",
            field=models.BooleanField(
                default=False,
                help_text="系統根據累積數量或工時自動判斷的完工狀態",
                verbose_name="自動完工狀態",
            ),
        ),
        migrations.AddField(
            model_name="operatorsupplementreport",
            name="completion_time",
            field=models.DateTimeField(
                blank=True,
                help_text="系統記錄的完工確認時間",
                null=True,
                verbose_name="完工確認時間",
            ),
        ),
        migrations.AddField(
            model_name="operatorsupplementreport",
            name="cumulative_quantity",
            field=models.IntegerField(
                default=0,
                help_text="此工單在此工序上的累積完成數量",
                verbose_name="累積完成數量",
            ),
        ),
        migrations.AddField(
            model_name="operatorsupplementreport",
            name="cumulative_hours",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="此工單在此工序上的累積工時",
                max_digits=8,
                verbose_name="累積工時",
            ),
        ),
    ]
