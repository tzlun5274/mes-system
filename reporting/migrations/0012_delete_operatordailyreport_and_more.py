# Generated by Django 5.1.8 on 2025-07-06 06:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0011_remove_shift_rework_operator_id_fields"),
    ]

    operations = [
        migrations.DeleteModel(
            name="OperatorDailyReport",
        ),
        migrations.DeleteModel(
            name="OperatorMonthlyReport",
        ),
        migrations.DeleteModel(
            name="OperatorScoreReport",
        ),
    ]
