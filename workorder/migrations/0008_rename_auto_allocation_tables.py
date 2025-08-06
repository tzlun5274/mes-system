# Generated manually to fix table name mismatch

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0007_alter_automanagementconfig_function_type'),
    ]

    operations = [
        migrations.RunSQL(
            # 重命名資料表
            sql="""
            ALTER TABLE workorder_auto_management_settings 
            RENAME TO workorder_auto_allocation_settings;
            
            ALTER TABLE workorder_auto_management_log 
            RENAME TO workorder_auto_allocation_log;
            """,
            # 回滾操作
            reverse_sql="""
            ALTER TABLE workorder_auto_allocation_settings 
            RENAME TO workorder_auto_management_settings;
            
            ALTER TABLE workorder_auto_allocation_log 
            RENAME TO workorder_auto_management_log;
            """
        ),
    ] 