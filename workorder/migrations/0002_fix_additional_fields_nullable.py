# 修復 WorkOrderProcess 模型中 additional_operators 和 additional_equipments 欄位的 NULL 約束
# 功能：將這兩個欄位設定為允許 NULL 值
# 作者：MES 系統
# 建立時間：2024年

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0001_initial'),
    ]

    operations = [
        # 修改 additional_operators 欄位允許 NULL
        migrations.AlterField(
            model_name='workorderprocess',
            name='additional_operators',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name="額外作業員",
                help_text="JSON格式儲存額外作業員清單",
            ),
        ),
        # 修改 additional_equipments 欄位允許 NULL
        migrations.AlterField(
            model_name='workorderprocess',
            name='additional_equipments',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name="額外設備",
                help_text="JSON格式儲存額外設備清單",
            ),
        ),
    ] 