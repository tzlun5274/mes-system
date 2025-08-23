# Generated manually for creating company order tables

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company_order', '0002_alter_companyorder_unique_together'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_code', models.CharField(max_length=10, verbose_name='公司代號')),
                ('mkordno', models.CharField(max_length=50, verbose_name='製令單號')),
                ('product_id', models.CharField(max_length=100, verbose_name='產品編號')),
                ('prodt_qty', models.PositiveIntegerField(verbose_name='生產數量')),
                ('est_take_mat_date', models.CharField(max_length=20, verbose_name='預定開工日')),
                ('est_stock_out_date', models.CharField(max_length=20, verbose_name='預定出貨日')),
                ('sync_time', models.DateTimeField(auto_now=True, verbose_name='同步時間')),
                ('complete_status', models.IntegerField(blank=True, null=True, verbose_name='完工狀態')),
                ('bill_status', models.IntegerField(blank=True, null=True, verbose_name='單況')),
                ('is_converted', models.BooleanField(default=False, verbose_name='是否已轉換成工單')),
                ('flag', models.IntegerField(blank=True, null=True, verbose_name='ERP狀態Flag')),
                ('mkord_date', models.CharField(blank=True, max_length=20, null=True, verbose_name='製令日期')),
                ('make_type', models.CharField(blank=True, max_length=20, null=True, verbose_name='製令類型')),
                ('producer', models.CharField(blank=True, max_length=20, null=True, verbose_name='生產人員')),
                ('functionary', models.CharField(blank=True, max_length=20, null=True, verbose_name='負責人')),
                ('remark', models.TextField(blank=True, null=True, verbose_name='備註')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
            ],
            options={
                'verbose_name': '公司製令單',
                'verbose_name_plural': '公司製令單',
                'db_table': 'workorder_company_order',
                'ordering': ['-est_stock_out_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CompanyOrderSystemConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=50, unique=True, verbose_name='設定名稱')),
                ('value', models.CharField(max_length=100, verbose_name='設定值')),
                ('description', models.TextField(blank=True, verbose_name='設定說明')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
            ],
            options={
                'verbose_name': '公司製令單系統設定',
                'verbose_name_plural': '公司製令單系統設定',
                'db_table': 'workorder_company_order_systemconfig',
                'ordering': ['key'],
            },
        ),
        migrations.AddIndex(
            model_name='companyorder',
            index=models.Index(fields=['company_code'], name='workorder_company_order_company_code_idx'),
        ),
        migrations.AddIndex(
            model_name='companyorder',
            index=models.Index(fields=['mkordno'], name='workorder_company_order_mkordno_idx'),
        ),
        migrations.AddIndex(
            model_name='companyorder',
            index=models.Index(fields=['product_id'], name='workorder_company_order_product_id_idx'),
        ),
        migrations.AddIndex(
            model_name='companyorder',
            index=models.Index(fields=['complete_status'], name='workorder_company_order_complete_status_idx'),
        ),
        migrations.AddIndex(
            model_name='companyorder',
            index=models.Index(fields=['bill_status'], name='workorder_company_order_bill_status_idx'),
        ),
        migrations.AddIndex(
            model_name='companyorder',
            index=models.Index(fields=['is_converted'], name='workorder_company_order_is_converted_idx'),
        ),
        migrations.AddIndex(
            model_name='companyorder',
            index=models.Index(fields=['est_stock_out_date'], name='workorder_company_order_est_stock_out_date_idx'),
        ),
        migrations.AddIndex(
            model_name='companyorder',
            index=models.Index(fields=['sync_time'], name='workorder_company_order_sync_time_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='companyorder',
            unique_together={('company_code', 'mkordno', 'product_id')},
        ),
    ]
