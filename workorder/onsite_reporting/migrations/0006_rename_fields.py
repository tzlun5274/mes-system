"""
現場報工模組 - 欄位重命名遷移
將 workorder 欄位重命名為 order_number
將 product_id 欄位重命名為 product_code
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onsite_reporting', '0005_onsitereportsession_and_more'),
    ]

    operations = [
        # 重命名 workorder 欄位為 order_number
        migrations.RenameField(
            model_name='onsitereport',
            old_name='workorder',
            new_name='order_number',
        ),
        # 重命名 product_id 欄位為 product_code
        migrations.RenameField(
            model_name='onsitereport',
            old_name='product_id',
            new_name='product_code',
        ),
    ] 