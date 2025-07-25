# Generated by Django 5.1.8 on 2025-07-22 00:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0036_operatorsupplementreport_rd_project_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="operatorsupplementreport",
            name="rd_sample_name",
            field=models.CharField(
                blank=True,
                help_text="請輸入RD樣品的具體名稱或描述",
                max_length=200,
                null=True,
                verbose_name="樣品名稱",
            ),
        ),
    ]
