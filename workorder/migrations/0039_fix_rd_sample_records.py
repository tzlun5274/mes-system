# Generated manually to fix RD sample records

from django.db import migrations


def fix_rd_sample_records(apps, schema_editor):
    """
    修復現有的 RD樣品記錄，確保 report_type 欄位正確設定
    """
    SMTProductionReport = apps.get_model("workorder", "SMTProductionReport")

    # 找出所有有 rd_workorder_number 但 report_type 不是 'rd_sample' 的記錄
    rd_records = (
        SMTProductionReport.objects.filter(rd_workorder_number__isnull=False)
        .exclude(rd_workorder_number="")
        .exclude(report_type="rd_sample")
    )

    # 更新這些記錄的 report_type 為 'rd_sample'
    updated_count = rd_records.update(report_type="rd_sample")
    print(f"已修復 {updated_count} 筆 RD樣品記錄")


def reverse_fix_rd_sample_records(apps, schema_editor):
    """
    反向操作：將修復的記錄恢復原狀
    """
    SMTProductionReport = apps.get_model("workorder", "SMTProductionReport")

    # 找出所有 report_type 為 'rd_sample' 但沒有 rd_workorder_number 的記錄
    records = SMTProductionReport.objects.filter(report_type="rd_sample").filter(
        rd_workorder_number__isnull=True
    )

    # 將這些記錄的 report_type 改回 'normal'
    updated_count = records.update(report_type="normal")
    print(f"已恢復 {updated_count} 筆記錄")


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0038_alter_smtproductionreport_options_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_rd_sample_records, reverse_fix_rd_sample_records),
    ]
