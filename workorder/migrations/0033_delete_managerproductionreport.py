# Generated by Django 5.1.8 on 2025-07-21 08:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workorder", "0032_alter_operatorsupplementreport_approval_status_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ManagerProductionReport",
        ),
    ]
