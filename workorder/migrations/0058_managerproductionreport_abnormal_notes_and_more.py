# Generated by Django 5.1.8 on 2025-07-26 04:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0057_operatorsupplementreport_rd_product_code_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="managerproductionreport",
            name="abnormal_notes",
            field=models.TextField(
                blank=True,
                help_text="記錄生產過程中的異常情況，如設備故障、品質問題等",
                verbose_name="異常記錄",
            ),
        ),
        migrations.AddField(
            model_name="operatorsupplementreport",
            name="abnormal_notes",
            field=models.TextField(
                blank=True,
                help_text="記錄生產過程中的異常情況，如設備故障、品質問題等",
                verbose_name="異常記錄",
            ),
        ),
        migrations.AddField(
            model_name="smtproductionreport",
            name="abnormal_notes",
            field=models.TextField(
                blank=True,
                help_text="記錄生產過程中的異常情況，如設備故障、品質問題等",
                verbose_name="異常記錄",
            ),
        ),
        migrations.AlterField(
            model_name="managerproductionreport",
            name="remarks",
            field=models.TextField(
                blank=True,
                help_text="請輸入任何需要補充的資訊，如設備標記、操作說明等",
                verbose_name="備註",
            ),
        ),
        migrations.AlterField(
            model_name="operatorsupplementreport",
            name="remarks",
            field=models.TextField(
                blank=True,
                help_text="請輸入任何需要補充的資訊，如設備標記、操作說明等",
                verbose_name="備註",
            ),
        ),
        migrations.AlterField(
            model_name="smtproductionreport",
            name="remarks",
            field=models.TextField(
                blank=True,
                help_text="請輸入任何需要補充的資訊，如設備標記、操作說明等",
                verbose_name="備註",
            ),
        ),
    ]
