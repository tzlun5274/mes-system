"""
更新 CompletedWorkOrderAnalysis 的唯一約束
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0012_remove_completed_workorder_report_data'),
    ]

    operations = [
        # 移除舊的唯一約束
        migrations.AlterUniqueTogether(
            name='completedworkorderanalysis',
            unique_together=set(),
        ),
        # 添加新的唯一約束（包含 product_code）
        migrations.AlterUniqueTogether(
            name='completedworkorderanalysis',
            unique_together={('workorder_id', 'company_code', 'product_code')},
        ),
    ]
