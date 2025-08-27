# Generated manually to fix table name mismatch

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0007_alter_automanagementconfig_function_type'),
    ]

    operations = [
        migrations.RunSQL(
            # 重命名資料表（添加存在性檢查）
            sql="""
            DO $$
            BEGIN
                -- 檢查並重命名 workorder_auto_management_settings
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'workorder_auto_management_settings') THEN
                    ALTER TABLE workorder_auto_management_settings 
                    RENAME TO workorder_auto_allocation_settings;
                END IF;
                
                -- 檢查並重命名 workorder_auto_management_log
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'workorder_auto_management_log') THEN
                    ALTER TABLE workorder_auto_management_log 
                    RENAME TO workorder_auto_allocation_log;
                END IF;
            END $$;
            """,
            # 回滾操作（添加存在性檢查）
            reverse_sql="""
            DO $$
            BEGIN
                -- 檢查並重命名 workorder_auto_allocation_settings
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'workorder_auto_allocation_settings') THEN
                    ALTER TABLE workorder_auto_allocation_settings 
                    RENAME TO workorder_auto_management_settings;
                END IF;
                
                -- 檢查並重命名 workorder_auto_allocation_log
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'workorder_auto_allocation_log') THEN
                    ALTER TABLE workorder_auto_allocation_log 
                    RENAME TO workorder_auto_management_log;
                END IF;
            END $$;
            """
        ),
    ] 