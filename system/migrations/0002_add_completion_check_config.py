# Generated manually for CompletionCheckConfig

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompletionCheckConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=True, help_text='啟用或停用完工檢查定時任務', verbose_name='啟用狀態')),
                ('interval_minutes', models.IntegerField(default=5, help_text='每多少分鐘檢查一次完工狀態', verbose_name='檢查間隔（分鐘）')),
                ('start_time', models.TimeField(default='08:00', help_text='每日開始檢查的時間', verbose_name='開始時間')),
                ('end_time', models.TimeField(default='18:00', help_text='每日結束檢查的時間', verbose_name='結束時間')),
                ('max_workorders_per_check', models.IntegerField(default=100, help_text='每次檢查最多處理多少個工單，避免系統負載過重', verbose_name='每次檢查最大工單數')),
                ('enable_notifications', models.BooleanField(default=True, help_text='工單完工時是否發送通知', verbose_name='啟用通知')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('updated_by', models.CharField(blank=True, max_length=100, null=True, verbose_name='最後更新者')),
            ],
            options={
                'verbose_name': '完工檢查配置',
                'verbose_name_plural': '完工檢查配置',
                'db_table': 'system_completion_check_config',
            },
        ),
    ] 