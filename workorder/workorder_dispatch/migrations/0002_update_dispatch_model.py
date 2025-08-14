# Generated manually for updating dispatch model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workorder_dispatch', '0001_initial'),
    ]

    operations = [
        # 新增產品名稱欄位
        migrations.AddField(
            model_name='workorderdispatch',
            name='product_name',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='產品名稱'),
        ),
        
        # 新增作業員和設備資訊欄位
        migrations.AddField(
            model_name='workorderdispatch',
            name='assigned_operator',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='分配作業員'),
        ),
        
        migrations.AddField(
            model_name='workorderdispatch',
            name='assigned_equipment',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='分配設備'),
        ),
        
        migrations.AddField(
            model_name='workorderdispatch',
            name='process_name',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='工序名稱'),
        ),
        
        # 新增資料庫索引
        migrations.AddIndex(
            model_name='workorderdispatch',
            index=models.Index(fields=['order_number'], name='workorder_d_order_n_123456_idx'),
        ),
        
        migrations.AddIndex(
            model_name='workorderdispatch',
            index=models.Index(fields=['product_code'], name='workorder_d_product_123456_idx'),
        ),
        
        migrations.AddIndex(
            model_name='workorderdispatch',
            index=models.Index(fields=['status'], name='workorder_d_status_123456_idx'),
        ),
        
        migrations.AddIndex(
            model_name='workorderdispatch',
            index=models.Index(fields=['dispatch_date'], name='workorder_d_dispatch_123456_idx'),
        ),
        
        # 新增歷史記錄模型
        migrations.CreateModel(
            name='DispatchHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=50, verbose_name='操作類型')),
                ('old_status', models.CharField(blank=True, max_length=20, null=True, verbose_name='原狀態')),
                ('new_status', models.CharField(blank=True, max_length=20, null=True, verbose_name='新狀態')),
                ('operator', models.CharField(max_length=100, verbose_name='操作人員')),
                ('notes', models.TextField(blank=True, verbose_name='備註')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='操作時間')),
                ('workorder_dispatch', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='dispatch_history', to='workorder_dispatch.workorderdispatch', verbose_name='派工單')),
            ],
            options={
                'verbose_name': '派工歷史',
                'verbose_name_plural': '派工歷史記錄',
                'db_table': 'workorder_dispatch_history',
                'ordering': ['-created_at'],
            },
        ),
    ] 