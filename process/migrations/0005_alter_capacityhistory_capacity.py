# Generated by Django 5.1.8 on 2025-07-02 04:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("process", "0004_alter_productprocessstandardcapacity_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="capacityhistory",
            name="capacity",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="history",
                to="process.productprocessstandardcapacity",
            ),
        ),
    ]
