# Generated by Django 5.1.8 on 2025-07-16 03:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0012_quicksupplementlog_defect_qty"),
    ]

    operations = [
        migrations.DeleteModel(
            name="QuickSupplementLog",
        ),
    ]
