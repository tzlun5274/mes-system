# Generated manually to remove SupervisorProductionReport model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workorder_reporting', '0001_initial'),
    ]

    operations = [
        # 移除主管報工資料表，避免與主管審核功能混淆
        migrations.DeleteModel(
            name='SupervisorProductionReport',
        ),
    ] 