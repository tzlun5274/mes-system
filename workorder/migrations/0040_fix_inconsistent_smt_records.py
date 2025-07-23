# Generated manually to fix inconsistent SMT records

from django.db import migrations


def fix_inconsistent_smt_records(apps, schema_editor):
    """
    修正不一致的SMT記錄，確保沒有工單關聯的記錄被標記為RD樣品
    """
    SMTProductionReport = apps.get_model('workorder', 'SMTProductionReport')
    
    # 找出所有標記為正式工單但沒有關聯工單的記錄
    inconsistent_records = SMTProductionReport.objects.filter(
        report_type='normal',
        workorder__isnull=True
    )
    
    # 將這些記錄修正為RD樣品
    if inconsistent_records.exists():
        updated_count = inconsistent_records.update(
            report_type='rd_sample',
            product_id='RD樣品產品'
        )
    else:
        updated_count = 0
    
    print(f"已修正 {updated_count} 筆不一致的SMT記錄為RD樣品")


def reverse_fix_inconsistent_smt_records(apps, schema_editor):
    """
    反向操作：將修正的記錄恢復原狀
    """
    SMTProductionReport = apps.get_model('workorder', 'SMTProductionReport')
    
    # 將所有RD樣品記錄的report_type改回normal
    rd_records = SMTProductionReport.objects.filter(
        report_type='rd_sample',
        product_id='RD樣品產品'
    )
    
    updated_count = rd_records.update(
        report_type='normal',
        product_id=''
    )
    
    print(f"已恢復 {updated_count} 筆RD樣品記錄")


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0039_fix_rd_sample_records'),
    ]

    operations = [
        migrations.RunPython(
            fix_inconsistent_smt_records,
            reverse_fix_inconsistent_smt_records
        ),
    ] 