# Generated manually to fix operator RD sample records

from django.db import migrations


def fix_operator_rd_sample_records(apps, schema_editor):
    """
    修正作業員補登報工中沒有工單關聯但報工類型為正式報工的記錄
    這些記錄應該被標記為RD樣品
    """
    OperatorSupplementReport = apps.get_model('workorder', 'OperatorSupplementReport')
    
    # 找出所有標記為正式報工但沒有關聯工單的記錄
    inconsistent_records = OperatorSupplementReport.objects.filter(
        report_type='normal',
        workorder__isnull=True
    )
    
    # 將這些記錄修正為RD樣品
    if inconsistent_records.exists():
        updated_count = inconsistent_records.update(
            report_type='rd_sample',
            product_id='RD樣品產品'
        )
        print(f"已修正 {updated_count} 筆作業員補登報工記錄為RD樣品")
        
        # 列出修正的記錄詳細資訊
        for record in inconsistent_records:
            print(f"  - 記錄ID: {record.id}, 作業員: {record.operator.name if record.operator else 'N/A'}, 日期: {record.work_date}")
    else:
        print("沒有發現需要修正的作業員補登報工記錄")


def reverse_fix_operator_rd_sample_records(apps, schema_editor):
    """
    反向操作：將修正的記錄恢復原狀
    """
    OperatorSupplementReport = apps.get_model('workorder', 'OperatorSupplementReport')
    
    # 將所有RD樣品記錄的report_type改回normal
    rd_records = OperatorSupplementReport.objects.filter(
        report_type='rd_sample',
        product_id='RD樣品產品'
    )
    
    updated_count = rd_records.update(
        report_type='normal',
        product_id=''
    )
    
    print(f"已恢復 {updated_count} 筆作業員補登報工記錄")


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0045_update_rd_sample_detection'),
    ]

    operations = [
        migrations.RunPython(
            fix_operator_rd_sample_records,
            reverse_fix_operator_rd_sample_records
        ),
    ] 