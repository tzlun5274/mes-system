# Generated manually to remove supervisor production report table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0070_add_missing_fields_to_production_detail'),
    ]

    operations = [
        # 移除主管報工資料表，避免與主管審核功能混淆
        migrations.DeleteModel(
            name='SupervisorProductionReport',
        ),
    ] 