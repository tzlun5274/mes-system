# Generated manually for SMTProductionReport model

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("equip", "0001_initial"),
        ("workorder", "0022_merge_20250719_1452"),
    ]

    operations = [
        migrations.CreateModel(
            name="SMTProductionReport",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "report_time",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="報工時間"
                    ),
                ),
                ("quantity", models.IntegerField(verbose_name="報工數量")),
                (
                    "hours",
                    models.DecimalField(
                        decimal_places=2,
                        default=0.0,
                        max_digits=5,
                        verbose_name="工作時數",
                    ),
                ),
                (
                    "production_status",
                    models.CharField(
                        choices=[
                            ("start", "開始生產"),
                            ("pause", "暫停"),
                            ("complete", "完工"),
                        ],
                        max_length=10,
                        verbose_name="報工狀態",
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="備註說明")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="建立時間"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新時間"),
                ),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="equip.equipment",
                        verbose_name="設備",
                    ),
                ),
                (
                    "workorder",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="workorder.workorder",
                        verbose_name="工單",
                    ),
                ),
            ],
            options={
                "verbose_name": "SMT 報工記錄",
                "verbose_name_plural": "SMT 報工記錄",
                "db_table": "workorder_smt_production_report",
                "ordering": ["-report_time"],
            },
        ),
    ]
