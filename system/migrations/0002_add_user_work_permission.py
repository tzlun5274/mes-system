# Generated manually for UserWorkPermission model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserWorkPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operator_codes', models.TextField(blank=True, help_text='可操作的作業員編號，多個用逗號分隔，留空表示可操作所有作業員', verbose_name='作業員編號')),
                ('process_names', models.TextField(blank=True, help_text='可操作的工序名稱，多個用逗號分隔，留空表示可操作所有工序', verbose_name='工序名稱')),
                ('permission_type', models.CharField(choices=[('fill_work', '填報報工'), ('onsite_reporting', '現場報工'), ('both', '填報報工 + 現場報工')], default='both', max_length=20, verbose_name='權限類型')),
                ('is_active', models.BooleanField(default=True, verbose_name='啟用狀態')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='備註')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='work_permissions', to='auth.user', verbose_name='使用者')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_work_permissions', to='auth.user', verbose_name='建立者')),
            ],
            options={
                'verbose_name': '使用者工作權限',
                'verbose_name_plural': '使用者工作權限',
                'db_table': 'system_user_work_permission',
                'unique_together': {('user', 'permission_type')},
            },
        ),
    ] 