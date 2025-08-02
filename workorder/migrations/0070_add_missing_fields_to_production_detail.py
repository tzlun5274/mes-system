# Generated manually to add missing fields from report tables to WorkOrderProductionDetail

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0069_add_original_report_fields'),
    ]

    operations = [
        # 工時資訊欄位
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='work_hours',
            field=models.FloatField(default=0.0, verbose_name='工作時數'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='overtime_hours',
            field=models.FloatField(default=0.0, verbose_name='加班時數'),
        ),
        
        # 休息時間相關欄位
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='has_break',
            field=models.BooleanField(default=False, verbose_name='是否有休息時間'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='break_start_time',
            field=models.TimeField(blank=True, null=True, verbose_name='休息開始時間'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='break_end_time',
            field=models.TimeField(blank=True, null=True, verbose_name='休息結束時間'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='break_hours',
            field=models.FloatField(default=0.0, verbose_name='休息時數'),
        ),
        
        # 報工類型欄位
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='report_type',
            field=models.CharField(default='normal', max_length=20, verbose_name='報工類型'),
        ),
        
        # 數量相關欄位
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='allocated_quantity',
            field=models.IntegerField(default=0, verbose_name='分配數量'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='quantity_source',
            field=models.CharField(default='original', max_length=20, verbose_name='數量來源'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='allocation_notes',
            field=models.TextField(blank=True, verbose_name='分配說明'),
        ),
        
        # 完工相關欄位
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='is_completed',
            field=models.BooleanField(default=False, verbose_name='是否已完工'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='completion_method',
            field=models.CharField(default='manual', max_length=20, verbose_name='完工判斷方式'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='auto_completed',
            field=models.BooleanField(default=False, verbose_name='自動完工狀態'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='completion_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='完工確認時間'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='cumulative_quantity',
            field=models.IntegerField(default=0, verbose_name='累積完成數量'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='cumulative_hours',
            field=models.FloatField(default=0.0, verbose_name='累積工時'),
        ),
        
        # 核准相關欄位
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='approval_status',
            field=models.CharField(default='approved', max_length=20, verbose_name='核准狀態'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='approved_by',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='核准人員'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='核准時間'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='approval_remarks',
            field=models.TextField(blank=True, verbose_name='核准備註'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='rejection_reason',
            field=models.TextField(blank=True, verbose_name='駁回原因'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='rejected_by',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='駁回人員'),
        ),
        migrations.AddField(
            model_name='workorderproductiondetail',
            name='rejected_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='駁回時間'),
        ),
    ] 