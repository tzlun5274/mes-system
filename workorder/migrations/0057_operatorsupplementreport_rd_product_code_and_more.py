# Generated by Django 5.1.8 on 2025-07-25 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0056_merge_20250724_2049"),
    ]

    operations = [
        migrations.AddField(
            model_name="operatorsupplementreport",
            name="rd_product_code",
            field=models.CharField(
                blank=True,
                help_text="請輸入RD樣品的產品編號，用於識別具體的RD樣品工序與設備資訊",
                max_length=100,
                null=True,
                verbose_name="RD產品編號",
            ),
        ),
        migrations.AddField(
            model_name="operatorsupplementreport",
            name="rd_workorder_number",
            field=models.CharField(
                blank=True,
                help_text="RD樣品模式的工單號碼",
                max_length=100,
                null=True,
                verbose_name="RD樣品工單號碼",
            ),
        ),
    ]
